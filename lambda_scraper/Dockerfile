# Playwright's official image already bundles Chromium + every system library
# it needs. We add the AWS Lambda Runtime Interface Client on top so the same
# image can run as a Lambda container image.
FROM mcr.microsoft.com/playwright/python:v1.50.0-jammy

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    LAMBDA_TASK_ROOT=/var/task \
    # Chromium writes its profile/config to $HOME; only /tmp is writable in Lambda.
    HOME=/tmp

WORKDIR ${LAMBDA_TASK_ROOT}

# awslambdaric is the Lambda Runtime Interface Client (the runtime bootstrap).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt awslambdaric

# Guarantee the Chromium build matches the installed Playwright version.
RUN playwright install chromium

COPY handler.py scraper.py ./

# The runtime client turns the container into a Lambda; CMD names the handler.
ENTRYPOINT ["python", "-m", "awslambdaric"]
CMD ["handler.lambda_handler"]
