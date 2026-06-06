from app.parsers.base import ParsedFile, SupportedLanguage, detect_language
from app.parsers.pattern_parser import PatternParser
from app.parsers.python_parser import PythonParser


class ASTAnalyzer:
    def __init__(self) -> None:
        self.parsers = {
            SupportedLanguage.PYTHON: PythonParser(),
            SupportedLanguage.GO: PatternParser(SupportedLanguage.GO),
            SupportedLanguage.JAVA: PatternParser(SupportedLanguage.JAVA),
            SupportedLanguage.TYPESCRIPT: PatternParser(SupportedLanguage.TYPESCRIPT),
        }

    def analyze(self, path: str, source: str) -> ParsedFile:
        language = detect_language(path)
        parser = self.parsers.get(language)
        if parser is None:
            return ParsedFile(path=path, language=SupportedLanguage.UNKNOWN)
        return parser.parse(path, source)

    def analyze_patch(self, path: str, patch: str | None) -> ParsedFile:
        source = self._source_from_patch(patch or "")
        return self.analyze(path, source)

    @staticmethod
    def _source_from_patch(patch: str) -> str:
        lines = []
        for line in patch.splitlines():
            if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
                continue
            if line.startswith("+"):
                lines.append(line[1:])
            elif line.startswith(" "):
                lines.append(line[1:])
        return "\n".join(lines)
