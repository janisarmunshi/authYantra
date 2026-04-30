import os
from functools import lru_cache
from datetime import timedelta
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings"""

    # App settings
    APP_NAME: str = "Auth Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENV: str = os.getenv("ENV", "development")

    # Database
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "authYantra")

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{quote_plus(self.POSTGRES_PASSWORD)}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # JWT settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production-with-secure-key-32-chars-min")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Encryption
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "change-me-in-production-32-chars-key")

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds
    LOGIN_RATE_LIMIT: int = 5  # attempts per minute

    # Microsoft Entra ID
    ENTRA_ID_TENANT_ID: str = os.getenv("ENTRA_ID_TENANT_ID", "")
    ENTRA_ID_CLIENT_ID: str = os.getenv("ENTRA_ID_CLIENT_ID", "")
    ENTRA_ID_CLIENT_SECRET: str = os.getenv("ENTRA_ID_CLIENT_SECRET", "")
    ENTRA_ID_AUTHORITY: str = "https://login.microsoftonline.com"

    # SMTP / Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtpout.secureserver.net")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USE_SSL: bool = os.getenv("SMTP_USE_SSL", "true").lower() == "true"
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "false").lower() == "true"
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "admin@marketyantra.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "admin@marketyantra.com")
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "authYantra")

    # Frontend URL (used in email links)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # Password reset token expiry
    PASSWORD_RESET_EXPIRE_MINUTES: int = int(os.getenv("PASSWORD_RESET_EXPIRE_MINUTES", "60"))

    # API settings
    CORS_ORIGINS: list = ["*"]  # Restrict in production

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
