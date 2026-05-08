"""Entity Linking Service - Wikidata & Groq Disambiguation.

Queries Wikidata and uses LLM to select the correct entity based on context.
"""

import requests
import json
from typing import List, Dict, Optional, Any
from groq import Groq
from app.core.logging import logger

WIKIDATA_SEARCH_URL = "https://www.wikidata.org/w/api.php"
USER_AGENT = "NewsAgencyBot/1.0"


def search_wikidata(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search Wikidata for an entity name."""
    try:
        params = {
            "action": "wbsearchentities",
            "format": "json",
            "language": "es",
            "uselang": "es",
            "search": query,
            "limit": limit,
        }
        response = requests.get(WIKIDATA_SEARCH_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=10)
        return [
            {"id": item["id"], "label": item["label"], "description": item.get("description", "")}
            for item in response.json().get("search", [])
        ]
    except Exception:
        return []


def resolve_entity(name: str, context: str, client: Groq, model: str) -> Optional[Dict[str, Any]]:
    """Resolves an entity using Wikidata search and LLM disambiguation."""
    candidates = search_wikidata(name)
    if not candidates:
        return None

    prompt = f"""You are a precise entity linking system.
Entity: "{name}"
Context: "{context}"
Candidates: {json.dumps(candidates)}

Select the correct Wikidata "id" or null if none match. Reply ONLY with JSON: {{"id": "Q..." or null, "reasoning": "..."}}"""

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        data = json.loads(response.choices[0].message.content)
        selected_id = data.get("id")

        cand = next((c for c in candidates if c["id"] == selected_id), None)
        if cand:
            return {"wikidata_id": cand["id"], "name": cand["label"], "description": cand["description"]}
    except Exception:
        pass
    return None
