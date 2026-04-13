from typing import Any, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from app.services.analytics_service import (
    get_employee_performance,
    get_product_ranking,
    get_sales_trend,
    get_store_sales_summary,
)
from app.services.agent_service import analyze_question
from app.services.saved_queries_service import create_saved_query
from app.schemas.skills import AnalyzeRequest, AnalyzeResponse
from app.schemas.saved_queries import SavedQueryCreate
from app.core.security import verify_api_key
from app.db.rw_session import get_rw_db
from app.models.analysis_logs import AnalysisLog
from app.models.agent_turn import AgentTurn

router = APIRouter(prefix="/analytics", tags=["Analytics"], dependencies=[Depends(verify_api_key)])


@router.get(
    "/store-sales-summary",
    summary="Total & average sales by office/store",
    response_model=list[dict[str, Any]],
)
def store_sales_summary():
    return get_store_sales_summary()


@router.get(
    "/product-ranking",
    summary="Product revenue ranking",
    response_model=list[dict[str, Any]],
)
def product_ranking(limit: int = Query(20, ge=1, le=100)):
    return get_product_ranking(limit=limit)


@router.get(
    "/employee-performance",
    summary="Sales performance per employee",
    response_model=list[dict[str, Any]],
)
def employee_performance():
    return get_employee_performance()


@router.get(
    "/sales-trend",
    summary="Monthly sales trend (optionally filtered by year)",
    response_model=list[dict[str, Any]],
)
def sales_trend(year: Optional[int] = Query(None, description="Filter by year, e.g. 2004")):
    return get_sales_trend(year=year)


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Natural language analysis (Qwen agent self-loop)",
)
def analyze(payload: AnalyzeRequest, db: Session = Depends(get_rw_db)):
    result = analyze_question(payload.question, db=db)

    saved_id: Optional[int] = None
    if result.get("generated_code"):
        sq = create_saved_query(
            db,
            SavedQueryCreate(
                title=payload.question[:255],
                natural_language_query=payload.question,
                generated_code=result.get("generated_code"),
                result_summary=result.get("answer", "")[:2000],
            ),
        )
        saved_id = sq.id

    return AnalyzeResponse(
        answer=result["answer"],
        iterations=result["iterations"],
        generated_code=result.get("generated_code"),
        saved_query_id=saved_id,
        tool_trace=result.get("tool_trace", []),
        log_id=result.get("log_id"),
    )


@router.get(
    "/logs",
    summary="List all analysis logs",
    response_model=list[dict[str, Any]],
    tags=["Analytics"],
)
def list_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_rw_db),
):
    rows = (
        db.query(AnalysisLog)
        .order_by(AnalysisLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "query_text": r.query_text,
            "status": r.status,
            "iterations": r.iterations,
            "final_answer": r.final_answer,
            "created_at": str(r.created_at),
        }
        for r in rows
    ]


@router.get(
    "/logs/{log_id}/turns",
    summary="Get every saved LLM turn for an analysis run",
    response_model=list[dict[str, Any]],
    tags=["Analytics"],
)
def get_turns(log_id: int, db: Session = Depends(get_rw_db)):
    log = db.query(AnalysisLog).filter(AnalysisLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail=f"Analysis log {log_id} not found.")
    turns = (
        db.query(AgentTurn)
        .filter(AgentTurn.log_id == log_id)
        .order_by(AgentTurn.iteration, AgentTurn.id)
        .all()
    )
    return [
        {
            "id": t.id,
            "iteration": t.iteration,
            "tool_name": t.tool_name,
            "llm_content": t.llm_content,
            "tool_input": t.tool_input,
            "tool_output": t.tool_output,
            "created_at": str(t.created_at),
        }
        for t in turns
    ]
