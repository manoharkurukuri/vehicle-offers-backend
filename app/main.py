from contextlib import asynccontextmanager

import logfire
from fastapi import FastAPI

from app.core.config import settings

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
