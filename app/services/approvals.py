from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Approval, ApprovalStatus


class ApprovalService:
    async def create_pending(self, session: AsyncSession, artifact_id: str) -> Approval:
        approval = Approval(artifact_id=artifact_id, status=ApprovalStatus.PENDING)
        session.add(approval)
        await session.commit()
        await session.refresh(approval)
        return approval

    async def decide(
        self,
        session: AsyncSession,
        approval_id: str,
        status: ApprovalStatus,
        reviewer: str,
        comments: str | None = None,
    ) -> Approval | None:
        approval = await session.get(Approval, approval_id)
        if not approval:
            return None
        approval.status = status
        approval.reviewer = reviewer
        approval.comments = comments
        await session.commit()
        await session.refresh(approval)
        return approval
