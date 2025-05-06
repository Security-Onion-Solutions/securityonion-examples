from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Only handles the encryption key for sensitive data in SQLite.
    All other configuration is stored in the database.
    """

    # Core settings
    ENCRYPTION_KEY: str = (
        "dGhpc2lzYXZhbGlkZmVybmV0a2V5Zm9yZGV2ZWxvcG1lbnQ="  # Valid Fernet key for development
    )
    SECRET_KEY: str = (
        "default-jwt-secret"  # Default for development, should be overridden in production
    )

    # Database settings
    DATABASE_URL: str = "sqlite+aiosqlite:////app/data/app.db"  # Default SQLite location in Docker volume
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# Create global settings instance
settings = Settings()
