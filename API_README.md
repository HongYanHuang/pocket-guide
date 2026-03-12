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

## Transcript Endpoints

### Sectioned Transcript

Get sectioned transcript with titles and knowledge points for enhanced navigation and comprehension.

**Endpoint:** `GET /pois/{city}/{poi_id}/sectioned-transcript`

**Parameters:**
- `language` (query, optional): Language code (e.g., "en", "zh-tw"). Default: "en"
- `tour_id` (query, optional): Tour ID for tour-specific transcripts

**Response:**

```json
{
  "poi": "Colosseum",
  "language": "en",
  "generated_at": "2026-03-09T10:30:00Z",
  "version": "v1_2026-03-09",
  "total_sections": 3,
  "estimated_duration_seconds": 240,
  "has_sectioned_transcript": true,
  "sections": [
    {
      "section_number": 1,
      "title": "The Blood Sport Myth",
      "knowledge_point": "Why gladiatorial combat was less deadly than movies suggest",
      "transcript": "Picture this: You're a gladiator...",
      "estimated_duration_seconds": 80,
      "word_count": 133,
      "audio_file": "audio_section_1_en.mp3"
    },
    {
      "section_number": 2,
      "title": "The Engineering Marvel",
      "knowledge_point": "How Roman engineers built the world's largest amphitheater",
      "transcript": "Let's talk about the genius behind this structure...",
      "estimated_duration_seconds": 90,
      "word_count": 150,
      "audio_file": "audio_section_2_en.mp3"
    },
    {
      "section_number": 3,
      "title": "The Modern Legacy",
      "knowledge_point": "Why the Colosseum still influences stadium design today",
      "transcript": "Fast forward to today...",
      "estimated_duration_seconds": 70,
      "word_count": 117,
      "audio_file": "audio_section_3_en.mp3"
    }
  ],
  "summary_points": [
    "Gladiator battles were regulated sports, not death matches",
    "Roman engineering techniques are still used in stadiums today",
    "The Colosseum took only 8 years to build with 60,000 workers"
  ]
}
```

**Fallback Behavior:**
- If `sectioned_transcript_{language}.json` doesn't exist, returns plain transcript as single section with `has_sectioned_transcript: false`
- `audio_file` will point to `audio_{language}.mp3` for backward compatibility

**Example:**

```bash
# Get sectioned transcript in English
curl "http://localhost:8000/pois/rome/colosseum/sectioned-transcript?language=en"

# Get sectioned transcript in Chinese (Traditional)
curl "http://localhost:8000/pois/rome/colosseum/sectioned-transcript?language=zh-tw"
```

### Audio File Serving

Stream or download audio files for individual sections or full transcript.

**Endpoint:** `GET /pois/{city}/{poi_id}/audio/{filename}`

**Parameters:**
- `filename` (path): Audio filename
  - Section audio: `audio_section_{N}_{language}.mp3` (e.g., `audio_section_1_en.mp3`)
  - Full audio: `audio_{language}.mp3` (e.g., `audio_en.mp3`)

**Response:** MP3 audio file (Content-Type: audio/mpeg)

**Examples:**

```bash
# Stream section 1 audio
curl "http://localhost:8000/pois/rome/colosseum/audio/audio_section_1_en.mp3" -o section1.mp3

# Stream full audio (backward compatible)
curl "http://localhost:8000/pois/rome/colosseum/audio/audio_en.mp3" -o full_audio.mp3

# Use in HTML5 audio player
<audio controls src="http://localhost:8000/pois/rome/colosseum/audio/audio_section_1_en.mp3"></audio>
```

### Plain Transcript (Legacy)

Get plain text transcript without sections. Still supported for backward compatibility.

**Endpoint:** `GET /pois/{city}/{poi_id}/transcript`

**Parameters:**
- `language` (query, optional): Language code. Default: "en"
- `tour_id` (query, optional): Tour ID for tour-specific transcripts

**Response:**

```json
{
  "transcript": "Full transcript text without sections...",
  "summary": ["Point 1", "Point 2", "Point 3"],
  "has_transcript": true,
  "has_summary": true,
  "language": "en",
  "available_languages": ["en", "zh-tw", "fr"]
}
```

## Benefits of Sectioned Transcripts

**For Users:**
- **Navigation**: Jump to specific stories/topics
- **Progress Tracking**: See which sections completed
- **Better Comprehension**: Clear learning objectives per section
- **Flexible Listening**: Play/skip individual sections (30-90 seconds each)
- **Mobile-Friendly**: Pause after section, resume later

**For Developers:**
- **Foundation for Audio Chapters**: Section-based audio playback
- **Enhanced UX**: Accordion UI with section cards
- **Backward Compatible**: Legacy endpoints continue working
- **Dual Storage**: Both `sectioned_transcript_{lang}.json` and `transcript_{lang}.txt` saved
