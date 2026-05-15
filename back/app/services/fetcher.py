"""外部数据获取服务模块"""
import akshare as ak
import pandas as pd
import logging
import requests
import json
import re
import time
from datetime import datetime

from app.cache import (
    is_purchase_cache_valid,
    get_purchase_cache_data,
    update_purchase_cache,
)

logger = logging.getLogger(__name__)


def fetch_spot_data():
    """获取 LOF 实时交易数据（直接请求东方财富接口，绕过 akshare 失效域名）"""
    url = "https://push2delay.eastmoney.com/api/qt/clist/get"
    base_params = {
        "pn": "1",
        "pz": "500",
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "wbp2u": "|0|0|0|web",
        "fid": "f3",
        "fs": "b:MK0404,b:MK0405,b:MK0406,b:MK0407",
        "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152",
    }

    # 获取第一页
    r = requests.get(url, params=base_params, timeout=30)
    r.raise_for_status()
    data_json = r.json()
    per_page_num = len(data_json["data"]["diff"])
    total_page = (data_json["data"]["total"] + per_page_num - 1) // per_page_num

    temp_list = [pd.DataFrame(data_json["data"]["diff"])]

    # 获取剩余页面
    for page in range(2, total_page + 1):
        params = base_params.copy()
        params["pn"] = str(page)
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data_json = r.json()
        temp_list.append(pd.DataFrame(data_json["data"]["diff"]))

    temp_df = pd.concat(temp_list, ignore_index=True)
    temp_df.rename(
        columns={
            "f12": "代码",
            "f14": "名称",
            "f2": "最新价",
            "f4": "涨跌额",
            "f3": "涨跌幅",
            "f5": "成交量",
            "f6": "成交额",
            "f17": "开盘价",
            "f15": "最高价",
            "f16": "最低价",
            "f18": "昨收",
            "f20": "总市值",
        },
        inplace=True,
    )
    # 数值类型转换
    numeric_cols = ["最新价", "涨跌额", "涨跌幅", "成交量", "成交额", "开盘价", "最高价", "最低价", "昨收", "总市值"]
    for col in numeric_cols:
        if col in temp_df.columns:
            temp_df[col] = pd.to_numeric(temp_df[col], errors="coerce")
    return temp_df


def fetch_purchase_data():
    """获取基金净值和限额信息（直接调用东方财富 API，用 json.loads 替代 demjson 解析）"""
    # 检查缓存是否有效
    if is_purchase_cache_valid():
        elapsed = (pd.Timestamp.now() - _get_purchase_cache_time()).total_seconds()
        logger.info("使用缓存的净值/限额数据，缓存已 %.0f 秒", elapsed)
        return get_purchase_cache_data()

    url = "https://fund.eastmoney.com/Data/Fund_JJJZ_Data.aspx"
    params = {
        "t": "8",
        "page": "1,50000",
        "js": "reData",
        "sort": "fcode,asc",
    }
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36",
        "Referer": "https://fund.eastmoney.com/",
    }

    try:
        r = requests.get(url, params=params, headers=req_headers, timeout=30)
        r.raise_for_status()
        data_text = r.text

        # 去除 JS 包装 var reData=...;  → 纯 JSON
        clean_text = data_text.strip()
        if clean_text.startswith("var reData="):
            clean_text = clean_text[len("var reData="):]
        clean_text = clean_text.rstrip(";")

        # 给无引号的 key 加双引号，变成合法 JSON，再用 json.loads（C 实现）解析
        # 比 akshare 用的 demjson.decode（纯 Python）快 ~150 倍
        valid_json = re.sub(r'([{,]\s*)(\w+)\s*:', r'\1"\2":', clean_text)
        data_json = json.loads(valid_json)

        temp_df = pd.DataFrame(data_json["datas"])
        # datas 列顺序：0基金代码 1基金简称 2基金类型 3最新净值 4净值时间 5申购状态 6赎回状态
        #              7下一开放日 8购买起点 9日累计限定金额 10- 11- 12手续费
        result = temp_df.iloc[:, [0, 3, 9, 5]].copy()
        result.columns = ["基金代码", "最新净值/万份收益", "日累计限定金额", "申购状态"]
        result["最新净值/万份收益"] = pd.to_numeric(result["最新净值/万份收益"], errors="coerce")
        result["日累计限定金额"] = pd.to_numeric(result["日累计限定金额"], errors="coerce")
    except Exception as e:
        logger.warning("直接解析净值/限额数据失败：%s，回退到 akshare", e)
        df = ak.fund_purchase_em()
        result = df[["基金代码", "最新净值/万份收益", "日累计限定金额", "申购状态"]]

    # 更新缓存
    update_purchase_cache(result)
    return result.copy()


def _get_purchase_cache_time():
    """获取缓存时间（内部使用，避免循环导入）"""
    from app.cache import purchase_cache
    return purchase_cache["time"]


