from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LEADMAP_",
        extra="ignore",
    )

    database_url: str = "sqlite:///./data/leadmap.db"
    geographic_artifact_dir: str = "./data/geography"
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    browser_headless: bool = False
    max_capture_results: int = 20

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
