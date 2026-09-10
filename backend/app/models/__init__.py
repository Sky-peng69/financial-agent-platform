import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ORG_USER = "org_user"
    INVESTOR = "investor"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FileStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSED = "parsed"
    FAILED = "failed"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    members: Mapped[list["User"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.INVESTOR, nullable=False)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    organization: Mapped[Organization | None] = relationship(back_populates="members")
    tasks: Mapped[list["Task"]] = relationship(back_populates="user")
    files: Mapped[list["ResearchFile"]] = relationship(back_populates="user")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    input_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_references: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="tasks")
    files: Mapped[list["ResearchFile"]] = relationship(back_populates="task")


class ResearchFile(Base):
    __tablename__ = "research_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[FileStatus] = mapped_column(SAEnum(FileStatus), default=FileStatus.UPLOADED, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="files")
    task: Mapped[Task | None] = relationship(back_populates="files")
