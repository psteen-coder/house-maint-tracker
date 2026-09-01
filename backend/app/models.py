from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="member")  # admin|member|viewer
    theme: Mapped[str] = mapped_column(String(40), default="light")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    occurrences: Mapped[list["Occurrence"]] = relationship(back_populates="assignee")


class SessionToken(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class Task(Base):
    """Recurring maintenance definition."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=30)
    recurrence: Mapped[str] = mapped_column(String(20), default="once")
    season: Mapped[str | None] = mapped_column(String(20), nullable=True)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conditions: Mapped[str] = mapped_column(Text, default="[]")  # JSON list of strings
    weather_prefs: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    default_assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    depends_on_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    occurrences: Mapped[list["Occurrence"]] = relationship(back_populates="task")

    def prefs(self) -> dict:
        try:
            return json.loads(self.weather_prefs or "{}")
        except json.JSONDecodeError:
            return {}

    def condition_list(self) -> list:
        try:
            data = json.loads(self.conditions or "[]")
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []


class Occurrence(Base):
    __tablename__ = "occurrences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    due_date: Mapped[date] = mapped_column(Date)
    original_due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="todo")  # todo|in_progress|done
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    weather_adjusted: Mapped[bool] = mapped_column(Boolean, default=False)
    weather_reason: Mapped[str] = mapped_column(String(40), default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    task: Mapped[Task] = relationship(back_populates="occurrences")
    assignee: Mapped[User | None] = relationship(back_populates="occurrences")


def make_engine(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, future=True)
    return engine, sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
