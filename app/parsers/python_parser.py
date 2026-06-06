import ast

from app.parsers.base import ParsedFile, Parser, SupportedLanguage, Symbol


class PythonParser(Parser):
    language = SupportedLanguage.PYTHON

    def parse(self, path: str, source: str) -> ParsedFile:
        try:
            tree = ast.parse(source or "")
        except SyntaxError as exc:
            return ParsedFile(
                path=path,
                language=self.language,
                errors=[f"syntax_error:{exc.lineno}:{exc.msg}"],
            )

        symbols: list[Symbol] = []
        imports: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                symbols.append(
                    Symbol(
                        name=node.name,
                        kind="function",
                        line=node.lineno,
                        signature=self._function_signature(node),
                        docstring=ast.get_docstring(node),
                    )
                )
            elif isinstance(node, ast.ClassDef):
                symbols.append(
                    Symbol(
                        name=node.name,
                        kind="class",
                        line=node.lineno,
                        docstring=ast.get_docstring(node),
                    )
                )
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.extend(f"{module}.{alias.name}".strip(".") for alias in node.names)

        return ParsedFile(path=path, language=self.language, symbols=symbols, imports=imports)

    @staticmethod
    def _function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        args = [arg.arg for arg in node.args.args]
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")
        prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        return f"{prefix}def {node.name}({', '.join(args)})"
