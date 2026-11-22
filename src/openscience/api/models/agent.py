"""Agent registry ORM model."""

import uuid

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from openscience.api.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class AgentModel(Base):
    """A registered specialized agent."""

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    input_types: Mapped[list] = mapped_column(JSON, default=list)
    output_types: Mapped[list] = mapped_column(JSON, default=list)
