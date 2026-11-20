from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JWT_SECRET = "dev-only-change-me"
DEFAULT_ADMIN_PASSWORD = "Admin@12345"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Office Parking Slot Tracker API"
    environment: str = "development"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "parking_tracker"
    jwt_secret_key: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    admin_password: str = DEFAULT_ADMIN_PASSWORD
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_for_runtime(self) -> None:
        if self.environment != "development" and self.jwt_secret_key == DEFAULT_JWT_SECRET:
            raise RuntimeError("JWT_SECRET_KEY must be set to a strong secret outside development.")
        if self.environment != "development" and self.admin_password == DEFAULT_ADMIN_PASSWORD:
            raise RuntimeError("ADMIN_PASSWORD must be changed outside development.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
