from pydantic import BaseModel

from app.db.models import ArtifactType


class ArtifactRead(BaseModel):
    id: str
    pull_request_id: str
    artifact_type: ArtifactType
    path: str | None
    title: str
    content: str
    model: str
    prompt_version: str
    quality_score: float

    model_config = {"from_attributes": True}


class ValidationRead(BaseModel):
    validator: str
    passed: bool
    score: float
    details: dict

    model_config = {"from_attributes": True}
