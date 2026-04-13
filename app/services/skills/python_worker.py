"""
Isolated Python worker process.

This script is launched as a subprocess by run_python_analysis.py.
It receives a JSON payload on stdin:
    {"code": "<python source>"}

It executes the code in a controlled namespace that provides:
    - read_sql(sql, params=(), max_rows=50000) -> pandas.DataFrame
    - whitelisted imports: pandas, numpy, math, statistics, datetime, re
    - restricted builtins (no open, eval, exec, compile, __import__, input)

All output must go through print() to stdout.
On completion it writes a JSON result to stdout (last line):
    {"status": "success", "stdout": "...", "summary": {"line_count": N}}
or
    {"status": "failed", "error_type": "...", "message": "..."}
"""
import sys
import os
import json
import io
import traceback
import builtins

import re as _re

import pandas as pd
import sqlalchemy
from sqlalchemy import text

_ALLOWED_SQL_START = ("select", "with")
_FORBIDDEN_SQL_RE = _re.compile(
    r"\binsert\b|\bupdate\b|\bdelete\b|\bdrop\b|\balter\b|\bcreate\b"
    r"|\btruncate\b|\bgrant\b|\brevoke\b|\bload\s+data\b"
    r"|\binto\s+outfile\b|\binto\s+dumpfile\b",
    _re.IGNORECASE | _re.DOTALL,
)


def _check_sql(sql: str) -> None:
    stripped = sql.strip().lower()
    if not any(stripped.startswith(k) for k in _ALLOWED_SQL_START):
        raise RuntimeError(f"Only SELECT / WITH queries are allowed.")
    match = _FORBIDDEN_SQL_RE.search(sql)
    if match:
        raise RuntimeError(f"Forbidden SQL keyword detected: '{match.group()}'.")


def _build_read_sql(engine: sqlalchemy.engine.Engine):
    def read_sql(
        sql: str,
        params: tuple | dict = (),
        max_rows: int = 50_000,
    ) -> pd.DataFrame:
        _check_sql(sql)

        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params if params else None)

        if len(df) > max_rows:
            raise RuntimeError(
                f"Query returned {len(df):,} rows, exceeding limit of {max_rows:,}."
            )
        return df

    return read_sql


_ALLOWED_IMPORT_TOPS: frozenset[str] = frozenset(
    {"pandas", "numpy", "math", "statistics", "datetime", "re"}
)


def _make_safe_import():
    _real_import = builtins.__import__

    def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        top = name.split(".")[0]
        if top not in _ALLOWED_IMPORT_TOPS:
            raise ImportError(f"Import of '{name}' is not allowed in the analysis sandbox.")
        return _real_import(name, globals, locals, fromlist, level)

    return _safe_import


def _safe_builtins() -> dict:
    _allowed_names = {
        "abs", "all", "any", "bin", "bool", "callable", "chr", "dict",
        "dir", "divmod", "enumerate", "filter", "float", "format",
        "frozenset", "getattr", "hasattr", "hash", "hex", "id", "int",
        "isinstance", "issubclass", "iter", "len", "list", "map", "max",
        "min", "next", "object", "oct", "ord", "pow", "print", "range",
        "repr", "reversed", "round", "set", "setattr", "slice", "sorted",
        "str", "sum", "super", "tuple", "type", "zip",
        "True", "False", "None",
        "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
        "RuntimeError", "StopIteration", "NotImplementedError",
        "ArithmeticError", "ZeroDivisionError", "OverflowError",
    }
    safe = {name: getattr(builtins, name) for name in _allowed_names if hasattr(builtins, name)}
    safe["__build_class__"] = builtins.__build_class__
    safe["__import__"] = _make_safe_import()
    return safe


def main() -> None:
    payload_raw = sys.stdin.read()
    try:
        payload = json.loads(payload_raw)
        code = payload["code"]
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": "INVALID_INPUT", "message": str(exc)}))
        return

    db_url = os.environ.get("DB_RO_URL", "")
    if not db_url:
        print(json.dumps({"status": "failed", "error_type": "CONFIG_ERROR", "message": "DB_RO_URL not set"}))
        return

    try:
        engine = sqlalchemy.create_engine(db_url, pool_pre_ping=True)
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": "DB_CONNECT_ERROR", "message": str(exc)}))
        return

    read_sql = _build_read_sql(engine)

    import math
    import statistics
    import datetime
    import re
    import numpy as np

    namespace: dict = {
        "__builtins__": _safe_builtins(),
        "pd": pd,
        "np": np,
        "math": math,
        "statistics": statistics,
        "datetime": datetime,
        "re": re,
        "read_sql": read_sql,
    }

    stdout_capture = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_capture

    try:
        exec(compile(code, "<user_code>", "exec"), namespace)  # noqa: S102
        sys.stdout = old_stdout
        captured = stdout_capture.getvalue()
        lines = [l for l in captured.splitlines() if l]
        result = {
            "status": "success",
            "stdout": captured,
            "summary": {"line_count": len(lines)},
        }
    except Exception:
        sys.stdout = old_stdout
        tb = traceback.format_exc()
        result = {
            "status": "failed",
            "error_type": "EXECUTION_ERROR",
            "message": tb,
        }
    finally:
        sys.stdout = old_stdout
        try:
            engine.dispose()
        except Exception:
            pass

    print(json.dumps(result))


if __name__ == "__main__":
    main()
