import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.vision import router as vision_router
from api.voice import router as voice_router
from api.pomodoro import router as pomodoro_router
from api.dashboard import router as dashboard_router
from api.health import router as health_router
from database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    init_db()
    logger.info("SmartStudyPal API 启动成功，访问 http://localhost:8000/docs 查看API文档")
    yield


app = FastAPI(title="SmartStudyPal API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vision_router, prefix="/api/vision", tags=["vision"])
app.include_router(voice_router, prefix="/api/voice", tags=["voice"])
app.include_router(pomodoro_router, prefix="/api/pomodoro", tags=["pomodoro"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(health_router, prefix="/api/health", tags=["health"])


@app.get("/")
async def root():
    return {
        "message": "SmartStudyPal API is running",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
