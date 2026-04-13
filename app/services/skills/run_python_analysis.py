"""Orchestrates the safe execution of user-supplied Python analysis code."""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.skills.ast_guard import check_code

WORKER_SCRIPT = Path(__file__).parent / "python_worker.py"
EXECUTION_TIMEOUT = 30


def run_python_analysis(code: str) -> dict[str, Any]:
    """
    1. Run AST guard — reject immediately if code is unsafe.
    2. Launch isolated subprocess worker.
    3. Pass code via stdin, collect stdout.
    4. Return structured success or error response.
    """
    violation = check_code(code)
    if violation is not None:
        return {
            "status": "blocked",
            "error_type": violation.error_type,
            "message": violation.message,
            "hint": "Use only pandas, numpy, math, statistics, datetime, re. "
                    "Call read_sql() to query the database.",
        }

    env = {
        **os.environ,
        "DB_RO_URL": settings.RO_DATABASE_URL,
    }

    try:
        proc = subprocess.run(
            [sys.executable, str(WORKER_SCRIPT)],
            input=json.dumps({"code": code}),
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "error_type": "EXECUTION_TIMEOUT",
            "message": f"Execution exceeded {EXECUTION_TIMEOUT} seconds.",
            "hint": "Simplify the query or reduce the dataset size.",
        }

    raw_out = proc.stdout.strip()
    raw_err = proc.stderr.strip()

    if not raw_out:
        return {
            "status": "failed",
            "error_type": "WORKER_ERROR",
            "message": raw_err or "Worker produced no output.",
        }

    last_line = raw_out.splitlines()[-1]
    try:
        result = json.loads(last_line)
    except json.JSONDecodeError:
        return {
            "status": "failed",
            "error_type": "WORKER_ERROR",
            "message": f"Could not parse worker output: {raw_out[:500]}",
        }

    return result
