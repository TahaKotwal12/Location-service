from http.server import BaseHTTPRequestHandler
import json
import sys
import os
import asyncio
from urllib.parse import urlparse, parse_qs

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our services
from app.services.geocoding import GeocodingService
from app.services.validation import ValidationService
from app.services.cache import CacheService

class handler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Initialize services
        self.geocoding_service = GeocodingService()
        self.validation_service = ValidationService()
        self.cache_service = CacheService()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self._send_json_response({
                "service": "Mini Location Service",
                "version": "1.0.0",
                "status": "running",
                "endpoints": {
                    "reverse_geocode": "POST /api/v1/location/reverse",
                    "batch_geocode": "POST /api/v1/location/reverse/batch",
                    "health": "GET /api/v1/location/health"
                }
            })
        elif parsed_path.path == '/api/v1/location/health':
            self._handle_health_check()
        else:
            self._send_error_response(404, "Not Found")
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/v1/location/reverse':
            self._handle_reverse_geocode()
        elif parsed_path.path == '/api/v1/location/reverse/batch':
            self._handle_batch_reverse_geocode()
        else:
            self._send_error_response(404, "Not Found")
    
    def _handle_health_check(self):
        try:
            from datetime import datetime
            # Simple health check
            response = {
                "status": "healthy",
                "services": {
                    "cache": "up",
                    "geocoding": "up"
                },
                "timestamp": datetime.utcnow()
            }
            self._send_json_response(response)
        except Exception as e:
            self._send_error_response(500, f"Health check failed: {str(e)}")
    
    def _handle_reverse_geocode(self):
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error_response(400, "Request body required")
                return
            
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            # Validate required fields
            if 'latitude' not in data or 'longitude' not in data:
                self._send_error_response(400, "latitude and longitude are required")
                return
            
            lat = float(data['latitude'])
            lng = float(data['longitude'])
            language = data.get('language', 'en')
            
            # Validate coordinates
            try:
                self.validation_service.validate_coordinates(lat, lng)
            except ValueError as e:
                self._send_error_response(400, str(e))
                return
            
            # Run async geocoding
            result = asyncio.run(self._geocode_async(lat, lng, language))
            self._send_json_response(result)
            
        except json.JSONDecodeError:
            self._send_error_response(400, "Invalid JSON")
        except ValueError as e:
            self._send_error_response(400, str(e))
        except Exception as e:
            self._send_error_response(500, f"Internal server error: {str(e)}")
    
    def _handle_batch_reverse_geocode(self):
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error_response(400, "Request body required")
                return
            
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            # Validate required fields
            if 'locations' not in data:
                self._send_error_response(400, "locations array is required")
                return
            
            locations = data['locations']
            language = data.get('language', 'en')
            
            if len(locations) > 100:
                self._send_error_response(400, "Maximum 100 locations allowed")
                return
            
            # Process batch
            result = asyncio.run(self._batch_geocode_async(locations, language))
            self._send_json_response(result)
            
        except json.JSONDecodeError:
            self._send_error_response(400, "Invalid JSON")
        except Exception as e:
            self._send_error_response(500, f"Internal server error: {str(e)}")
    
    async def _geocode_async(self, lat, lng, language):
        """Async geocoding with caching"""
        try:
            # Check cache first
            cached_result = await self.cache_service.get_location(lat, lng, language)
            if cached_result:
                return {
                    "success": True,
                    "data": cached_result,
                    "cached": True
                }
            
            # Get location from geocoding service
            location_response = await self.geocoding_service.reverse_geocode(lat, lng, language)
            
            # Cache the result
            if location_response.success:
                await self.cache_service.set_location(lat, lng, language, location_response.dict())
            
            return location_response.dict()
            
        except Exception as e:
            return {
                "success": False,
                "error": {
                    "code": "GEOCODING_ERROR",
                    "message": str(e)
                },
                "coordinates": {"latitude": lat, "longitude": lng}
            }
    
    async def _batch_geocode_async(self, locations, language):
        """Async batch geocoding"""
        results = []
        
        for location in locations:
            try:
                lat = float(location['latitude'])
                lng = float(location['longitude'])
                
                result = await self._geocode_async(lat, lng, language)
                results.append(result)
                
            except Exception as e:
                results.append({
                    "success": False,
                    "error": {
                        "code": "INVALID_LOCATION",
                        "message": str(e)
                    }
                })
        
        successful = sum(1 for r in results if r.get('success', False))
        
        return {
            "success": True,
            "total_requests": len(locations),
            "successful_requests": successful,
            "results": results
        }
    
    def _send_json_response(self, data, status_code=200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        response_json = json.dumps(data, indent=2, default=self._json_serializer)
        self.wfile.write(response_json.encode())
    
    def _json_serializer(self, obj):
        """JSON serializer for objects not serializable by default json code"""
        from datetime import datetime
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def _send_error_response(self, status_code, message):
        """Send error response"""
        error_data = {
            "success": False,
            "error": {
                "code": f"HTTP_{status_code}",
                "message": message
            }
        }
        self._send_json_response(error_data, status_code)
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers() 