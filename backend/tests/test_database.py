import pytest
from pathlib import Path
from database import DatabaseManager


def test_create_tables(db_manager):
    assert db_manager.engine is not None
    assert db_manager.SessionLocal is not None


def test_create_and_get_user(db_manager):
    user = db_manager.create_user("张三")
    assert user.id is not None
    assert user.username == "张三"

    fetched = db_manager.get_user(user.id)
    assert fetched is not None
    assert fetched.username == "张三"


def test_get_user_by_username(db_manager):
    db_manager.create_user("李四")
    fetched = db_manager.get_user_by_username("李四")
    assert fetched is not None
    assert fetched.username == "李四"


def test_create_and_end_session(db_manager, sample_user):
    session = db_manager.create_session(sample_user.id)
    assert session.id is not None
    assert session.user_id == sample_user.id

    ended = db_manager.end_session(session.id, focus_score_avg=75.5)
    assert ended.end_time is not None
    assert ended.focus_score_avg == 75.5


def test_add_snapshot(db_manager, sample_user):
    session = db_manager.create_session(sample_user.id)
    snap = db_manager.add_snapshot(
        session.id, 80.0, 85.0, 70.0, "专注", 80.0, "专注"
    )
    assert snap.id is not None
    assert snap.ear_score == 80.0
    assert snap.emotion_label == "专注"

    snapshots = db_manager.get_session_snapshots(session.id)
    assert len(snapshots) >= 1


def test_create_and_complete_pomodoro(db_manager, sample_user):
    pomo = db_manager.create_pomodoro(sample_user.id, "阅读论文", 1500, "学习")
    assert pomo.id is not None
    assert pomo.task_name == "阅读论文"

    completed = db_manager.complete_pomodoro(pomo.id, 1480, 82.5)
    assert completed.completed is True
    assert completed.actual_duration == 1480


def test_today_pomodoro_stats(db_manager, sample_user):
    pomo = db_manager.create_pomodoro(sample_user.id, "写代码", 1500)
    db_manager.complete_pomodoro(pomo.id, 1500, 85.0)

    stats = db_manager.get_today_pomodoro_stats(sample_user.id)
    assert stats["completed"] >= 1
    assert stats["total_duration_seconds"] > 0
