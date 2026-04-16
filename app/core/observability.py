"""Observability module for the application."""

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.core.config import settings
from app.core.logging import logger


# def langfuse_init():
#    """Initialize Langfuse."""
"""    langfuse = Langfuse(
        tracing_enabled=settings.LANGFUSE_TRACING_ENABLED,
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST,
        environment=settings.ENVIRONMENT.value,
        debug=settings.DEBUG,
    )

    if langfuse.auth_check():
        logger.debug("langfuse_auth_success")
    else:
        logger.debug("langfuse_auth_failure") """


def langfuse_init():
    """Inicializa Langfuse."""
    import os

    # Solo inicializar si las claves existen
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        print("⚠️  Langfuse disabled: Missing credentials.")
        return

    try:
        from langfuse import Langfuse

        langfuse = Langfuse()
        if langfuse.auth_check():
            logger.info("langfuse_connected")
        else:
            logger.warning("langfuse_auth_failed")
    except Exception as e:
        logger.warning("langfuse_init_error", error=str(e))


def get_langfuse_callback_handler() -> CallbackHandler:
    """Create a Langfuse CallbackHandler for tracking LLM interactions.

    Returns:
        CallbackHandler: Configured Langfuse callback handler.
    """
    return CallbackHandler()


langfuse_callback_handler = get_langfuse_callback_handler()
