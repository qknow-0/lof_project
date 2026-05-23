#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACK_DIR="$PROJECT_ROOT/back"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_help() {
    echo "用法: ./deploy.sh <command>"
    echo ""
    echo "命令:"
    echo "  up       构建并启动服务"
    echo "  down     停止并移除容器"
    echo "  restart  重启服务"
    echo "  logs     查看日志"
    echo "  build    仅构建镜像"
    echo "  ps       查看容器状态"
    echo "  clean    停止容器并删除镜像"
}

case "${1:-}" in
    up)
        log_info "构建并启动服务..."
        cd "$PROJECT_ROOT"
        docker compose up -d --build
        log_info "服务已启动"
        docker compose ps
        ;;
    down)
        log_info "停止服务..."
        cd "$PROJECT_ROOT"
        docker compose down
        log_info "服务已停止"
        ;;
    restart)
        log_info "重启服务..."
        cd "$PROJECT_ROOT"
        docker compose down
        docker compose up -d --build
        log_info "服务已重启"
        ;;
    logs)
        cd "$PROJECT_ROOT"
        docker compose logs -f
        ;;
    build)
        log_info "构建镜像..."
        cd "$PROJECT_ROOT"
        docker compose build --no-cache
        log_info "镜像构建完成"
        ;;
    ps)
        cd "$PROJECT_ROOT"
        docker compose ps
        ;;
    clean)
        log_info "停止容器并删除镜像..."
        cd "$PROJECT_ROOT"
        docker compose down --rmi all
        log_info "清理完成"
        ;;
    *)
        show_help
        exit 1
        ;;
esac