def fetch_estimate_data():
    """获取基金实时估算净值（全量获取后过滤 LOF，确保不遗漏跨分类基金）"""
    try:
        url = "https://api.fund.eastmoney.com/FundGuZhi/GetFundGZList"
        params = {
            "type": "1",  # 全部类型，避免 LOF 基金被归到其他分类而遗漏
            "sort": "3",
            "orderType": "desc",
            "canbuy": "0",
            "pageIndex": "1",
            "pageSize": "50000",
            "_": str(int(pd.Timestamp.now().timestamp() * 1000)),
        }
        req_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36",
            "Referer": "https://fund.eastmoney.com/",
        }
        r = requests.get(url, params=params, headers=req_headers, timeout=30)
        r.raise_for_status()
        json_data = r.json()

        data_list = json_data["Data"]["list"]
        if not data_list:
            logger.warning("估算净值返回空数据")
            return pd.DataFrame(columns=["基金代码", "估算净值"])

        temp_df = pd.DataFrame(data_list)
        # API 返回 30 列，只取：列0=基金代码，列20=估算净值
        result = temp_df.iloc[:, [0, 20]].copy()
        result.columns = ["基金代码", "估算净值"]
        result["估算净值"] = pd.to_numeric(result["估算净值"], errors="coerce")
        return result
    except Exception as e:
        logger.warning("获取估算净值失败：%s，回退到 akshare", e)
        try:
            df = ak.fund_value_estimation_em()
            estimate_col = [c for c in df.columns if "估算数据-估算值" in c]
            if not estimate_col:
                return pd.DataFrame(columns=["基金代码", "估算净值"])
            df = df.rename(columns={estimate_col[0]: "估算净值"})
            df["估算净值"] = pd.to_numeric(df["估算净值"], errors="coerce")
            return df[["基金代码", "估算净值"]].copy()
        except Exception as e2:
            logger.warning("akshare 估算净值也失败：%s", e2)
            return pd.DataFrame(columns=["基金代码", "估算净值"])


def fetch_ths_kline(fund_code: str, max_days: int = 120) -> pd.DataFrame | None:
    """获取同花顺 K-line 数据（主数据源）。
    同花顺换手率基于场内份额，可直接算出准确的场内份额。
    返回字段: date, price, volume(手), turnover(万元), share_volume(万份)
    """
    current_year = datetime.now().year
    years = [current_year, current_year - 1]
    ths_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"http://stockpage.10jqka.com.cn/{fund_code}/",
    }
    all_rows = []
    for year in years:
        url = f"http://d.10jqka.com.cn/v6/line/hs_{fund_code}/01/{year}.js"
        try:
            r = requests.get(url, headers=ths_headers, timeout=30)
            r.raise_for_status()
            content = r.text
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1:
                continue
            data = json.loads(content[start:end + 1])
            data_str = data.get("data", "")
            if not data_str:
                continue
            for day_str in data_str.split(";"):
                parts = day_str.split(",")
                if len(parts) < 8:
                    continue
                date_raw = parts[0]
                date = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:]}"
                vol_shares = float(parts[5])
                turnover_rate = float(parts[7])
                # 同花顺换手率基于场内份额：换手率(%) = 成交量(股) / 场内份额(股) * 100
                # => 场内份额(万份) = 成交量(股) / (换手率(%) / 100) / 10000
                share_volume = round(vol_shares / turnover_rate / 100, 2) if turnover_rate > 0 else None
                all_rows.append({
                    "date": date,
                    "price": float(parts[4]),
                    "volume": round(vol_shares / 100, 2),  # 手
                    "turnover": round(float(parts[6]) / 10000, 2),  # 万元
                    "share_volume": share_volume,
                })
        except Exception as e:
            logger.warning("同花顺 %s 年数据获取失败：%s", year, e)

    if not all_rows:
        return None
    df = pd.DataFrame(all_rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df.tail(max_days).reset_index(drop=True)


def fetch_em_kline(fund_code: str, secid: str, max_days: int = 120) -> pd.DataFrame | None:
    """获取东方财富 K-line 数据（备用数据源）。
    东方财富换手率基于总份额，算出的 share_volume 为总份额。
    返回字段: date, price, volume(手), turnover(万元), share_volume(万份)
    """
    kline_url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    kline_params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "0",
        "end": "20500101",
        "lmt": str(max_days),
    }
    kline_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://quote.eastmoney.com/{secid.replace('.', '')}.html",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }

    last_err = None
    session = requests.Session()
    for attempt in range(5):
        try:
            if attempt > 0:
                session = requests.Session()
                time.sleep(1 + attempt * 0.5)
            r = session.get(kline_url, params=kline_params, headers=kline_headers, timeout=30)
            r.raise_for_status()
            kline_data = r.json()
            kline_list = kline_data.get("data", {}).get("klines", [])
            if kline_list:
                break
        except Exception as e:
            last_err = e
            logger.warning("东方财富 K 线请求失败（尝试 %d/5）：%s", attempt + 1, e)
            if attempt < 4:
                time.sleep(2 ** attempt)
    session.close()

    if not kline_list:
        logger.error("东方财富 K 线全部失败：%s", last_err)
        return None

    price_rows = []
    for item in kline_list:
        parts = item.split(",")
        turnover_rate = float(parts[10]) if len(parts) > 10 and parts[10] else 0
        volume_lots = float(parts[5]) if len(parts) > 5 and parts[5] else 0
        # 东方财富换手率基于总份额，算出的 share_volume 为总份额
        share_volume = round(volume_lots / turnover_rate, 2) if turnover_rate > 0 else None
        price_rows.append({
            "date": parts[0],
            "price": float(parts[2]),
            "volume": volume_lots,
            "turnover": round(float(parts[6]) / 10000, 2) if len(parts) > 6 and parts[6] else None,
            "share_volume": share_volume,
        })

    df = pd.DataFrame(price_rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df