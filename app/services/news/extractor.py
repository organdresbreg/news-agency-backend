"""Extractor Service - NER with SpaCy and LLM.

Processes news items sequentially after translation.
"""

import spacy
from sqlmodel import Session
from app.models.news import NewsItem
from app.models.entities import Entity
from typing import List
from app.core.logging import logger
import os
import time
from groq import Groq
from app.services.news import linker

try:
    nlp = spacy.load("es_core_news_lg")
except Exception:
    nlp = None

SPACY_TO_DB_MAP = {"PER": "PERSON", "ORG": "ORGANIZATION", "GPE": "LOCATION", "LOC": "LOCATION"}


def _extract_spacy(db: Session, item: NewsItem):
    text = f"{item.title_es or item.title}. {item.content_es or item.content_snippet or ''}"
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in SPACY_TO_DB_MAP:
            name = ent.text.strip()
            entity = db.query(Entity).filter(Entity.name.ilike(name)).first()
            if not entity:
                entity = Entity(name=name, type=SPACY_TO_DB_MAP[ent.label_])
                db.add(entity)
                db.flush()
            if entity not in item.entities and not entity.is_ignored:
                item.entities.append(entity)
    item.entities_extracted = True


def _refine_llm(db: Session, item: NewsItem, client: Groq, model: str):
    text = f"{item.title_es or item.title}. {item.content_es or item.content_snippet or ''}"
    for entity in list(item.entities):
        if entity.wikidata_id or entity.is_ignored:
            continue
        resolved = linker.resolve_entity(entity.name, text, client, model)
        if resolved:
            existing = db.query(Entity).filter(Entity.wikidata_id == resolved["wikidata_id"]).first()
            if existing:
                if existing not in item.entities:
                    item.entities.append(existing)
                if entity in item.entities:
                    item.entities.remove(entity)
            else:
                entity.name, entity.wikidata_id, entity.description = (
                    resolved["name"],
                    resolved["wikidata_id"],
                    resolved["description"],
                )


def process_extraction_pipeline(db: Session, item_ids: List[int] = None):
    """Processes the full NER extraction and linking pipeline for pending news items."""
    if not nlp:
        return
    query = db.query(NewsItem).filter(NewsItem.entities_extracted.is_(False))
    if item_ids:
        query = query.filter(NewsItem.id.in_(item_ids))
    items = query.order_by(NewsItem.id.asc()).limit(50).all()

    for item in items:
        item.status = "EXTRACTING"
        db.commit()
        _extract_spacy(db, item)
        item.status = "REFINING"
        db.commit()

    api_key = os.getenv("GROQ_API_KEY")
    client = Groq(api_key=api_key) if api_key else None
    if client:
        for item in items:
            _refine_llm(db, item, client, os.getenv("MODEL", "llama-3.1-8b-instant"))
            item.status = "PROCESSED"
            db.commit()
            time.sleep(1)
    else:
        for item in items:
            item.status = "PROCESSED"
            db.commit()


def process_pending_entities(db: Session, item_ids: List[int] = None) -> int:
    """Entrypoint for processing pending entities for specific items."""
    process_extraction_pipeline(db, item_ids)
    return 1


def process_native_pending(db: Session) -> int:
    """Entrypoint for processing all pending entities natively."""
    process_extraction_pipeline(db)
    return 1
