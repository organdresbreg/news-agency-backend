"""Database models for entities and entity types."""

from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON, Text

if TYPE_CHECKING:
    from .sources import Source
    from .news import NewsItem

from .links import EntitySourceLink, NewsEntityLink


class Entity(SQLModel, table=True):
    """Represents a named entity (Person, Org, etc.) detected in news."""

    __tablename__ = "entities"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    type: Optional[str] = None
    is_ignored: bool = Field(default=False)
    aliases: List[str] = Field(default_factory=list, sa_column=Column(JSON))

    # Entity Linking Fields
    wikidata_id: Optional[str] = Field(default=None, unique=True, index=True)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    image_url: Optional[str] = None
    wikipedia_url: Optional[str] = None

    # Relaciones
    sources: List["Source"] = Relationship(back_populates="entities", link_model=EntitySourceLink)
    news_items: List["NewsItem"] = Relationship(back_populates="entities", link_model=NewsEntityLink)


class EntityType(SQLModel, table=True):
    """Predefined categories for entities (e.g., Person, Place)."""

    __tablename__ = "entity_types"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    color: str
