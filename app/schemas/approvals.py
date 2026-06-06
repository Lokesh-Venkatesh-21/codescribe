from pydantic import BaseModel, Field

from app.db.models import ApprovalStatus


class ApprovalDecision(BaseModel):
    status: ApprovalStatus = Field(..., examples=["approved"])
    reviewer: str
    comments: str | None = None


class ApprovalRead(BaseModel):
    id: str
    artifact_id: str
    status: ApprovalStatus
    reviewer: str | None = None
    comments: str | None = None

    model_config = {"from_attributes": True}
