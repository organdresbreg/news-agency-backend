"""Entry point for Chainlit App. Routing lógico según el "Modo" seleccionado."""

import os

import chainlit as cl
from agents.registry import get_agent
from config import DEFAULT_MODE
from dotenv import load_dotenv
from handlers.auth import authenticate_user
from handlers.session import init_session_state

# Cargar .env.development si existe, o .env por defecto
load_dotenv(dotenv_path=".env.development", override=True)


@cl.password_auth_callback
async def auth_callback(username: str, password: str):
    """Callback de autenticación de Chainlit."""
    token = await authenticate_user(username, password)
    if token:
        # En Chainlit el callback de autenticación no tiene contexto websocket aún.
        # Pasamos el token como metadata para recuperarlo después.
        return cl.User(identifier=username, metadata={"token": token})
    return None


@cl.on_chat_start
async def on_chat_start():
    """Se ejecuta al iniciar la sesión del usuario (después del login)."""
    # Recuperamos el usuario y el token de la sesión actual
    user = cl.user_session.get("user")
    if user and user.metadata and "token" in user.metadata:
        cl.user_session.set("token", user.metadata["token"])

    init_session_state()
    cl.user_session.set("mode", DEFAULT_MODE)

    # Inicializar el agente del modo por defecto
    agent = get_agent(DEFAULT_MODE)
    await agent.initialize()


@cl.on_message
async def on_message(message: cl.Message):
    """Se ejecuta al recibir un mensaje del usuario."""
    current_mode = cl.user_session.get("mode", DEFAULT_MODE)
    agent = get_agent(current_mode)

    # Delegar el procesamiento al agente específico
    await agent.process_message(message)
