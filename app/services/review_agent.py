import re
from dataclasses import dataclass
from typing import Any

from app.db.models import ReviewDecision
from app.parsers.base import ParsedFile
from app.services.generators import GeneratedDocument
from app.services.pr_intelligence import PRIntelligenceResult


@dataclass(frozen=True)
class InlineReviewComment:
    path: str
    line: int
    category: str
    severity: str
    issue: str
    suggestion: str


@dataclass(frozen=True)
class ReviewResult:
    decision: ReviewDecision
    confidence_score: float
    comments: list[InlineReviewComment]
    risk_summary: str
    security_summary: str
    improvement_suggestions: list[str]


class ReviewAgent:
    def review(
        self,
        changed_files: list[dict[str, Any]],
        parsed_files: list[ParsedFile],
        intelligence: PRIntelligenceResult,
    ) -> tuple[ReviewResult, GeneratedDocument]:
        comments = self._comments(changed_files, parsed_files, intelligence)
        decision = self._decision(comments, intelligence)
        confidence = self._confidence(comments, intelligence)
        result = ReviewResult(
            decision=decision,
            confidence_score=confidence,
            comments=comments,
            risk_summary=self._risk_summary(intelligence),
            security_summary=self._security_summary(intelligence),
            improvement_suggestions=self._suggestions(comments, intelligence),
        )
        return result, GeneratedDocument(
            title="review_report.md",
            content=self._report_markdown(result),
            model="review_agent:deterministic",
            structured_output={
                "decision": result.decision,
                "confidence_score": result.confidence_score,
                "comment_count": len(result.comments),
            },
        )

    def _comments(
        self,
        changed_files: list[dict[str, Any]],
        parsed_files: list[ParsedFile],
        intelligence: PRIntelligenceResult,
    ) -> list[InlineReviewComment]:
        comments: list[InlineReviewComment] = []
        for file_data in changed_files:
            path = file_data["filename"]
            added_lines = self._added_lines(file_data.get("patch") or "")
            for line_number, line in added_lines:
                comments.extend(self._line_comments(path, line_number, line))

        comments.extend(self._testing_comments(changed_files, parsed_files))
        comments.extend(self._security_comments(intelligence))
        return self._dedupe(comments)

    def _line_comments(
        self,
        path: str,
        line_number: int,
        line: str,
    ) -> list[InlineReviewComment]:
        lowered = line.lower()
        comments: list[InlineReviewComment] = []
        if "print(" in lowered and not path.lower().startswith("tests/"):
            comments.append(
                InlineReviewComment(
                    path=path,
                    line=line_number,
                    category="code_quality",
                    severity="Low",
                    issue="Debug output appears in changed production code.",
                    suggestion="Use structured logging or remove the debug statement before merge.",
                )
            )
        if re.search(r"\bexcept\s*:", line):
            comments.append(
                InlineReviewComment(
                    path=path,
                    line=line_number,
                    category="maintainability",
                    severity="Medium",
                    issue="Bare exception handlers can hide real failures.",
                    suggestion="Catch a specific exception type and preserve useful error context.",
                )
            )
        if "select *" in lowered:
            comments.append(
                InlineReviewComment(
                    path=path,
                    line=line_number,
                    category="performance",
                    severity="Medium",
                    issue="Unbounded column selection can increase query cost and data exposure.",
                    suggestion="Select only the columns needed by the caller.",
                )
            )
        if re.search(r"subprocess\.(run|popen|call).*shell\s*=\s*true|os\.system\(", lowered):
            comments.append(
                InlineReviewComment(
                    path=path,
                    line=line_number,
                    category="security",
                    severity="High",
                    issue="Shell execution with interpolated input can enable command injection.",
                    suggestion=(
                        "Avoid shell=True and pass arguments as a list after validating inputs."
                    ),
                )
            )
        if re.search(r"(?i)(secret|password|api[_-]?key|token)\s*=\s*['\"][^'\"]{8,}", line):
            comments.append(
                InlineReviewComment(
                    path=path,
                    line=line_number,
                    category="security",
                    severity="High",
                    issue="The diff appears to add a hardcoded secret or credential.",
                    suggestion="Move secrets to environment variables or a managed secret store.",
                )
            )
        if "todo" in lowered or "fixme" in lowered:
            comments.append(
                InlineReviewComment(
                    path=path,
                    line=line_number,
                    category="maintainability",
                    severity="Low",
                    issue="The change introduces unresolved follow-up work.",
                    suggestion="Resolve the TODO or link it to a tracked issue with ownership.",
                )
            )
        return comments

    def _testing_comments(
        self,
        changed_files: list[dict[str, Any]],
        parsed_files: list[ParsedFile],
    ) -> list[InlineReviewComment]:
        has_source_change = any(
            parsed_file.language != "unknown" and parsed_file.symbols
            for parsed_file in parsed_files
        )
        has_test_change = any(
            self._is_test_file(file_data["filename"]) for file_data in changed_files
        )
        if not has_source_change or has_test_change:
            return []

        first_source = next(
            file_data
            for file_data in changed_files
            if not self._is_test_file(file_data["filename"])
        )
        return [
            InlineReviewComment(
                path=first_source["filename"],
                line=self._first_added_line(first_source.get("patch") or ""),
                category="testing",
                severity="Medium",
                issue="Source behavior changed without a corresponding test file update.",
                suggestion="Add or update tests that cover the changed behavior and edge cases.",
            )
        ]

    @staticmethod
    def _security_comments(intelligence: PRIntelligenceResult) -> list[InlineReviewComment]:
        comments: list[InlineReviewComment] = []
        for finding in intelligence.security_findings:
            comments.append(
                InlineReviewComment(
                    path=finding.path,
                    line=finding.line or 1,
                    category="security",
                    severity=finding.severity.title(),
                    issue=finding.detail,
                    suggestion=f"Address `{finding.rule}` before publishing this change.",
                )
            )
        return comments

    @staticmethod
    def _decision(
        comments: list[InlineReviewComment],
        intelligence: PRIntelligenceResult,
    ) -> ReviewDecision:
        if any(comment.severity == "High" for comment in comments):
            return ReviewDecision.REQUEST_CHANGES
        if intelligence.risk.score >= 65 or any(
            comment.severity == "Medium" for comment in comments
        ):
            return ReviewDecision.NEEDS_HUMAN_REVIEW
        return ReviewDecision.APPROVE

    @staticmethod
    def _confidence(
        comments: list[InlineReviewComment],
        intelligence: PRIntelligenceResult,
    ) -> float:
        base = 0.86
        base -= min(0.25, intelligence.risk.score / 400)
        base -= min(0.2, len(comments) * 0.03)
        return round(max(0.35, min(0.95, base)), 2)

    @staticmethod
    def _risk_summary(intelligence: PRIntelligenceResult) -> str:
        drivers = ", ".join(intelligence.risk.drivers)
        return f"Risk score {intelligence.risk.score}/100. Drivers: {drivers}."

    @staticmethod
    def _security_summary(intelligence: PRIntelligenceResult) -> str:
        if not intelligence.security_findings:
            return "No security findings detected by static review rules."
        return f"{len(intelligence.security_findings)} security finding(s) detected."

    @staticmethod
    def _suggestions(
        comments: list[InlineReviewComment],
        intelligence: PRIntelligenceResult,
    ) -> list[str]:
        suggestions = [comment.suggestion for comment in comments]
        if intelligence.risk.score >= 50:
            suggestions.append("Use a staged rollout and monitor key service metrics after deploy.")
        return list(dict.fromkeys(suggestions)) or ["No blocking improvements identified."]

    @staticmethod
    def _report_markdown(result: ReviewResult) -> str:
        comments = (
            "\n".join(
                f"- `{comment.severity}` `{comment.path}:{comment.line}` "
                f"{comment.issue} Suggested improvement: {comment.suggestion}"
                for comment in result.comments
            )
            or "- No inline comments generated"
        )
        suggestions = "\n".join(f"- {suggestion}" for suggestion in result.improvement_suggestions)
        return (
            "# AI Review Report\n\n"
            f"## Decision\n{result.decision}\n\n"
            f"## Confidence\n{result.confidence_score:.2f}\n\n"
            f"## Risk Summary\n{result.risk_summary}\n\n"
            f"## Security Findings\n{result.security_summary}\n\n"
            f"## Inline Comments\n{comments}\n\n"
            f"## Improvement Suggestions\n{suggestions}\n"
        )

    @staticmethod
    def _added_lines(patch: str) -> list[tuple[int, str]]:
        added: list[tuple[int, str]] = []
        new_line_number = 1
        for line in patch.splitlines():
            if line.startswith("@@"):
                match = re.search(r"\+(\d+)", line)
                new_line_number = int(match.group(1)) if match else 1
                continue
            if line.startswith("+") and not line.startswith("+++"):
                added.append((new_line_number, line[1:]))
                new_line_number += 1
            elif line.startswith(" "):
                new_line_number += 1
        return added

    @staticmethod
    def _first_added_line(patch: str) -> int:
        added = ReviewAgent._added_lines(patch)
        return added[0][0] if added else 1

    @staticmethod
    def _is_test_file(path: str) -> bool:
        lowered = path.lower()
        return (
            "/test" in lowered
            or lowered.startswith("tests/")
            or lowered.endswith(("_test.go", ".spec.ts", ".test.ts"))
        )

    @staticmethod
    def _dedupe(comments: list[InlineReviewComment]) -> list[InlineReviewComment]:
        seen: set[tuple[str, int, str, str]] = set()
        deduped: list[InlineReviewComment] = []
        for comment in comments:
            key = (comment.path, comment.line, comment.category, comment.issue)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(comment)
        return deduped
