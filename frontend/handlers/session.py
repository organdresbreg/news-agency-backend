"""Gestión de estado y ciclo de vida de la sesión del usuario."""

import chainlit as cl


def init_session_state():
    """Gestión de cl.user_session y estado global."""
    if not cl.user_session.get("messages"):
        cl.user_session.set("messages", [])
