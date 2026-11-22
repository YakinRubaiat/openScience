"""Response schemas for the openScience API."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Bearer token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token lifetime in seconds")


class AgentInfo(BaseModel):
    """Summary metadata for a registered agent."""

    name: str
    category: str
    description: str


class AgentListResponse(BaseModel):
    """List of available agents."""

    agents: list[AgentInfo]


class SessionInfo(BaseModel):
    """Information about an active session."""

    session_id: str
    project_dir: str
    compute_backend: str
    sandbox_enabled: bool
    datasets: list[str] = Field(default_factory=list)


class StatusResponse(BaseModel):
    """Generic status response."""

    status: str
    message: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Result of an analysis invocation."""

    status: str
    result: Optional[Any] = None
    message: Optional[str] = None


class AskResponse(BaseModel):
    """Answer returned by the orchestrator."""

    status: str
    answer: Optional[str] = None
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    status: str = "error"
    message: str
    detail: Optional[dict[str, Any]] = None
