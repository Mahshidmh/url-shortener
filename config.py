from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    api_key: str


settings = Settings()
