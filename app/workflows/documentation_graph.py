from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import (
    Approval,
    ArtifactType,
    ChangedFile,
    DocumentationArtifact,
    PullRequest,
    PullRequestReview,
    PullRequestStatus,
    ReviewComment,
    ValidationResult,
)
from app.db.repository import clear_pull_request_outputs
from app.parsers.base import ParsedFile, Symbol
from app.services.approvals import ApprovalService
from app.services.ast_analysis import ASTAnalyzer
from app.services.evaluation import DocumentationEvaluator
from app.services.generators import DocumentationGenerator, GeneratedDocument
from app.services.metrics import MetricsService
from app.services.pr_intelligence import PRIntelligenceEngine
from app.services.review_agent import ReviewAgent, ReviewResult
from app.services.review_publishing import ReviewPublisher
from app.services.validation import ValidationPipeline


@dataclass
class DocumentationState:
    pull_request: PullRequest
    changed_files: list[dict[str, Any]]
    parsed_files: list[ParsedFile] = field(default_factory=list)
    generated: list[tuple[GeneratedDocument, ParsedFile | None, str]] = field(default_factory=list)
    artifacts: list[DocumentationArtifact] = field(default_factory=list)
    approvals: list[Approval] = field(default_factory=list)
    intelligence_metrics: dict[str, float] = field(default_factory=dict)
    review_result: ReviewResult | None = None
    quality_score: float = 0


