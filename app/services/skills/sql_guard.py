"""SQL safety guard for the read_sql() helper injected into the analysis sandbox."""
import re

ALLOWED_START: tuple[str, ...] = ("select", "with")

FORBIDDEN_KEYWORDS: list[str] = [
    r"\binsert\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\balter\b",
    r"\bcreate\b",
    r"\btruncate\b",
    r"\bgrant\b",
    r"\brevoke\b",
    r"\bload\s+data\b",
    r"\binto\s+outfile\b",
    r"\binto\s+dumpfile\b",
]

_FORBIDDEN_RE = re.compile(
    "|".join(FORBIDDEN_KEYWORDS), re.IGNORECASE | re.DOTALL
)


class SQLSecurityError(Exception):
    pass


def check_sql(sql: str) -> None:
    """Raise SQLSecurityError if the SQL is not a safe read-only query."""
    stripped = sql.strip().lower()

    if not any(stripped.startswith(k) for k in ALLOWED_START):
        raise SQLSecurityError(
            f"Only SELECT / WITH queries are allowed. Got: '{stripped[:40]}...'"
        )

    match = _FORBIDDEN_RE.search(sql)
    if match:
        raise SQLSecurityError(
            f"Forbidden SQL keyword detected: '{match.group()}'."
        )
