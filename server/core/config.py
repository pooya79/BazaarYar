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

    frontend_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        validation_alias="FRONTEND_ORIGINS",
    )
    phoenix_enabled: bool = Field(
        default=False,
        validation_alias="PHOENIX_ENABLED",
    )
    phoenix_project_name: str = Field(
        default="bazaaryar-agent",
        validation_alias="PHOENIX_PROJECT_NAME",
    )
    phoenix_collector_endpoint: str = Field(
        default="http://localhost:4317",
        validation_alias="PHOENIX_COLLECTOR_ENDPOINT",
    )

    gemini_model: str = Field(
        default="gemini-3-pro-preview",
        validation_alias="GEMINI_MODEL",
    )
    gemini_thinking_level: str = Field(
        default="high",
        validation_alias="GEMINI_THINKING_LEVEL",
    )
    google_api_key: str = Field(
        default="",
        validation_alias="GOOGLE_API_KEY",
    )

    openai_model: str = Field(
        default="gpt-4.1-mini",
        validation_alias="OPENAI_MODEL",
    )
    openai_api_key: str = Field(
        default="",
        validation_alias="OPENAI_API_KEY",
    )

    openailike_model: str = Field(
        default="gpt-4.1-mini",
        validation_alias="OPENAILIKE_MODEL",
    )
    openailike_api_key: str = Field(
        default="",
        validation_alias="OPENAILIKE_API_KEY",
    )
    openailike_base_url: str = Field(
        default="",
        validation_alias="OPENAILIKE_BASE_URL",
    )

    upload_storage_dir: str = Field(
        default="server/storage/uploads",
        validation_alias="UPLOAD_STORAGE_DIR",
    )
    upload_max_size_bytes: int = Field(
        default=15 * 1024 * 1024,
        validation_alias="UPLOAD_MAX_SIZE_BYTES",
    )
    context_max_tokens: int = Field(
        default=16_000,
        validation_alias="CONTEXT_MAX_TOKENS",
    )
    context_target_tokens: int = Field(
        default=12_000,
        validation_alias="CONTEXT_TARGET_TOKENS",
    )
    context_keep_last_turns: int = Field(
        default=6,
        validation_alias="CONTEXT_KEEP_LAST_TURNS",
    )
    tables_agent_write_enabled: bool = Field(
        default=False,
        validation_alias="TABLES_AGENT_WRITE_ENABLED",
    )
    tables_max_columns: int = Field(
        default=150,
        validation_alias="TABLES_MAX_COLUMNS",
    )
    tables_max_file_size_bytes: int = Field(
        default=25 * 1024 * 1024,
        validation_alias="TABLES_MAX_FILE_SIZE_BYTES",
    )
    tables_max_import_rows: int = Field(
        default=50_000,
        validation_alias="TABLES_MAX_IMPORT_ROWS",
    )
    tables_max_query_rows: int = Field(
        default=500,
        validation_alias="TABLES_MAX_QUERY_ROWS",
    )
    tables_export_max_rows: int = Field(
        default=5_000,
        validation_alias="TABLES_EXPORT_MAX_ROWS",
    )
    tables_query_timeout_ms: int = Field(
        default=8_000,
        validation_alias="TABLES_QUERY_TIMEOUT_MS",
    )
    tables_max_filters: int = Field(
        default=20,
        validation_alias="TABLES_MAX_FILTERS",
    )
    tables_max_aggregates: int = Field(
        default=10,
        validation_alias="TABLES_MAX_AGGREGATES",
    )
    tables_max_cell_length: int = Field(
        default=4_000,
        validation_alias="TABLES_MAX_CELL_LENGTH",
    )
    sandbox_tool_enabled: bool = Field(
        default=False,
        validation_alias="SANDBOX_TOOL_ENABLED",
    )
    sandbox_docker_image: str = Field(
        default="bazaaryar-python-sandbox:latest",
        validation_alias="SANDBOX_DOCKER_IMAGE",
    )
    sandbox_docker_bin: str = Field(
        default="docker",
        validation_alias="SANDBOX_DOCKER_BIN",
    )
    sandbox_max_runtime_seconds: int = Field(
        default=90,
        validation_alias="SANDBOX_MAX_RUNTIME_SECONDS",
    )
    sandbox_max_memory_mb: int = Field(
        default=1024,
        validation_alias="SANDBOX_MAX_MEMORY_MB",
    )
    sandbox_max_cpu: float = Field(
        default=1.0,
        validation_alias="SANDBOX_MAX_CPU",
    )
    sandbox_max_artifacts: int = Field(
        default=8,
        validation_alias="SANDBOX_MAX_ARTIFACTS",
    )
    sandbox_max_artifact_bytes: int = Field(
        default=10_485_760,
        validation_alias="SANDBOX_MAX_ARTIFACT_BYTES",
    )
    sandbox_max_code_chars: int = Field(
        default=20_000,
        validation_alias="SANDBOX_MAX_CODE_CHARS",
    )

    @computed_field
    @property
    def frontend_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

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
