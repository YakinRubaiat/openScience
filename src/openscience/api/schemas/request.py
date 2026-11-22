"""Request schemas for the openScience API."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Credentials payload for token issuance."""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoadDataRequest(BaseModel):
    """Payload for loading a data file into a session."""

    file_path: str = Field(..., min_length=1)
    format: str = Field(default="auto")
    name: Optional[str] = None
    options: dict[str, Any] = Field(default_factory=dict)


class AnalyzeRequest(BaseModel):
    """Payload for running an analysis task."""

    task: str = Field(..., min_length=1)
    specialist: Optional[str] = None
    data_name: Optional[str] = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class AskRequest(BaseModel):
    """Payload for asking a natural-language question."""

    question: str = Field(..., min_length=1)


class CreateSessionRequest(BaseModel):
    """Payload for creating a new session."""

    project_dir: Optional[str] = None
    compute_backend: str = "local"
    sandbox_enabled: bool = False