class DocumentationWorkflow:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.ast_analyzer = ASTAnalyzer()
        self.generator = DocumentationGenerator(settings)
        self.validator = ValidationPipeline()
        self.evaluator = DocumentationEvaluator()
        self.approvals = ApprovalService()
        self.metrics = MetricsService()
        self.intelligence = PRIntelligenceEngine()
        self.reviewer = ReviewAgent()

    async def run(self, session: AsyncSession, state: DocumentationState) -> DocumentationState:
        try:
            await clear_pull_request_outputs(session, state.pull_request.id)
            await self._record_files(session, state)
            await self._generate_documents(state)
            await self._persist_and_validate(session, state)
            await self._persist_review(session, state)
            if self.settings.auto_post_reviews:
                await ReviewPublisher(self.settings).publish(session, state.pull_request.id)
            await self._create_approvals(session, state)
            state.pull_request.status = PullRequestStatus.READY_FOR_REVIEW
            await session.commit()
            return state
        except Exception:
            state.pull_request.status = PullRequestStatus.FAILED
            await session.commit()
            raise

    async def _record_files(self, session: AsyncSession, state: DocumentationState) -> None:
        state.pull_request.status = PullRequestStatus.PROCESSING
        for file_data in state.changed_files:
            path = file_data["filename"]
            patch = file_data.get("patch")
            parsed = self.ast_analyzer.analyze_patch(path, patch)
            state.parsed_files.append(parsed)
            session.add(
                ChangedFile(
                    pull_request_id=state.pull_request.id,
                    path=path,
                    language=parsed.language,
                    status=file_data.get("status", "modified"),
                    patch=patch,
                    additions=file_data.get("additions", 0),
                    deletions=file_data.get("deletions", 0),
                    ast_metadata={
                        "symbols": [symbol.__dict__ for symbol in parsed.symbols],
                        "imports": parsed.imports,
                        "errors": parsed.errors,
                        "github": {
                            "sha": file_data.get("sha"),
                            "previous_filename": file_data.get("previous_filename"),
                            "blob_url": file_data.get("blob_url"),
                            "raw_url": file_data.get("raw_url"),
                            "contents_url": file_data.get("contents_url"),
                        },
                        "raw": file_data.get("raw", {}),
                    },
                )
            )
        await session.commit()

    async def _generate_documents(self, state: DocumentationState) -> None:
        for parsed_file, file_data in zip(state.parsed_files, state.changed_files, strict=False):
            for symbol in parsed_file.symbols:
                scoped_file = self._scoped_file(parsed_file, symbol)
                if symbol.kind == "function":
                    document = await self.generator.generate_function_documentation(
                        parsed_file,
                        symbol,
                        file_data.get("patch"),
                    )
                    state.generated.append((document, scoped_file, "function_doc"))
                elif symbol.kind == "class":
                    document = await self.generator.generate_class_documentation(
                        parsed_file,
                        symbol,
                        file_data.get("patch"),
                    )
                    state.generated.append((document, scoped_file, "class_doc"))

            document = await self.generator.generate_module_summary(
                parsed_file, file_data.get("patch")
            )
            state.generated.append((document, parsed_file, "module_summary"))

        pr_summary = await self.generator.generate_pr_summary(
            state.pull_request.repo_full_name,
            state.pull_request.pr_number,
            state.parsed_files,
        )
        state.generated.append((pr_summary, None, "pr_summary"))

        release_notes = await self.generator.generate_release_notes(
            state.pull_request.repo_full_name,
            state.pull_request.pr_number,
            state.parsed_files,
        )
        state.generated.append((release_notes, None, "release_notes"))

        intelligence, reports = self.intelligence.analyze(
            state.pull_request.repo_full_name,
            state.pull_request.pr_number,
            state.changed_files,
            state.parsed_files,
        )
        review_result, review_report = self.reviewer.review(
            state.changed_files,
            state.parsed_files,
            intelligence,
        )
        state.intelligence_metrics = intelligence.metrics
        state.review_result = review_result
        report_types = [
            "pr_summary",
            "risk_report",
            "security_report",
            "impact_analysis",
            "quality_report",
        ]
        for report, artifact_type in zip(reports, report_types, strict=True):
            state.generated.append((report, None, artifact_type))
        state.generated.append((review_report, None, "review_report"))

    async def _persist_and_validate(self, session: AsyncSession, state: DocumentationState) -> None:
        scores: list[float] = []
        for document, parsed_file, artifact_type in state.generated:
            evaluation = self.evaluator.score(document.content, parsed_file)
            artifact = DocumentationArtifact(
                pull_request_id=state.pull_request.id,
                artifact_type=ArtifactType(artifact_type),
                path=parsed_file.path if parsed_file else self._report_path(document),
                title=document.title,
                content=document.content,
                model=document.model,
                prompt_version=document.prompt_version,
                quality_score=evaluation.score,
            )
            session.add(artifact)
            await session.flush()
            state.artifacts.append(artifact)
            scores.append(evaluation.score)

            if parsed_file:
                for outcome in self.validator.run(document.content, parsed_file):
                    session.add(
                        ValidationResult(
                            artifact_id=artifact.id,
                            validator=outcome.validator,
                            passed=outcome.passed,
                            score=outcome.score,
                            details=outcome.details,
                        )
                    )

        state.quality_score = round(sum(scores) / len(scores), 2) if scores else 0
        await self.metrics.record(
            session,
            state.pull_request.id,
            "documentation_quality_score",
            state.quality_score,
            {"artifact_count": len(state.artifacts)},
        )
        for name, value in state.intelligence_metrics.items():
            await self.metrics.record(
                session,
                state.pull_request.id,
                name,
                value,
                {"source": "pr_intelligence"},
            )

    async def _create_approvals(self, session: AsyncSession, state: DocumentationState) -> None:
        for artifact in state.artifacts:
            approval = await self.approvals.create_pending(session, artifact.id)
            state.approvals.append(approval)

    async def _persist_review(self, session: AsyncSession, state: DocumentationState) -> None:
        if not state.review_result:
            return

        review = PullRequestReview(
            pull_request_id=state.pull_request.id,
            decision=state.review_result.decision,
            confidence_score=state.review_result.confidence_score,
            risk_summary=state.review_result.risk_summary,
            security_summary=state.review_result.security_summary,
            improvement_suggestions=state.review_result.improvement_suggestions,
        )
        session.add(review)
        await session.flush()

        for comment in state.review_result.comments:
            session.add(
                ReviewComment(
                    review_id=review.id,
                    path=comment.path,
                    line=comment.line,
                    category=comment.category,
                    severity=comment.severity,
                    issue=comment.issue,
                    suggestion=comment.suggestion,
                )
            )
        await session.commit()

    @staticmethod
    def _scoped_file(parsed_file: ParsedFile, symbol: Symbol) -> ParsedFile:
        return ParsedFile(
            path=parsed_file.path,
            language=parsed_file.language,
            symbols=[symbol],
            imports=parsed_file.imports,
            errors=parsed_file.errors,
        )

    @staticmethod
    def _report_path(document: GeneratedDocument) -> str | None:
        return document.title if document.title.endswith(".md") else None


def build_langgraph_workflow() -> Any:
    """Expose the intended LangGraph topology for production workers.

    The imperative workflow above is used for local determinism. This graph gives teams a clear
    upgrade path to distributed nodes, checkpoints, interrupts, and reviewer gates.
    """
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        return None

    graph = StateGraph(dict)
    graph.add_node("extract_changed_files", lambda state: state)
    graph.add_node("parse_ast", lambda state: state)
    graph.add_node("generate_docs", lambda state: state)
    graph.add_node("validate_docs", lambda state: state)
    graph.add_node("self_review", lambda state: state)
    graph.add_node("human_approval", lambda state: state)
    graph.add_node("publish", lambda state: state)

    graph.set_entry_point("extract_changed_files")
    graph.add_edge("extract_changed_files", "parse_ast")
    graph.add_edge("parse_ast", "generate_docs")
    graph.add_edge("generate_docs", "validate_docs")
    graph.add_edge("validate_docs", "self_review")
    graph.add_edge("self_review", "human_approval")
    graph.add_conditional_edges(
        "human_approval",
        lambda state: "publish" if state.get("approved") else END,
        {"publish": "publish", END: END},
    )
    graph.add_edge("publish", END)
    return graph.compile()
