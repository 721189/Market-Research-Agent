import os
from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    PROJECT_NAME: str = "MarketAI Authoritative API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://marketai:secret@postgres:5432/marketai"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # Object Storage (S3 / MinIO)
    S3_ENDPOINT: str = os.getenv("S3_ENDPOINT", "http://minio:9000")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "marketai-reports")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    
    # Gemini AI
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # Security & Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "marketai-super-secret-key-change-in-prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://marketai.app",
    ]
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://marketai.app",
    ]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE_IP: int = 60
    RATE_LIMIT_PER_MINUTE_USER: int = 120
    RATE_LIMIT_PER_MINUTE_ORG: int = 300

    class Config:
        case_sensitive = True

settings = Settings()
