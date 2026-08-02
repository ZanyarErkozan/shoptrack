from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Vitrin"
    database_url: str = "sqlite:///./shoptrack.db"
    host: str = "0.0.0.0"
    port: int = 7070
    currency: str = "TRY"


@lru_cache
def get_settings() -> Settings:
    return Settings()
