import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Generator

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

logger = logging.getLogger(__name__)

Base = declarative_base()

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DEFAULT_DB_PATH = DATA_DIR / "smartstudypal.db"


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.now)

    sessions = relationship("StudySession", back_populates="user", lazy="dynamic")
    pomodoros = relationship("PomodoroRecord", back_populates="user", lazy="dynamic")


class StudySession(Base):
    __tablename__ = "study_session"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, nullable=True)
    focus_score_avg = Column(Float, nullable=True)

    user = relationship("User", back_populates="sessions")
    snapshots = relationship("FocusSnapshot", back_populates="session", lazy="dynamic")


class FocusSnapshot(Base):
    __tablename__ = "focus_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("study_session.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    ear_score = Column(Float, default=0)
    head_score = Column(Float, default=0)
    body_score = Column(Float, default=0)
    voice_emotion = Column(String(50), default="未知")
    final_focus_score = Column(Float, default=0)
    emotion_label = Column(String(50), default="未知")

    session = relationship("StudySession", back_populates="snapshots")


class PomodoroRecord(Base):
    __tablename__ = "pomodoro_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    task_name = Column(String(200), nullable=False)
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, nullable=True)
    planned_duration = Column(Integer, nullable=False)
    actual_duration = Column(Integer, nullable=True)
    completed = Column(Boolean, default=False)
    focus_score_avg = Column(Float, nullable=True)
    category = Column(String(50), nullable=True)

    user = relationship("User", back_populates="pomodoros")


