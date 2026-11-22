"""Session ORM model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from openscience.api.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SessionModel(Base):
    """A persisted openScience session."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    project_dir: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    compute_backend: Mapped[str] = mapped_column(String(64), default="local")
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    data_keys: Mapped[list] = mapped_column(JSON, default=list)
    loaded_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    owner: Mapped["UserModel"] = relationship("UserModel", back_populates="sessions")  # noqa: F821
    tasks: Mapped[list["TaskModel"]] = relationship(  # noqa: F821
        "TaskModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="TaskModel.created_at",
    )
