from app.parsers.base import SupportedLanguage
from app.services.ast_analysis import ASTAnalyzer


def test_python_ast_analyzer_extracts_symbols() -> None:
    parsed = ASTAnalyzer().analyze(
        "service.py",
        "class Billing:\n    pass\n\nasync def calculate_total(amount):\n    return amount\n",
    )

    assert parsed.language == SupportedLanguage.PYTHON
    assert {symbol.name for symbol in parsed.symbols} == {"Billing", "calculate_total"}


def test_patch_source_ignores_diff_metadata() -> None:
    parsed = ASTAnalyzer().analyze_patch(
        "service.py",
        "@@ -0,0 +1,2 @@\n+def ship_order(order_id):\n+    return order_id\n",
    )

    assert [symbol.name for symbol in parsed.symbols] == ["ship_order"]
