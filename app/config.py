import os
from datetime import timedelta
from pydantic import BaseSettings, PostgresDsn, EmailStr
import secrets

class Settings(BaseSettings):
    # Base URL
    BASE_URL: str = os.getenv("LEAGUELEDGER_BASE_URL", "http://localhost:8000")
    
    # Database settings
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "3306")
    DB_NAME: str = os.getenv("DB_NAME", "leagueledger")
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASS: str = os.getenv("DB_PASS", "")
    
    # MySQL connection string
    DATABASE_URL: str = f"mysql+mysqldb://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # Session settings
    SESSION_MAX_AGE: int = 86400  # 1 day in seconds
    
    # Email settings
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "noreply@leagueledger.net")
    MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME", "LeagueLedger")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "587"))
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "localhost")
    MAIL_STARTTLS: bool = os.getenv("MAIL_STARTTLS", "True").lower() == "true"
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL_TLS", "False").lower() == "true"
    MAIL_USE_CREDENTIALS: bool = os.getenv("MAIL_USE_CREDENTIALS", "True").lower() == "true"
    MAIL_VALIDATE_CERTS: bool = os.getenv("MAIL_VALIDATE_CERTS", "True").lower() == "true"
    
    # OAuth Settings
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    # QR Code settings
    QR_CODE_BOX_SIZE: int = 10
    QR_CODE_BORDER: int = 4
    
    # Team settings
    MAX_TEAM_SIZE: int = 10
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
