import logging
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

_db = None
_fusion_engine = None


def get_db():
    global _db
    if _db is None:
        from database import DatabaseManager
        _db = DatabaseManager()
        _db.create_tables()
    return _db


def get_fusion_engine():
    global _fusion_engine
    if _fusion_engine is None:
        from modules.fusion_engine import FusionEngine
        _fusion_engine = FusionEngine()
    return _fusion_engine


class PomodoroCreateRequest(BaseModel):
    user_id: int = 1
    task_name: str
    planned_duration: int = 1500
    category: Optional[str] = None


class PomodoroCompleteRequest(BaseModel):
    actual_duration: int
    focus_score_avg: Optional[float] = None


class SessionCreateRequest(BaseModel):
    user_id: int = 1


class SnapshotCreateRequest(BaseModel):
    session_id: int
    ear_score: float = 0
    head_score: float = 0
    body_score: float = 0
    voice_emotion: str = "未知"
    final_focus_score: float = 0
    emotion_label: str = "未知"


@router.post("/session/start")
async def start_session(req: SessionCreateRequest):
    """开始学习会话"""
    try:
        db = get_db()
        session = db.create_session(req.user_id)
        return {
            "success": True,
            "data": {
                "session_id": session.id,
                "user_id": session.user_id,
                "start_time": session.start_time.isoformat() if session.start_time else None,
            }
        }
    except Exception as e:
        logger.error(f"开始会话失败: {e}")
        return {"success": False, "message": str(e)}


@router.post("/session/{session_id}/end")
async def end_session(session_id: int, focus_score_avg: float = None):
    """结束学习会话"""
    try:
        db = get_db()
        session = db.end_session(session_id, focus_score_avg)
        if session:
            return {
                "success": True,
                "data": {
                    "session_id": session.id,
                    "end_time": session.end_time.isoformat() if session.end_time else None,
                    "focus_score_avg": session.focus_score_avg,
                }
            }
        return {"success": False, "message": "会话不存在"}
    except Exception as e:
        logger.error(f"结束会话失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/session/list")
async def list_sessions(user_id: int = 1, limit: int = 20):
    """列出学习会话"""
    try:
        db = get_db()
        sessions = db.list_sessions(user_id, limit)
        result = []
        for s in sessions:
            result.append({
                "id": s.id,
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "focus_score_avg": s.focus_score_avg,
            })
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"列出会话失败: {e}")
        return {"success": False, "message": str(e)}


@router.post("/snapshot")
async def add_snapshot(req: SnapshotCreateRequest):
    """添加专注度快照"""
    try:
        db = get_db()
        snap = db.add_snapshot(
            req.session_id, req.ear_score, req.head_score,
            req.body_score, req.voice_emotion, req.final_focus_score,
            req.emotion_label,
        )
        return {
            "success": True,
            "data": {
                "id": snap.id,
                "final_focus_score": snap.final_focus_score,
                "emotion_label": snap.emotion_label,
            }
        }
    except Exception as e:
        logger.error(f"添加快照失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/snapshot/{session_id}")
async def get_snapshots(session_id: int):
    """获取会话快照列表"""
    try:
        db = get_db()
        snapshots = db.get_session_snapshots(session_id)
        result = []
        for s in snapshots:
            result.append({
                "id": s.id,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                "ear_score": s.ear_score,
                "head_score": s.head_score,
                "body_score": s.body_score,
                "voice_emotion": s.voice_emotion,
                "final_focus_score": s.final_focus_score,
                "emotion_label": s.emotion_label,
            })
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"获取快照失败: {e}")
        return {"success": False, "message": str(e)}


@router.post("/pomodoro/start")
async def start_pomodoro(req: PomodoroCreateRequest):
    """开始番茄钟"""
    try:
        db = get_db()
        pomo = db.create_pomodoro(req.user_id, req.task_name, req.planned_duration, req.category)
        return {
            "success": True,
            "data": {
                "id": pomo.id,
                "task_name": pomo.task_name,
                "planned_duration": pomo.planned_duration,
                "start_time": pomo.start_time.isoformat() if pomo.start_time else None,
            }
        }
    except Exception as e:
        logger.error(f"开始番茄钟失败: {e}")
        return {"success": False, "message": str(e)}


@router.post("/pomodoro/{pomodoro_id}/complete")
async def complete_pomodoro(pomodoro_id: int, req: PomodoroCompleteRequest):
    """完成番茄钟"""
    try:
        db = get_db()
        pomo = db.complete_pomodoro(pomodoro_id, req.actual_duration, req.focus_score_avg)
        if pomo:
            return {
                "success": True,
                "data": {
                    "id": pomo.id,
                    "completed": pomo.completed,
                    "actual_duration": pomo.actual_duration,
                    "focus_score_avg": pomo.focus_score_avg,
                }
            }
        return {"success": False, "message": "番茄钟记录不存在"}
    except Exception as e:
        logger.error(f"完成番茄钟失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/pomodoro/list")
async def list_pomodoros(user_id: int = 1, date_str: str = None, limit: int = 20):
    """列出番茄钟记录"""
    try:
        db = get_db()
        pomos = db.list_pomodoros(user_id, date_str, limit)
        result = []
        for p in pomos:
            result.append({
                "id": p.id,
                "task_name": p.task_name,
                "start_time": p.start_time.isoformat() if p.start_time else None,
                "end_time": p.end_time.isoformat() if p.end_time else None,
                "planned_duration": p.planned_duration,
                "actual_duration": p.actual_duration,
                "completed": p.completed,
                "focus_score_avg": p.focus_score_avg,
                "category": p.category,
            })
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"列出番茄钟失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/pomodoro/today-stats")
async def today_pomodoro_stats(user_id: int = 1):
    """今日番茄钟统计"""
    try:
        db = get_db()
        stats = db.get_today_pomodoro_stats(user_id)
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        return {"success": False, "message": str(e)}


@router.post("/fuse")
async def fuse_focus_score(vision_score: float = 0, voice_emotion: str = "未知"):
    """融合视觉和语音专注度"""
    try:
        engine = get_fusion_engine()
        result = engine.fuse(vision_score, voice_emotion)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"融合失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/trend")
async def get_focus_trend(n: int = 10):
    """获取专注度趋势"""
    try:
        engine = get_fusion_engine()
        trend = engine.get_trend(n)
        return {"success": True, "data": trend}
    except Exception as e:
        logger.error(f"获取趋势失败: {e}")
        return {"success": False, "message": str(e)}
