"""Ingestor Service - RSS Feed Processing.

Handles raw RSS feed ingestion without translation.
Extracts: title, link, date, content (cascade: content > summary > description)
Saves to: title and content_snippet columns
"""

import feedparser
import requests
from sqlmodel import Session
from app.models.newsroom import Source, NewsItem
from datetime import datetime, timedelta, timezone
from langdetect import detect
from bs4 import BeautifulSoup
import re
from typing import Tuple, List
from app.core.logging import logger


def clean_html(html_content: str) -> str:
    """Remove HTML tags and clean whitespace from content."""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def process_feeds(db: Session) -> Tuple[int, List[int]]:
    """Process all active RSS feeds and ingest new items.

    Returns:
        Tuple[int, List[int]]: (count of new items, list of new item IDs)
    """
    sources = db.query(Source).filter(Source.type == "RSS", Source.active.is_(True)).all()

    new_items_count = 0
    new_item_ids = []

    # Filter: 24h freshness
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=1)
    logger.info("starting_rss_scan", freshness_cutoff=cutoff_date.isoformat())

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    for source in sources:
        url = source.config.get("url")
        if not url:
            continue

        try:
            logger.info("fetching_rss_feed", source_name=source.name, url=url)

            response = requests.get(url, headers=HEADERS, timeout=20)
            response.raise_for_status()

            feed = feedparser.parse(response.content)
            logger.info("parsing_rss_entries", count=len(feed.entries), source_name=source.name)

            for entry in feed.entries:
                try:
                    link = entry.get("link")
                    if not link:
                        continue

                    # 1. Existence Check
                    existing = db.query(NewsItem).filter(NewsItem.url == link).first()
                    if existing:
                        continue

                    # 2. Freshness Check (24h)
                    item_date = datetime.now(timezone.utc)
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            item_date = datetime(*entry.published_parsed[:6]).replace(tzinfo=timezone.utc)
                        except Exception:
                            pass

                    if item_date < cutoff_date:
                        continue

                    # 3. Content Extraction (Robust)
                    title = entry.get("title", "Sin título")
                    content_raw = ""
                    if hasattr(entry, "content") and entry.content:
                        content_raw = entry.content[0].value
                    elif hasattr(entry, "summary_detail") and entry.summary_detail:
                        content_raw = entry.summary_detail.value
                    elif hasattr(entry, "summary"):
                        content_raw = entry.summary
                    else:
                        content_raw = entry.get("description", "")

                    content_snippet = clean_html(content_raw)

                    # 4. Language detection (Quick sample)
                    text_sample = f"{title} {content_snippet[:200]}".strip()
                    detected_lang = "unknown"
                    if text_sample:
                        try:
                            detected_lang = detect(text_sample)
                        except Exception:
                            pass

                    # 5. Create Item
                    new_item = NewsItem(
                        source_id=source.id,
                        title=title,
                        url=link,
                        published_date=item_date.isoformat(),
                        status="DISCOVERED",
                        language=detected_lang,
                        content_snippet=content_snippet,
                    )
                    db.add(new_item)
                    db.flush()
                    new_item_ids.append(new_item.id)
                    new_items_count += 1

                except Exception as entry_e:
                    logger.exception("rss_entry_processing_failed", error_message=str(entry_e))
                    continue

        except Exception as source_e:
            logger.exception("rss_source_sync_failed", source_name=source.name, error_message=str(source_e))

    db.commit()
    logger.info("rss_sync_complete", created_count=new_items_count)
    return new_items_count, new_item_ids
