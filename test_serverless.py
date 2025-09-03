#!/usr/bin/env python3
"""
Test script to verify the serverless version works
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.main import app
from app.services.cache import CacheService

def test_imports():
    """Test that all imports work correctly"""
    print("✅ All imports successful")

def test_cache_service():
    """Test the in-memory cache service"""
    cache = CacheService()
    
    # Test cache operations
    import asyncio
    
    async def test_cache():
        # Test set and get
        test_data = {"test": "data", "cached": True}
        await cache.set_location(40.7128, -74.0060, "en", test_data)
        
        result = await cache.get_location(40.7128, -74.0060, "en")
        assert result is not None
        assert result["test"] == "data"
        
        # Test health check
        health = await cache.health_check()
        assert health == True
        
        print("✅ Cache service working correctly")
    
    asyncio.run(test_cache())

def test_app_creation():
    """Test that the FastAPI app is created correctly"""
    assert app is not None
    assert hasattr(app, 'routes')
    print("✅ FastAPI app created successfully")

if __name__ == "__main__":
    print("Testing serverless version...")
    
    try:
        test_imports()
        test_cache_service() 
        test_app_creation()
        print("\n🎉 All tests passed! The serverless version is ready for Vercel deployment.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1) 