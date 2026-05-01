"""Database model for news source categories."""

from typing import Optional
from sqlmodel import SQLModel, Field
from .base import BaseModel


class Category(BaseModel, table=True):
    """Represents a category for news sources."""

    __tablename__ = "categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    is_predefined: bool = Field(default=False)
