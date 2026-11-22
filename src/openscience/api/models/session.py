"""Session model and in-memory registry.

Wraps :class:`openscience.core.session.ScienceSession` with a stable ID so
the REST layer can address multiple concurrent sessions.
"""

import uuid
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Optional

from openscience.core.session import ScienceSession


@dataclass
class SessionRecord:
    """A live ScienceSession plus its identifier."""

    session_id: str
    session: ScienceSession
    project_dir: Path
    compute_backend: str = "local"
    sandbox_enabled: bool = False

    def list_datasets(self) -> list[str]:
        """Names of datasets loaded into the session."""
        return list(self.session._data.keys())


class SessionStore:
    """Thread-safe in-memory registry of sessions."""

    def __init__(self) -> None:
        self._records: dict[str, SessionRecord] = {}
        self._lock = RLock()

    def create(
        self,
        project_dir: Optional[str] = None,
        compute_backend: str = "local",
        sandbox_enabled: bool = False,
    ) -> SessionRecord:
        """Create and register a new session."""
        session_id = uuid.uuid4().hex
        session = ScienceSession(
            project_dir=project_dir,
            compute_backend=compute_backend,
            sandbox_enabled=sandbox_enabled,
        )
        record = SessionRecord(
            session_id=session_id,
            session=session,
            project_dir=session.project_dir,
            compute_backend=compute_backend,
            sandbox_enabled=sandbox_enabled,
        )
        with self._lock:
            self._records[session_id] = record
        return record

    def get(self, session_id: str) -> Optional[SessionRecord]:
        """Fetch a session record, or None if unknown."""
        with self._lock:
            return self._records.get(session_id)

    def delete(self, session_id: str) -> bool:
        """Remove a session. Returns True when one was deleted."""
        with self._lock:
            return self._records.pop(session_id, None) is not None

    def list_ids(self) -> list[str]:
        """Return all known session IDs."""
        with self._lock:
            return list(self._records.keys())


# Shared registry used by the routes module.
store = SessionStore()
