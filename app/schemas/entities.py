"""Pydantic schemas for entities."""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List

from .sources import SourceResponse


class EntityBase(BaseModel):
    """Base schema for an entity."""

    name: str
    type: Optional[str] = None


class EntityCreate(EntityBase):
    """Schema for creating an entity."""

    source_ids: List[int] = []
    aliases: List[str] = []


class EntityResponse(EntityBase):
    """Response schema for an entity, including related sources."""

    id: int
    is_ignored: bool = False
    aliases: List[str] = []

    wikidata_id: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    wikipedia_url: Optional[str] = None

    sources: List[SourceResponse] = []
    model_config = ConfigDict(from_attributes=True)


class EntitySimpleResponse(BaseModel):
    """Simplified response schema for an entity."""

    id: int
    name: str
    type: str
    is_ignored: bool = False
    wikidata_id: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    wikipedia_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


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
    model_config = ConfigDict(from_attributes=True)
