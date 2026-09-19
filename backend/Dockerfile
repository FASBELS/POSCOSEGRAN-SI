FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/pyproject.toml ./
COPY backend/src ./src
RUN pip install .
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./
COPY backend/scripts ./scripts
COPY knowledge /knowledge

RUN useradd --create-home --uid 10001 aplicacion && chown -R aplicacion:aplicacion /app
USER aplicacion

EXPOSE 8000
CMD ["uvicorn", "poscosegran.api.app:crear_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
