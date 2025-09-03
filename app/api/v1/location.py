"""Location API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
import structlog

from app.models.request import LocationRequest, BatchLocationRequest
from app.models.response import LocationResponse, BatchLocationResponse, ErrorResponse
from app.services.geocoding import GeocodingService
from app.services.validation import ValidationService
from app.services.cache import CacheService

logger = structlog.get_logger()

router = APIRouter(
    prefix="/api/v1/location",
    tags=["location"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        429: {"model": ErrorResponse, "description": "Rate Limit Exceeded"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)

# Initialize services
geocoding_service = GeocodingService()
validation_service = ValidationService()
cache_service = CacheService()


@router.post("/reverse", response_model=LocationResponse)
async def reverse_geocode(request: LocationRequest):
    """
    Reverse geocode a single GPS coordinate to get location information
    
    - **latitude**: GPS latitude coordinate (-90 to 90)
    - **longitude**: GPS longitude coordinate (-180 to 180)
    - **language**: Optional language code for the response (default: en)
    """
    try:
        # Validate coordinates
        validation_service.validate_coordinates(request.latitude, request.longitude)
        
        # Check cache first
        cached_result = await cache_service.get_location(
            request.latitude, 
            request.longitude, 
            request.language
        )
        
        if cached_result:
            logger.info("Cache hit", lat=request.latitude, lng=request.longitude)
            return LocationResponse(**cached_result)
        
        # Get location from geocoding service
        location_response = await geocoding_service.reverse_geocode(
            request.latitude,
            request.longitude,
            request.language
        )
        
        # Cache the result (convert to dict for caching)
        await cache_service.set_location(
            request.latitude,
            request.longitude,
            request.language,
            location_response.dict()
        )
        
        logger.info("Reverse geocoding successful", lat=request.latitude, lng=request.longitude)
        return location_response
        
    except ValueError as e:
        logger.warning("Validation error", error=str(e), lat=request.latitude, lng=request.longitude)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Geocoding error", error=str(e), lat=request.latitude, lng=request.longitude)
        raise HTTPException(status_code=500, detail="Failed to process location request")


@router.post("/reverse/batch", response_model=BatchLocationResponse)
async def batch_reverse_geocode(request: BatchLocationRequest):
    """
    Reverse geocode multiple GPS coordinates in a single request
    
    - **locations**: List of coordinate objects with latitude and longitude
    - **language**: Optional language code for all responses (default: en)
    """
    try:
        if len(request.locations) > 100:  # Limit batch size
            raise HTTPException(status_code=400, detail="Batch size cannot exceed 100 locations")
        
        results = []
        for i, location in enumerate(request.locations):
            try:
                # Validate coordinates
                validation_service.validate_coordinates(location.latitude, location.longitude)
                
                # Check cache first
                cached_result = await cache_service.get_location(
                    location.latitude,
                    location.longitude,
                    request.language
                )
                
                if cached_result:
                    results.append(LocationResponse(**cached_result))
                else:
                    # Get location from geocoding service
                    location_response = await geocoding_service.reverse_geocode(
                        location.latitude,
                        location.longitude,
                        request.language
                    )
                    
                    # Cache the result (convert to dict for caching)
                    await cache_service.set_location(
                        location.latitude,
                        location.longitude,
                        request.language,
                        location_response.dict()
                    )
                    
                    results.append(location_response)
                    
            except ValueError as e:
                # Add error result for invalid coordinates
                results.append(LocationResponse(
                    success=False,
                    error={
                        "code": "INVALID_COORDINATES",
                        "message": str(e)
                    },
                    coordinates={
                        "latitude": location.latitude,
                        "longitude": location.longitude
                    }
                ))
            except Exception as e:
                # Add error result for geocoding failure
                results.append(LocationResponse(
                    success=False,
                    error={
                        "code": "GEOCODING_ERROR",
                        "message": "Failed to process location"
                    },
                    coordinates={
                        "latitude": location.latitude,
                        "longitude": location.longitude
                    }
                ))
        
        successful_results = len([r for r in results if r.success])
        logger.info("Batch geocoding completed", 
                   total=len(request.locations), 
                   successful=successful_results)
        
        return BatchLocationResponse(
            success=True,
            total_requests=len(request.locations),
            successful_requests=successful_results,
            results=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch geocoding error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process batch request")


@router.get("/health")
async def health_check():
    """Health check endpoint for the location service"""
    try:
        # Test cache connection
        await cache_service.health_check()
        
        # Test geocoding service
        await geocoding_service.health_check()
        
        return {
            "status": "healthy",
            "services": {
                "cache": "up",
                "geocoding": "up"
            }
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        } 