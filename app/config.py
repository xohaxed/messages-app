"""Application configuration, loaded from environment variables.

No secret has a default. A missing DB_PASSWORD stops the app at startup with
a clear validation error instead of failing later inside a connection stack
trace. min_length=1 also rejects an EMPTY password, which otherwise slips
through and produces a confusing "no password supplied" retry loop.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str = Field(min_length=1)
    app_env: str = "dev"


settings = Settings()
