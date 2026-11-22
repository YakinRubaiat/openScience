"""Session lifecycle routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from openscience.api.config import get_settings
from openscience.api.database import get_db
from openscience.api.deps import SessionRegistry
from openscience.api.middleware.auth import get_current_active_user
from openscience.api.models.session import SessionModel
from openscience.api.models.task import TaskModel
from openscience.api.models.user import UserModel
from openscience.api.schemas.request import (
    AnalysisRequest,
    LoadDataRequest,
    SessionCreateRequest,
    VisualizeRequest,
    WriteRequest,
)
from openscience.api.schemas.response import (
    MessageResponse,
    ResultsResponse,
    SessionResponse,
    TaskResponse,
)
from openscience.api.utils.serialization import serialize_result, to_jsonable
from openscience.core.orchestrator import Result
from openscience.core.session import ScienceSession

logger = logging.getLogger("openscience.api")

router = APIRouter(prefix="/sessions", tags=["sessions"])

# In-memory registry of live ``ScienceSession`` objects (database rows are
# the source of truth for metadata/history; this holds live execution state).
live_sessions = SessionRegistry()


def _get_owned_session(db: Session, session_id: str, user: UserModel) -> SessionModel:
    """Fetch a session row and enforce ownership."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    if session.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
    return session


def _refresh_live_session(db_session: SessionModel) -> ScienceSession:
    """Return (creating if needed) the live framework session for a DB row."""
    live = live_sessions.get(db_session.id)
    if live is None:
        settings = get_settings()
        live = ScienceSession(
            project_dir=db_session.project_dir or None,
            compute_backend=db_session.compute_backend,
            sandbox_enabled=settings.sandbox_enabled,
        )
        live_sessions.set(db_session.id, live)
    return live


def _record_task(
    db: Session,
    session_id: str,
    task_type: str,
    description: str,
    parameters: dict,
    status_value: str,
    result=None,
    error=None,
) -> TaskModel:
    task = TaskModel(
        session_id=session_id,
        task_type=task_type,
        description=description,
        parameters=to_jsonable(parameters),
        status=status_value,
        result=serialize_result(result) if result is not None else None,
        error=error,
    )
    db.add(task)
    return task


def _fail_task(
    exc: Exception, db: Session, session_id: str, task_type: str, description: str, parameters: dict
) -> None:
    logger.exception("Session %s %s failed", session_id, task_type)
    _record_task(
        db,
        session_id,
        task_type=task_type,
        description=description,
        parameters=parameters,
        status_value="failed",
        error=str(exc),
    )
    db.commit()
    raise HTTPException(status_code=400, detail=f"{task_type} failed: {exc}") from exc


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new session",
)
def create_session(
    payload: SessionCreateRequest,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user),
) -> SessionModel:
    """Create a new analysis session owned by the current user."""
    settings = get_settings()
    session = SessionModel(
        name=payload.name,
        owner_id=user.id,
        project_dir=payload.project_dir,
        compute_backend=payload.compute_backend or settings.compute_backend,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    _refresh_live_session(session)
    return session


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get a session",
)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user),
) -> SessionModel:
    """Retrieve session metadata."""
    return _get_owned_session(db, session_id, user)


@router.post(
    "/{session_id}/load",
    response_model=TaskResponse,
    summary="Load data into a session",
)
def load_data(
    session_id: str,
    payload: LoadDataRequest,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user),
) -> TaskModel:
    """Load a dataset into the session."""
    session_row = _get_owned_session(db, session_id, user)
    live = _refresh_live_session(session_row)
    parameters = payload.model_dump()

    try:
        live.load_data(payload.file_path, format=payload.format, name=payload.name)
    except Exception as exc:
        _fail_task(exc, db, session_id, "load", f"Load {payload.file_path}", parameters)

    task = _record_task(
        db,
        session_id,
        task_type="load",
        description=f"Load {payload.file_path}",
        parameters=parameters,
        status_value="completed",
        result={"loaded": payload.name or payload.file_path, "data_keys": list(live._data.keys())},
    )
    session_row.data_keys = list(live._data.keys())
    db.commit()
    db.refresh(task)
    return task


