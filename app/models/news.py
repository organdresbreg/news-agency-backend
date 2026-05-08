"""Database models for news items."""

from typing import Optional, List, Dict, Any, TYPE_CHECKING

from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON, Text

if TYPE_CHECKING:
    from .entities import Entity

# --- Link Models (Tablas intermedias para Many-to-Many) ---

from .links import NewsEntityLink

# --- Modelos Principales ---

from .sources import Source, SourceHealth


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

    # Propagación de Calidad de la Fuente
    trust_score: float = Field(default=50.0)
    tier: int = Field(default=3)

    # Relaciones
    source: Optional["Source"] = Relationship(back_populates="news_items")
    entities: List["Entity"] = Relationship(back_populates="news_items", link_model=NewsEntityLink)