class DatabaseManager:
    """数据库管理器：SQLAlchemy ORM + CRUD操作"""

    def __init__(self, db_path: str = None):
        path = db_path or str(DEFAULT_DB_PATH)
        self.engine = create_engine(f"sqlite:///{path}", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        logger.info(f"数据库管理器初始化: {path}")

    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(self.engine)
        logger.info("数据库表创建完成")

    def get_db(self) -> Generator[Session, None, None]:
        """返回数据库 session 的生成器（用于 FastAPI Depends）"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def get_db_session(self) -> Session:
        """返回一个数据库 session"""
        return self.SessionLocal()

    # User CRUD
    def create_user(self, username: str) -> User:
        """创建用户"""
        with self.get_db_session() as session:
            user = User(username=username)
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info(f"创建用户: {username} (id={user.id})")
            return user

    def get_user(self, user_id: int) -> Optional[User]:
        """查询用户"""
        with self.get_db_session() as session:
            return session.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """按用户名查询"""
        with self.get_db_session() as session:
            return session.query(User).filter(User.username == username).first()

    def list_users(self) -> List[User]:
        """列出所有用户"""
        with self.get_db_session() as session:
            return session.query(User).all()

    # StudySession CRUD
    def create_session(self, user_id: int) -> StudySession:
        """创建学习会话"""
        with self.get_db_session() as session:
            s = StudySession(user_id=user_id)
            session.add(s)
            session.commit()
            session.refresh(s)
            return s

    def end_session(self, session_id: int, focus_score_avg: float = None) -> Optional[StudySession]:
        """结束学习会话"""
        with self.get_db_session() as session:
            s = session.query(StudySession).filter(StudySession.id == session_id).first()
            if s:
                s.end_time = datetime.now()
                if focus_score_avg is not None:
                    s.focus_score_avg = focus_score_avg
                session.commit()
                session.refresh(s)
            return s

    def get_session(self, session_id: int) -> Optional[StudySession]:
        """查询学习会话"""
        with self.get_db_session() as session:
            return session.query(StudySession).filter(StudySession.id == session_id).first()

    def list_sessions(self, user_id: int, limit: int = 50) -> List[StudySession]:
        """列出用户的学习会话"""
        with self.get_db_session() as session:
            return (session.query(StudySession)
                    .filter(StudySession.user_id == user_id)
                    .order_by(StudySession.start_time.desc())
                    .limit(limit).all())

    def get_today_sessions(self, user_id: int) -> List[StudySession]:
        """获取今日学习会话"""
        today = date.today()
        with self.get_db_session() as session:
            return (session.query(StudySession)
                    .filter(StudySession.user_id == user_id,
                            StudySession.start_time >= datetime.combine(today, datetime.min.time()))
                    .all())

    # FocusSnapshot CRUD
    def add_snapshot(self, session_id: int, ear_score: float, head_score: float,
                     body_score: float, voice_emotion: str, final_focus_score: float,
                     emotion_label: str) -> FocusSnapshot:
        """添加专注度快照"""
        with self.get_db_session() as session:
            snap = FocusSnapshot(
                session_id=session_id,
                ear_score=ear_score,
                head_score=head_score,
                body_score=body_score,
                voice_emotion=voice_emotion,
                final_focus_score=final_focus_score,
                emotion_label=emotion_label,
            )
            session.add(snap)
            session.commit()
            session.refresh(snap)
            return snap

    def get_session_snapshots(self, session_id: int) -> List[FocusSnapshot]:
        """获取会话的所有快照"""
        with self.get_db_session() as session:
            return (session.query(FocusSnapshot)
                    .filter(FocusSnapshot.session_id == session_id)
                    .order_by(FocusSnapshot.timestamp).all())

    # PomodoroRecord CRUD
    def create_pomodoro(self, user_id: int, task_name: str, planned_duration: int,
                        category: str = None) -> PomodoroRecord:
        """创建番茄钟记录"""
        with self.get_db_session() as session:
            p = PomodoroRecord(
                user_id=user_id,
                task_name=task_name,
                planned_duration=planned_duration,
                category=category,
            )
            session.add(p)
            session.commit()
            session.refresh(p)
            return p

    def complete_pomodoro(self, pomodoro_id: int, actual_duration: int,
                          focus_score_avg: float = None) -> Optional[PomodoroRecord]:
        """完成番茄钟"""
        with self.get_db_session() as session:
            p = session.query(PomodoroRecord).filter(PomodoroRecord.id == pomodoro_id).first()
            if p:
                p.end_time = datetime.now()
                p.actual_duration = actual_duration
                p.completed = True
                if focus_score_avg is not None:
                    p.focus_score_avg = focus_score_avg
                session.commit()
                session.refresh(p)
            return p

    def get_pomodoro(self, pomodoro_id: int) -> Optional[PomodoroRecord]:
        """查询番茄钟记录"""
        with self.get_db_session() as session:
            return session.query(PomodoroRecord).filter(PomodoroRecord.id == pomodoro_id).first()

    def list_pomodoros(self, user_id: int, date_str: str = None,
                       limit: int = 50) -> List[PomodoroRecord]:
        """列出番茄钟记录"""
        with self.get_db_session() as session:
            q = session.query(PomodoroRecord).filter(PomodoroRecord.user_id == user_id)
            if date_str:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                q = q.filter(
                    PomodoroRecord.start_time >= datetime.combine(target_date, datetime.min.time()),
                    PomodoroRecord.start_time < datetime.combine(target_date, datetime.max.time()),
                )
            return q.order_by(PomodoroRecord.start_time.desc()).limit(limit).all()

    def get_today_pomodoro_stats(self, user_id: int) -> dict:
        """获取今日番茄钟统计"""
        today = date.today()
        with self.get_db_session() as session:
            records = (session.query(PomodoroRecord)
                       .filter(PomodoroRecord.user_id == user_id,
                               PomodoroRecord.start_time >= datetime.combine(today, datetime.min.time()))
                       .all())
            completed = sum(1 for r in records if r.completed)
            total_duration = sum(r.actual_duration or 0 for r in records if r.completed)
            avg_focus = 0.0
            focus_scores = [r.focus_score_avg for r in records if r.focus_score_avg is not None]
            if focus_scores:
                avg_focus = sum(focus_scores) / len(focus_scores)

            return {
                "total": len(records),
                "completed": completed,
                "total_duration_seconds": total_duration,
                "total_focus_hours": round(total_duration / 3600, 2),
                "avg_focus_score": round(avg_focus, 1),
            }

def init_db(db_path: str = None) -> DatabaseManager:
    """初始化数据库"""
    db = DatabaseManager(db_path)
    db.create_tables()
    return db


def test():
    """数据库模块测试"""
    print("=== 数据库模块测试 ===")
    import tempfile
    tmp_db = Path(tempfile.gettempdir()) / "test_smartstudypal.db"
    if tmp_db.exists():
        tmp_db.unlink()

    db = DatabaseManager(str(tmp_db))
    db.create_tables()
    print("[OK] 数据库初始化和表创建成功")

    user = db.create_user("测试用户")
    print(f"[OK] 创建用户: id={user.id}, username={user.username}")

    fetched = db.get_user(user.id)
    assert fetched is not None and fetched.username == "测试用户"
    print("[OK] 查询用户成功")

    session = db.create_session(user.id)
    print(f"[OK] 创建学习会话: id={session.id}")

    snap = db.add_snapshot(session.id, 85.0, 90.0, 80.0, "专注", 85.0, "专注")
    print(f"[OK] 添加专注度快照: id={snap.id}, score={snap.final_focus_score}")

    pomo = db.create_pomodoro(user.id, "阅读论文", 1500, "学习")
    print(f"[OK] 创建番茄钟: id={pomo.id}, task={pomo.task_name}")

    completed = db.complete_pomodoro(pomo.id, 1480, 82.5)
    print(f"[OK] 完成番茄钟: completed={completed.completed}, duration={completed.actual_duration}s")

    stats = db.get_today_pomodoro_stats(user.id)
    print(f"[OK] 今日统计: {stats}")

    tmp_db.unlink()
    print("[OK] 数据库模块测试完成")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test()
