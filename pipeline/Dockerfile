# Una sola imagen para productor y consumidor; docker-compose elige el comando.
# Se construye desde la raíz del proyecto para poder copiar data/calories.csv
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pipeline/pyproject.toml pipeline/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY pipeline/fitness_pipeline ./fitness_pipeline
COPY data ./data

RUN useradd --create-home --uid 10001 app
USER app

CMD ["python", "-m", "fitness_pipeline.consumer"]
