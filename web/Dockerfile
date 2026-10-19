# Se construye desde la raíz del proyecto (contexto ".") para poder copiar data/calories.csv
FROM python:3.13-slim

# uv instala las dependencias exactas de uv.lock (mucho más rápido que pip)
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Primero solo las dependencias: esta capa se reutiliza mientras no cambie uv.lock
COPY web/pyproject.toml web/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY web/fitnessapp ./fitnessapp
COPY data ./data

# No ejecutar como root dentro del contenedor
RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/healthz', timeout=4)"

# Gunicorn en lugar del servidor de desarrollo de Flask (app.run con debug=True).
# PORT lo define la plataforma de despliegue (Render, Railway...); en local es 8000.
CMD ["sh", "-c", "exec gunicorn 'fitnessapp:create_app()' --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --access-logfile -"]
