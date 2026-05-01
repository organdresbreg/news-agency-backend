"""Pydantic schemas for news source categories."""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class CategoryBase(BaseModel):
    """Base schema for a news source category."""

    name: str
    is_predefined: bool = False


class CategoryCreate(CategoryBase):
    """Schema for creating a new category."""

    pass


class CategoryResponse(CategoryBase):
    """Response schema for a news source category."""

    id: int

    model_config = ConfigDict(from_attributes=True)
