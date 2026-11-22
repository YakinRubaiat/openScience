"""User model for API authentication.

This is a minimal in-memory user representation. A production deployment
should back this with a real database and salted password hashing.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    """An authenticated API user."""

    username: str
    hashed_password: str
    disabled: bool = False
    scopes: list = field(default_factory=list)

    def is_active(self) -> bool:
        """Return True if the user can authenticate."""
        return not self.disabled


# In-memory development users. Passwords are SHA-256 hashes of the
# plaintext values documented below — replace with a real store in prod.
_DEFAULT_USERS = {
    "admin": User(
        username="admin",
        # sha256("admin")
        hashed_password="8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",
        scopes=["read", "write", "admin"],
    ),
    "researcher": User(
        username="researcher",
        # sha256("researcher")
        hashed_password="c1c05743a9fa944b61a2e9b0e36f1ff86cbe02e19a1a94d3a656f0e6f7fdb27e",
        scopes=["read", "write"],
    ),
}


def get_user(username: str) -> Optional[User]:
    """Look up a user by username."""
    return _DEFAULT_USERS.get(username)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compare a plaintext password against its SHA-256 hash."""
    import hashlib

    digest = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return digest == hashed_password
