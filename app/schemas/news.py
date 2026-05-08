"""Pydantic schemas for news items."""

from pydantic import BaseModel, ConfigDict

from typing import Optional, List, Dict, Any
from datetime import datetime


from .sources import SourceResponse
from .entities import EntitySimpleResponse


class NewsItemBase(BaseModel):
    """Base schema for a news item."""

    title: str
    url: str
    published_date: Optional[str] = None
    status: str = "DISCOVERED"
    trust_score: float = 50.0
    tier: int = 3


class NewsItemCreate(NewsItemBase):
    """Schema for creating a news item."""

    source_id: int


class NewsItemResponse(NewsItemBase):
    """Response schema for a news item, including extracted entities."""

    id: int
    source_id: int
    source: Optional[SourceResponse] = None
    created_at: datetime
    language: Optional[str] = None
    content_snippet: Optional[str] = None
    title_es: Optional[str] = None
    content_es: Optional[str] = None

    entities: List[EntitySimpleResponse] = []
    model_config = ConfigDict(from_attributes=True)


class NewsItemStatusUpdate(BaseModel):
    """Schema for updating a news item status."""

    status: str


class BatchIdRequest(BaseModel):
    """Request schema for batch operations involving IDs."""

    ids: List[int]
