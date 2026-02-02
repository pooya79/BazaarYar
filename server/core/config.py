from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _build_postgres_dsn(
    *,
    host: str,
    port: int,
    name: str,
    user: str,
    password: str,
    ssl_mode: str,
) -> str:
    encoded_user = quote_plus(user)
    encoded_password = quote_plus(password) if password else ""
    auth = f"{encoded_user}:{encoded_password}" if encoded_password else encoded_user
    dsn = f"postgresql://{auth}@{host}:{port}/{name}"
    if ssl_mode:
        dsn = f"{dsn}?sslmode={quote_plus(ssl_mode)}"
    return dsn


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="development", validation_alias="ENVIRONMENT")

    db_host: str = Field(default="localhost", validation_alias="DB_HOST")
    db_port: int = Field(default=5432, validation_alias="DB_PORT")
    db_name: str = Field(default="bazaaryar_dev", validation_alias="DB_NAME")
    db_user: str = Field(default="bazaaryar", validation_alias="DB_USER")
    db_password: str = Field(default="bazaaryar", validation_alias="DB_PASSWORD")
    db_ssl_mode: str = Field(default="prefer", validation_alias="DB_SSL_MODE")

    database_url: PostgresDsn | None = Field(default=None, validation_alias="DATABASE_URL")

    @computed_field
    @property
    def database_dsn(self) -> str:
        if self.database_url is not None:
            return str(self.database_url)
        return _build_postgres_dsn(
            host=self.db_host,
            port=self.db_port,
            name=self.db_name,
            user=self.db_user,
            password=self.db_password,
            ssl_mode=self.db_ssl_mode,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
