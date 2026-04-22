"""Agente especializado en redacción y síntesis de contenido."""

import chainlit as cl

from .base import BaseModeAgent


class WriterAgent(BaseModeAgent):
    """Implementación para Summary Writer."""

    async def initialize(self):
        """Inicializa el agente Writer."""
        await cl.Message(content="Modo Writer activado.").send()

    async def process_message(self, message: cl.Message):
        """Procesa la solicitud de redacción o síntesis de contenido."""
        await cl.Message(content="Escribiendo resumen... (Funcionalidad pendiente de implementar)").send()
