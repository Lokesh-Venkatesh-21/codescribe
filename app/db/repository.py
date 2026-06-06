from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Approval,
    ChangedFile,
    DocumentationArtifact,
    Feedback,
    PullRequest,
    PullRequestReview,
    PullRequestStatus,
    QualityMetric,
    ReviewComment,
    ReviewFeedback,
    ValidationResult,
)


async def create_pull_request(session: AsyncSession, pull_request: PullRequest) -> PullRequest:
    session.add(pull_request)
    await session.commit()
    await session.refresh(pull_request)
    return pull_request


async def upsert_pull_request_revision(
    session: AsyncSession, pull_request: PullRequest
) -> PullRequest:
    existing = await get_pull_request_by_revision(
        session,
        pull_request.repo_full_name,
        pull_request.pr_number,
        pull_request.head_sha,
    )
    if existing:
        existing.title = pull_request.title
        existing.author = pull_request.author
        existing.raw_payload = pull_request.raw_payload
        existing.status = PullRequestStatus.RECEIVED
        await session.commit()
        await session.refresh(existing)
        return existing

    return await create_pull_request(session, pull_request)


async def get_pull_request_by_revision(
    session: AsyncSession,
    repo_full_name: str,
    pr_number: int,
    head_sha: str,
) -> PullRequest | None:
    stmt = select(PullRequest).where(
        PullRequest.repo_full_name == repo_full_name,
        PullRequest.pr_number == pr_number,
        PullRequest.head_sha == head_sha,
    )
    return await session.scalar(stmt)


async def get_pull_request(session: AsyncSession, pull_request_id: str) -> PullRequest | None:
    stmt: Select[tuple[PullRequest]] = (
        select(PullRequest)
        .where(PullRequest.id == pull_request_id)
        .options(selectinload(PullRequest.files), selectinload(PullRequest.artifacts))
    )
    return await session.scalar(stmt)


async def clear_pull_request_outputs(session: AsyncSession, pull_request_id: str) -> None:
    artifact_ids = select(DocumentationArtifact.id).where(
        DocumentationArtifact.pull_request_id == pull_request_id
    )
    await session.execute(delete(Approval).where(Approval.artifact_id.in_(artifact_ids)))
    await session.execute(delete(Feedback).where(Feedback.artifact_id.in_(artifact_ids)))
    await session.execute(
        delete(ValidationResult).where(ValidationResult.artifact_id.in_(artifact_ids))
    )
    await session.execute(
        delete(DocumentationArtifact).where(
            DocumentationArtifact.pull_request_id == pull_request_id
        )
    )
    await session.execute(delete(ChangedFile).where(ChangedFile.pull_request_id == pull_request_id))
    await session.execute(
        delete(QualityMetric).where(QualityMetric.pull_request_id == pull_request_id)
    )
    review_ids = select(PullRequestReview.id).where(
        PullRequestReview.pull_request_id == pull_request_id
    )
    await session.execute(delete(ReviewComment).where(ReviewComment.review_id.in_(review_ids)))
    await session.execute(delete(ReviewFeedback).where(ReviewFeedback.review_id.in_(review_ids)))
    await session.execute(
        delete(PullRequestReview).where(PullRequestReview.pull_request_id == pull_request_id)
    )
    await session.commit()
