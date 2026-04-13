from typing import Generator
from sqlalchemy.orm import Session
from app.core.database import ROSessionLocal


def get_ro_db() -> Generator[Session, None, None]:
    db = ROSessionLocal()
    try:
        yield db
    finally:
        db.close()
