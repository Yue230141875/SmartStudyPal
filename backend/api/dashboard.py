import logging
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter()

_db = None


def get_db():
    global _db
    if _db is None:
        from database import DatabaseManager
        _db = DatabaseManager()
        _db.create_tables()
    return _db


@router.get("/overview")
async def get_overview(user_id: int = 1):
    """获取仪表盘概览数据"""
    try:
        db = get_db()
        pomo_stats = db.get_today_pomodoro_stats(user_id)
        today_sessions = db.get_today_sessions(user_id)

        total_session_time = 0
        for s in today_sessions:
            if s.end_time and s.start_time:
                total_session_time += (s.end_time - s.start_time).total_seconds()

        focus_scores = []
        for s in today_sessions:
            if s.focus_score_avg is not None:
                focus_scores.append(s.focus_score_avg)

        avg_focus = sum(focus_scores) / len(focus_scores) if focus_scores else 0

        return {
            "success": True,
            "data": {
                "today": {
                    "pomodoro_completed": pomo_stats["completed"],
                    "pomodoro_total": pomo_stats["total"],
                    "focus_hours": pomo_stats["total_focus_hours"],
                    "session_count": len(today_sessions),
                    "session_time_hours": round(total_session_time / 3600, 2),
                    "avg_focus_score": round(avg_focus, 1),
                }
            }
        }
    except Exception as e:
        logger.error(f"获取概览失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/weekly-focus")
async def get_weekly_focus(user_id: int = 1):
    """获取最近7天专注度趋势"""
    try:
        db = get_db()
        today = date.today()
        result = []

        for i in range(6, -1, -1):
            target_date = today - timedelta(days=i)
            date_str = target_date.isoformat()
            pomos = db.list_pomodoros(user_id, date_str, limit=100)

            completed = sum(1 for p in pomos if p.completed)
            total_duration = sum(p.actual_duration or 0 for p in pomos if p.completed)
            focus_scores = [p.focus_score_avg for p in pomos if p.focus_score_avg is not None]
            avg_focus = sum(focus_scores) / len(focus_scores) if focus_scores else 0

            result.append({
                "date": date_str,
                "pomodoro_completed": completed,
                "focus_minutes": round(total_duration / 60, 1),
                "avg_focus_score": round(avg_focus, 1),
            })

        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"获取周趋势失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/focus-distribution")
async def get_focus_distribution(user_id: int = 1, days: int = 7):
    """获取专注度分布统计"""
    try:
        db = get_db()
        today = date.today()
        distribution = {"专注": 0, "轻度分心": 0, "明显走神": 0, "疲劳": 0}

        for i in range(days):
            target_date = today - timedelta(days=i)
            date_str = target_date.isoformat()
            pomos = db.list_pomodoros(user_id, date_str, limit=100)
            for p in pomos:
                if p.focus_score_avg is not None:
                    if p.focus_score_avg >= 75:
                        distribution["专注"] += 1
                    elif p.focus_score_avg >= 50:
                        distribution["轻度分心"] += 1
                    elif p.focus_score_avg >= 25:
                        distribution["明显走神"] += 1
                    else:
                        distribution["疲劳"] += 1

        return {"success": True, "data": distribution}
    except Exception as e:
        logger.error(f"获取分布统计失败: {e}")
        return {"success": False, "message": str(e)}


@router.get("/study-heatmap")
async def get_study_heatmap(user_id: int = 1, days: int = 30):
    """获取学习热力图数据"""
    try:
        db = get_db()
        today = date.today()
        result = []

        for i in range(days - 1, -1, -1):
            target_date = today - timedelta(days=i)
            date_str = target_date.isoformat()
            pomos = db.list_pomodoros(user_id, date_str, limit=100)
            total_minutes = sum((p.actual_duration or 0) for p in pomos if p.completed) / 60
            result.append({
                "date": date_str,
                "minutes": round(total_minutes, 1),
            })

        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"获取热力图失败: {e}")
        return {"success": False, "message": str(e)}
