"""Extractor Service - Named Entity Recognition (NER) with SpaCy.

Handles local entity extraction from news items using SpaCy.
Processes both translated news and native Spanish news.
"""

import spacy
from spacy.matcher import PhraseMatcher
import re
from sqlmodel import Session
from app.models.newsroom import NewsItem, Entity
from typing import List, Optional, Set
from app.core.logging import logger

# Load SpaCy model globally
try:
    logger.info("loading_spacy_model", model_name="es_core_news_lg")
    nlp = spacy.load("es_core_news_lg")
    logger.info("spacy_model_loaded")
except Exception as e:
    logger.exception("spacy_model_load_failed", error_message=str(e))
    nlp = None


# Mapping SpaCy labels to DB Enums
# We only care about PER, ORG, LOC, GPE
SPACY_TO_DB_MAP = {"PER": "PERSON", "ORG": "ORGANIZATION", "GPE": "LOCATION", "LOC": "LOCATION"}

STOP_PREFIXES = (
    "El ",
    "La ",
    "Los ",
    "Las ",
    "Un ",
    "Una ",
    "En ",
    "De ",
    "Para ",
    "Por ",
    "Con ",
    "Sobre ",
    "Según ",
)


def is_valid_entity(text: str, label: str) -> bool:
    """Apply heuristic filters to avoid 'garbage' entities."""
    if not text:
        return False

    # Mapping check only for SPACY labels.
    # For Matcher results (CONCEPT), we skip label mapping check here
    # as we already know we want it.
    if label not in SPACY_TO_DB_MAP and label != "CONCEPT":
        return False

    # 1. Stopwords/Articles at the start (Case Insensitive)
    text_lower = text.lower()
    if any(text_lower.startswith(p.lower()) for p in STOP_PREFIXES):
        return False

    # 2. Length check (2 to 50 chars)
    if not (2 <= len(text) <= 50):
        return False

    # 3. Excessive Punctuation or Special Chars
    if "\n" in text or "\t" in text:
        return False

    if re.search(r'[.]{2,}|["]{2,}', text):  # Excessive dots or quotes
        return False

    # 4. Must not be just a number or special symbols
    if text.replace(" ", "").isdigit():
        return False

    return True


def load_watchlist_matcher(db: Session, nlp_obj: spacy.language.Language) -> Optional[tuple]:
    """Loads active entity names AND their aliases from Entity table into a SpaCy PhraseMatcher.

    Returns (matcher, alias_map, types_map)

    alias_map: { "alias_lower": "Canonical Name" }
    types_map: { "canonical_name_lower": "TYPE" }
    """
    try:
        # Load entities that are NOT ignored
        active_entities = db.query(Entity).filter(Entity.is_ignored.is_(False)).all()

        if not active_entities:
            return None, {}, {}

        matcher = PhraseMatcher(nlp_obj.vocab, attr="LOWER")
        types_map = {}
        alias_map = {}
        patterns = []

        for e in active_entities:
            # Add Canonical Name
            doc = nlp_obj.make_doc(e.name)
            patterns.append(doc)
            types_map[e.name.lower()] = e.type
            alias_map[e.name.lower()] = e.name  # Map itself to itself

            # Add Aliases
            if e.aliases:
                for alias in e.aliases:
                    if alias and alias.strip():
                        alias_doc = nlp_obj.make_doc(alias)
                        patterns.append(alias_doc)
                        alias_map[alias.lower()] = e.name  # Map alias to canonical

        if not patterns:
            return None, {}, {}

        matcher.add("WATCH_LIST", patterns)

        logger.info("watch_list_loaded", pattern_count=len(patterns))
        return matcher, alias_map, types_map
    except Exception as e:
        logger.exception("watch_list_load_failed", error_message=str(e))
        return None, {}, {}


def get_blacklisted_names(db: Session) -> Set[str]:
    """Returns a set of lowercase names of ignored entities."""
    ignored = db.query(Entity.name).filter(Entity.is_ignored.is_(True)).all()

    return {name[0].lower() for name in ignored}


