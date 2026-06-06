from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentationArtifact
from app.db.session import get_session
from app.schemas.artifacts import ArtifactRead

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}", response_model=ArtifactRead)
async def read_artifact(
    artifact_id: str,
    session: AsyncSession = Depends(get_session),
) -> ArtifactRead:
    artifact = await session.get(DocumentationArtifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return ArtifactRead.model_validate(artifact)


@router.get("", response_model=list[ArtifactRead])
async def list_artifacts(
    pull_request_id: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[ArtifactRead]:
    stmt = select(DocumentationArtifact)
    if pull_request_id:
        stmt = stmt.where(DocumentationArtifact.pull_request_id == pull_request_id)
    artifacts = list((await session.scalars(stmt)).all())
    return [ArtifactRead.model_validate(artifact) for artifact in artifacts]
