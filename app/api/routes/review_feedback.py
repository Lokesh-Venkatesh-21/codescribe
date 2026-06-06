from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import FeedbackOutcome, ReviewDecision
from app.db.session import get_session
from app.services.feedback_evaluation import FeedbackEvaluationService

router = APIRouter(prefix="/review", tags=["review feedback"])


class ReviewFeedbackRequest(BaseModel):
    human_reviewer_decision: ReviewDecision
    outcome: FeedbackOutcome
    reviewer: str
    team: str | None = None
    notes: str | None = None


@router.post("/{review_id}/feedback")
async def submit_review_feedback(
    review_id: str,
    request: ReviewFeedbackRequest,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        feedback = await FeedbackEvaluationService(settings).submit_feedback(
            session,
            review_id=review_id,
            human_reviewer_decision=request.human_reviewer_decision,
            outcome=request.outcome,
            reviewer=request.reviewer,
            team=request.team,
            notes=request.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {
        "id": feedback.id,
        "review_id": feedback.review_id,
        "pull_request_id": feedback.pull_request_id,
        "ai_recommendation": feedback.ai_recommendation,
        "human_reviewer_decision": feedback.human_reviewer_decision,
        "outcome": feedback.outcome,
        "reviewer": feedback.reviewer,
        "team": feedback.team,
        "created_at": feedback.created_at.isoformat(),
    }
