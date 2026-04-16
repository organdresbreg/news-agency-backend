"""Observability module for the application."""

import os

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.core.logging import logger


def langfuse_init():
    """Inicializa Langfuse."""
    # Solo inicializar si las claves existen
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        print("⚠️  Langfuse disabled: Missing credentials.")
        return

    try:
        langfuse = Langfuse()
        if langfuse.auth_check():
            logger.info("langfuse_connected")
        else:
            logger.warning("langfuse_auth_failed")
    except Exception as e:  # noqa
        logger.warning("langfuse_init_error", error=str(e))


def get_langfuse_callback_handler() -> CallbackHandler:
    """Create a Langfuse CallbackHandler for tracking LLM interactions.

    Returns:
        CallbackHandler: Configured Langfuse callback handler.
    """
    return CallbackHandler()


langfuse_callback_handler = get_langfuse_callback_handler()
