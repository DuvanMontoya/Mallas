from __future__ import annotations


class RuleSchemaError(ValueError):
    """Raised when a rule JSON value cannot be parsed as the versioned AST."""

    def __init__(self, message: str, *, path: str = "$") -> None:
        self.path = path
        super().__init__(f"{path}: {message}")


class RuleEvaluationError(ValueError):
    """Raised when an evaluation context violates its exact arithmetic contract."""
