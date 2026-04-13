from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SavedQueryCreate(BaseModel):
    title: str
    natural_language_query: str
    generated_code: Optional[str] = None
    result_summary: Optional[str] = None


class SavedQueryUpdate(BaseModel):
    title: Optional[str] = None
    natural_language_query: Optional[str] = None
    generated_code: Optional[str] = None
    result_summary: Optional[str] = None


class SavedQueryResponse(BaseModel):
    id: int
    title: str
    natural_language_query: str
    generated_code: Optional[str] = None
    result_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SavedQueryList(BaseModel):
    total: int
    items: list[SavedQueryResponse]
