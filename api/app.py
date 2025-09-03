import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app
from app.main import app

# Import Mangum for ASGI to AWS Lambda/Vercel adapter
try:
    from mangum import Mangum
    # Create the handler with explicit configuration
    handler = Mangum(
        app,
        lifespan="off",
        api_gateway_base_path=None,
        text_mime_types=[
            "application/json",
            "application/javascript",
            "application/xml",
            "application/vnd.api+json",
        ]
    )
except ImportError:
    # Fallback if Mangum is not available
    handler = app

# For compatibility with different serverless platforms
application = handler
app_handler = handler 