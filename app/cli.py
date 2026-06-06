import argparse
import asyncio
import subprocess
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.ast_analysis import ASTAnalyzer
from app.services.generators import DocumentationGenerator
from app.services.github import GitHubClient
from app.services.pr_intelligence import PRIntelligenceEngine
from app.services.review_agent import ReviewAgent


def main() -> None:
    parser = argparse.ArgumentParser(prog="codescribe")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze = subparsers.add_parser(
        "analyze-pr",
        help="Analyze a pull request from a local git diff",
    )
    analyze.add_argument("--repo", required=True)
    analyze.add_argument("--pr-number", type=int, required=True)
    analyze.add_argument("--base-ref", required=True)
    analyze.add_argument("--head-ref", required=True)
    analyze.add_argument("--output-dir", default="codescribe-reports")
    analyze.add_argument("--post-comment", default="false")

    args = parser.parse_args()
    if args.command == "analyze-pr":
        asyncio.run(
            analyze_pr_command(
                repo=args.repo,
                pr_number=args.pr_number,
                base_ref=args.base_ref,
                head_ref=args.head_ref,
                output_dir=Path(args.output_dir),
                post_comment=_parse_bool(args.post_comment),
            )
        )


async def analyze_pr_command(
    repo: str,
    pr_number: int,
    base_ref: str,
    head_ref: str,
    output_dir: Path,
    post_comment: bool = False,
) -> list[Path]:
    diff = _git_diff(base_ref, head_ref)
    changed_files = changed_files_from_diff(diff)
    return await generate_reports(
        repo=repo,
        pr_number=pr_number,
        changed_files=changed_files,
        output_dir=output_dir,
        post_comment=post_comment,
    )


async def generate_reports(
    repo: str,
    pr_number: int,
    changed_files: list[dict[str, Any]],
    output_dir: Path,
    post_comment: bool = False,
    settings: Settings | None = None,
) -> list[Path]:
    settings = settings or Settings()
    output_dir.mkdir(parents=True, exist_ok=True)
    analyzer = ASTAnalyzer()
    generator = DocumentationGenerator(settings)
    parsed_files = [
        analyzer.analyze_patch(file_data["filename"], file_data.get("patch"))
        for file_data in changed_files
    ]

    documentation_sections = []
    for parsed_file, file_data in zip(parsed_files, changed_files, strict=False):
        for symbol in parsed_file.symbols:
            if symbol.kind == "function":
                doc = await generator.generate_function_documentation(
                    parsed_file, symbol, file_data.get("patch")
                )
                documentation_sections.append(doc.content)
            elif symbol.kind == "class":
                doc = await generator.generate_class_documentation(
                    parsed_file, symbol, file_data.get("patch")
                )
                documentation_sections.append(doc.content)
        module_doc = await generator.generate_module_summary(parsed_file, file_data.get("patch"))
        documentation_sections.append(module_doc.content)

    intelligence, reports = PRIntelligenceEngine().analyze(
        repo,
        pr_number,
        changed_files,
        parsed_files,
    )
    review, review_report = ReviewAgent().review(changed_files, parsed_files, intelligence)
    del review

    written = [
        _write_report(
            output_dir / "documentation_report.md",
            "# Documentation Report\n\n" + "\n\n---\n\n".join(documentation_sections),
        )
    ]
    for report in reports:
        written.append(_write_report(output_dir / report.title, report.content))
    written.append(_write_report(output_dir / review_report.title, review_report.content))

    if post_comment:
        body = (output_dir / "pr_summary.md").read_text(encoding="utf-8")
        await GitHubClient(settings).create_pr_comment(repo, pr_number, body)

    return written


def changed_files_from_diff(diff: str) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    patch_lines: list[str] = []

    for line in diff.splitlines():
        if line.startswith("diff --git "):
            if current:
                current["patch"] = "\n".join(patch_lines)
                files.append(current)
            current = _file_from_diff_header(line)
            patch_lines = [line]
            continue
        if not current:
            continue
        patch_lines.append(line)
        if line.startswith("new file mode"):
            current["status"] = "added"
        elif line.startswith("deleted file mode"):
            current["status"] = "removed"
        elif line.startswith("+") and not line.startswith("+++"):
            current["additions"] += 1
        elif line.startswith("-") and not line.startswith("---"):
            current["deletions"] += 1

    if current:
        current["patch"] = "\n".join(patch_lines)
        files.append(current)

    return files


def _file_from_diff_header(line: str) -> dict[str, Any]:
    parts = line.split()
    filename = parts[-1][2:] if len(parts) >= 4 and parts[-1].startswith("b/") else parts[-1]
    return {
        "filename": filename,
        "status": "modified",
        "patch": "",
        "additions": 0,
        "deletions": 0,
    }


def _git_diff(base_ref: str, head_ref: str) -> str:
    range_spec = f"{base_ref}...{head_ref}"
    result = subprocess.run(
        ["git", "diff", "--find-renames", "--unified=80", range_spec],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _write_report(path: Path, content: str) -> Path:
    path.write_text(content + "\n", encoding="utf-8")
    return path


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


if __name__ == "__main__":
    main()
