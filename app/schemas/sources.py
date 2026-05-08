"""Pydantic schemas for news sources."""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class SourceBase(BaseModel):
    """Base schema for a news source."""

    name: str
    url: str
    type: str = "RSS"
    subtype: Optional[str] = None
    icon: Optional[str] = None
    active: bool = True
    category: str = "General"

    health_status: str = "HEALTHY"
    last_fetch_attempt: Optional[datetime] = None
    last_successful_fetch: Optional[datetime] = None
    consecutive_errors: int = 0
    last_error: Optional[str] = None

    tier: int = 3
    trust_score: float = 50.0
    fetch_frequency_minutes: int = 60
    scraping_strategy: str = "rss_only"
    etag: Optional[str] = None
    last_modified_header: Optional[str] = None


class SourceCreate(SourceBase):
    """Schema for creating a news source."""

    pass


class SourceResponse(SourceBase):
    """Response schema for a news source."""

    id: int
    model_config = ConfigDict(from_attributes=True)


class SourceTestRequest(BaseModel):
    """Schema for requesting a test of a news source."""

    url: str


class SourceTestResponse(BaseModel):
    """Response schema for a source test."""

    success: bool
    message: str
    suggested_frequency_minutes: Optional[int] = None
    recent_titles: List[str] = []
