from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import verify_api_key

from app.schemas.skills import RunPythonRequest, RunPythonSuccess
from app.services.skills.observe_schema import observe_schema
from app.services.skills.run_python_analysis import run_python_analysis

router = APIRouter(prefix="/skills", tags=["Skills"], dependencies=[Depends(verify_api_key)])

_ERROR_TYPE_TO_HTTP: dict[str, int] = {
    "SECURITY_VIOLATION": status.HTTP_403_FORBIDDEN,
    "SQL_BLOCKED":        status.HTTP_403_FORBIDDEN,
    "SYNTAX_ERROR":       status.HTTP_422_UNPROCESSABLE_ENTITY,
    "RUNTIME_ERROR":      status.HTTP_422_UNPROCESSABLE_ENTITY,
    "EXECUTION_ERROR":    status.HTTP_422_UNPROCESSABLE_ENTITY,
    "INVALID_INPUT":      status.HTTP_422_UNPROCESSABLE_ENTITY,
    "EXECUTION_TIMEOUT":  status.HTTP_408_REQUEST_TIMEOUT,
    "WORKER_ERROR":       status.HTTP_500_INTERNAL_SERVER_ERROR,
    "CONFIG_ERROR":       status.HTTP_500_INTERNAL_SERVER_ERROR,
    "DB_CONNECT_ERROR":   status.HTTP_500_INTERNAL_SERVER_ERROR,
}


@router.post(
    "/observe_schema",
    summary="Skill 1 – Observe database schema (read-only)",
    response_model=dict[str, Any],
    responses={
        500: {
            "description": "Schema read failed",
            "content": {
                "application/json": {
                    "example": {
                        "status": "failed",
                        "error_type": "SCHEMA_READ_ERROR",
                        "message": "Failed to inspect database schema.",
                    }
                }
            },
        }
    },
)
def observe_schema_endpoint():
    try:
        return observe_schema()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "failed",
                "error_type": "SCHEMA_READ_ERROR",
                "message": str(exc),
            },
        )


@router.post(
    "/run_python_analysis",
    summary="Skill 2 – Run Python analysis code in isolated sandbox",
    response_model=RunPythonSuccess,
    responses={
        200: {"description": "Code executed successfully"},
        403: {"description": "Code blocked by security policy (SECURITY_VIOLATION or SQL_BLOCKED)"},
        408: {"description": "Execution timed out (EXECUTION_TIMEOUT)"},
        422: {"description": "Syntax error or runtime exception in submitted code"},
        500: {"description": "Internal worker process error"},
    },
)
def run_python_analysis_endpoint(payload: RunPythonRequest):
    result = run_python_analysis(payload.code)
    if result.get("status") == "success":
        return result
    http_status = _ERROR_TYPE_TO_HTTP.get(
        result.get("error_type", ""), status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    raise HTTPException(status_code=http_status, detail=result)
