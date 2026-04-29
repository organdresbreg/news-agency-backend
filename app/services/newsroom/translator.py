"""Translator Service - Language Detection & Translation.

Handles language detection and translation to Spanish using Groq.
Processes items where title_es IS NULL.
"""

import os
import json
import time
from typing import List, Dict, Any
from sqlmodel import Session
from app.models.newsroom import NewsItem
from langdetect import detect, LangDetectException
from groq import Groq
from app.services.newsroom import extractor
from app.core.logging import logger


def translate_batch(client: Groq, model: str, items_to_translate: List[NewsItem]) -> Dict[str, Any]:
    """Helper to translate a batch of news items using a single Groq API call.

    Includes performance and usage metrics tracking.
    """
    if not items_to_translate:
        return {"results": {}, "usage": None, "duration": 0}

    # Logging which items are being sent
    logger.info("sending_batch_to_translate", item_ids=[item.id for item in items_to_translate])

    # Construct the batch request payload
    batch_payload = {}
    for item in items_to_translate:
        batch_payload[str(item.id)] = {"title": item.title, "content": item.content_snippet or "No summary available"}

    prompt = f"""You are a professional news translator. Translate the following news items to Neutral Spanish. Maintain a journalistic tone and keep proper nouns where appropriate.

CRITICAL GRAMMAR RULES:
1. TITLES: NEVER include a trailing period (.) at the end of the title.
2. CONTENT/SUMMARY: ALWAYS include a trailing period (.) at the end of the summary.

Return ONLY a JSON object where keys are the IDs provided.

Structure:
{{
  "ID": {{
    "title_es": "translated title",
    "content_es": "translated content"
  }}
}}

Items to translate:
{json.dumps(batch_payload, indent=2)}"""

    batch_start = time.time()
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a translation service that outputs strictly valid JSON."},
                {"role": "user", "content": prompt},
            ],
            model=model,
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        batch_duration = time.time() - batch_start

        # Extract usage metrics from response
        usage = response.usage
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens

        logger.info(
            "batch_metrics",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            duration_s=round(batch_duration, 2),
        )

        # Parse JSON content
        result = json.loads(response.choices[0].message.content)

        for item_id, data in result.items():
            logger.info("item_translated", item_id=item_id, title_es=data.get("title_es", "")[:50])

        return {"results": result, "usage": usage, "duration": batch_duration}

    except Exception as e:
        logger.exception(
            "batch_translation_failed",
            error_type=type(e).__name__,
            error_message=str(e),
            duration_s=round(time.time() - batch_start, 2),
        )

        return {"results": {}, "usage": None, "duration": time.time() - batch_start}


def process_pending_translations(db: Session, item_ids: List[int] = None) -> int:
    """Process translations for news items using batching and rate limiting.

    Provides detailed execution metrics.
    """
    total_process_start = time.time()
    logger.info("starting_translation_service", mode="batch")

    # 1. Fetch all items where title_es IS NULL
    query = db.query(NewsItem).filter(NewsItem.title_es.is_(None))

    if item_ids:
        query = query.filter(NewsItem.id.in_(item_ids))

    pending_items = query.all()

    if not pending_items:
        logger.info("no_pending_translations")
        return 0

    logger.info("pending_translations_found", count=len(pending_items))

    # 2. Local Phase: Detect language and handle Spanish items
    batch_queue = []
    local_copies = 0
    for item in pending_items:
        try:
            # Language Detection
            if not item.language or item.language == "unknown":
                text_sample = f"{item.title} {item.content_snippet or ''}".strip()
                try:
                    item.language = detect(text_sample)
                except LangDetectException:
                    item.language = "unknown"

            # Handle Spanish immediately
            if item.language == "es":
                item.title_es = item.title
                item.content_es = item.content_snippet
                local_copies += 1
            else:
                batch_queue.append(item)
        except Exception as e:
            logger.exception(
                "local_processing_failed",
                item_id=item.id,
                error_type=type(e).__name__,
                error_message=str(e),
            )

    if local_copies > 0:
        logger.info("local_translations_completed", count=local_copies)

    db.commit()  # Save detections

    if not batch_queue:
        logger.info("Proceso concluido sin llamadas externas.")
        return len(pending_items)

    # 3. API Phase: Batch translation
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("API_KEY")
    model = os.getenv("MODEL", "llama-3.1-8b-instant")

    if not api_key:
        logger.error("api_key_missing", key_name="GROQ_API_KEY")
        return 0

    client = Groq(api_key=api_key)
    batch_size = 5
    translated_count = 0
    total_batches = (len(batch_queue) + batch_size - 1) // batch_size

    # Accumulated metrics
    acc_input_tokens = 0
    acc_output_tokens = 0
    acc_total_tokens = 0

    logger.info("starting_batch_translation", total_items=len(batch_queue), total_batches=total_batches)

    for i in range(0, len(batch_queue), batch_size):
        current_batch = batch_queue[i : i + batch_size]
        batch_num = i // batch_size + 1
        logger.info(
            "processing_batch", batch_num=batch_num, total_batches=total_batches, batch_size=len(current_batch)
        )

        batch_data = translate_batch(client, model, current_batch)
        batch_results = batch_data["results"]
        usage = batch_data["usage"]

        if usage:
            acc_input_tokens += usage.prompt_tokens
            acc_output_tokens += usage.completion_tokens
            acc_total_tokens += usage.total_tokens

        # Map results back to items
        for item in current_batch:
            item_id_str = str(item.id)
            if item_id_str in batch_results:
                item.title_es = batch_results[item_id_str].get("title_es")
                item.content_es = batch_results[item_id_str].get("content_es")
                translated_count += 1
            else:
                logger.warning("item_translation_missing", item_id=item.id)
                item.title_es = f"[Fallo] {item.title}"
                item.content_es = item.content_snippet

        db.commit()

        # --- Automatic Entity Extraction ---
        # The moment a batch is translated, we process its entities
        batch_ids = [item.id for item in current_batch]
        try:
            extractor.process_pending_entities(db, item_ids=batch_ids)
        except Exception as e:
            logger.exception(
                "auto_extraction_failed",
                batch_ids=batch_ids,
                error_type=type(e).__name__,
                error_message=str(e),
            )

        # 4. Partial Summary after each batch
        logger.info(
            "translation_process_partial_summary",
            translated_count=translated_count,
            input_tokens=acc_input_tokens,
            output_tokens=acc_output_tokens,
            total_tokens=acc_total_tokens,
            total_duration_s=round(time.time() - total_process_start, 2),
        )

        # 5. Rate Limiting Pause
        if i + batch_size < len(batch_queue):
            logger.info("[PAUSA] Esperando 12 segundos para cumplir con el Rate Limit...")
            time.sleep(12)

    total_duration = time.time() - total_process_start

    logger.info(
        "translation_process_final_summary",
        translated_count=translated_count,
        local_copies=local_copies,
        input_tokens=acc_input_tokens,
        output_tokens=acc_output_tokens,
        total_tokens=acc_total_tokens,
        total_duration_s=round(total_duration, 2),
    )

    return translated_count
