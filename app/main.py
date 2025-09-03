from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time
import uuid
from datetime import datetime
import structlog

from app.config import settings
from app.api.v1.location import router as location_router
from app.utils.logging import configure_logging

# Configure structured logging
configure_logging()
logger = structlog.get_logger()

# Create FastAPI app (simplified for serverless)
app = FastAPI(
    title="Mini Location Service",
    description="High-performance location microservice for GPS coordinate reverse geocoding",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Request ID and timing middleware
@app.middleware("http")
async def add_request_id_and_timing(request: Request, call_next):
    """Add request ID and measure processing time"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Add request ID to headers
    request.state.request_id = request_id
    
    # Process request
    response = await call_next(request)
    
    # Add timing and request ID to response headers
    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.3f}s"
    
    # Log request
    logger.info(
        "Request processed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=f"{process_time:.3f}s",
        request_id=request_id
    )
    
    return response

# Rate limiting middleware (simple implementation)
request_counts = {}
@app.middleware("http")
async def rate_limiting(request: Request, call_next):
    """Simple rate limiting by IP"""
    if settings.ENVIRONMENT == "production":
        client_ip = request.client.host
        current_minute = int(time.time() / 60)
        key = f"{client_ip}:{current_minute}"
        
        if key in request_counts:
            request_counts[key] += 1
        else:
            request_counts[key] = 1
        
        # Clean old entries
        keys_to_remove = [k for k in request_counts.keys() 
                         if int(k.split(':')[1]) < current_minute - 1]
        for k in keys_to_remove:
            del request_counts[k]
        
        if request_counts[key] > settings.RATE_LIMIT_PER_IP:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    response = await call_next(request)
    return response

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.warning("Validation error", errors=exc.errors(), request_id=getattr(request.state, 'request_id', None))
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request data",
                "details": exc.errors()
            },
            "timestamp": datetime.utcnow().isoformat(),
            "requestId": getattr(request.state, 'request_id', None)
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail
            },
            "timestamp": datetime.utcnow().isoformat(),
            "requestId": getattr(request.state, 'request_id', None)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    request_id = getattr(request.state, 'request_id', None)
    logger.error("Unexpected error", error=str(exc), request_id=request_id)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "requestId": request_id
        }
    )

# Include routers
app.include_router(location_router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs_url": "/docs" if settings.ENVIRONMENT == "development" else None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower()
    )
