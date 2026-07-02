from pydantic_settings import BaseSettings
from typing import Optional


VERSION = "1.3.0"


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017/cse"
    mongo_host: str = ""
    jwt_secret_key: str = "super-secret-key-change-in-production"
    jwt_access_token_expires: int = 86400

    class Config:
        env_file = ".env"


settings = Settings()
