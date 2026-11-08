import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, Date, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base
uid = lambda: str(uuid.uuid4())
now = lambda: datetime.utcnow()
class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="student")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
class Subject(Base):
    __tablename__ = "subjects"
    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(300), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
class SyllabusVersion(Base):
    __tablename__ = "syllabus_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    subject_code: Mapped[str] = mapped_column(ForeignKey("subjects.code"), index=True)
    academic_year: Mapped[str] = mapped_column(String(9))
    status: Mapped[str] = mapped_column(String(12), default="draft")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    content: Mapped[dict] = mapped_column(JSON, default=dict)  # {"units":[{"title","topics":[..]}]}
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject_code: Mapped[str] = mapped_column(String(20))
    syllabus_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(200), default="New chat")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    messages = relationship("Message", cascade="all, delete-orphan", order_by="Message.created_at")
class Message(Base):
    __tablename__ = "conversation_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
class QuestionPaper(Base):
    __tablename__ = "question_papers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    subject_code: Mapped[str] = mapped_column(ForeignKey("subjects.code"), index=True)
    year: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(12), default="draft")  # draft|published|archived
    default_duration_min: Mapped[int] = mapped_column(Integer, default=30)
    questions = relationship("Question", cascade="all, delete-orphan", order_by="Question.position")
class Question(Base):
    __tablename__ = "questions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    paper_id: Mapped[str] = mapped_column(ForeignKey("question_papers.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    qtype: Mapped[str] = mapped_column(String(20))  # single|multiple|assertion_reason
    text: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON, default=list)  # ["opt a", ...]
    answer: Mapped[list] = mapped_column(JSON, default=list)   # indices
    marks: Mapped[float] = mapped_column(Float, default=1)
    negative: Mapped[float] = mapped_column(Float, default=0)
    explanation: Mapped[str] = mapped_column(Text, default="")
class PracticeSession(Base):
    __tablename__ = "practice_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("question_papers.id"))
    mode: Mapped[str] = mapped_column(String(10))
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    incorrect: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)
    time_taken_s: Mapped[int] = mapped_column(Integer, default=0)
    responses = relationship("PracticeResponse", cascade="all, delete-orphan")
class PracticeResponse(Base):
    __tablename__ = "practice_responses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey("practice_sessions.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"))
    selected: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(10))
    marks: Mapped[float] = mapped_column(Float, default=0)
class Activity(Base):
    __tablename__ = "student_activity"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    day: Mapped[date] = mapped_column(Date, index=True)
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
class AcademicYear(Base):
    __tablename__ = "academic_years"
    label: Mapped[str] = mapped_column(String(9), primary_key=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
class Document(Base):  # original uploads live in object storage; this row points to them
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    kind: Mapped[str] = mapped_column(String(20))  # syllabus|paper|answer_key
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(400))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
class Blueprint(Base):
    __tablename__ = "paper_blueprints"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    subject_code: Mapped[str] = mapped_column(ForeignKey("subjects.code"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12), default="draft")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    spec: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
class GeneratedPaper(Base):
    __tablename__ = "generated_papers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject_code: Mapped[str] = mapped_column(String(20))
    syllabus_version_id: Mapped[str] = mapped_column(String(36))
    blueprint_id: Mapped[str] = mapped_column(String(36))
    blueprint_version: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(200))
    questions: Mapped[list] = mapped_column(JSON)  # snapshot incl. answers
    meta: Mapped[dict] = mapped_column(JSON, default=dict)  # spec snapshot, model, attempts
    status: Mapped[str] = mapped_column(String(10), default="generated")
    score: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    incorrect: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
class CommunityMessage(Base):
    __tablename__ = "community_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    room: Mapped[str] = mapped_column(String(30), default="class12")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(String(500))
    reports: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
