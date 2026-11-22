"""Response schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    detail: str
    error: Optional[str] = None


class TokenResponse(BaseModel):
    """JWT access token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds")


class UserResponse(BaseModel):
    """Public representation of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime


class AgentDetail(BaseModel):
    """Detailed description of an agent."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    category: str
    description: str
    required_skills: List[str] = Field(default_factory=list)
    input_types: List[str] = Field(default_factory=list)
    output_types: List[str] = Field(default_factory=list)


class AgentListResponse(BaseModel):
    """List of available agents."""

    agents: List[AgentDetail]
    total: int


class TaskResponse(BaseModel):
    """Representation of an executed task."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    task_type: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime


class SessionResponse(BaseModel):
    """Representation of a session."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    owner_id: str
    project_dir: Optional[str] = None
    compute_backend: str
    status: str
    data_keys: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ResultsResponse(BaseModel):
    """All results recorded for a session."""

    session_id: str
    results: Dict[str, Any]
    tasks: List[TaskResponse]
