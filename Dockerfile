FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Migrations + runtime assets.
COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts

CMD ["python", "-m", "playnext"]
