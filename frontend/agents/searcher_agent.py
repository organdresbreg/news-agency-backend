"""Agente especializado en búsqueda de información en internet."""

import chainlit as cl

from .base import BaseModeAgent


class SearcherAgent(BaseModeAgent):
    """Implementación para Web Searcher."""

    async def initialize(self):
        """Inicializa el agente Web Searcher."""
        await cl.Message(content="Modo Web Searcher activado.").send()

    async def process_message(self, message: cl.Message):
        """Procesa la solicitud de búsqueda en internet."""
        await cl.Message(content="Buscando información... (Funcionalidad pendiente de implementar)").send()
