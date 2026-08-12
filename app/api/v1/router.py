from fastapi import APIRouter

from app.api.v1.endpoints import companies, offers, scrape_runs


api_router = APIRouter()
api_router.include_router(companies.router)
api_router.include_router(offers.router)
api_router.include_router(scrape_runs.router)
