from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.approvals import ApprovalDecision, ApprovalRead
from app.services.approvals import ApprovalService

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("/{approval_id}/decision", response_model=ApprovalRead)
async def decide_approval(
    approval_id: str,
    decision: ApprovalDecision,
    session: AsyncSession = Depends(get_session),
) -> ApprovalRead:
    approval = await ApprovalService().decide(
        session,
        approval_id=approval_id,
        status=decision.status,
        reviewer=decision.reviewer,
        comments=decision.comments,
    )
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    return ApprovalRead.model_validate(approval)
