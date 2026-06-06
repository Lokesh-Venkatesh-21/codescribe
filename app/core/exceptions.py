class CodeScribeError(Exception):
    """Base application exception."""


class ExternalServiceError(CodeScribeError):
    """Raised when a third-party system fails."""
