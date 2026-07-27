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
    market_indicator_artifact_dir: str = "./data/market-indicators"
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    browser_headless: bool = False
    browser_profile_directory: str = "browser-profile"
    max_capture_results: int = 20
    max_traversal_results: int = 100
    max_traversal_scrolls: int = 40
    max_traversal_seconds: float = 90.0
    max_stagnant_scrolls: int = 3

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