def _extract_from_item(
    db: Session,
    item: NewsItem,
    matcher: PhraseMatcher = None,
    watchlist_types: dict = None,
    alias_map: dict = None,
    blacklist: Set[str] = None,
):
    """Internal helper to process a single NewsItem."""
    if blacklist is None:
        blacklist = set()
    if watchlist_types is None:
        watchlist_types = {}
    if alias_map is None:
        alias_map = {}

    try:
        # Use Spanish content if available (translated), else fallback to original (native ES)
        title = item.title_es or item.title
        content = item.content_es or item.content_snippet or ""
        text = f"{title}. {content}".strip()

        doc = nlp(text)
        entities_to_save = {}  # canonical_name_lower -> (canonical_name, type)

        # Step 1: Statistical NER
        for ent in doc.ents:
            ent_text = ent.text.strip()
            ent_lower = ent_text.lower()
            ent_label = ent.label_

            # Check if this text maps to a known canonical entity
            canonical_name = alias_map.get(ent_lower, ent_text)
            canonical_lower = canonical_name.lower()

            # Skip if in blacklist (check canonical)
            if canonical_lower in blacklist:
                continue

            if is_valid_entity(ent_text, ent_label):
                db_type = SPACY_TO_DB_MAP[ent_label]
                # If mapped, prefer the mapped type
                if ent_lower in alias_map:
                    db_type = watchlist_types.get(canonical_lower, db_type)

                entities_to_save[canonical_lower] = (canonical_name, db_type)

        # Step 2: Deterministic Matcher (Watch List)
        if matcher:
            matches = matcher(doc)
            for _, start, end in matches:
                span = doc[start:end]
                ent_text = span.text.strip()
                ent_lower = ent_text.lower()

                # Resolve to Canonical Name
                canonical_name = alias_map.get(ent_lower, ent_text)
                canonical_lower = canonical_name.lower()

                if canonical_lower not in entities_to_save:
                    # Use the specific type from WatchList if available, else default to CONCEPT
                    ent_type = watchlist_types.get(canonical_lower, "CONCEPT")
                    entities_to_save[canonical_lower] = (canonical_name, ent_type)

        # Step 3: Save and Link
        entities_added = 0
        for _, (ent_name, ent_type) in entities_to_save.items():
            # Check existing (ilike for case-insensitive match)
            existing_entity = db.query(Entity).filter(Entity.name.ilike(ent_name)).first()

            # Double check ignore status (even if not in batch blacklist yet)
            if existing_entity and existing_entity.is_ignored:
                continue

            if not existing_entity:
                existing_entity = Entity(name=ent_name, type=ent_type)
                db.add(existing_entity)
                db.flush()
            else:
                pass

            if existing_entity not in item.entities:
                item.entities.append(existing_entity)
                entities_added += 1

        item.entities_extracted = True
        logger.info("item_entities_linked", item_id=item.id, count=entities_added, lang=item.language)
        return True
    except Exception as e:
        logger.exception("item_entity_extraction_failed", item_id=item.id, error_message=str(e))
        item.entities_extracted = True  # Mark to avoid retrying indefinitely
        return False


def process_pending_entities(db: Session, item_ids: List[int] = None) -> int:
    """Processes translated items (Flow A)."""
    if nlp is None:
        return 0

    # Load Watch List Matcher and Black List once per batch
    matcher, alias_map, watchlist_types = load_watchlist_matcher(db, nlp)
    blacklist = get_blacklisted_names(db)

    query = db.query(NewsItem).filter(NewsItem.entities_extracted.is_(False))

    if item_ids:
        query = query.filter(NewsItem.id.in_(item_ids))
    else:
        query = query.filter(NewsItem.title_es.is_not(None)).limit(10)

    items = query.all()
    count = 0
    for item in items:
        if _extract_from_item(db, item, matcher, watchlist_types, alias_map, blacklist):
            count += 1
    db.commit()
    return count


def process_native_pending(db: Session) -> int:
    """Processes native Spanish items (Flow B)."""
    if nlp is None:
        return 0

    # Load Watch List Matcher and Black List once per batch
    matcher, alias_map, watchlist_types = load_watchlist_matcher(db, nlp)
    blacklist = get_blacklisted_names(db)

    # Query items that are ES and have not been processed.
    items = (
        db.query(NewsItem).filter(NewsItem.language == "es", NewsItem.entities_extracted.is_(False)).limit(100).all()
    )

    if not items:
        return 0

    logger.info("processing_native_news", count=len(items))

    count = 0
    for item in items:
        if _extract_from_item(db, item, matcher, watchlist_types, alias_map, blacklist):
            count += 1
    db.commit()
    return count
