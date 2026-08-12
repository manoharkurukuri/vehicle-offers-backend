# Official Playwright image ships Chromium + all system libraries it needs.
FROM mcr.microsoft.com/playwright/python:v1.50.0-jammy

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_HEADLESS=true

WORKDIR /app

# Install Python dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The base image already bundles browsers, but re-run to guarantee the
# Chromium build matches the installed Playwright version.
RUN playwright install chromium

COPY . .

# Generated Excel files land here; on Fargate this is ephemeral (see notes).
RUN mkdir -p storage/offers

EXPOSE 8000

# Honor the platform-provided PORT if present (App Runner), else default 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
