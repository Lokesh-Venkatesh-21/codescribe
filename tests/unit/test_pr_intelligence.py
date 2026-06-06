from app.parsers.base import ParsedFile, SupportedLanguage, Symbol
from app.services.pr_intelligence import ChangeType, PRIntelligenceEngine


def test_pr_intelligence_classifies_scores_and_detects_security() -> None:
    changed_files = [
        {
            "filename": "app/auth.py",
            "status": "modified",
            "patch": (
                "@@ -1,0 +1,3 @@\n"
                '+API_KEY = "super-secret-token"\n'
                "+def login(user_id):\n"
                '+    return db.execute(f"select * from users where id={user_id}")\n'
            ),
            "additions": 3,
            "deletions": 0,
        },
        {
            "filename": ".github/workflows/deploy.yml",
            "status": "modified",
            "patch": "@@\n+permissions: write-all\n",
            "additions": 1,
            "deletions": 0,
        },
    ]
    parsed_files = [
        ParsedFile(
            path="app/auth.py",
            language=SupportedLanguage.PYTHON,
            symbols=[
                Symbol(name="AuthService", kind="class"),
                Symbol(name="login", kind="function"),
            ],
        )
    ]

    result, reports = PRIntelligenceEngine().analyze(
        "acme/widgets",
        99,
        changed_files,
        parsed_files,
    )

    assert ChangeType.SECURITY in result.classifications
    assert ChangeType.INFRASTRUCTURE in result.classifications
    assert result.risk.score >= 40
    assert result.security_findings
    assert result.dependency_graph.modified_functions == ["app/auth.py:login"]
    assert result.dependency_graph.impacted_classes == ["app/auth.py:AuthService"]
    assert result.quality.security_score < 100
    assert {report.title for report in reports} == {
        "pr_summary.md",
        "risk_report.md",
        "security_report.md",
        "impact_analysis.md",
        "quality_report.md",
    }
