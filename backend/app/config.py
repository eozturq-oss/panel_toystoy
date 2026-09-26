from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    trendyol_supplier_id: str
    trendyol_api_key: SecretStr
    trendyol_api_secret: SecretStr
    trendyol_base_url: str = "https://apigw.trendyol.com"
    trendyol_user_agent: str = "ToyMarketplaceIntegration/1.0"
    trendyol_timeout_seconds: float = 30.0
    hepsiburada_merchant_id: str | None = None
    hepsiburada_username: str | None = None
    hepsiburada_password: SecretStr | None = None
    hepsiburada_secret_key: SecretStr | None = None
    hepsiburada_base_url: str = "https://listing-external.hepsiburada.com"
    hepsiburada_timeout_seconds: float = 30.0
    marketplace_dry_run: bool = False

    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
