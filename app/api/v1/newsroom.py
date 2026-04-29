"""Newsroom API endpoints for managing sources, news items, and entities."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from typing import List
from sqlmodel import Session
from sqlalchemy.orm import joinedload
from sqlalchemy import text
from datetime import datetime

from app.services.database import database_service
from app.models.newsroom import Source, NewsItem, Entity, EntityType, AgentConfig
from app.schemas import newsroom as schemas
from app.services.newsroom import ingestor, translator, extractor
from app.core.logging import logger

router = APIRouter()


def get_db():
    """Dependency to get a database session."""
    with database_service.get_session_maker() as session:
        yield session


# --- Background Tasks Helpers ---


def auto_translate_background(new_item_ids: List[int]):
    """Helper to translate items. Extraction is handled internally by translator per batch."""
    with database_service.get_session_maker() as db:
        try:
            logger.info("auto_translate_background_started", count=len(new_item_ids))
            count = translator.process_pending_translations(db, new_item_ids)
            logger.info("auto_translate_background_completed", count=count)
        except Exception as e:
            logger.exception(
                "auto_translate_background_failed",
                new_item_ids=new_item_ids,
                error_type=type(e).__name__,
                error_message=str(e),
            )


def auto_extract_entities_background():
    """Helper to extract entities from translated items (if any left)."""
    with database_service.get_session_maker() as db:
        try:
            count = extractor.process_pending_entities(db)
            if count > 0:
                logger.info("auto_extract_entities_completed", count=count)
        except Exception as e:
            logger.exception(
                "auto_extract_entities_failed",
                error_type=type(e).__name__,
                error_message=str(e),
            )


def auto_extract_native_background():
    """Helper to extract entities from native Spanish items."""
    with database_service.get_session_maker() as db:
        try:
            count = extractor.process_native_pending(db)
            if count > 0:
                logger.info("auto_extract_native_completed", count=count)
        except Exception as e:
            logger.exception(
                "auto_extract_native_failed",
                error_type=type(e).__name__,
                error_message=str(e),
            )


# --- Status and Stats ---


@router.get("/status")
async def get_status():
    """Returns the current system status."""
    return {"status": "online", "system_active": True}


@router.get("/dashboard-stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Returns basic statistics for the dashboard."""
    sources_count = db.query(Source).count()
    active_news_count = db.query(NewsItem).filter(NewsItem.status == "DISCOVERED").count()
    return {"active_news": active_news_count, "sources_count": sources_count}


# --- Sources ---


