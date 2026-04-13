from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings


rw_engine = create_engine(
    settings.RW_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)

ro_engine = create_engine(
    settings.RO_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)

RWSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=rw_engine)
ROSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ro_engine)


class Base(DeclarativeBase):
    pass
