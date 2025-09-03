import json
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.config import settings
from app.models.response import PlaceType
import structlog

logger = structlog.get_logger()

# In-memory cache for serverless environment
_cache_store = {}

class CacheService:
    def __init__(self):
        # Use in-memory cache for serverless deployment
        self.cache_store = _cache_store
    
    def generate_cache_key(self, lat: float, lng: float, language: str = "en") -> str:
        """Generate cache key for coordinates with precision rounding"""
        precision = settings.CACHE_PRECISION
        rounded_lat = round(lat * (10 ** precision)) / (10 ** precision)
        rounded_lng = round(lng * (10 ** precision)) / (10 ** precision)
        return f"location:{rounded_lat}:{rounded_lng}:{language}"
    
    def get_cache_ttl(self, place_type: str) -> int:
        """Get TTL based on place type"""
        ttl_mapping = {
            PlaceType.STREET_ADDRESS: 86400,    # 24 hours
            PlaceType.LOCALITY: 604800,         # 7 days
            PlaceType.ADMINISTRATIVE: 2592000,  # 30 days
            PlaceType.ESTABLISHMENT: 86400,     # 24 hours
            PlaceType.POINT_OF_INTEREST: 86400  # 24 hours
        }
        return ttl_mapping.get(place_type, settings.CACHE_TTL_DEFAULT)
    
    async def get_location(self, lat: float, lng: float, language: str = "en") -> Optional[Dict[Any, Any]]:
        """Get cached location data"""
        try:
            cache_key = self.generate_cache_key(lat, lng, language)
            
            if cache_key in self.cache_store:
                cached_item = self.cache_store[cache_key]
                
                # Check if cache has expired
                if datetime.utcnow() < cached_item['expires_at']:
                    logger.info("Cache hit", cache_key=cache_key)
                    return cached_item['data']
                else:
                    # Remove expired item
                    del self.cache_store[cache_key]
            
            logger.info("Cache miss", cache_key=cache_key)
            return None
            
        except Exception as e:
            logger.error("Cache error during get", error=str(e))
            return None
    
    async def set_location(
        self, 
        lat: float, 
        lng: float, 
        language: str,
        data: Dict[Any, Any], 
        place_type: Optional[str] = None
    ) -> bool:
        """Cache location data"""
        try:
            cache_key = self.generate_cache_key(lat, lng, language)
            ttl = self.get_cache_ttl(place_type) if place_type else settings.CACHE_TTL_DEFAULT
            
            # Add cache metadata
            cache_data = {
                **data,
                "cached_at": datetime.utcnow().isoformat(),
                "cache_ttl": ttl
            }
            
            # Store with expiration time
            self.cache_store[cache_key] = {
                'data': cache_data,
                'expires_at': datetime.utcnow() + timedelta(seconds=ttl)
            }
            
            logger.info("Data cached", cache_key=cache_key, ttl=ttl)
            return True
            
        except Exception as e:
            logger.error("Cache error during set", error=str(e))
            return False
    
    async def health_check(self) -> bool:
        """Check cache health"""
        try:
            # Simple health check for in-memory cache
            return True
        except Exception:
            return False