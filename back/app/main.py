"""FastAPI 应用入口：创建 app、配置中间件、挂载路由、启动定时告警"""
import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.lof import router as lof_router
from app.services.alerter import run_alert_cycle

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

cron_expr = f"0 {settings.cron_hours} * * {settings.cron_days}"


def _parse_cron_config():
    """解析 cron_hours 和 cron_days 为可快速检查的集合"""
    hours = {int(h) for h in settings.cron_hours.split(",")}
    # mon-fri -> 0-4 (Monday=0)
    day_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
    days = set()
    for part in settings.cron_days.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            start_idx = day_map[start]
            end_idx = day_map[end]
            days.update(range(start_idx, end_idx + 1))
        else:
            days.add(day_map[part])
    return hours, days


def _alert_loop():
    """后台线程：每 30 秒检查一次当前时间，匹配 cron 配置时触发告警"""
    tz = ZoneInfo("Asia/Shanghai")
    hours, days = _parse_cron_config()
    last_fire_date = None
    tick = 0

    while not _stop_event.is_set():
        now = datetime.now(tz)
        today_key = now.strftime("%Y-%m-%d")
        tick += 1
        if tick % 120 == 1:
            logger.info("alert-loop heartbeat #%d, current=%s, hours=%s, days=%s",
                        tick, now.strftime("%Y-%m-%d %H:%M:%S"), hours, days)

        if (
            now.hour in hours
            and now.minute == 0
            and now.weekday() in days
            and last_fire_date != today_key + str(now.hour)
        ):
            # 在目标小时的 0-30 秒内触发，记录防重复
            if now.second < 30:
                last_fire_date = today_key + str(now.hour)
                logger.info("定时告警触发: %s", now.strftime("%Y-%m-%d %H:%M:%S"))
                try:
                    run_alert_cycle()
                except Exception:
                    logger.exception("告警周期异常")

        _stop_event.wait(timeout=30)


_stop_event = threading.Event()
_thread: threading.Thread | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _thread
    logger.info("告警调度器已启动: cron=%s，推送目标=%s", cron_expr, settings.api_base_url or "未配置")
    # 启动时立即执行一次
    threading.Thread(target=run_alert_cycle, daemon=True).start()
    # 启动定时轮询线程
    _thread = threading.Thread(target=_alert_loop, daemon=True, name="alert-loop")
    _thread.start()
    yield
    _stop_event.set()
    logger.info("告警调度器已停止")


app = FastAPI(title="LOF 基金监控系统", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(lof_router)
