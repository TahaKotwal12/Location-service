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
        
        # Parse address components based on source
        if source == "google_maps":
            components, formatted_address = self._parse_google_maps_response(raw_data)
        elif source == "nominatim":
            components, formatted_address = self._parse_nominatim_response(raw_data)
        elif source == "mapbox":
            components, formatted_address = self._parse_mapbox_response(raw_data)
        else:
            components = AddressComponents()
            formatted_address = "Address not available"
        
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
    
    def _parse_google_maps_response(self, data: Dict[str, Any]) -> tuple:
        """Parse Google Maps API response"""
        formatted_address = data.get("formatted_address", "Address not available")
        
        # Initialize components
        components_data = {
            "street": None,
            "locality": None,
            "city": None,
            "state": None,
            "country": None,
            "countryCode": None,
            "pincode": None
        }
        
        # Parse address components
        for component in data.get("address_components", []):
            types = component.get("types", [])
            long_name = component.get("long_name")
            short_name = component.get("short_name")
            
            if "route" in types:
                components_data["street"] = long_name
            elif "sublocality_level_1" in types or "sublocality" in types:
                components_data["locality"] = long_name
            elif "locality" in types:
                components_data["city"] = long_name
            elif "administrative_area_level_1" in types:
                components_data["state"] = long_name
            elif "country" in types:
                components_data["country"] = long_name
                components_data["countryCode"] = short_name
            elif "postal_code" in types:
                components_data["pincode"] = long_name
        
        components = AddressComponents(**components_data)
        return components, formatted_address
    
    def _parse_nominatim_response(self, data: Dict[str, Any]) -> tuple:
        """Parse Nominatim API response"""
        formatted_address = data.get("display_name", "Address not available")
        
        address = data.get("address", {})
        components_data = {
            "street": address.get("road"),
            "locality": address.get("suburb") or address.get("neighbourhood"),
            "city": address.get("city") or address.get("town") or address.get("village"),
            "state": address.get("state"),
            "country": address.get("country"),
            "countryCode": address.get("country_code", "").upper() if address.get("country_code") else None,
            "pincode": address.get("postcode")
        }
        
        components = AddressComponents(**components_data)
        return components, formatted_address
    
    def _parse_mapbox_response(self, data: Dict[str, Any]) -> tuple:
        """Parse Mapbox API response"""
        formatted_address = data.get("place_name", "Address not available")
        
        # Mapbox uses context array for components
        context = data.get("context", [])
        properties = data.get("properties", {})
        
        components_data = {
            "street": properties.get("address"),
            "locality": None,
            "city": None,
            "state": None,
            "country": None,
            "countryCode": None,
            "pincode": None
        }
        
        for item in context:
            item_id = item.get("id", "")
            if item_id.startswith("place"):
                components_data["city"] = item.get("text")
            elif item_id.startswith("region"):
                components_data["state"] = item.get("text")
            elif item_id.startswith("country"):
                components_data["country"] = item.get("text")
                components_data["countryCode"] = item.get("short_code", "").upper()
            elif item_id.startswith("postcode"):
                components_data["pincode"] = item.get("text")
        
        components = AddressComponents(**components_data)
        return components, formatted_address
    
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