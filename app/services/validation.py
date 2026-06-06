from dataclasses import dataclass

from app.parsers.base import ParsedFile


@dataclass(frozen=True)
class ValidationOutcome:
    validator: str
    passed: bool
    score: float
    details: dict


class ASTStructureValidator:
    name = "ast_structure"

    def validate(self, content: str, parsed_file: ParsedFile) -> ValidationOutcome:
        missing_symbols = [
            symbol.name
            for symbol in parsed_file.symbols
            if symbol.kind in {"function", "class"} and symbol.name not in content
        ]
        score = (
            1.0
            if not parsed_file.symbols
            else 1 - (len(missing_symbols) / len(parsed_file.symbols))
        )
        return ValidationOutcome(
            validator=self.name,
            passed=score >= 0.8 and not parsed_file.errors,
            score=round(max(score, 0), 2),
            details={"missing_symbols": missing_symbols, "parse_errors": parsed_file.errors},
        )


class CompletenessValidator:
    name = "documentation_completeness"

    def validate(self, content: str, parsed_file: ParsedFile) -> ValidationOutcome:
        required_markers = ["Summary", "Changes"]
        if parsed_file.symbols:
            required_markers.append("Documented symbols")
        missing = [marker for marker in required_markers if marker not in content]
        score = 1 - (len(missing) / len(required_markers))
        return ValidationOutcome(
            validator=self.name,
            passed=score >= 0.75,
            score=round(score, 2),
            details={"missing_sections": missing},
        )


class HallucinationValidator:
    name = "hallucination_detection"

    RISKY_PHRASES = (
        "guarantees",
        "always secure",
        "zero downtime",
        "impossible to fail",
        "proves",
    )

    def validate(self, content: str, parsed_file: ParsedFile) -> ValidationOutcome:
        risky = [phrase for phrase in self.RISKY_PHRASES if phrase in content.lower()]
        symbol_names = {symbol.name for symbol in parsed_file.symbols}
        code_like_tokens = {
            token.strip("`()[]{}.,:")
            for token in content.split()
            if token.startswith("`") and token.endswith("`")
        }
        unknown_symbols = sorted(
            token
            for token in code_like_tokens
            if token and token not in symbol_names and "." not in token
        )
        score = 1.0 - min(0.8, len(risky) * 0.2 + len(unknown_symbols) * 0.1)
        return ValidationOutcome(
            validator=self.name,
            passed=score >= 0.75,
            score=round(score, 2),
            details={"risky_phrases": risky, "unknown_symbols": unknown_symbols},
        )


class ValidationPipeline:
    def __init__(self) -> None:
        self.validators = [
            ASTStructureValidator(),
            CompletenessValidator(),
            HallucinationValidator(),
        ]

    def run(self, content: str, parsed_file: ParsedFile) -> list[ValidationOutcome]:
        return [validator.validate(content, parsed_file) for validator in self.validators]
