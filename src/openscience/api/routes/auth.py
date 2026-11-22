"""Authentication routes."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from openscience.api.config import get_settings
from openscience.api.database import get_db
from openscience.api.middleware.auth import (
    create_access_token,
    get_current_active_user,
    hash_password,
    verify_password,
)
from openscience.api.models.user import UserModel
from openscience.api.schemas.request import LoginRequest, UserCreateRequest
from openscience.api.schemas.response import TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(payload: UserCreateRequest, db: Session = Depends(get_db)) -> UserModel:
    """Create a new user account."""
    existing = (
        db.query(UserModel)
        .filter(or_(UserModel.username == payload.username, UserModel.email == payload.email))
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        )
    user = UserModel(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Obtain an access token",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate with username/password and receive a JWT."""
    user = db.query(UserModel).filter(UserModel.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    settings = get_settings()
    expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(subject=user.id, expires_delta=expires)
    return TokenResponse(access_token=token, expires_in=int(expires.total_seconds()))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current user",
)
def read_me(user: UserModel = Depends(get_current_active_user)) -> UserModel:
    """Return the authenticated user's profile."""
    return user
