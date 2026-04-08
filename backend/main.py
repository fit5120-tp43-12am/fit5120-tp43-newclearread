from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.api import router
from routes.text import router as text_router

app = FastAPI()

# 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段可以这样
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(text_router, prefix="/api")

@app.get("/")
def home():
    return {"message": "Backend is running!"}


def test():
    return {"message": "Hello from backend!"}

