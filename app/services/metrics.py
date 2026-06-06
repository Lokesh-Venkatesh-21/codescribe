from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import QualityMetric


class MetricsService:
    async def record(
        self,
        session: AsyncSession,
        pull_request_id: str,
        name: str,
        value: float,
        dimensions: dict | None = None,
    ) -> QualityMetric:
        metric = QualityMetric(
            pull_request_id=pull_request_id,
            name=name,
            value=value,
            dimensions=dimensions or {},
        )
        session.add(metric)
        await session.commit()
        await session.refresh(metric)
        return metric
