FROM python:3.12-slim

ARG POETRY_VERSION=2.5.1

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
RUN poetry install --no-root --no-ansi

COPY . .

RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 5000

# Migrations and seeding run before the server; if either fails the container exits.
CMD ["sh", "-c", "alembic upgrade head && flask --app app.bootstrap:create_app seed-initial-data && flask --app app.bootstrap:create_app run --host 0.0.0.0 --port 5000 --debug"]
