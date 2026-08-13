# Backend no longer runs Playwright — scraping is a separate Lambda image.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Generated Excel files land here; on Fargate this is ephemeral (see notes).
RUN mkdir -p storage/offers

EXPOSE 8000

# Honor the platform-provided PORT if present (App Runner), else default 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
