from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime_config()
    await init_db()
    yield


app = FastAPI(
    title="金融 Agent 平台",
    description="多用户金融 AI Agent SaaS 平台 —— 银行员工和个人投资者的智能助手",
    version="0.1.0",
    lifespan=lifespan,
)

import os

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        os.getenv("FRONTEND_URL", ""),
        # Netlify 部署域名
        "https://yijin-301.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.auth import router as auth_router
from app.api.agents import router as agents_router
from app.api.tasks import router as tasks_router
from app.api.files import router as files_router

app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(tasks_router)
app.include_router(files_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "金融 Agent 平台"}
