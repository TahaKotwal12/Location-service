import httpx
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import structlog
from app.config import settings
from app.models.response import (
    Address, AddressComponents, CoordinatesResponse, 
    AccuracyLevel, PlaceType, Metadata, LocationData, LocationResponse
)

logger = structlog.get_logger()

class GeocodingService:
    def __init__(self):
        self.google_maps_url = "https://maps.googleapis.com/maps/api/geocode/json"
        self.mapbox_url = "https://api.mapbox.com/geocoding/v5/mapbox.places"
        self.nominatim_url = "https://nominatim.openstreetmap.org/reverse"
        self.timeout = settings.EXTERNAL_API_TIMEOUT
    
    async def reverse_geocode(
        self, 
        lat: float, 
        lng: float, 
        language: str = "en"
    ) -> LocationResponse:
        """Main reverse geocoding with fallback strategy"""
        start_time = datetime.utcnow()
        
        # Try Google Maps first
        if settings.GOOGLE_MAPS_API_KEY:
            try:
                result = await self._google_maps_reverse_geocode(lat, lng, language)
                if result:
                    processing_time = self._calculate_processing_time(start_time)
                    location_data = self._create_location_data(result, "google_maps", processing_time)
                    return LocationResponse(
                        success=True,
                        data=location_data,
                        coordinates={"latitude": lat, "longitude": lng}
                    )
            except Exception as e:
                logger.warning("Google Maps API failed", error=str(e))
        
        # Try Mapbox as fallback
        if settings.MAPBOX_ACCESS_TOKEN:
            try:
                result = await self._mapbox_reverse_geocode(lat, lng, language)
                if result:
                    processing_time = self._calculate_processing_time(start_time)
                    location_data = self._create_location_data(result, "mapbox", processing_time)
                    return LocationResponse(
                        success=True,
                        data=location_data,
                        coordinates={"latitude": lat, "longitude": lng}
                    )
            except Exception as e:
                logger.warning("Mapbox API failed", error=str(e))
        
        # Try Nominatim as final fallback
        try:
            result = await self._nominatim_reverse_geocode(lat, lng, language)
            if result:
                processing_time = self._calculate_processing_time(start_time)
                location_data = self._create_location_data(result, "nominatim", processing_time)
                return LocationResponse(
                    success=True,
                    data=location_data,
                    coordinates={"latitude": lat, "longitude": lng}
                )
        except Exception as e:
            logger.warning("Nominatim API failed", error=str(e))
        
        # All services failed
        return LocationResponse(
            success=False,
            error={
                "code": "GEOCODING_FAILED",
                "message": "All geocoding services failed"
            },
            coordinates={"latitude": lat, "longitude": lng}
        )
    
    async def _google_maps_reverse_geocode(self, lat: float, lng: float, language: str) -> Optional[Dict[str, Any]]:
        """Google Maps reverse geocoding"""
        params = {
            "latlng": f"{lat},{lng}",
            "key": settings.GOOGLE_MAPS_API_KEY,
            "language": language
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.google_maps_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data["status"] == "OK" and data["results"]:
                return data["results"][0]
        return None
    
    async def _mapbox_reverse_geocode(self, lat: float, lng: float, language: str) -> Optional[Dict[str, Any]]:
        """Mapbox reverse geocoding"""
        url = f"{self.mapbox_url}/{lng},{lat}.json"
        params = {
            "access_token": settings.MAPBOX_ACCESS_TOKEN,
            "language": language
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data["features"]:
                return data["features"][0]
        return None
    
    async def _nominatim_reverse_geocode(self, lat: float, lng: float, language: str) -> Optional[Dict[str, Any]]:
        """Nominatim reverse geocoding"""
        params = {
            "lat": lat,
            "lon": lng,
            "format": "json",
            "addressdetails": 1,
            "accept-language": language
        }
        
        headers = {
            "User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION}"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.nominatim_url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if data:
                return data
        return None
    
    def _create_location_data(self, raw_data: Dict[str, Any], source: str, processing_time: str) -> LocationData:
        """Create LocationData from raw API response"""
        # This is a simplified version - in practice, you'd parse each API's response format
        
        # Default address components
        components = AddressComponents(
            street="Unknown Street",
            locality="Unknown City",
            state="Unknown State",
            country="Unknown Country",
            countryCode="XX"
        )
        
        # Try to extract formatted address
        formatted_address = "Address not available"
        if source == "google_maps":
            formatted_address = raw_data.get("formatted_address", "Address not available")
        elif source == "nominatim":
            formatted_address = raw_data.get("display_name", "Address not available")
        elif source == "mapbox":
            formatted_address = raw_data.get("place_name", "Address not available")
        
        address = Address(
            fullAddress=formatted_address,
            formattedAddress=formatted_address,
            shortAddress=formatted_address[:50] + "..." if len(formatted_address) > 50 else formatted_address,
            components=components,
            coordinates=CoordinatesResponse(
                latitude=0.0,
                longitude=0.0,
                accuracy=AccuracyLevel.MEDIUM
            ),
            placeType=PlaceType.LOCALITY,
            confidence=0.8
        )
        
        metadata = Metadata(
            source=source,
            processingTime=processing_time,
            cached=False,
            lastUpdated=datetime.utcnow()
        )
        
        return LocationData(
            address=address,
            metadata=metadata
        )
    
    def _calculate_processing_time(self, start_time: datetime) -> str:
        """Calculate processing time"""
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        return f"{duration:.3f}s"
    
    async def health_check(self) -> bool:
        """Check if geocoding services are available"""
        try:
            # Simple connectivity test
            async with httpx.AsyncClient(timeout=1) as client:
                response = await client.get("https://httpbin.org/status/200")
                return response.status_code == 200
        except:
            return False