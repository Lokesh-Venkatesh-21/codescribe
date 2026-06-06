import logging
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings
from app.parsers.base import ParsedFile, Symbol
from app.services.llm_providers import BaseLLMProvider, build_llm_provider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeneratedDocument:
    title: str
    content: str
    model: str
    structured_output: dict[str, Any]
    prompt_version: str = "v1"


class DocumentationGenerator:
    def __init__(self, settings: Settings, provider: BaseLLMProvider | None = None) -> None:
        self.settings = settings
        self.provider = provider or build_llm_provider(settings)

    async def generate_function_documentation(
        self,
        parsed_file: ParsedFile,
        symbol: Symbol,
        patch: str | None,
    ) -> GeneratedDocument:
        context = self._context(parsed_file, patch, target_symbol=symbol)
        prompt = self._prompt(
            task="function-level documentation",
            context=context,
            instructions=(
                "Document the target function. Include behavior, parameters, return value, "
                "side effects, edge cases, and reviewer notes when inferable from the diff."
            ),
        )
        structured = await self.provider.generate_json(prompt, context)
        return self._document(
            title=f"Function documentation: {symbol.name}",
            structured=structured,
        )

    async def generate_class_documentation(
        self,
        parsed_file: ParsedFile,
        symbol: Symbol,
        patch: str | None,
    ) -> GeneratedDocument:
        context = self._context(parsed_file, patch, target_symbol=symbol)
        prompt = self._prompt(
            task="class documentation",
            context=context,
            instructions=(
                "Document the target class. Include responsibility, important methods, state, "
                "collaborators, lifecycle, and risks when inferable from the diff."
            ),
        )
        structured = await self.provider.generate_json(prompt, context)
        return self._document(
            title=f"Class documentation: {symbol.name}",
            structured=structured,
        )

    async def generate_module_summary(
        self, parsed_file: ParsedFile, patch: str | None
    ) -> GeneratedDocument:
        context = self._context(parsed_file, patch)
        prompt = self._prompt(
            task="module summary",
            context=context,
            instructions=(
                "Summarize the changed module. Cover changed functions/classes, behavior, "
                "risks, validation needs, and public API impact."
            ),
        )
        structured = await self.provider.generate_json(prompt, context)
        return self._document(
            title=f"Module summary: {parsed_file.path}",
            structured=structured,
        )

    async def generate_pr_summary(
        self, repo_full_name: str, pr_number: int, parsed_files: list[ParsedFile]
    ) -> GeneratedDocument:
        context = self._pr_context(repo_full_name, pr_number, parsed_files)
        prompt = self._prompt(
            task="pull request summary",
            context=context,
            instructions=(
                "Create a concise pull request summary for reviewers. Include what changed, "
                "important implementation details, changed functions, risks, and review focus."
            ),
        )
        structured = await self.provider.generate_json(prompt, context)
        return self._document(
            title=f"PR summary: {repo_full_name} #{pr_number}",
            structured=structured,
        )

    async def generate_release_notes(
        self, repo_full_name: str, pr_number: int, parsed_files: list[ParsedFile]
    ) -> GeneratedDocument:
        context = self._pr_context(repo_full_name, pr_number, parsed_files)
        prompt = self._prompt(
            task="release notes",
            context=context,
            instructions=(
                "Create release-note-ready copy. Focus on user-visible behavior, migrations, "
                "breaking changes, operational notes, and known risks."
            ),
        )
        structured = await self.provider.generate_json(prompt, context)
        return self._document(
            title=f"Release notes: {repo_full_name} #{pr_number}",
            structured=structured,
        )

    def _document(self, title: str, structured: dict[str, Any]) -> GeneratedDocument:
        return GeneratedDocument(
            title=title,
            content=self._render_markdown(structured),
            model=f"{self.provider.name}:{self.provider.model}",
            structured_output=structured,
        )

    def _context(
        self,
        parsed_file: ParsedFile,
        patch: str | None,
        target_symbol: Symbol | None = None,
    ) -> dict[str, Any]:
        return {
            "path": parsed_file.path,
            "language": parsed_file.language,
            "symbols": [symbol.__dict__ for symbol in parsed_file.symbols],
            "target_symbol": target_symbol.__dict__ if target_symbol else None,
            "imports": parsed_file.imports,
            "parse_errors": parsed_file.errors,
            "patch": patch or "",
        }

    def _pr_context(
        self,
        repo_full_name: str,
        pr_number: int,
        parsed_files: list[ParsedFile],
    ) -> dict[str, Any]:
        return {
            "repo_full_name": repo_full_name,
            "pr_number": pr_number,
            "files": [
                {
                    "path": parsed_file.path,
                    "language": parsed_file.language,
                    "symbols": [symbol.__dict__ for symbol in parsed_file.symbols],
                    "parse_errors": parsed_file.errors,
                }
                for parsed_file in parsed_files
            ],
            "symbols": [
                symbol.__dict__ for parsed_file in parsed_files for symbol in parsed_file.symbols
            ],
        }

    @staticmethod
    def _prompt(task: str, context: dict[str, Any], instructions: str) -> str:
        return (
            "You are CodeScribe, an AI documentation generator for GitHub pull requests.\n"
            "Return only valid JSON with these keys: summary, generated_docs, "
            "changed_functions, risks, confidence_score.\n"
            "generated_docs should be an array of objects with name, kind, and documentation "
            "when documenting symbols, or concise strings for PR-level artifacts.\n"
            "Use only facts supported by the AST metadata and diff. Avoid inventing behavior.\n"
            f"Task: {task}\n"
            f"Instructions: {instructions}\n"
            f"Context JSON:\n{context}"
        )

    @staticmethod
    def _render_markdown(structured: dict[str, Any]) -> str:
        docs = structured.get("generated_docs") or []
        changed_functions = structured.get("changed_functions") or []
        risks = structured.get("risks") or []
        confidence_score = structured.get("confidence_score", 0.5)

        doc_lines: list[str] = []
        for item in docs:
            if isinstance(item, dict):
                name = item.get("name", "Generated item")
                kind = item.get("kind", "doc")
                documentation = item.get("documentation", "")
                doc_lines.append(f"- `{name}` ({kind}): {documentation}")
            else:
                doc_lines.append(f"- {item}")

        function_lines = [f"- `{name}`" for name in changed_functions] or ["- None detected"]
        risk_lines = [f"- {risk}" for risk in risks] or ["- No material risks detected"]

        return (
            "## Summary\n"
            f"{structured.get('summary', '')}\n\n"
            "## Changes\n"
            "The change touches the files and symbols detected by the analysis pipeline.\n\n"
            "## Documented symbols\n"
            f"{chr(10).join(doc_lines) if doc_lines else '- No generated docs returned'}\n\n"
            "## Changed functions\n"
            f"{chr(10).join(function_lines)}\n\n"
            "## Risks\n"
            f"{chr(10).join(risk_lines)}\n\n"
            "## Confidence\n"
            f"{confidence_score:.2f}\n\n"
            "## Review notes\n"
            "A human reviewer should confirm intent, edge cases, and public API impact "
            "before publishing."
        )
