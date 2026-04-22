"""Definición de la clase base y estructura común para todos los agentes."""

from abc import ABC, abstractmethod

import chainlit as cl


class BaseModeAgent(ABC):
    """Contrato común para todos los agentes/modos."""

    @abstractmethod
    async def initialize(self):
        """Inicializa la UI y el estado específico del agente."""
        pass

    @abstractmethod
    async def process_message(self, message: cl.Message):
        """Procesa un mensaje entrante según la lógica del agente."""
        pass
