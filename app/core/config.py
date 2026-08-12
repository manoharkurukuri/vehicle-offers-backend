from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Vehicle Offer Extraction API"
    app_env: str = "local"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./vehicle_offers.db"
    local_storage_dir: str = "./storage/offers"
    app_timezone: str = "America/Los_Angeles"

    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "llama-3.3-70b-versatile"
    groq_structured_output_method: Literal[
        "function_calling", "json_mode", "json_schema"
    ] = "function_calling"
    groq_timeout_seconds: int = 120
    groq_max_retries: int = 2
    max_body_chars: int = 350_000

    scrapingbee_api_key: SecretStr = SecretStr("")
    scrapingbee_endpoint: str = "https://app.scrapingbee.com/api/v1/"
    playwright_headless: bool = False
    scrape_timeout_seconds: int = 60
    scrapingbee_timeout_seconds: int = 90

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
