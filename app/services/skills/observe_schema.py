"""Skill 1: observe_schema — returns the full database schema via the read-only account."""
from typing import Any
from app.db.mysql_schema_reader import read_schema


def observe_schema() -> dict[str, Any]:
    """Return structured schema information for all business tables."""
    return read_schema()
