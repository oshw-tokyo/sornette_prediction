"""
FastAPI Configuration Settings
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FCO Analysis API"
    VERSION: str = "2.1.0"
    DESCRIPTION: str = "Financial Crisis Observatory Analysis System API"
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True  # Development mode
    
    # CORS Settings
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",  # Next.js development
        "http://localhost:8000",  # FastAPI Swagger UI
        "https://fco.yourdomain.com",  # Production frontend
    ]
    
    # Database Settings
    DATABASE_URL: Optional[str] = None
    SQLITE_DB_PATH: str = "../results/analysis_results.db"  # Reuse existing DB
    
    # Security Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # External API Keys (from existing .env)
    FRED_API_KEY: Optional[str] = os.getenv("FRED_API_KEY")
    ALPHA_VANTAGE_KEY: Optional[str] = os.getenv("ALPHA_VANTAGE_KEY")
    COINGECKO_API_KEY: Optional[str] = os.getenv("COINGECKO_API_KEY")
    
    # FCO Analysis Settings
    DEFAULT_ANALYSIS_PERIOD: int = 365  # days
    DEFAULT_WINDOW_MIN: int = 125
    DEFAULT_WINDOW_MAX: int = 750
    DEFAULT_WINDOW_STEP: int = 5
    
    # WebSocket Settings
    WS_MESSAGE_QUEUE_SIZE: int = 100
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    class Config:
        env_file = "../.env"  # Load from project root .env
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env
        
    def get_database_url(self) -> str:
        """Get database URL (SQLite for dev, PostgreSQL for prod)"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # Use SQLite for development (existing database)
        return f"sqlite:///{self.SQLITE_DB_PATH}"


settings = Settings()