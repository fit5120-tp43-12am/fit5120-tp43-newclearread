import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.api import router
from backend.routes.text import router as text_router

app = FastAPI()

# 从环境变量读取 CORS 白名单，多个域名用逗号分隔
allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

# 本地开发默认值（当未配置环境变量时使用）
if not allowed_origins:
    allowed_origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(text_router, prefix="/api")

@app.get("/")
def home(): 
    return {"message": "Backend is running!"}


def test():
    return {"message": "Hello from backend!"}

