from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import QualityMetric
from app.db.session import get_session
from app.services.feedback_evaluation import FeedbackEvaluationService

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def metrics_summary(
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await FeedbackEvaluationService(settings).dashboard_metrics(session)


@router.get("/accuracy")
async def accuracy_metrics(
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> dict:
    metrics = await FeedbackEvaluationService(settings).calculate_metrics(session)
    return {
        "false_positive_rate": metrics.false_positive_rate,
        "false_negative_rate": metrics.false_negative_rate,
        "reviewer_agreement_rate": metrics.reviewer_agreement_rate,
        "average_confidence": metrics.average_confidence,
        "total_feedback": metrics.total_feedback,
    }


@router.get("/reviewer-agreement")
async def reviewer_agreement_metrics(
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> dict:
    metrics = await FeedbackEvaluationService(settings).calculate_metrics(session)
    return {
        "reviewer_agreement_rate": metrics.reviewer_agreement_rate,
        "average_confidence": metrics.average_confidence,
        "total_feedback": metrics.total_feedback,
    }


@router.get("/quality")
async def quality_metrics(
    pull_request_id: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    stmt = select(QualityMetric).order_by(desc(QualityMetric.created_at)).limit(100)
    if pull_request_id:
        stmt = stmt.where(QualityMetric.pull_request_id == pull_request_id)
    metrics = list((await session.scalars(stmt)).all())
    return [
        {
            "pull_request_id": metric.pull_request_id,
            "name": metric.name,
            "value": float(metric.value),
            "dimensions": metric.dimensions,
            "created_at": metric.created_at.isoformat(),
        }
        for metric in metrics
    ]
