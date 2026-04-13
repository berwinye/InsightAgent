from typing import Generator
from sqlalchemy.orm import Session
from app.core.database import RWSessionLocal


def get_rw_db() -> Generator[Session, None, None]:
    db = RWSessionLocal()
    try:
        yield db
    finally:
        db.close()
