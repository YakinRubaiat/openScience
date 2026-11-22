"""Shared services and application-level dependencies."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from openscience.api.models.agent import AgentModel
from openscience.core.session import ScienceSession

logger = logging.getLogger("openscience.api")

__all__ = ["SessionRegistry", "register_agents"]


class SessionRegistry:
    """In-memory registry of live ``ScienceSession`` objects."""

    def __init__(self) -> None:
        self._sessions: dict[str, ScienceSession] = {}

    def get(self, session_id: str) -> Optional[ScienceSession]:
        return self._sessions.get(session_id)

    def set(self, session_id: str, session: ScienceSession) -> None:
        self._sessions[session_id] = session

    def drop(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def clear(self) -> None:
        self._sessions.clear()


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
