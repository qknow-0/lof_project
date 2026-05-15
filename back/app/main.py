"""FastAPI 应用入口：创建 app、配置中间件、挂载路由"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.lof import router as lof_router

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="LOF 基金监控系统")

# 解决跨域，让 Vue 能调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(lof_router)