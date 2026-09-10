#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! docker info >/dev/null 2>&1; then
  if command -v colima >/dev/null 2>&1; then
    echo "正在启动本地 Docker 环境..."
    colima start
  else
    echo "未检测到正在运行的 Docker 环境，请启动 Docker Desktop 后重试。" >&2
    exit 1
  fi
fi

cd "$PROJECT_DIR"
docker-compose up -d db redis

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "正在启动后端..."
DATABASE_URL="postgresql+asyncpg://finagent:finagent_dev@127.0.0.1:5433/finagent" \
PYTHONPATH=backend \
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8001 &
BACKEND_PID=$!

echo "正在启动前端..."
cd "$PROJECT_DIR/frontend"
npm run dev -- --hostname 127.0.0.1 &
FRONTEND_PID=$!

echo "开发环境已启动："
echo "  前端：http://127.0.0.1:3000/login"
echo "  后端：http://127.0.0.1:8001/health"
wait
