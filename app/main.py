from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Load .env into the process environment so boto3 (and other SDKs that read
# os.environ directly, e.g. AWS_ACCESS_KEY_ID) can see the credentials.
load_dotenv()

import logfire  # noqa: E402
from fastapi import FastAPI  # noqa: E402

from app.core.config import settings  # noqa: E402

# Configure Logfire before importing the application's Pydantic schemas/models.
logfire.configure(
    service_name=settings.app_name,
    environment=settings.app_env,
    send_to_logfire="if-token-present",
)
logfire.instrument_pydantic(record="failure")

from app.api.v1.router import api_router  # noqa: E402
from app.core.exception_handlers import register_exception_handlers  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
import app.models  # noqa: E402, F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Simple v1 bootstrapping. Replace with Alembic migrations before production.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)

logfire.instrument_fastapi(app)
logfire.instrument_sqlalchemy(engine=engine)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
