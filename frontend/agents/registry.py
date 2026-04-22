"""Registro y fábrica de agentes por modo de operación."""

from typing import Dict, Type

from .base import BaseModeAgent
from .chat_agent import ChatAgent
from .scraper_agent import ScraperAgent
from .searcher_agent import SearcherAgent
from .writer_agent import WriterAgent

# Registro central de agentes
AGENT_REGISTRY: Dict[str, Type[BaseModeAgent]] = {
    "chat": ChatAgent,
    "searcher": SearcherAgent,
    "scraper": ScraperAgent,
    "writer": WriterAgent,
}


def get_agent(mode_name: str) -> BaseModeAgent:
    """Obtiene la instancia del agente correspondiente al modo solicitado."""
    agent_class = AGENT_REGISTRY.get(mode_name)
    if not agent_class:
        raise ValueError(f"Agente para modo '{mode_name}' no encontrado.")
    return agent_class()
