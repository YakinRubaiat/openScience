"""Agent registry routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from openscience.api.database import get_db
from openscience.api.middleware.auth import get_current_active_user
from openscience.api.models.agent import AgentModel
from openscience.api.models.user import UserModel
from openscience.api.schemas.response import AgentDetail, AgentListResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get(
    "",
    response_model=AgentListResponse,
    summary="List all agents",
)
def list_agents(
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user),
) -> AgentListResponse:
    """List every registered agent."""
    agents = db.query(AgentModel).order_by(AgentModel.category, AgentModel.name).all()
    return AgentListResponse(
        agents=[AgentDetail.model_validate(a) for a in agents],
        total=len(agents),
    )


@router.get(
    "/{name}",
    response_model=AgentDetail,
    summary="Get agent details",
)
def get_agent(
    name: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user),
) -> AgentModel:
    """Get a single agent by name."""
    agent = db.query(AgentModel).filter(AgentModel.name == name).first()
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown agent: {name}",
        )
    return agent
