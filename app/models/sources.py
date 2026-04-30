"""Database models for news sources."""

import enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Text, JSON
from .links import EntitySourceLink


class SourceHealth(str, enum.Enum):
    """Enumeration for the health status of a news source."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    BANNED = "BANNED"


class Source(SQLModel, table=True):
    """Represents a news source (RSS, etc.) with professional gatekeeping capabilities."""

    __tablename__ = "sources"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    url: str = Field(unique=True, index=True)
    type: str = Field(default="RSS")
    subtype: Optional[str] = None
    icon: Optional[str] = None
    active: bool = Field(default=True)
    category: str = Field(default="General", index=True)

    # --- Métricas de Salud (Health & Observability) ---
    health_status: SourceHealth = Field(default=SourceHealth.HEALTHY)
    last_fetch_attempt: Optional[datetime] = None
    last_successful_fetch: Optional[datetime] = None
    consecutive_errors: int = Field(default=0)
    last_error: Optional[str] = Field(default=None, sa_column=Column(Text))

    # --- Gobernanza y Confianza (Trust & Governance) ---
    tier: int = Field(default=3, description="1: Oficial/Primaria, 2: Agregador, 3: Blog/Secundaria")
    trust_score: float = Field(default=50.0, description="Puntuación de fiabilidad del 1 al 100")

    # --- Reglas de Consumo y Caché (Ingestion Rules) ---
    fetch_frequency_minutes: int = Field(default=60)
    scraping_strategy: str = Field(default="rss_only")
    etag: Optional[str] = None
    last_modified_header: Optional[str] = None

    # Relaciones - Usamos strings para tipos pero la clase real para el link_model
    entities: List["Entity"] = Relationship(back_populates="sources", link_model=EntitySourceLink)  # noqa: F821
    news_items: List["NewsItem"] = Relationship(back_populates="source")  # noqa: F821
