"""FastAPI 应用入口：创建 app、配置中间件、挂载路由、启动定时告警"""
import json
import logging
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.lof import router as lof_router
from app.services.alerter import run_alert_cycle

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

cron_expr = f"0 {settings.cron_hours} * * {settings.cron_days}"

_ALERT_STATE_FILE = Path(__file__).parent / ".alert_state.json"


def _parse_cron_config():
    """解析 cron_hours 和 cron_days 为可快速检查的集合"""
    hours = {int(h) for h in settings.cron_hours.split(",")}
    day_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
    days = set()
    for part in settings.cron_days.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            days.update(range(day_map[start], day_map[end] + 1))
        else:
            days.add(day_map[part])
    return hours, days


def _load_fired_slots() -> set[str]:
    """加载已触发的时段集合，格式 {"2026-05-29-11", "2026-05-29-14"}"""
    try:
        if _ALERT_STATE_FILE.exists():
            data = json.loads(_ALERT_STATE_FILE.read_text())
            return set(data)
    except Exception:
        logger.warning("读取 .alert_state.json 失败，重置")
    return set()


def _save_fired_slots(slots: set[str]) -> None:
    """持久化已触发时段，只保留最近 30 天"""
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    slots = {s for s in slots if s[:10] >= cutoff}
    _ALERT_STATE_FILE.write_text(json.dumps(sorted(slots), ensure_ascii=False))


def _alert_loop():
    """后台线程：每 30 秒检查一次，当前时间 >= 目标时段时触发告警"""
    tz = ZoneInfo("Asia/Shanghai")
    hours, days = _parse_cron_config()
    fired_slots = _load_fired_slots()
    tick = 0

    while not _stop_event.is_set():
        now = datetime.now(tz)
        today = now.strftime("%Y-%m-%d")
        tick += 1
        if tick % 120 == 1:
            logger.info("alert-loop heartbeat #%d, current=%s, hours=%s, days=%s, fired=%d",
                        tick, now.strftime("%Y-%m-%d %H:%M:%S"), hours, days, len(fired_slots))

        if now.weekday() in days:
            for h in hours:
                slot = f"{today}-{h}"
                if slot in fired_slots:
                    continue
                # 当前时间 >= 该时段的起始时间（hh:00:00）
                slot_start = datetime(now.year, now.month, now.day, h, 0, 0, tzinfo=tz)
                if now >= slot_start:
                    fired_slots.add(slot)
                    logger.info("定时告警触发: slot=%s, now=%s", slot, now.strftime("%Y-%m-%d %H:%M:%S"))
                    try:
                        run_alert_cycle()
                    except Exception:
                        logger.exception("告警周期异常")
                    _save_fired_slots(fired_slots)

        for _ in range(30):
            if _stop_event.is_set():
                return
            time.sleep(1)


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
