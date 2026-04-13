from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class AgentTurn(Base):
    __tablename__ = "agent_turns"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    log_id = Column(Integer, ForeignKey("analysis_logs.id"), nullable=False, index=True)
    iteration = Column(Integer, nullable=False)
    tool_name = Column(String(50), nullable=False)
    llm_content = Column(Text, nullable=True)
    tool_input = Column(Text, nullable=True)
    tool_output = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
