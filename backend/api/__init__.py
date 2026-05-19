from .vision import router as vision_router
from .voice import router as voice_router
from .pomodoro import router as pomodoro_router
from .dashboard import router as dashboard_router

__all__ = [
    "vision_router",
    "voice_router",
    "pomodoro_router",
    "dashboard_router",
]
