import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    LLM_API_KEYS: str = "placeholder_key_1,placeholder_key_2"
    DATABASE_URL: str = "sqlite:////data/app.db"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    ENABLE_FAILURE_SIMULATION: bool = True
    LLM_MODEL: str = "gemini/gemini-flash-lite-latest"
    MOCK_LLM: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def key_pool(self) -> List[str]:
        keys = [k.strip() for k in self.LLM_API_KEYS.split(",") if k.strip()]
        return keys

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

settings = Settings()
