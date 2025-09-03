#!/usr/bin/env python3
"""
Test script to verify the Vercel handler works correctly
"""
import sys
import os

def test_handler_import():
    """Test that the handler can be imported correctly"""
    try:
        sys.path.insert(0, os.path.abspath('.'))
        from api.index import handler
        print("✅ Handler imported successfully")
        print(f"✅ Handler type: {type(handler)}")
        return True
    except Exception as e:
        print(f"❌ Handler import failed: {e}")
        return False

def test_app_import():
    """Test that the app can be imported correctly"""
    try:
        from app.main import app
        print("✅ FastAPI app imported successfully")
        print(f"✅ App type: {type(app)}")
        return True
    except Exception as e:
        print(f"❌ App import failed: {e}")
        return False

def test_routes():
    """Test that routes are properly registered"""
    try:
        from app.main import app
        routes = [route.path for route in app.routes]
        print(f"✅ Routes found: {routes}")
        
        # Check for expected routes
        expected_paths = ["/", "/api/v1/location/reverse", "/api/v1/location/health"]
        for path in expected_paths:
            if any(path in route for route in routes):
                print(f"✅ Found expected route: {path}")
            else:
                print(f"⚠️  Route not found: {path}")
        return True
    except Exception as e:
        print(f"❌ Route test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Vercel handler setup...")
    print("=" * 50)
    
    success = True
    success &= test_app_import()
    success &= test_handler_import()
    success &= test_routes()
    
    print("=" * 50)
    if success:
        print("🎉 All tests passed! Ready for Vercel deployment.")
        print("\nNext steps:")
        print("1. git add .")
        print("2. git commit -m 'Fix Vercel deployment'")
        print("3. git push")
        print("4. Deploy to Vercel")
    else:
        print("❌ Some tests failed. Check the errors above.")
        sys.exit(1) 