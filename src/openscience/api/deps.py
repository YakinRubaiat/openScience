"""Shared FastAPI dependencies and application services."""

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from openscience.api.database import get_db
from openscience.api.models.agent import AgentModel
from openscience.core.session import ScienceSession

logger = logging.getLogger("openscience.api")

__all__ = ["get_db", "get_live_session", "register_agents", "session_registry"]


class SessionRegistry:
    """In-memory registry of live ``ScienceSession`` objects.

    Database rows are the source of truth for metadata and history; this
    registry keeps the live in-memory framework objects used to execute work.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ScienceSession] = {}

    def get(self, session_id: str) -> ScienceSession | None:
        return self._sessions.get(session_id)

    def set(self, session_id: str, session: ScienceSession) -> None:
        self._sessions[session_id] = session

    def drop(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def clear(self) -> None:
        self._sessions.clear()


session_registry = SessionRegistry()


def get_live_session(session_id: str) -> ScienceSession:
    """Resolve the live ``ScienceSession`` or raise 404."""
    session = session_registry.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id!r} is not loaded on this server",
        )
    return session


def register_agents(db: Session, orchestrator) -> None:
    """Sync the orchestrator's agent registry into the database."""
    for name, agent_class in orchestrator.agents.items():
        metadata = agent_class.metadata
        existing = db.query(AgentModel).filter(AgentModel.name == name).one_or_none()
        if existing is None:
            db.add(
                AgentModel(
                    name=metadata.name,
                    category=metadata.category,
                    description=metadata.description,
                    required_skills=list(metadata.required_skills),
                    input_types=list(metadata.input_types),
                    output_types=list(metadata.output_types),
                )
            )
        else:
            existing.category = metadata.category
            existing.description = metadata.description
            existing.required_skills = list(metadata.required_skills)
            existing.input_types = list(metadata.input_types)
            existing.output_types = list(metadata.output_types)
    db.commit()
