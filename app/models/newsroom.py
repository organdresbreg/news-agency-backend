"""Database models for the newsroom system."""

from typing import Optional, List, Dict, Any

from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON, Text

# --- Link Models (Tablas intermedias para Many-to-Many) ---


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


# --- Modelos Principales ---


class Source(SQLModel, table=True):
    """Represents a news source (RSS, etc.)."""

    __tablename__ = "sources"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str] = Field(default=None, index=True)
    type: Optional[str] = None
    subtype: Optional[str] = None
    # Para JSON en SQLModel, le decimos a SQLAlchemy explícitamente que use su tipo JSON
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    icon: Optional[str] = None
    health_status: str = Field(default="OK")
    active: bool = Field(default=True)

    # Relaciones
    entities: List["Entity"] = Relationship(back_populates="sources", link_model=EntitySourceLink)
    news_items: List["NewsItem"] = Relationship(back_populates="source")


class Entity(SQLModel, table=True):
    """Represents a named entity (Person, Org, etc.) detected in news."""

    __tablename__ = "entities"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    type: Optional[str] = None
    is_ignored: bool = Field(default=False)
    aliases: List[str] = Field(default_factory=list, sa_column=Column(JSON))

    # Relaciones
    sources: List["Source"] = Relationship(back_populates="entities", link_model=EntitySourceLink)
    news_items: List["NewsItem"] = Relationship(back_populates="entities", link_model=NewsEntityLink)


class NewsItem(SQLModel, table=True):
    """Represents a single news article or post."""

    __tablename__ = "news_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: Optional[int] = Field(default=None, foreign_key="sources.id", index=True)
    title: Optional[str] = Field(default=None, index=True)
    url: Optional[str] = Field(default=None, unique=True, index=True)
    published_date: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="DISCOVERED")
    language: Optional[str] = None
    content_snippet: Optional[str] = None

    # Para textos largos, forzamos el tipo Text
    full_content: Optional[str] = Field(default=None, sa_column=Column(Text))
    title_es: Optional[str] = None
    content_es: Optional[str] = Field(default=None, sa_column=Column(Text))

    entities_extracted: bool = Field(default=False)

    # Relaciones
    source: Optional["Source"] = Relationship(back_populates="news_items")
    entities: List["Entity"] = Relationship(back_populates="news_items", link_model=NewsEntityLink)


class AgentConfig(SQLModel, table=True):
    """System configuration keys and values."""

    __tablename__ = "agent_config"

    key: str = Field(primary_key=True, index=True)
    value: Optional[str] = None


class EntityType(SQLModel, table=True):
    """Predefined categories for entities (e.g., Person, Place)."""

    __tablename__ = "entity_types"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    color: str
