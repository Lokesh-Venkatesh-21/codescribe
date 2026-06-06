from app.db.models import ReviewDecision
from app.parsers.base import ParsedFile, SupportedLanguage, Symbol
from app.services.pr_intelligence import PRIntelligenceEngine
from app.services.review_agent import ReviewAgent


def test_review_agent_generates_actionable_comments_and_decision() -> None:
    changed_files = [
        {
            "filename": "app/auth.py",
            "status": "modified",
            "patch": (
                "@@ -1,0 +1,4 @@\n"
                '+API_KEY = "super-secret-token"\n'
                "+def login(user_id):\n"
                "+    print(user_id)\n"
                '+    return db.execute(f"select * from users where id={user_id}")\n'
            ),
            "additions": 4,
            "deletions": 0,
        }
    ]
    parsed_files = [
        ParsedFile(
            path="app/auth.py",
            language=SupportedLanguage.PYTHON,
            symbols=[Symbol(name="login", kind="function")],
        )
    ]
    intelligence, _reports = PRIntelligenceEngine().analyze(
        "acme/widgets",
        1,
        changed_files,
        parsed_files,
    )

    review, report = ReviewAgent().review(changed_files, parsed_files, intelligence)

    assert review.decision == ReviewDecision.REQUEST_CHANGES
    assert review.confidence_score > 0
    assert any(comment.severity == "High" for comment in review.comments)
    assert any(comment.category == "testing" for comment in review.comments)
    assert report.title == "review_report.md"
    assert "Decision" in report.content
