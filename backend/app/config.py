from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = 8000
    cors_origins: str = ""
    max_llm_attempts: int = Field(default=3, ge=1)
    max_threat_model_bytes: int = Field(default=200_000, ge=1)
    database_url: str = "sqlite:///./data/fault-tree-ai.db"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
