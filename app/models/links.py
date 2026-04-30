"""Link models for many-to-many relationships."""

from typing import Optional
from sqlmodel import SQLModel, Field


class EntitySourceLink(SQLModel, table=True):
    """Link table between entities and their sources."""

    __tablename__ = "entity_sources"
    entity_id: Optional[int] = Field(default=None, foreign_key="entities.id", primary_key=True)
    source_id: Optional[int] = Field(default=None, foreign_key="sources.id", primary_key=True)


class NewsEntityLink(SQLModel, table=True):
    """Link table between news items and extracted entities."""

    __tablename__ = "news_entities"
    news_id: Optional[int] = Field(default=None, foreign_key="news_items.id", primary_key=True)
    entity_id: Optional[int] = Field(default=None, foreign_key="entities.id", primary_key=True)
