from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env")
    API_ID: str
    API_HASH: str
    SESSION_NAME: str

    @property
    def session_path(self) -> str:
        return str(PROJECT_ROOT / self.SESSION_NAME)


settings = Settings()  # ty: ignore[missing-argument]
