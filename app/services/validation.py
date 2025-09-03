from typing import Tuple, Optional
from app.models.request import LocationRequest
from app.config import settings

class ValidationService:
    @staticmethod
    def validate_coordinates(lat: float, lng: float) -> None:
        """Validate GPS coordinates"""
        if not (-90 <= lat <= 90):
            raise ValueError(f"Latitude {lat} must be between -90 and 90 degrees")
        
        if not (-180 <= lng <= 180):
            raise ValueError(f"Longitude {lng} must be between -180 and 180 degrees")
    
    @staticmethod
    def validate_country_support(country_code: Optional[str]) -> bool:
        """Check if country is supported"""
        if not country_code:
            return True  # Auto-detect
        return country_code.upper() in settings.SUPPORTED_COUNTRIES
    
    @staticmethod
    def validate_request(request: LocationRequest) -> Tuple[bool, Optional[str]]:
        """Comprehensive request validation"""
        # Validate coordinates
        coords_valid, coords_error = ValidationService.validate_coordinates(
            request.coordinates.latitude, 
            request.coordinates.longitude
        )
        if not coords_valid:
            return False, coords_error
        
        # Validate country support
        if not ValidationService.validate_country_support(request.countryCode):
            return False, f"Country {request.countryCode} is not supported"
        
        return True, None