"""
Central configuration.

All environment-specific values live here.
To switch from SQLite to PostgreSQL, change DATABASE_URL only - nothing else changes.
"""


class Settings:
    APP_NAME: str = "Finance Tracker API"
    APP_VERSION: str = "1.0.0"

    # Database - swap to postgresql://user:pass@host/db for production
    DATABASE_URL: str = "sqlite:///./finance_tracker.db"

    # JWT
    SECRET_KEY: str = "finance-tracker-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100


settings = Settings()
