"""Pydantic schemas for system configuration."""

from pydantic import BaseModel, ConfigDict
from typing import Optional


class AgentConfigBase(BaseModel):
    """Base schema for system configuration."""

    key: str
    value: str


class AgentConfigCreate(AgentConfigBase):
    """Schema for creating system configuration."""

    pass


class AgentConfigResponse(AgentConfigBase):
    """Response schema for system configuration."""

    model_config = ConfigDict(from_attributes=True)


class AIConfigSettings(BaseModel):
    """Schema for AI-related configuration settings."""

    api_key: Optional[str] = None
    system_prompt: Optional[str] = None
