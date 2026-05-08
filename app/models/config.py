"""Database models for system configuration."""

from typing import Optional
from sqlmodel import SQLModel, Field


class AgentConfig(SQLModel, table=True):
    """System configuration keys and values."""

    __tablename__ = "agent_config"

    key: str = Field(primary_key=True, index=True)
    value: Optional[str] = None
