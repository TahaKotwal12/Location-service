"""Logging configuration utilities"""
import structlog
import sys
from app.config import settings


def configure_logging():
    """Configure structured logging with structlog"""
    # Use JSON renderer for production/serverless environments
    renderer = structlog.processors.JSONRenderer()
    if settings.ENVIRONMENT == "development":
        renderer = structlog.dev.ConsoleRenderer()
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    ) 