"""FastAPI 应用入口：创建 app、配置中间件、挂载路由、启动定时告警"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.routers.lof import router as lof_router
from app.services.alerter import run_alert_cycle

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
cron_expr = f"0 {settings.cron_hours} * * {settings.cron_days}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        run_alert_cycle,
        "cron",
        hour=settings.cron_hours,
        minute="0",
        day_of_week=settings.cron_days,
        id="lof_alert",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("告警调度器已启动: cron=%s，推送目标=%s", cron_expr, settings.api_base_url or "未配置")
    # 启动时立即执行一次
    scheduler.add_job(run_alert_cycle, id="lof_alert_startup")
    yield
    scheduler.shutdown(wait=False)
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
