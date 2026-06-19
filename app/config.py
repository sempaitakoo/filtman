from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    API_ID: str
    API_HASH: str
    SESSION_NAME: str


settings = Settings()  # pyright: ignore[reportCallIssue]
