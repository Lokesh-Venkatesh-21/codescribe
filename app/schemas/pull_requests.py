from pydantic import BaseModel

from app.db.models import PullRequestStatus
from app.schemas.artifacts import ArtifactRead


class PullRequestRead(BaseModel):
    id: str
    repo_full_name: str
    pr_number: int
    head_sha: str
    title: str
    author: str
    status: PullRequestStatus
    artifacts: list[ArtifactRead] = []

    model_config = {"from_attributes": True}


class ProcessPullRequestRequest(BaseModel):
    repo_full_name: str
    pr_number: int
    head_sha: str
    title: str
    author: str
    files: list[dict] = []


class ProcessPullRequestResponse(BaseModel):
    pull_request_id: str
    status: PullRequestStatus
    artifact_count: int
    quality_score: float
