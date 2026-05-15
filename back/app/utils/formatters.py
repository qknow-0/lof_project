"""格式化工具函数"""
import pandas as pd


def format_limit(value):
    """格式化限额显示"""
    if pd.isna(value):
        return "-"
    if value == 0:
        return "-"
    if value >= 1e8:
        return "不限"
    if value < 10000:
        return f"{value:.0f}元/日"
    return f"{value / 10000:.0f}万/日"


def format_amount(value):
    """格式化金额：成交额/总市值"""
    if pd.isna(value):
        return "-"
    if value >= 1e8:
        return f"{value / 1e8:.2f}亿"
    if value >= 1e4:
        return f"{value / 1e4:.2f}万"
    return f"{value:.0f}"