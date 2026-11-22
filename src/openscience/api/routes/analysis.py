"""Analysis capability routes."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from openscience.api.database import get_db
from openscience.api.middleware.auth import get_current_active_user
from openscience.api.models.agent import AgentModel
from openscience.api.models.user import UserModel
from openscience.api.schemas.response import AgentDetail

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get(
    "/capabilities",
    response_model=List[AgentDetail],
    summary="List analysis capabilities",
)
def list_analysis_capabilities(
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_active_user),
) -> List[AgentDetail]:
    """List agents capable of running data analyses."""
    agents = (
        db.query(AgentModel)
        .filter(AgentModel.category == "analysis")
        .order_by(AgentModel.name)
        .all()
    )
    return [AgentDetail.model_validate(a) for a in agents]
