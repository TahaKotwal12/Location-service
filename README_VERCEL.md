# Deploy to Vercel

This FastAPI location service is ready for Vercel deployment.

## Quick Deploy

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/yourusername/location)

## Manual Deployment

1. **Install Vercel CLI**
   ```bash
   npm i -g vercel
   ```

2. **Clone and Deploy**
   ```bash
   git clone <your-repo>
   cd location
   vercel --prod
   ```

## Environment Variables

Set these in your Vercel dashboard under Settings > Environment Variables:

### Optional (for better geocoding accuracy):
- `GOOGLE_MAPS_API_KEY` - Google Maps Geocoding API key
- `MAPBOX_ACCESS_TOKEN` - Mapbox access token

### Service Configuration:
- `APP_NAME` - Service name (default: "Mini Location Service")
- `ENVIRONMENT` - Environment (production/development)
- `EXTERNAL_API_TIMEOUT` - API timeout in seconds (default: 10)
- `LOG_LEVEL` - Logging level (default: "INFO")

## API Endpoints

Once deployed, your service will be available at:

- **Root**: `https://your-app.vercel.app/`
- **Health**: `https://your-app.vercel.app/api/v1/location/health`
- **Reverse Geocode**: `POST https://your-app.vercel.app/api/v1/location/reverse`
- **Batch Geocode**: `POST https://your-app.vercel.app/api/v1/location/reverse/batch`

## Example Usage

```bash
curl -X POST "https://your-app.vercel.app/api/v1/location/reverse" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 40.7128,
    "longitude": -74.0060,
    "language": "en"
  }'
```

## Features

- ✅ Serverless-ready (no Redis dependency)
- ✅ In-memory caching for session
- ✅ Multiple geocoding providers (Google Maps, Mapbox, Nominatim)
- ✅ Automatic fallback to free Nominatim service
- ✅ Rate limiting and error handling
- ✅ Structured logging
- ✅ OpenAPI documentation

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python -m uvicorn app.main:app --reload --port 3000
```

Visit `http://localhost:3000/docs` for API documentation. 