def _resolve_result(live: ScienceSession, result_key):
    """Resolve the analysis result referenced by ``result_key``."""
    if not live._results:
        raise HTTPException(status_code=400, detail="No analysis results available yet")
    key = result_key if result_key is not None else list(live._results.keys())[-1]
    if key not in live._results:
        raise HTTPException(status_code=404, detail=f"Result not found: {key}")
    return key, live._results[key]


@router.post(
    "/{session_id}/analyze",
    response_model=TaskResponse,
    summary="Run an analysis task",
)
def analyze(
    session_id: str,
    payload: AnalysisRequest,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user),
) -> TaskModel:
    """Run an analysis task in the session."""
    session_row = _get_owned_session(db, session_id, user)
    live = _refresh_live_session(session_row)
    parameters = payload.model_dump()

    try:
        result = live.analyze(
            task=payload.task,
            specialist=payload.specialist,
            data_name=payload.data_name,
            **payload.parameters,
        )
    except Exception as exc:
        _fail_task(exc, db, session_id, "analyze", payload.task, parameters)

    task = _record_task(
        db,
        session_id,
        task_type="analyze",
        description=payload.task,
        parameters=parameters,
        status_value="completed",
        result=result,
    )
    db.commit()
    db.refresh(task)
    return task


@router.post(
    "/{session_id}/visualize",
    response_model=TaskResponse,
    summary="Generate a visualization",
)
def visualize(
    session_id: str,
    payload: VisualizeRequest,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user),
) -> TaskModel:
    """Generate a visualization from a stored analysis result."""
    session_row = _get_owned_session(db, session_id, user)
    live = _refresh_live_session(session_row)
    result_key, result = _resolve_result(live, payload.result_key)
    parameters = payload.model_dump()

    try:
        viz = live.visualize(
            result,
            type=payload.type,
            style=payload.style,
            output=payload.output,
        )
    except Exception as exc:
        _fail_task(exc, db, session_id, "visualize", f"visualize:{result_key}", parameters)

    task = _record_task(
        db,
        session_id,
        task_type="visualize",
        description=f"Visualize result: {result_key}",
        parameters=parameters,
        status_value="completed",
        result=viz,
    )
    db.commit()
    db.refresh(task)
    return task


@router.post(
    "/{session_id}/write",
    response_model=TaskResponse,
    summary="Generate scientific writing",
)
def write(
    session_id: str,
    payload: WriteRequest,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user),
) -> TaskModel:
    """Generate a methods/style write-up from a stored analysis result."""
    session_row = _get_owned_session(db, session_id, user)
    live = _refresh_live_session(session_row)
    result_key, result = _resolve_result(live, payload.result_key)
    parameters = payload.model_dump()

    try:
        document = live.write_methods(
            result,
            style=payload.style,
            citation_format=payload.citation_format,
        )
        if not isinstance(document, Result):
            document = Result.coerce(document)
    except Exception as exc:
        _fail_task(exc, db, session_id, "write", f"write:{result_key}", parameters)

    task = _record_task(
        db,
        session_id,
        task_type="write",
        description=f"Write-up of result: {result_key}",
        parameters=parameters,
        status_value="completed",
        result=document,
    )
    db.commit()
    db.refresh(task)
    return task


@router.get(
    "/{session_id}/results",
    response_model=ResultsResponse,
    summary="Get session results",
)
def get_results(
    session_id: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user),
) -> ResultsResponse:
    """Return all recorded results and tasks for a session."""
    _get_owned_session(db, session_id, user)

    tasks = (
        db.query(TaskModel)
        .filter(TaskModel.session_id == session_id)
        .order_by(TaskModel.created_at)
        .all()
    )

    results: dict = {}
    live = live_sessions.get(session_id)
    if live is not None:
        for key, value in live._results.items():
            results[key] = serialize_result(value)
    for task in tasks:
        if task.task_type == "analyze" and task.status == "completed" and task.result is not None:
            results.setdefault(task.description, task.result)

    return ResultsResponse(
        session_id=session_id,
        results=results,
        tasks=[TaskResponse.model_validate(t) for t in tasks],
    )


@router.delete(
    "/{session_id}",
    response_model=MessageResponse,
    summary="Delete a session",
)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user),
) -> MessageResponse:
    """Delete a session and its history."""
    session_row = _get_owned_session(db, session_id, user)
    db.delete(session_row)
    db.commit()
    live_sessions.drop(session_id)
    return MessageResponse(message=f"Session {session_id} deleted")
