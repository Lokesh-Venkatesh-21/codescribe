import pytest

from app.cli import changed_files_from_diff, generate_reports
from app.core.config import Settings


def test_changed_files_from_diff_parses_patch_metadata() -> None:
    diff = """diff --git a/app/service.py b/app/service.py
index 111..222 100644
--- a/app/service.py
+++ b/app/service.py
@@ -1,2 +1,3 @@
+def quote(quantity):
+    return quantity * 10
"""

    files = changed_files_from_diff(diff)

    assert files == [
        {
            "filename": "app/service.py",
            "status": "modified",
            "patch": diff.rstrip("\n"),
            "additions": 2,
            "deletions": 0,
        }
    ]


@pytest.mark.asyncio
async def test_generate_reports_without_webhook_server(tmp_path) -> None:
    changed_files = [
        {
            "filename": "app/service.py",
            "status": "modified",
            "patch": "@@\n+def quote(quantity):\n+    return quantity * 10\n",
            "additions": 2,
            "deletions": 0,
        }
    ]

    written = await generate_reports(
        repo="acme/widgets",
        pr_number=1,
        changed_files=changed_files,
        output_dir=tmp_path,
        settings=Settings(llm_provider="local_fallback"),
    )

    names = {path.name for path in written}
    assert {
        "documentation_report.md",
        "risk_report.md",
        "security_report.md",
        "review_report.md",
    }.issubset(names)


def test_github_actions_mode_config() -> None:
    settings = Settings(codescribe_mode="github_action", post_pr_comment=False)

    assert settings.codescribe_mode == "github_action"
    assert not settings.post_pr_comment
