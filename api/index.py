import sys
import os

# Add the parent directory to Python path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

# Create a simple ASGI app handler for Vercel
def handler(event, context):
    """
    Vercel serverless function handler
    """
    # Import here to avoid issues with Vercel's runtime
    from mangum import Mangum
    
    # Create Mangum handler with proper configuration
    asgi_handler = Mangum(app, lifespan="off", api_gateway_base_path=None)
    
    return asgi_handler(event, context) 