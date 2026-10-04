from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    api_key: str
    log_level: str = "INFO"

settings = Settings()
