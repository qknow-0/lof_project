"""缓存状态管理模块"""
import pandas as pd

# LOF 实时数据缓存
cache_data = {"data": [], "time": None}

# 净值/限额数据缓存（该数据变化频率低，缓存 5 分钟）
purchase_cache = {"data": None, "time": None}
PURCHASE_CACHE_TTL_SECONDS = 300  # 5 分钟


def update_purchase_cache(data: pd.DataFrame) -> None:
    """更新净值/限额缓存"""
    global purchase_cache
    purchase_cache = {"data": data, "time": pd.Timestamp.now()}


def get_purchase_cache_age() -> float:
    """获取净值/限额缓存已存在的秒数"""
    if purchase_cache["time"] is None:
        return float("inf")
    return (pd.Timestamp.now() - purchase_cache["time"]).total_seconds()


def is_purchase_cache_valid() -> bool:
    """判断净值/限额缓存是否仍然有效"""
    if purchase_cache["data"] is None or purchase_cache["time"] is None:
        return False
    return get_purchase_cache_age() < PURCHASE_CACHE_TTL_SECONDS


def get_purchase_cache_data() -> pd.DataFrame:
    """获取缓存的净值/限额数据副本"""
    return purchase_cache["data"].copy()


def update_cache_data(data: list) -> None:
    """更新 LOF 实时数据缓存"""
    global cache_data
    cache_data = {"data": data, "time": pd.Timestamp.now()}


def get_cached_lof_data() -> dict | None:
    """获取缓存的 LOF 实时数据（仅在缓存存在时返回）"""
    if cache_data["data"]:
        return {"data": cache_data["data"], "time": cache_data["time"]}
    return None