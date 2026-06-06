from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
from app.db.models import (
    ArtifactType,
    DocumentationArtifact,
    PullRequestReview,
    QualityMetric,
    ReviewDecision,
    ReviewPublicationStatus,
)
from app.db.session import get_session
from app.services.review_publishing import ReviewPublisher

router = APIRouter(prefix="/pr", tags=["pr intelligence"])


@router.get("/{pull_request_id}/summary")
async def pr_summary(
    pull_request_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    artifact = await _report_artifact(
        session, pull_request_id, ArtifactType.PR_SUMMARY, "pr_summary.md"
    )
    return _artifact_response(artifact)


@router.get("/{pull_request_id}/risk")
async def pr_risk(
    pull_request_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    artifact = await _report_artifact(
        session,
        pull_request_id,
        ArtifactType.RISK_REPORT,
        "risk_report.md",
    )
    return {
        **_artifact_response(artifact),
        "metrics": await _metrics(session, pull_request_id, ["risk_score"]),
    }


@router.get("/{pull_request_id}/security")
async def pr_security(
    pull_request_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    artifact = await _report_artifact(
        session,
        pull_request_id,
        ArtifactType.SECURITY_REPORT,
        "security_report.md",
    )
    return {
        **_artifact_response(artifact),
        "metrics": await _metrics(session, pull_request_id, ["security_score"]),
    }


@router.get("/{pull_request_id}/quality")
async def pr_quality(
    pull_request_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    artifact = await _report_artifact(
        session,
        pull_request_id,
        ArtifactType.QUALITY_REPORT,
        "quality_report.md",
    )
    return {
        **_artifact_response(artifact),
        "metrics": await _metrics(
            session,
            pull_request_id,
            [
                "documentation_score",
                "complexity_score",
                "maintainability_score",
                "security_score",
                "overall_quality_score",
            ],
        ),
    }


@router.get("/{pull_request_id}/review")
async def pr_review(
    pull_request_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    review = await _latest_review(session, pull_request_id)
    artifact = await _report_artifact(
        session,
        pull_request_id,
        ArtifactType.REVIEW_REPORT,
        "review_report.md",
    )
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return {
        **_review_response(review),
        "report": _artifact_response(artifact),
    }


@router.post("/{pull_request_id}/approve")
async def approve_review(
    pull_request_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    review = await _latest_review(session, pull_request_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    review.publication_status = ReviewPublicationStatus.APPROVED_FOR_PUBLICATION
    await session.commit()
    await session.refresh(review)
    return _review_response(review)


@router.post("/{pull_request_id}/request-changes")
async def request_review_changes(
    pull_request_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    review = await _latest_review(session, pull_request_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    review.decision = ReviewDecision.REQUEST_CHANGES
    review.publication_status = ReviewPublicationStatus.CHANGES_REQUESTED_BY_HUMAN
    await session.commit()
    await session.refresh(review)
    return _review_response(review)


@router.post("/{pull_request_id}/publish-review")
async def publish_review(
    pull_request_id: str,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> dict:
    review = await _latest_review(session, pull_request_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if (
        not settings.auto_post_reviews
        and review.publication_status != ReviewPublicationStatus.APPROVED_FOR_PUBLICATION
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review must be approved before publishing",
        )
    published = await ReviewPublisher(settings).publish(session, pull_request_id)
    return _review_response(published)


async def _report_artifact(
    session: AsyncSession,
    pull_request_id: str,
    artifact_type: ArtifactType,
    path: str,
) -> DocumentationArtifact:
    stmt = (
        select(DocumentationArtifact)
        .where(
            DocumentationArtifact.pull_request_id == pull_request_id,
            DocumentationArtifact.artifact_type == artifact_type,
            DocumentationArtifact.path == path,
        )
        .order_by(desc(DocumentationArtifact.created_at))
    )
    artifact = await session.scalar(stmt)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return artifact


async def _metrics(
    session: AsyncSession,
    pull_request_id: str,
    names: list[str],
) -> dict[str, float]:
    stmt = select(QualityMetric).where(
        QualityMetric.pull_request_id == pull_request_id,
        QualityMetric.name.in_(names),
    )
    metrics = list((await session.scalars(stmt)).all())
    return {metric.name: float(metric.value) for metric in metrics}


async def _latest_review(
    session: AsyncSession,
    pull_request_id: str,
) -> PullRequestReview | None:
    stmt = (
        select(PullRequestReview)
        .where(PullRequestReview.pull_request_id == pull_request_id)
        .options(selectinload(PullRequestReview.comments))
        .order_by(desc(PullRequestReview.created_at))
    )
    return await session.scalar(stmt)


def _artifact_response(artifact: DocumentationArtifact) -> dict:
    return {
        "artifact_id": artifact.id,
        "pull_request_id": artifact.pull_request_id,
        "artifact_type": artifact.artifact_type,
        "path": artifact.path,
        "title": artifact.title,
        "content": artifact.content,
        "quality_score": float(artifact.quality_score),
    }


def _review_response(review: PullRequestReview) -> dict:
    return {
        "review_id": review.id,
        "pull_request_id": review.pull_request_id,
        "decision": review.decision,
        "confidence_score": float(review.confidence_score),
        "publication_status": review.publication_status,
        "github_review_id": review.github_review_id,
        "risk_summary": review.risk_summary,
        "security_summary": review.security_summary,
        "improvement_suggestions": review.improvement_suggestions,
        "comments": [
            {
                "id": comment.id,
                "path": comment.path,
                "line": comment.line,
                "category": comment.category,
                "severity": comment.severity,
                "issue": comment.issue,
                "suggestion": comment.suggestion,
                "is_published": comment.is_published,
                "github_comment_id": comment.github_comment_id,
            }
            for comment in review.comments
        ],
    }
