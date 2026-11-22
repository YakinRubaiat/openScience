"""Request schemas."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from openscience.api.utils.validation import (
    SafeAgentName,
    SafeFilePath,
    SessionName,
    Username,
)


class UserCreateRequest(BaseModel):
    """Payload for registering a new user."""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: Username
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Payload for obtaining an access token."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class SessionCreateRequest(BaseModel):
    """Payload for creating a new session."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: SessionName
    project_dir: Optional[SafeFilePath] = None
    compute_backend: str = Field(default="local", max_length=64)


class LoadDataRequest(BaseModel):
    """Payload for loading data into a session."""

    model_config = ConfigDict(str_strip_whitespace=True)

    file_path: SafeFilePath
    format: str = Field(default="auto", max_length=32, pattern=r"^[a-zA-Z0-9_]*$")
    name: Optional[str] = Field(default=None, max_length=255, pattern=r"^[\w\-. ]*$")


class AnalysisRequest(BaseModel):
    """Payload for running an analysis."""

    model_config = ConfigDict(str_strip_whitespace=True)

    task: str = Field(min_length=1, max_length=4000)
    specialist: Optional[SafeAgentName] = None
    data_name: Optional[str] = Field(default=None, max_length=255)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class VisualizeRequest(BaseModel):
    """Payload for generating a visualization."""

    model_config = ConfigDict(str_strip_whitespace=True)

    result_key: Optional[str] = Field(default=None, max_length=4000)
    type: str = Field(default="auto", max_length=32, pattern=r"^[a-zA-Z0-9_]*$")
    style: str = Field(default="publication", max_length=32, pattern=r"^[a-zA-Z0-9_\-]*$")
    output: Optional[SafeFilePath] = None


class WriteRequest(BaseModel):
    """Payload for generating scientific writing."""

    model_config = ConfigDict(str_strip_whitespace=True)

    result_key: Optional[str] = Field(default=None, max_length=4000)
    style: str = Field(default="nature", max_length=32, pattern=r"^[a-zA-Z0-9_\-]*$")
    citation_format: str = Field(default="apa", max_length=32, pattern=r"^[a-zA-Z0-9_\-]*$")
