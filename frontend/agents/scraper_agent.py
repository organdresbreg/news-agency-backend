"""Agente especializado en extracción de contenido web (Scraper)."""

import chainlit as cl

from .base import BaseModeAgent


class ScraperAgent(BaseModeAgent):
    """Implementación para Scraper."""

    async def initialize(self):
        """Inicializa el agente Scraper."""
        await cl.Message(content="Modo Scraper activado.").send()

    async def process_message(self, message: cl.Message):
        """Procesa el mensaje del usuario en modo Scraper."""
        await cl.Message(content="Extrayendo datos... (Funcionalidad pendiente de implementar)").send()