@router.get("/sources", response_model=List[schemas.SourceResponse])
def read_sources(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieves a list of news sources."""
    return db.query(Source).offset(skip).limit(limit).all()


@router.post("/sources", response_model=schemas.SourceResponse)
def create_source(source: schemas.SourceCreate, db: Session = Depends(get_db)):
    """Creates a new news source."""
    db_source = Source(**source.model_dump())
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source


@router.put("/sources/{source_id}", response_model=schemas.SourceResponse)
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


@router.delete("/sources/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    """Deletes a news source."""
    db_source = db.query(Source).filter(Source.id == source_id).first()
    if db_source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(db_source)
    db.commit()
    return {"ok": True}


# --- News Operations ---


@router.post("/scan")
def scan_sources(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Triggers a scan of all active sources to ingest new content."""
    count, new_ids = ingestor.process_feeds(db)
    background_tasks.add_task(auto_extract_native_background)
    if new_ids:
        background_tasks.add_task(auto_translate_background, new_ids)
    return {"new_items": count, "new_item_ids": new_ids}


@router.get("/news/discovered", response_model=List[schemas.NewsItemResponse])
def get_discovered_news(db: Session = Depends(get_db)):
    """Retrieves all news items with 'DISCOVERED' status."""
    return (
        db.query(NewsItem)
        .options(joinedload(NewsItem.source), joinedload(NewsItem.entities))
        .filter(NewsItem.status == "DISCOVERED")
        .order_by(NewsItem.published_date.desc())
        .all()
    )


@router.put("/news/{news_id}/status", response_model=schemas.NewsItemResponse)
def update_news_status(news_id: int, status_update: schemas.NewsItemStatusUpdate, db: Session = Depends(get_db)):
    """Updates the status of a news item."""
    item = db.query(NewsItem).filter(NewsItem.id == news_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="News item not found")
    item.status = status_update.status
    db.commit()
    db.refresh(item)
    return item


@router.get("/news/rejected", response_model=List[schemas.NewsItemResponse])
def get_rejected_news(db: Session = Depends(get_db)):
    """Retrieves all news items with 'REJECTED' status."""
    return (
        db.query(NewsItem)
        .options(joinedload(NewsItem.source), joinedload(NewsItem.entities))
        .filter(NewsItem.status == "REJECTED")
        .order_by(NewsItem.published_date.desc())
        .all()
    )


@router.delete("/news/{news_id}")
def delete_news_item(news_id: int, db: Session = Depends(get_db)):
    """Deletes a news item."""
    item = db.query(NewsItem).filter(NewsItem.id == news_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="News item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.delete("/news/rejected/all")
def empty_trash(db: Session = Depends(get_db)):
    """Deletes all news items with 'REJECTED' status."""
    db.query(NewsItem).filter(NewsItem.status == "REJECTED").delete(synchronize_session=False)
    db.commit()
    return {"ok": True}


@router.put("/news/{news_id}/restore", response_model=schemas.NewsItemResponse)
def restore_news_item(news_id: int, db: Session = Depends(get_db)):
    """Restores a rejected news item to 'DISCOVERED' status."""
    item = db.query(NewsItem).filter(NewsItem.id == news_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="News item not found")
    item.status = "DISCOVERED"
    db.commit()
    db.refresh(item)
    return item


@router.post("/news/batch/delete")
def batch_delete_news(request: schemas.BatchIdRequest, db: Session = Depends(get_db)):
    """Deletes multiple news items in a single request."""
    db.query(NewsItem).filter(NewsItem.id.in_(request.ids)).delete(synchronize_session=False)
    db.commit()
    return {"ok": True, "count": len(request.ids)}


@router.post("/news/batch/restore")
def batch_restore_news(request: schemas.BatchIdRequest, db: Session = Depends(get_db)):
    """Restores multiple news items in a single request."""
    db.query(NewsItem).filter(NewsItem.id.in_(request.ids)).update(
        {NewsItem.status: "DISCOVERED"}, synchronize_session=False
    )
    db.commit()
    return {"ok": True, "count": len(request.ids)}


@router.post("/extract-entities")
def trigger_extract_entities(db: Session = Depends(get_db)):
    """Manually triggers entity extraction on pending news items."""
    try:
        count = extractor.process_pending_entities(db)
        return {"extracted_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Entity Types ---


@router.get("/entity-types", response_model=List[schemas.EntityTypeResponse])
def read_entity_types(db: Session = Depends(get_db)):
    """Retrieves all available entity types."""
    return db.query(EntityType).all()


@router.post("/entity-types", response_model=schemas.EntityTypeResponse)
def create_entity_type(entity_type: schemas.EntityTypeCreate, db: Session = Depends(get_db)):
    """Creates a new entity type."""
    existing = db.query(EntityType).filter(EntityType.name.ilike(entity_type.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Entity type with this name already exists")
    db_entity_type = EntityType(name=entity_type.name, color=entity_type.color)
    try:
        db.add(db_entity_type)
        db.commit()
        db.refresh(db_entity_type)
        return db_entity_type
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/entity-types/{type_id}", response_model=schemas.EntityTypeResponse)
def update_entity_type(type_id: int, entity_type: schemas.EntityTypeCreate, db: Session = Depends(get_db)):
    """Updates an existing entity type."""
    db_type = db.query(EntityType).filter(EntityType.id == type_id).first()
    if not db_type:
        raise HTTPException(status_code=404, detail="Entity type not found")
    existing = db.query(EntityType).filter(EntityType.name.ilike(entity_type.name), EntityType.id != type_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Entity type with this name already exists")
    db_type.name = entity_type.name
    db_type.color = entity_type.color
    db.commit()
    db.refresh(db_type)
    return db_type


@router.delete("/entity-types/{type_id}")
def delete_entity_type(type_id: int, db: Session = Depends(get_db)):
    """Deletes an entity type."""
    db_type = db.query(EntityType).filter(EntityType.id == type_id).first()
    if not db_type:
        raise HTTPException(status_code=404, detail="Entity type not found")
    db.delete(db_type)
    db.commit()
    return {"ok": True}


# --- Entities ---


@router.get("/entities", response_model=List[schemas.EntityResponse])
def read_entities(skip: int = 0, limit: int = 100, include_ignored: bool = False, db: Session = Depends(get_db)):
    """Retrieves a list of entities."""
    query = db.query(Entity).options(joinedload(Entity.sources))
    if not include_ignored:
        query = query.filter(Entity.is_ignored.is_(False))

    return query.offset(skip).limit(limit).all()


@router.post("/entities", response_model=schemas.EntityResponse)
def create_entity(entity: schemas.EntityCreate, db: Session = Depends(get_db)):
    """Creates a new entity."""
    db_entity = Entity(name=entity.name, type=entity.type)
    if hasattr(entity, "description") and entity.description:
        db_entity.description = entity.description

    if entity.source_ids:
        sources = db.query(Source).filter(Source.id.in_(entity.source_ids)).all()
        db_entity.sources = sources

    db.add(db_entity)
    try:
        db.commit()
        db.refresh(db_entity)
        return db_entity
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/entities/{entity_id}", response_model=schemas.EntityResponse)
def update_entity(entity_id: int, entity: schemas.EntityCreate, db: Session = Depends(get_db)):
    """Updates an existing entity."""
    db_entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if db_entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    db_entity.name = entity.name
    db_entity.type = entity.type
    if hasattr(entity, "description") and entity.description:
        db_entity.description = entity.description

    if entity.source_ids is not None:
        sources = db.query(Source).filter(Source.id.in_(entity.source_ids)).all()
        db_entity.sources = sources

    try:
        db.commit()
        db.refresh(db_entity)
        return db_entity
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/entities/{entity_id}")
def delete_entity(entity_id: int, db: Session = Depends(get_db)):
    """Deletes an entity."""
    db_entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if db_entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    db.delete(db_entity)
    db.commit()
    return {"ok": True}


@router.put("/entities/{entity_id}/ignore")
def toggle_ignore_entity(entity_id: int, db: Session = Depends(get_db)):
    """Toggles the 'is_ignored' status of an entity."""
    db_entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if db_entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    db_entity.is_ignored = not db_entity.is_ignored
    db.commit()
    db.refresh(db_entity)
    return {"ok": True, "is_ignored": db_entity.is_ignored}


# --- System Backup & Restore ---


@router.get("/system/export")
def export_system(db: Session = Depends(get_db)):
    """Exports the entire system configuration (sources, entities, types, etc.) as JSON."""
    try:
        sources = db.query(Source).all()
        entities = db.query(Entity).options(joinedload(Entity.sources)).all()
        entity_types = db.query(EntityType).all()
        configs = db.query(AgentConfig).all()

        sources_data = [
            {
                "id": s.id,
                "name": s.name,
                "type": s.type,
                "subtype": s.subtype,
                "config": s.config,
                "icon": s.icon,
                "health_status": s.health_status,
                "active": s.active,
            }
            for s in sources
        ]

        entities_data = [
            {
                "id": e.id,
                "name": e.name,
                "type": e.type,
                "description": getattr(e, "description", None),
                "is_ignored": e.is_ignored,
                "source_ids": [s.id for s in e.sources],
            }
            for e in entities
        ]

        entity_types_data = [{"id": et.id, "name": et.name, "color": et.color} for et in entity_types]
        configs_data = [{"key": c.key, "value": c.value} for c in configs]

        return {
            "sources": sources_data,
            "entities": entities_data,
            "entity_types": entity_types_data,
            "agent_config": configs_data,
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/system/import")
async def import_system(data: dict, db: Session = Depends(get_db)):
    """Imports and replaces the system configuration from a JSON object."""
    try:
        db.execute(text("DELETE FROM news_entities"))
        db.execute(text("DELETE FROM entity_sources"))
        db.query(Source).delete()
        db.query(Entity).delete()
        db.query(EntityType).delete()
        db.query(AgentConfig).delete()
        db.commit()

        for et_data in data.get("entity_types", []):
            db.add(EntityType(name=et_data["name"], color=et_data["color"]))
        db.flush()

        source_map = {}
        for s_data in data.get("sources", []):
            old_id = s_data.get("id")
            new_source = Source(
                name=s_data["name"],
                type=s_data["type"],
                subtype=s_data.get("subtype"),
                config=s_data["config"],
                icon=s_data.get("icon"),
                health_status=s_data.get("health_status", "OK"),
                active=s_data.get("active", True),
            )
            db.add(new_source)
            db.flush()
            source_map[old_id] = new_source

        for e_data in data.get("entities", []):
            new_entity = Entity(
                name=e_data["name"],
                type=e_data["type"],
                description=e_data.get("description"),
                is_ignored=e_data.get("is_ignored", False),
            )
            if "source_ids" in e_data:
                new_entity.sources = [source_map[sid] for sid in e_data["source_ids"] if sid in source_map]
            db.add(new_entity)

        for c_data in data.get("agent_config", []):
            db.add(AgentConfig(key=c_data["key"], value=c_data["value"]))

        db.commit()
        return {"ok": True, "message": "System configuration restored successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/init-defaults")
def initialize_entity_types(db: Session = Depends(get_db)):
    """Initialize default entity types if none exist."""
    count = db.query(EntityType).count()
    if count == 0:
        default_types = [
            {"name": "Persona", "color": "blue"},
            {"name": "Organización", "color": "purple"},
            {"name": "Lugar", "color": "green"},
            {"name": "Concepto", "color": "slate"},
        ]
        for type_data in default_types:
            db.add(EntityType(**type_data))
        db.commit()
        return {"ok": True, "message": f"Initialized {len(default_types)} default entity types"}
    return {"ok": True, "message": "Entity types already initialized"}
