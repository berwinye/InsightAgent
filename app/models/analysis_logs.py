from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class AnalysisLog(Base):
    __tablename__ = "analysis_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    query_text = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="running")
    error_type = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    iterations = Column(Integer, default=0)
    final_answer = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
