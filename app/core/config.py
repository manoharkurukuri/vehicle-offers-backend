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

    # Scraping runs in a dedicated AWS Lambda container image.
    aws_region: str = "ap-south-2"
    scraper_lambda_name: str = "vehicle_offer_scraper"
    scraper_lambda_invoke_timeout: int = 180

    # Generated Excel workbooks are stored on Cloudinary (as raw files).
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: SecretStr = SecretStr("")
    cloudinary_api_secret: SecretStr = SecretStr("")
    cloudinary_folder: str = "vehicle-offers"

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
