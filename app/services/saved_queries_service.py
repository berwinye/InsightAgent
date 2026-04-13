from sqlalchemy.orm import Session
from app.models.saved_queries import SavedQuery
from app.schemas.saved_queries import SavedQueryCreate, SavedQueryUpdate
from app.core.exceptions import NotFoundError


def create_saved_query(db: Session, payload: SavedQueryCreate) -> SavedQuery:
    obj = SavedQuery(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_saved_queries(db: Session, skip: int = 0, limit: int = 100) -> dict:
    total = db.query(SavedQuery).count()
    items = (
        db.query(SavedQuery)
        .order_by(SavedQuery.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {"total": total, "items": items}


def get_saved_query(db: Session, query_id: int) -> SavedQuery:
    obj = db.query(SavedQuery).filter(SavedQuery.id == query_id).first()
    if not obj:
        raise NotFoundError("SavedQuery", query_id)
    return obj


def update_saved_query(
    db: Session, query_id: int, payload: SavedQueryUpdate
) -> SavedQuery:
    obj = get_saved_query(db, query_id)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_saved_query(db: Session, query_id: int) -> None:
    obj = get_saved_query(db, query_id)
    db.delete(obj)
    db.commit()
