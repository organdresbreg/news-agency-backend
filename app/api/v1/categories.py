"""API endpoints for managing news source categories."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.services.database import database_service
from app.models.categories import Category
from app.schemas.categories import CategoryCreate, CategoryResponse

router = APIRouter()


def get_db():
    """Dependency to get a database session."""
    with database_service.get_session_maker() as session:
        yield session


@router.get("/", response_model=List[CategoryResponse])
def list_categories(session: Session = Depends(get_db)):
    """List all categories."""
    categories = session.exec(select(Category)).all()

    # Seed default categories if none exist
    if not categories:
        initial_names = [
            "General",
            "Medio Oriente",
            "Unión Europea",
            "BRICS+",
            "Norteamérica",
            "Latinoamérica",
            "Asia-Pacífico",
            "África",
            "Organismos Int.",
        ]
        for name in initial_names:
            cat = Category(name=name, is_predefined=True)
            session.add(cat)
        session.commit()
        categories = session.exec(select(Category)).all()

    return categories


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(category_in: CategoryCreate, session: Session = Depends(get_db)):
    """Create a new category."""
    # Check if exists
    existing = session.exec(select(Category).where(Category.name == category_in.name)).first()
    if existing:
        return existing

    category = Category.model_validate(category_in)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.delete("/{category_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_name: str, session: Session = Depends(get_db)):
    """Delete a category by name."""
    category = session.exec(select(Category).where(Category.name == category_name)).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Don't delete General
    if category.name == "General":
        raise HTTPException(status_code=400, detail="Cannot delete General category")

    session.delete(category)
    session.commit()
    return None
