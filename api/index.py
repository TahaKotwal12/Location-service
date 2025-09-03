from mangum import Mangum
import sys
import os

# Add the parent directory to Python path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

# Create the handler that Vercel will invoke
handler = Mangum(app, lifespan="off") 