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

    # Google Gemini via its OpenAI-compatible endpoint.
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_timeout_seconds: int = 120
    gemini_max_retries: int = 2
    # Cap completion size so long 5-offer outputs don't get truncated mid-JSON.
    gemini_max_tokens: int = 8000

    # Active LLM provider.
    llm_provider: Literal["gemini", "groq"] = "gemini"

    max_body_chars: int = 350_000

    # Scraping runs in a dedicated AWS Lambda container image.
    aws_region: str = "ap-south-2"
    scraper_lambda_name: str = "vehicle_offer_scraper"
    scraper_lambda_invoke_timeout: int = 180

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
