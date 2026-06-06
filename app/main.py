from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import (
    approvals,
    artifacts,
    health,
    metrics,
    pr_intelligence,
    pull_requests,
    review_feedback,
    webhooks,
)
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.models import Base
from app.db.session import engine

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI documentation generation and PR summary platform.",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(webhooks.router, prefix=settings.api_prefix)
app.include_router(pull_requests.router, prefix=settings.api_prefix)
app.include_router(approvals.router, prefix=settings.api_prefix)
app.include_router(artifacts.router, prefix=settings.api_prefix)
app.include_router(metrics.router, prefix=settings.api_prefix)
app.include_router(pr_intelligence.router, prefix=settings.api_prefix)
app.include_router(review_feedback.router, prefix=settings.api_prefix)
