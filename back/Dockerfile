FROM python:3.12-slim

ARG POETRY_VERSION=2.5.1
ARG INSTALL_DEV=true

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:/opt/poetry/bin:$PATH"

RUN python -m venv /opt/poetry \
    && /opt/poetry/bin/pip install "poetry==${POETRY_VERSION}" \
    && python -m venv /opt/venv

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        poetry install --no-root --no-ansi; \
    else \
        poetry install --no-root --no-ansi --only main; \
    fi

COPY . .

RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=3)"]

CMD ["sh", "scripts/start.sh"]
