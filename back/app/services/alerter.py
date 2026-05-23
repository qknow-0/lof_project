"""定时告警服务：拉取 LOF 数据 → 筛选 → 格式化 → 推送"""
import concurrent.futures
import json
import logging

import pandas as pd
import requests

from app.config import settings
from app.services.fetcher import fetch_spot_data, fetch_purchase_data, fetch_estimate_data
from app.utils.formatters import format_limit, format_amount

logger = logging.getLogger(__name__)

NOTIFY_PATH = "/api/v1/notify"


def fetch_and_filter() -> list[dict]:
    """拉取 LOF 实时数据，筛选 估算溢价率>0 且 成交额>100万，
    按估算溢价率降序取前 N 条，返回格式化后的 dict 列表。"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_spot = executor.submit(fetch_spot_data)
        future_purchase = executor.submit(fetch_purchase_data)
        future_estimate = executor.submit(fetch_estimate_data)

        spot = future_spot.result(timeout=30)
        purchase = future_purchase.result(timeout=30)
        estimate = future_estimate.result(timeout=30)

    # 只保留 LOF 基金
    lof_codes = set(spot["代码"].astype(str).tolist())
    purchase = purchase[purchase["基金代码"].astype(str).isin(lof_codes)]
    estimate = estimate[estimate["基金代码"].astype(str).isin(lof_codes)]

    # 合并
    df = spot.merge(purchase, left_on="代码", right_on="基金代码", how="left") \
             .merge(estimate, left_on="代码", right_on="基金代码", how="left")

    # 计算溢价率
    df["溢价率"] = (
        (df["最新价"] - df["最新净值/万份收益"]) / df["最新净值/万份收益"] * 100
    ).round(2)
    df["估算溢价率"] = (
        (df["最新价"] - df["估算净值"]) / df["估算净值"] * 100
    ).round(2)

    # 筛选：排除暂停申购、估算溢价率 > 0、成交额 > 100万
    mask = (
        ~df["申购状态"].astype(str).str.contains("暂停", na=False)
        & df["估算溢价率"].notna()
        & (df["估算溢价率"] > 0)
        & df["成交额"].notna()
        & (df["成交额"] > 1_000_000)
    )
    filtered = df[mask].copy()

    # 按估算溢价率降序，取 top N
    filtered = filtered.sort_values("估算溢价率", ascending=False)
    filtered = filtered.head(settings.max_count)

    # 格式化输出
    records = []
    for _, row in filtered.iterrows():
        records.append({
            "fund_code": str(row["代码"]),
            "fund_name": str(row["名称"]),
            "on_exchange_price": _fmt_num(row["最新价"]),
            "off_exchange_nav": _fmt_num(row["最新净值/万份收益"]),
            "estimated_nav": _fmt_num(row["估算净值"]),
            "price_change": _fmt_pct(row["涨跌幅"]),
            "premium_rate_yesterday": _fmt_pct(row["溢价率"]),
            "premium_rate_realtime": _fmt_pct(row["估算溢价率"]),
            "daily_limit": format_limit(row["日累计限定金额"]),
            "subscription_suspended": _fmt_suspended(row.get("申购状态", "")),
            "fund_size": format_amount(row["总市值"]),
            "trading_volume": format_amount(row["成交额"]),
        })

    return records


def push_to_notify(records: list[dict]) -> None:
    """合并为一条消息 POST 到通知服务。"""
    if not settings.api_base_url:
        logger.info("未配置 LOF_ALERT_API_BASE_URL，跳过推送（共 %d 条）", len(records))
        return

    if not records:
        return

    url = settings.api_base_url.rstrip("/")
    if not url.endswith("/api/v1/notify"):
        url = f"{url}{NOTIFY_PATH}"

    body = json.dumps({
        "title": "基金套利监控",
        "funds": records,
    }, ensure_ascii=False)

    payload = {
        "channel": "feishu",
        "title": "基金套利提醒",
        "template": "fund_arbitrage",
        "body": body,
    }

    logger.info("推送内容：%s", json.dumps(records, ensure_ascii=False))

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"User-Agent": "LOF-Alert/1.0"},
            timeout=15,
        )
        if 200 <= resp.status_code < 300:
            logger.info("推送成功：%d 条基金", len(records))
        else:
            logger.warning("推送失败：HTTP %d %s", resp.status_code, resp.text[:200])
    except requests.RequestException as e:
        logger.warning("推送异常：%s", e)


def run_alert_cycle() -> None:
    """一次完整的告警周期，由 APScheduler 触发。"""
    try:
        logger.info("告警周期开始...")
        records = fetch_and_filter()
        logger.info("筛选结果：%d 条", len(records))
        push_to_notify(records)
    except Exception:
        logger.exception("告警周期异常")


def _fmt_num(val) -> str:
    """数值格式化为字符串，NaN → '-'"""
    if pd.isna(val):
        return "-"
    return str(val)


def _fmt_pct(val) -> str:
    """百分比格式化，NaN → '-'"""
    if pd.isna(val):
        return "-"
    return f"{val:+.2f}%"


def _fmt_suspended(status: str) -> str:
    """申购状态 → 是否暂停"""
    if "暂停" in str(status):
        return "是"
    return "否"
