"""Crawler Service - Full Text Extraction using Crawl4AI."""

import asyncio
from typing import List, Optional
from sqlmodel import Session
from app.models.newsroom import NewsItem
from app.core.config import settings
from app.core.logging import logger

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


async def crawl_news_items(db: Session, batch_size: int = 5):
    """Crawls news items that are in DISCOVERED status and missing full_content."""
    # 1. Fetch pending items
    items = (
        db.query(NewsItem).filter(NewsItem.status == "DISCOVERED", NewsItem.full_content.is_(None)).limit(20).all()
    )  # Process up to 20 per run

    if not items:
        logger.info("no_pending_extractions")
        return

    logger.info("starting_full_text_extraction", count=len(items))

    # Configure crawler
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=100,  # Only keep content with > 100 words (Crawl4AI built-in)
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Process in batches
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            urls = [item.url for item in batch]

            logger.info("processing_crawler_batch", batch_num=i // batch_size + 1, url_count=len(urls))

            try:
                # arun_many is optimized for multiple URLs
                results = await crawler.arun_many(urls=urls, config=run_config)

                for item, result in zip(batch, results, strict=False):
                    if result.success:
                        content = result.markdown.raw_markdown if result.markdown else ""

                        # Validate length (fallback to snippet if too short)
                        if content and len(content) > 150:
                            item.full_content = content
                            logger.info(
                                "content_extracted", url=item.url, content_length=len(content), item_id=item.id
                            )

                        else:
                            # Use content_snippet as fallback if extraction fails to get meaningful text
                            item.full_content = item.content_snippet
                            logger.warning(f"Content too short or empty for {item.url}, using snippet.")
                    else:
                        logger.error(
                            "crawl_item_failed",
                            url=item.url,
                            error_message=result.error_message,
                            status_code=result.status_code if hasattr(result, "status_code") else None,
                        )
                        item.full_content = item.content_snippet or ""

                db.commit()  # Commit after each batch

            except asyncio.TimeoutError:
                logger.exception("crawl_batch_timeout", batch_urls=urls)
                db.rollback()
                if settings.DEBUG:
                    raise
            except Exception as e:
                logger.exception(
                    "crawl_batch_unexpected_error",
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                db.rollback()
                if settings.DEBUG:
                    raise

    logger.info("extraction_process_finished")


def run_crawler_sync(db: Session, batch_size: int = 5):
    """Synchronous wrapper for async crawler."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(crawl_news_items(db, batch_size))
