"""Pydantic schemas for the newsroom API."""

from pydantic import BaseModel

from typing import Optional, List, Dict, Any
from datetime import datetime


class SourceBase(BaseModel):
    """Base schema for a news source."""

    name: str
    type: str
    subtype: Optional[str] = None
    config: Dict[str, Any]
    icon: Optional[str] = None
    health_status: str = "OK"
    active: bool = True


class SourceCreate(SourceBase):
    """Schema for creating a news source."""

    pass


class SourceResponse(SourceBase):
    """Response schema for a news source."""

    id: int

    class Config:
        """Pydantic config for SourceResponse."""

        from_attributes = True


class EntityBase(BaseModel):
    """Base schema for an entity."""

    name: str
    type: str


class EntityCreate(EntityBase):
    """Schema for creating an entity."""

    source_ids: List[int] = []
    aliases: List[str] = []


class EntityResponse(EntityBase):
    """Response schema for an entity, including related sources."""

    id: int
    is_ignored: bool = False
    aliases: List[str] = []
    sources: List[SourceResponse] = []

    class Config:
        """Pydantic config for EntityResponse."""

        from_attributes = True


class EntitySimpleResponse(BaseModel):
    """Simplified response schema for an entity."""

    id: int
    name: str
    type: str
    is_ignored: bool = False

    class Config:
        """Pydantic config for EntitySimpleResponse."""

        from_attributes = True


class NewsItemBase(BaseModel):
    """Base schema for a news item."""

    title: str
    url: str
    published_date: Optional[str] = None
    status: str = "DISCOVERED"


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

    class Config:
        """Pydantic config for NewsItemResponse."""

        from_attributes = True


class NewsItemStatusUpdate(BaseModel):
    """Schema for updating a news item status."""

    status: str


class AgentConfigBase(BaseModel):
    """Base schema for system configuration."""

    key: str
    value: str


class AgentConfigCreate(AgentConfigBase):
    """Schema for creating system configuration."""

    pass


class AgentConfigResponse(AgentConfigBase):
    """Response schema for system configuration."""

    class Config:
        """Pydantic config for AgentConfigResponse."""

        from_attributes = True


class BatchIdRequest(BaseModel):
    """Request schema for batch operations involving IDs."""

    ids: List[int]


class AIConfigSettings(BaseModel):
    """Schema for AI-related configuration settings."""

    api_key: Optional[str] = None
    system_prompt: Optional[str] = None


class EntityTypeBase(BaseModel):
    """Base schema for an entity type."""

    name: str
    color: str


class EntityTypeCreate(EntityTypeBase):
    """Schema for creating an entity type."""

    pass


class EntityTypeResponse(EntityTypeBase):
    """Response schema for an entity type."""

    id: int

    class Config:
        """Pydantic config for EntityTypeResponse."""

        from_attributes = True
