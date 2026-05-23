"""应用配置，优先读取 .env 文件，其次环境变量"""
from dataclasses import dataclass, field
from pathlib import Path
import os

from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
load_dotenv(Path(__file__).parent.parent / ".env")


@dataclass(frozen=True)
class Settings:
    api_base_url: str = field(
        default_factory=lambda: os.getenv("LOF_ALERT_API_BASE_URL", "")
    )
    cron_hours: str = field(
        default_factory=lambda: os.getenv("LOF_ALERT_CRON_HOURS", "11,14")
    )
    cron_days: str = field(
        default_factory=lambda: os.getenv("LOF_ALERT_CRON_DAYS", "mon-fri")
    )
    max_count: int = field(
        default_factory=lambda: int(os.getenv("LOF_ALERT_MAX_COUNT", "5"))
    )
    send_delay_seconds: float = field(
        default_factory=lambda: float(os.getenv("LOF_ALERT_SEND_DELAY_SECONDS", "0.5"))
    )
    backend_port: int = field(
        default_factory=lambda: int(os.getenv("LOF_BACKEND_PORT", "8000"))
    )


settings = Settings()
