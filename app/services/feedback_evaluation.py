import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.db.models import (
    ArtifactType,
    ChangedFile,
    DocumentationArtifact,
    FeedbackOutcome,
    PullRequest,
    PullRequestReview,
    ReviewDecision,
    ReviewFeedback,
    ReviewMetric,
)


@dataclass(frozen=True)
class FeedbackMetrics:
    acceptance_rate: float
    rejection_rate: float
    false_positive_rate: float
    false_negative_rate: float
    reviewer_agreement_rate: float
    average_confidence: float
    total_feedback: int


class FeedbackEvaluationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def submit_feedback(
        self,
        session: AsyncSession,
        review_id: str,
        human_reviewer_decision: ReviewDecision,
        outcome: FeedbackOutcome,
        reviewer: str,
        team: str | None = None,
        notes: str | None = None,
    ) -> ReviewFeedback:
        review = await self._review(session, review_id)
        if not review:
            raise ValueError("Review not found")

        feedback = ReviewFeedback(
            review_id=review.id,
            pull_request_id=review.pull_request_id,
            ai_recommendation=review.decision,
            human_reviewer_decision=human_reviewer_decision,
            outcome=outcome,
            reviewer=reviewer,
            team=team,
            notes=notes,
        )
        session.add(feedback)
        await session.flush()
        await self._append_dataset_row(session, review, feedback)
        metrics = await self.calculate_metrics(session)
        await self._store_metric_snapshot(session, metrics, reviewer=reviewer, team=team)
        await self._store_feedback_report(session, review.pull_request_id, metrics)
        await session.commit()
        await session.refresh(feedback)
        return feedback

    async def calculate_metrics(self, session: AsyncSession) -> FeedbackMetrics:
        feedback_rows = list((await session.scalars(select(ReviewFeedback))).all())
        if not feedback_rows:
            return FeedbackMetrics(0, 0, 0, 0, 0, 0, 0)

        review_ids = [feedback.review_id for feedback in feedback_rows]
        reviews = {
            review.id: review
            for review in (
                await session.scalars(
                    select(PullRequestReview).where(PullRequestReview.id.in_(review_ids))
                )
            ).all()
        }
        total = len(feedback_rows)
        accepted = sum(
            1 for feedback in feedback_rows if feedback.outcome == FeedbackOutcome.ACCEPTED
        )
        rejected = sum(
            1 for feedback in feedback_rows if feedback.outcome == FeedbackOutcome.REJECTED
        )
        agreement = sum(
            1
            for feedback in feedback_rows
            if feedback.ai_recommendation == feedback.human_reviewer_decision
        )
        false_positives = sum(
            1
            for feedback in feedback_rows
            if feedback.ai_recommendation != ReviewDecision.APPROVE
            and feedback.human_reviewer_decision == ReviewDecision.APPROVE
        )
        false_negatives = sum(
            1
            for feedback in feedback_rows
            if feedback.ai_recommendation == ReviewDecision.APPROVE
            and feedback.human_reviewer_decision == ReviewDecision.REQUEST_CHANGES
        )
        average_confidence = (
            sum(
                float(reviews[feedback.review_id].confidence_score)
                for feedback in feedback_rows
                if feedback.review_id in reviews
            )
            / total
        )

        return FeedbackMetrics(
            acceptance_rate=round(accepted / total, 3),
            rejection_rate=round(rejected / total, 3),
            false_positive_rate=round(false_positives / total, 3),
            false_negative_rate=round(false_negatives / total, 3),
            reviewer_agreement_rate=round(agreement / total, 3),
            average_confidence=round(average_confidence, 3),
            total_feedback=total,
        )

    async def dashboard_metrics(self, session: AsyncSession) -> dict[str, Any]:
        metrics = await self.calculate_metrics(session)
        snapshots = list(
            (
                await session.scalars(select(ReviewMetric).order_by(ReviewMetric.created_at.asc()))
            ).all()
        )
        return {
            "current": metrics.__dict__,
            "accuracy_trend": self._trend(snapshots, "reviewer_agreement_rate"),
            "acceptance_trend": self._trend(snapshots, "acceptance_rate"),
            "confidence_trend": self._trend(snapshots, "average_confidence"),
            "team_statistics": self._team_statistics(snapshots),
        }

    async def _review(
        self,
        session: AsyncSession,
        review_id: str,
    ) -> PullRequestReview | None:
        stmt = (
            select(PullRequestReview)
            .where(PullRequestReview.id == review_id)
            .options(selectinload(PullRequestReview.comments))
        )
        return await session.scalar(stmt)

    async def _append_dataset_row(
        self,
        session: AsyncSession,
        review: PullRequestReview,
        feedback: ReviewFeedback,
    ) -> None:
        pull_request = await session.get(PullRequest, review.pull_request_id)
        files = list(
            (
                await session.scalars(
                    select(ChangedFile).where(ChangedFile.pull_request_id == review.pull_request_id)
                )
            ).all()
        )
        row = {
            "pr_id": review.pull_request_id,
            "repo_full_name": pull_request.repo_full_name if pull_request else None,
            "pr_number": pull_request.pr_number if pull_request else None,
            "diff": "\n".join(file.patch or "" for file in files),
            "ai_review": {
                "decision": review.decision,
                "confidence_score": float(review.confidence_score),
                "comments": [
                    {
                        "path": comment.path,
                        "line": comment.line,
                        "severity": comment.severity,
                        "issue": comment.issue,
                        "suggestion": comment.suggestion,
                    }
                    for comment in review.comments
                ],
            },
            "human_review": {
                "decision": feedback.human_reviewer_decision,
                "reviewer": feedback.reviewer,
                "team": feedback.team,
                "notes": feedback.notes,
            },
            "outcome": feedback.outcome,
        }
        path = Path(self.settings.training_dataset_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(row, default=str) + "\n")

    async def _store_metric_snapshot(
        self,
        session: AsyncSession,
        metrics: FeedbackMetrics,
        reviewer: str,
        team: str | None,
    ) -> None:
        dimensions = {"reviewer": reviewer, "team": team}
        for name, value in metrics.__dict__.items():
            if name == "total_feedback":
                continue
            session.add(ReviewMetric(name=name, value=value, dimensions=dimensions))

    async def _store_feedback_report(
        self,
        session: AsyncSession,
        pull_request_id: str,
        metrics: FeedbackMetrics,
    ) -> None:
        feedback_rows = list(
            (
                await session.scalars(
                    select(ReviewFeedback).order_by(ReviewFeedback.created_at.desc()).limit(50)
                )
            ).all()
        )
        accepted = [
            feedback.ai_recommendation
            for feedback in feedback_rows
            if feedback.outcome == FeedbackOutcome.ACCEPTED
        ]
        rejected = [
            feedback.ai_recommendation
            for feedback in feedback_rows
            if feedback.outcome == FeedbackOutcome.REJECTED
        ]
        content = self._feedback_report_markdown(metrics, accepted, rejected)
        session.add(
            DocumentationArtifact(
                pull_request_id=pull_request_id,
                artifact_type=ArtifactType.FEEDBACK_REPORT,
                path="feedback_report.md",
                title="feedback_report.md",
                content=content,
                model="feedback_evaluation:deterministic",
                quality_score=1,
            )
        )

    @staticmethod
    def _feedback_report_markdown(
        metrics: FeedbackMetrics,
        accepted: list[ReviewDecision],
        rejected: list[ReviewDecision],
    ) -> str:
        return (
            "# Feedback Evaluation Report\n\n"
            f"## Acceptance Rate\n{metrics.acceptance_rate:.3f}\n\n"
            f"## Rejection Rate\n{metrics.rejection_rate:.3f}\n\n"
            f"## Reviewer Agreement Rate\n{metrics.reviewer_agreement_rate:.3f}\n\n"
            f"## Average Confidence\n{metrics.average_confidence:.3f}\n\n"
            f"## Top Accepted Recommendations\n{_counts_markdown(accepted)}\n\n"
            f"## Top Rejected Recommendations\n{_counts_markdown(rejected)}\n\n"
            "## Most Common Review Mistakes\n"
            f"- False positive rate: {metrics.false_positive_rate:.3f}\n"
            f"- False negative rate: {metrics.false_negative_rate:.3f}\n\n"
            "## Confidence Calibration\n"
            "Compare average confidence with reviewer agreement rate to tune thresholds."
        )

    @staticmethod
    def _trend(snapshots: list[ReviewMetric], name: str) -> list[dict[str, Any]]:
        return [
            {"value": float(metric.value), "created_at": metric.created_at.isoformat()}
            for metric in snapshots
            if metric.name == name
        ]

    @staticmethod
    def _team_statistics(snapshots: list[ReviewMetric]) -> dict[str, dict[str, float]]:
        team_values: dict[str, list[ReviewMetric]] = {}
        for metric in snapshots:
            team = metric.dimensions.get("team") or "unknown"
            team_values.setdefault(team, []).append(metric)
        return {
            team: {
                metric.name: float(metric.value)
                for metric in metrics
                if metric.name
                in {"acceptance_rate", "reviewer_agreement_rate", "average_confidence"}
            }
            for team, metrics in team_values.items()
        }


def _counts_markdown(values: list[ReviewDecision]) -> str:
    if not values:
        return "- None yet"
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return "\n".join(f"- `{name}`: {count}" for name, count in sorted(counts.items()))
