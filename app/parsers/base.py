from dataclasses import dataclass, field
from enum import StrEnum


class SupportedLanguage(StrEnum):
    PYTHON = "python"
    GO = "go"
    JAVA = "java"
    TYPESCRIPT = "typescript"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str
    line: int | None = None
    signature: str | None = None
    docstring: str | None = None


@dataclass(frozen=True)
class ParsedFile:
    path: str
    language: SupportedLanguage
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Parser:
    language: SupportedLanguage = SupportedLanguage.UNKNOWN

    def parse(self, path: str, source: str) -> ParsedFile:
        raise NotImplementedError


EXTENSION_LANGUAGE_MAP = {
    ".py": SupportedLanguage.PYTHON,
    ".go": SupportedLanguage.GO,
    ".java": SupportedLanguage.JAVA,
    ".ts": SupportedLanguage.TYPESCRIPT,
    ".tsx": SupportedLanguage.TYPESCRIPT,
}


def detect_language(path: str) -> SupportedLanguage:
    for extension, language in EXTENSION_LANGUAGE_MAP.items():
        if path.endswith(extension):
            return language
    return SupportedLanguage.UNKNOWN
