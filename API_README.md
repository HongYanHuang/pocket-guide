# POI Metadata API

FastAPI backend for managing POI metadata including coordinates, operation hours, and distance matrices.

## Running the Server

```bash
# Start the server
python src/api_server.py

# Or use uvicorn directly
uvicorn src.api_server:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

## API Documentation

Interactive API documentation is automatically available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints

### Health & Info
- `GET /` - API information and endpoint list
- `GET /health` - Health check

### Cities
- `GET /cities` - List all cities with POI counts
- `GET /cities/{city}/pois` - List all POIs for a city
- `GET /cities/{city}/verify` - Verify metadata completeness for a city
- `POST /cities/{city}/collect` - Collect metadata for all POIs in a city

### POI Metadata
- `GET /pois/{city}/{poi_id}` - Get detailed metadata for a POI
- `PUT /pois/{city}/{poi_id}/metadata` - Update POI metadata
- `POST /pois/{city}/{poi_id}/recollect` - Re-collect metadata from Google Maps

### Distance Matrix
- `GET /distances/{city}` - Get distance matrix for a city
- `POST /distances/{city}/recalculate` - Recalculate distance matrix

## Example Usage

### List Cities
```bash
curl http://localhost:8000/cities
```

Response:
```json
[
  {
    "name": "Athens",
    "slug": "athens",
    "poi_count": 2
  }
]
```

### Get POI Metadata
```bash
curl http://localhost:8000/pois/Athens/acropolis
```

Response:
```json
{
  "poi_id": "acropolis",
  "poi_name": "Acropolis",
  "city": "Athens",
  "metadata": {
    "coordinates": {
      "latitude": 37.9715323,
      "longitude": 23.7257492,
      "source": "google_maps_api",
      "collected_at": "2025-11-26T20:02:24.996765+00:00"
    },
    "operation_hours": {
      "weekday_text": [
        "Monday: 8:00 AM – 8:00 PM",
        "Tuesday: 8:00 AM – 8:00 PM",
        ...
      ]
    },
    "visit_info": {
      "indoor_outdoor": "outdoor",
      "typical_duration_minutes": 120,
      "accessibility": "partial"
    }
  }
}
```

### Update POI Metadata
```bash
curl -X PUT http://localhost:8000/pois/Athens/acropolis/metadata \
  -H "Content-Type: application/json" \
  -d '{
    "visit_info": {
      "indoor_outdoor": "outdoor",
      "typical_duration_minutes": 120,
      "accessibility": "wheelchair_accessible"
    },
    "verified": true
  }'
```

Response:
```json
{
  "message": "Metadata updated successfully for acropolis",
  "data": {
    "poi_id": "acropolis",
    "city": "Athens"
  }
}
```

### Get Distance Matrix
```bash
curl http://localhost:8000/distances/Athens
```

Response:
```json
{
  "city": "Athens",
  "generated_at": "2025-11-26T20:02:26.045477+00:00",
  "poi_count": 2,
  "poi_pairs": {
    "acropolis_to_arch-of-hadrian": {
      "origin_poi_id": "acropolis",
      "origin_poi_name": "Acropolis",
      "destination_poi_id": "arch-of-hadrian",
      "destination_poi_name": "Arch of Hadrian",
      "walking": {
        "duration_minutes": 10.9,
        "distance_km": 0.79,
        "duration_text": "11 mins",
        "distance_text": "0.8 km"
      },
      "transit": {...},
      "driving": {...}
    }
  }
}
```

### Verify Metadata Completeness
```bash
curl http://localhost:8000/cities/Athens/verify
```

Response:
```json
{
  "city": "Athens",
  "total_pois": 2,
  "complete": 2,
  "incomplete": 0,
  "missing_fields": {},
  "pois": [
    {
      "poi_id": "acropolis",
      "poi_name": "Acropolis",
      "has_metadata": true,
      "missing_fields": []
    }
  ]
}
```

## Data Models

### POIMetadataUpdate
Update POI metadata fields:
```json
{
  "coordinates": {
    "latitude": 37.9715,
    "longitude": 23.7257
  },
  "visit_info": {
    "indoor_outdoor": "outdoor|indoor|mixed|unknown",
    "typical_duration_minutes": 120,
    "accessibility": "wheelchair_accessible|partial|none|unknown"
  },
  "operation_hours": {...},
  "address": "string",
  "phone": "string",
  "website": "string",
  "wheelchair_accessible": true,
  "verified": true
}
```

## CORS Configuration

The API is configured to accept requests from any origin (`*`). For production use, update the CORS middleware in `src/api_server.py` to specify allowed origins:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Update this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Authentication

This API currently has no authentication. For production use, consider adding:
- API key authentication
- OAuth2/JWT tokens
- Rate limiting

## Error Responses

All errors return a consistent format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `200` - Success
- `404` - Resource not found (city or POI)
- `422` - Validation error (invalid request data)
- `500` - Internal server error
- `503` - Service unavailable (configuration issue)
