import os
from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    MAPBOX_ACCESS_TOKEN: Optional[str] = None
    
    # Service Configuration
    APP_NAME: str = "Mini Location Service"
    APP_VERSION: str = "1.0.0"
    PORT: int = 3000
    HOST: str = "0.0.0.0"
    ENVIRONMENT: str = "development"
    
    # Cache Configuration (In-memory for serverless)
    CACHE_TTL_DEFAULT: int = 86400  # 24 hours
    CACHE_PRECISION: int = 4  # Coordinate precision for caching
    
    # Rate Limiting
    MAX_REQUESTS_PER_MINUTE: int = 1000
    RATE_LIMIT_PER_IP: int = 100
    
    # Timeouts (Adjusted for serverless)
    EXTERNAL_API_TIMEOUT: int = 10
    MAX_RESPONSE_TIME_MS: int = 5000
    
    # Supported Countries
    SUPPORTED_COUNTRIES: List[str] = ["IN", "US", "GB", "CA", "AU"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()