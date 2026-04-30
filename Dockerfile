FROM python:3.13.2-slim

# Set working directory
WORKDIR /app

# Set non-sensitive environment variables
ARG APP_ENV=production

ENV APP_ENV=${APP_ENV} \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && pip install --upgrade pip \
    && pip install uv \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user earlier
RUN useradd -m appuser

# Copy pyproject.toml first to leverage Docker cache
COPY --chown=appuser:appuser pyproject.toml .
RUN uv venv && . .venv/bin/activate && uv pip install -e .

# Copy the application with correct ownership from the start
COPY --chown=appuser:appuser . .

# Make entrypoint script executable
RUN chmod +x /app/scripts/docker-entrypoint.sh

# Create logs directory and set ownership
RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs

# Set user
USER appuser

# Default port
EXPOSE 8000

# Log the environment we're using
RUN echo "Using ${APP_ENV} environment"

# Command to run the application
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
