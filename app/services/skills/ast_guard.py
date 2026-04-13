"""AST-based static analysis guard for user-submitted Python code."""
import ast
from typing import Optional

ALLOWED_IMPORTS: frozenset[str] = frozenset(
    {"pandas", "numpy", "math", "statistics", "datetime", "re"}
)

FORBIDDEN_CALLS: frozenset[str] = frozenset(
    {"open", "eval", "exec", "compile", "__import__", "input"}
)


class SecurityViolation(Exception):
    def __init__(self, error_type: str, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(message)


def _check_import(node: ast.Import) -> None:
    for alias in node.names:
        top = alias.name.split(".")[0]
        if top not in ALLOWED_IMPORTS:
            raise SecurityViolation(
                "SECURITY_VIOLATION",
                f"Import of module '{alias.name}' is not allowed. "
                f"Allowed modules: {sorted(ALLOWED_IMPORTS)}.",
            )


def _check_import_from(node: ast.ImportFrom) -> None:
    if node.module is None:
        return
    top = node.module.split(".")[0]
    if top not in ALLOWED_IMPORTS:
        raise SecurityViolation(
            "SECURITY_VIOLATION",
            f"Import of module '{node.module}' is not allowed. "
            f"Allowed modules: {sorted(ALLOWED_IMPORTS)}.",
        )


def _check_call(node: ast.Call) -> None:
    if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
        raise SecurityViolation(
            "SECURITY_VIOLATION",
            f"Call to '{node.func.id}()' is not allowed.",
        )
    if isinstance(node.func, ast.Attribute):
        attr = node.func.attr
        if attr in FORBIDDEN_CALLS:
            raise SecurityViolation(
                "SECURITY_VIOLATION",
                f"Call to '.{attr}()' is not allowed.",
            )


def check_code(code: str) -> Optional[SecurityViolation]:
    """Parse code and perform AST security checks.

    Returns a SecurityViolation if any check fails, or None if the code passes.
    Raises SyntaxError if the code cannot be parsed.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return SecurityViolation("SYNTAX_ERROR", f"SyntaxError: {exc}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            try:
                _check_import(node)
            except SecurityViolation as e:
                return e
        elif isinstance(node, ast.ImportFrom):
            try:
                _check_import_from(node)
            except SecurityViolation as e:
                return e
        elif isinstance(node, ast.Call):
            try:
                _check_call(node)
            except SecurityViolation as e:
                return e

    return None
