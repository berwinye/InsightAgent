from typing import Any, Union
from fastapi import APIRouter, Depends, status

from app.core.security import verify_api_key

from app.schemas.skills import RunPythonRequest, RunPythonSuccess, RunPythonError
from app.services.skills.observe_schema import observe_schema
from app.services.skills.run_python_analysis import run_python_analysis

router = APIRouter(prefix="/skills", tags=["Skills"], dependencies=[Depends(verify_api_key)])


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
        from fastapi import HTTPException

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
    response_model=Union[RunPythonSuccess, RunPythonError],
    responses={
        200: {
            "description": "Execution result (success or structured error)",
        }
    },
)
def run_python_analysis_endpoint(payload: RunPythonRequest):
    return run_python_analysis(payload.code)
