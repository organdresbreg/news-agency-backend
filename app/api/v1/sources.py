"""API endpoints for managing news sources."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlmodel import Session
import requests
import feedparser
from datetime import datetime, timezone

from app.services.database import database_service
from app.models.sources import Source
from app.schemas import sources as schemas
from app.core.logging import logger

router = APIRouter()


def get_db():
    """Dependency to get a database session."""
    with database_service.get_session_maker() as session:
        yield session


@router.get("", response_model=List[schemas.SourceResponse])
def read_sources(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieves a list of news sources."""
    return db.query(Source).offset(skip).limit(limit).all()


@router.post("/test", response_model=schemas.SourceTestResponse)
def test_source(request: schemas.SourceTestRequest):
    """Tests a source URL to validate parsing and suggest frequency."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(request.url, headers=headers, timeout=10)
        response.raise_for_status()

        feed = feedparser.parse(response.content)
        if not feed.entries:
            return schemas.SourceTestResponse(
                success=False, message="No se encontraron artículos. Asegúrate de que sea un feed RSS/Atom válido."
            )

        titles = [entry.get("title", "Sin título") for entry in feed.entries[:3]]

        # Calcular frecuencia sugerida basada en los últimos 10 posts
        suggested_freq = 60
        if len(feed.entries) >= 2:
            dates = []
            for entry in feed.entries[:10]:
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        dates.append(datetime(*entry.published_parsed[:6]).replace(tzinfo=timezone.utc))
                    except Exception:
                        pass

            if len(dates) >= 2:
                dates.sort(reverse=True)
                diffs = [(dates[i] - dates[i + 1]).total_seconds() / 60 for i in range(len(dates) - 1)]
                avg_diff = sum(diffs) / len(diffs)
                # Limitar entre 10 minutos y 24 horas (1440 mins)
                suggested_freq = max(10, min(1440, int(avg_diff)))

        return schemas.SourceTestResponse(
            success=True,
            message="Feed validado y parseado correctamente.",
            suggested_frequency_minutes=suggested_freq,
            recent_titles=titles,
        )

    except requests.exceptions.RequestException as e:
        return schemas.SourceTestResponse(success=False, message=f"Error de red al contactar la URL: {str(e)}")
    except Exception as e:
        return schemas.SourceTestResponse(success=False, message=f"Error inesperado al parsear la fuente: {str(e)}")


@router.post("", response_model=schemas.SourceResponse)
def create_source(source: schemas.SourceCreate, db: Session = Depends(get_db)):
    """Creates a new news source."""
    db_source = Source(**source.model_dump())
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source


@router.put("/{source_id}", response_model=schemas.SourceResponse)
def update_source(source_id: int, source: schemas.SourceCreate, db: Session = Depends(get_db)):
    """Updates an existing news source."""
    db_source = db.query(Source).filter(Source.id == source_id).first()
    if db_source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    for key, value in source.model_dump().items():
        setattr(db_source, key, value)

    db.commit()
    db.refresh(db_source)
    return db_source


@router.delete("/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    """Deletes a news source."""
    db_source = db.query(Source).filter(Source.id == source_id).first()
    if db_source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(db_source)
    db.commit()
    return {"ok": True}
