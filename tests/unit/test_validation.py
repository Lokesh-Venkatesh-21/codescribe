from app.parsers.base import ParsedFile, SupportedLanguage, Symbol
from app.services.validation import ValidationPipeline


def test_validation_pipeline_passes_symbol_coverage() -> None:
    parsed = ParsedFile(
        path="billing.py",
        language=SupportedLanguage.PYTHON,
        symbols=[Symbol(name="Invoice", kind="class"), Symbol(name="total", kind="function")],
    )
    content = (
        "## Summary\nDocuments billing behavior.\n\n"
        "## Changes\nAdds `Invoice` and `total`.\n\n"
        "## Documented symbols\n- Invoice\n- total"
    )

    outcomes = ValidationPipeline().run(content, parsed)

    assert all(outcome.passed for outcome in outcomes)


def test_validation_pipeline_flags_missing_symbols() -> None:
    parsed = ParsedFile(
        path="billing.py",
        language=SupportedLanguage.PYTHON,
        symbols=[Symbol(name="Invoice", kind="class"), Symbol(name="total", kind="function")],
    )
    content = "## Summary\nDocuments billing.\n\n## Changes\nAdds a service."

    outcomes = ValidationPipeline().run(content, parsed)

    ast_result = next(outcome for outcome in outcomes if outcome.validator == "ast_structure")
    assert not ast_result.passed
    assert ast_result.details["missing_symbols"] == ["Invoice", "total"]
