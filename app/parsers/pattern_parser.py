import re

from app.parsers.base import ParsedFile, Parser, SupportedLanguage, Symbol


class PatternParser(Parser):
    """Lightweight fallback parser for languages that should later use tree-sitter."""

    def __init__(self, language: SupportedLanguage) -> None:
        self.language = language

    def parse(self, path: str, source: str) -> ParsedFile:
        patterns = {
            SupportedLanguage.GO: [
                ("function", re.compile(r"func\s+(?:\([^)]+\)\s*)?(\w+)\s*\(([^)]*)\)")),
                ("class", re.compile(r"type\s+(\w+)\s+struct\b")),
            ],
            SupportedLanguage.JAVA: [
                ("class", re.compile(r"\b(?:class|interface|enum)\s+(\w+)")),
                (
                    "function",
                    re.compile(
                        r"\b(?:public|private|protected)?\s*(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\("
                    ),
                ),
            ],
            SupportedLanguage.TYPESCRIPT: [
                ("class", re.compile(r"\b(?:class|interface|type)\s+(\w+)")),
                ("function", re.compile(r"\b(?:function\s+)?(\w+)\s*=\s*(?:async\s*)?\(")),
                ("function", re.compile(r"\bfunction\s+(\w+)\s*\(")),
            ],
        }.get(self.language, [])

        symbols: list[Symbol] = []
        for line_number, line in enumerate((source or "").splitlines(), start=1):
            for kind, pattern in patterns:
                match = pattern.search(line)
                if match:
                    symbols.append(
                        Symbol(
                            name=match.group(1),
                            kind=kind,
                            line=line_number,
                            signature=line.strip(),
                        )
                    )

        return ParsedFile(path=path, language=self.language, symbols=symbols)
