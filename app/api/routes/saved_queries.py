from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.rw_session import get_rw_db
from app.schemas.saved_queries import (
    SavedQueryCreate,
    SavedQueryList,
    SavedQueryResponse,
    SavedQueryUpdate,
)
from app.services.saved_queries_service import (
    create_saved_query,
    delete_saved_query,
    get_saved_query,
    list_saved_queries,
    update_saved_query,
)

router = APIRouter(prefix="/saved-queries", tags=["Saved Queries"])


@router.post(
    "",
    response_model=SavedQueryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a saved query",
)
def create_endpoint(payload: SavedQueryCreate, db: Session = Depends(get_rw_db)):
    return create_saved_query(db, payload)


@router.get("", response_model=SavedQueryList, summary="List saved queries")
def list_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_rw_db),
):
    return list_saved_queries(db, skip=skip, limit=limit)


@router.get("/{query_id}", response_model=SavedQueryResponse, summary="Get saved query by ID")
def get_endpoint(query_id: int, db: Session = Depends(get_rw_db)):
    return get_saved_query(db, query_id)


@router.put("/{query_id}", response_model=SavedQueryResponse, summary="Update saved query")
def update_endpoint(
    query_id: int, payload: SavedQueryUpdate, db: Session = Depends(get_rw_db)
):
    return update_saved_query(db, query_id, payload)


@router.delete(
    "/{query_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete saved query",
)
def delete_endpoint(query_id: int, db: Session = Depends(get_rw_db)):
    delete_saved_query(db, query_id)
