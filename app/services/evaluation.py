from dataclasses import dataclass

from app.parsers.base import ParsedFile


@dataclass(frozen=True)
class EvaluationResult:
    score: float
    dimensions: dict[str, float]
    notes: list[str]


class DocumentationEvaluator:
    def score(self, content: str, parsed_file: ParsedFile | None = None) -> EvaluationResult:
        dimensions = {
            "specificity": self._specificity(content, parsed_file),
            "structure": self._structure(content),
            "completeness": self._completeness(content, parsed_file),
        }
        score = round(sum(dimensions.values()) / len(dimensions), 2)
        notes = [name for name, value in dimensions.items() if value < 0.7]
        return EvaluationResult(score=score, dimensions=dimensions, notes=notes)

    @staticmethod
    def _structure(content: str) -> float:
        sections = sum(1 for marker in ("##", "- ", "###") if marker in content)
        return min(1.0, 0.4 + sections * 0.25)

    @staticmethod
    def _specificity(content: str, parsed_file: ParsedFile | None) -> float:
        if not parsed_file or not parsed_file.symbols:
            return 0.75 if len(content) > 80 else 0.45
        matches = sum(1 for symbol in parsed_file.symbols if symbol.name in content)
        return min(1.0, matches / max(len(parsed_file.symbols), 1))

    @staticmethod
    def _completeness(content: str, parsed_file: ParsedFile | None) -> float:
        has_summary = "Summary" in content or len(content.split()) > 35
        has_behavior = any(word in content.lower() for word in ("returns", "raises", "side effect"))
        has_symbols = bool(parsed_file and parsed_file.symbols)
        base = 0.35 + (0.25 if has_summary else 0) + (0.2 if has_behavior else 0)
        return min(1.0, base + (0.2 if has_symbols else 0.1))
