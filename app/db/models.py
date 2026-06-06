from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class PullRequestStatus(StrEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    FAILED = "failed"


class ArtifactType(StrEnum):
    FUNCTION_DOC = "function_doc"
    CLASS_DOC = "class_doc"
    MODULE_SUMMARY = "module_summary"
    PR_SUMMARY = "pr_summary"
    RELEASE_NOTES = "release_notes"
    RISK_REPORT = "risk_report"
    SECURITY_REPORT = "security_report"
    IMPACT_ANALYSIS = "impact_analysis"
    QUALITY_REPORT = "quality_report"
    REVIEW_REPORT = "review_report"
    FEEDBACK_REPORT = "feedback_report"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class ReviewDecision(StrEnum):
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class ReviewPublicationStatus(StrEnum):
    DRAFT = "draft"
    APPROVED_FOR_PUBLICATION = "approved_for_publication"
    CHANGES_REQUESTED_BY_HUMAN = "changes_requested_by_human"
    PUBLISHED = "published"
    FAILED = "failed"


class FeedbackOutcome(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint(
            "repo_full_name",
            "pr_number",
            "head_sha",
            name="uq_pull_requests_repo_pr_head",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    repo_full_name: Mapped[str] = mapped_column(String(255), index=True)
    pr_number: Mapped[int] = mapped_column(Integer, index=True)
    head_sha: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(500))
    author: Mapped[str] = mapped_column(String(255))
    status: Mapped[PullRequestStatus] = mapped_column(
        Enum(PullRequestStatus), default=PullRequestStatus.RECEIVED
    )
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    files: Mapped[list["ChangedFile"]] = relationship(back_populates="pull_request")
    artifacts: Mapped[list["DocumentationArtifact"]] = relationship(back_populates="pull_request")
    review: Mapped["PullRequestReview | None"] = relationship(back_populates="pull_request")


class ChangedFile(Base):
    __tablename__ = "changed_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    pull_request_id: Mapped[str] = mapped_column(ForeignKey("pull_requests.id"), index=True)
    path: Mapped[str] = mapped_column(String(1000))
    language: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40))
    patch: Mapped[str | None] = mapped_column(Text)
    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    ast_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    pull_request: Mapped[PullRequest] = relationship(back_populates="files")


class DocumentationArtifact(Base):
    __tablename__ = "documentation_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    pull_request_id: Mapped[str] = mapped_column(ForeignKey("pull_requests.id"), index=True)
    artifact_type: Mapped[ArtifactType] = mapped_column(Enum(ArtifactType), index=True)
    path: Mapped[str | None] = mapped_column(String(1000))
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(120))
    prompt_version: Mapped[str] = mapped_column(String(80), default="v1")
    quality_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    pull_request: Mapped[PullRequest] = relationship(back_populates="artifacts")
    validation_results: Mapped[list["ValidationResult"]] = relationship(back_populates="artifact")
    approval: Mapped["Approval | None"] = relationship(back_populates="artifact")


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    artifact_id: Mapped[str] = mapped_column(ForeignKey("documentation_artifacts.id"), index=True)
    validator: Mapped[str] = mapped_column(String(120))
    passed: Mapped[bool]
    score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    artifact: Mapped[DocumentationArtifact] = relationship(back_populates="validation_results")


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    artifact_id: Mapped[str] = mapped_column(ForeignKey("documentation_artifacts.id"), index=True)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus), default=ApprovalStatus.PENDING
    )
    reviewer: Mapped[str | None] = mapped_column(String(255))
    comments: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    artifact: Mapped[DocumentationArtifact] = relationship(back_populates="approval")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    artifact_id: Mapped[str] = mapped_column(ForeignKey("documentation_artifacts.id"), index=True)
    reviewer: Mapped[str] = mapped_column(String(255))
    rating: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class QualityMetric(Base):
    __tablename__ = "quality_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    pull_request_id: Mapped[str] = mapped_column(ForeignKey("pull_requests.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    value: Mapped[float] = mapped_column(Numeric(8, 3))
    dimensions: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PullRequestReview(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    pull_request_id: Mapped[str] = mapped_column(ForeignKey("pull_requests.id"), index=True)
    decision: Mapped[ReviewDecision] = mapped_column(Enum(ReviewDecision), index=True)
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    risk_summary: Mapped[str] = mapped_column(Text)
    security_summary: Mapped[str] = mapped_column(Text)
    improvement_suggestions: Mapped[list] = mapped_column(JSON, default=list)
    publication_status: Mapped[ReviewPublicationStatus] = mapped_column(
        Enum(ReviewPublicationStatus), default=ReviewPublicationStatus.DRAFT, index=True
    )
    github_review_id: Mapped[str | None] = mapped_column(String(120))
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    pull_request: Mapped[PullRequest] = relationship(back_populates="review")
    comments: Mapped[list["ReviewComment"]] = relationship(back_populates="review")
    feedback: Mapped[list["ReviewFeedback"]] = relationship(back_populates="review")


class ReviewComment(Base):
    __tablename__ = "review_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.id"), index=True)
    path: Mapped[str] = mapped_column(String(1000))
    line: Mapped[int]
    category: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(20), index=True)
    issue: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(default=False)
    github_comment_id: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    review: Mapped[PullRequestReview] = relationship(back_populates="comments")


class ReviewFeedback(Base):
    __tablename__ = "review_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.id"), index=True)
    pull_request_id: Mapped[str] = mapped_column(ForeignKey("pull_requests.id"), index=True)
    ai_recommendation: Mapped[ReviewDecision] = mapped_column(Enum(ReviewDecision), index=True)
    human_reviewer_decision: Mapped[ReviewDecision] = mapped_column(
        Enum(ReviewDecision), index=True
    )
    outcome: Mapped[FeedbackOutcome] = mapped_column(Enum(FeedbackOutcome), index=True)
    reviewer: Mapped[str] = mapped_column(String(255), index=True)
    team: Mapped[str | None] = mapped_column(String(255), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    review: Mapped[PullRequestReview] = relationship(back_populates="feedback")


class ReviewMetric(Base):
    __tablename__ = "review_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), index=True)
    value: Mapped[float] = mapped_column(Numeric(8, 3))
    dimensions: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
