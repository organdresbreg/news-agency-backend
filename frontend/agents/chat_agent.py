"""Implementación del agente especializado en conversaciones chat."""

import chainlit as cl
import requests

from .base import BaseModeAgent

BASE_URL = "http://localhost:8000/api/v1"
CHAT_URL = f"{BASE_URL}/chatbot/chat"


class ChatAgent(BaseModeAgent):
    """Implementación para modo Chat."""

    async def initialize(self):
        """Inicializa el agente de Chat."""
        # Configurar UI específica del chat si fuera necesario
        pass

    async def process_message(self, message: cl.Message):
        """Procesa el mensaje del usuario en modo Chat."""
        token = cl.user_session.get("token")
        if not token:
            await cl.Message(content="⚠️ Por favor, autentícate primero.").send()
            return

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"messages": [{"role": "user", "content": message.content}]}

        msg = cl.Message(content="")
        await msg.send()

        try:
            # Petición síncrona por ahora (similar a lo que hacía streamlit)
            response = requests.post(CHAT_URL, json=payload, headers=headers)

            if response.status_code == 200:
                data = response.json()
                assistant_msg = data.get("messages", [])[-1].get("content", str(data))
                msg.content = assistant_msg
                await msg.update()
            else:
                msg.content = f"Error del servidor: {response.status_code} - {response.text}"
                await msg.update()
        except Exception as e:
            msg.content = f"Error de conexión: {str(e)}"
            await msg.update()
