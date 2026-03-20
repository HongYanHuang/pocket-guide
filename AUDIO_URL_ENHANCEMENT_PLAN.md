# Audio URL Enhancement Plan

## Goal

Add audio URLs to tour API responses so client apps can easily access audio files without manually constructing URLs.

## Current Situation

### What We Have
- ✅ Audio files generated and accessible at `/pois/{city}/{poi_id}/audio/{filename}`
- ✅ Tour API returns POI data
- ❌ No `poi_id` or `audio_url` in tour response
- ❌ Client must manually construct URLs from POI names

### Current Tour Response
```json
{
  "itinerary": [
    {
      "day": 1,
      "pois": [
        {
          "poi": "Colosseum",
          "reason": "...",
          "coordinates": {...}
          // ❌ No poi_id
          // ❌ No audio_url
        }
      ]
    }
  ]
}
```

## Proposed Changes

### 1. Add Fields to TourPOI Model

**File:** `src/api_models.py`

**Changes:**
```python
class TourPOI(BaseModel):
    """POI within a tour itinerary"""
    poi: str = Field(..., description="POI name")
    poi_id: Optional[str] = Field(None, description="POI identifier (kebab-case)")  # NEW
    reason: str = Field(..., description="Why this POI was selected")
    # ... existing fields ...

    # Audio fields (NEW)
    audio_url: Optional[str] = Field(None, description="URL to full POI audio file")
    audio_available: Optional[bool] = Field(None, description="Whether audio is available")
    has_sectioned_audio: Optional[bool] = Field(None, description="Whether POI has sectioned audio")
    audio_sections: Optional[List[Dict[str, Any]]] = Field(None, description="Audio sections if available")
```

### 2. Add Helper Function to Generate Audio URLs

**File:** `src/utils.py`

**New function:**
```python
def poi_name_to_id(poi_name: str) -> str:
    """
    Convert POI name to kebab-case ID

    Args:
        poi_name: POI name (e.g., "Colosseum", "St. Peter's Basilica")

    Returns:
        POI ID in kebab-case (e.g., "colosseum", "st.-peter's-basilica")
    """
    import re
    # Convert to lowercase
    poi_id = poi_name.lower()
    # Replace spaces and special chars with hyphens
    poi_id = re.sub(r'[^a-z0-9]+', '-', poi_id)
    # Remove leading/trailing hyphens
    poi_id = poi_id.strip('-')
    return poi_id


def get_poi_audio_url(city: str, poi_name: str, language: str, base_url: str = "") -> str:
    """
    Generate audio URL for a POI

    Args:
        city: City name
        poi_name: POI name
        language: Language code (e.g., 'en', 'zh-tw')
        base_url: Base URL (empty for relative URLs)

    Returns:
        Audio URL
    """
    city_slug = city.lower().replace(' ', '-')
    poi_id = poi_name_to_id(poi_name)
    language_code = normalize_language_code(language)

    return f"{base_url}/pois/{city_slug}/{poi_id}/audio/audio_{language_code}.mp3"


def check_audio_exists(city: str, poi_name: str, language: str, content_dir: str = "content") -> bool:
    """
    Check if audio file exists for a POI

    Args:
        city: City name
        poi_name: POI name
        language: Language code
        content_dir: Content directory path

    Returns:
        True if audio file exists
    """
    from pathlib import Path

    city_slug = city.lower().replace(' ', '-')
    poi_id = poi_name_to_id(poi_name)
    language_code = normalize_language_code(language)

    audio_path = Path(content_dir) / city_slug / poi_id / f"audio_{language_code}.mp3"
    return audio_path.exists() and audio_path.stat().st_size > 0


def get_poi_audio_sections(city: str, poi_name: str, language: str, content_dir: str = "content") -> List[Dict[str, Any]]:
    """
    Get audio sections for a POI if available

    Args:
        city: City name
        poi_name: POI name
        language: Language code
        content_dir: Content directory path

    Returns:
        List of audio sections with URLs
    """
    from pathlib import Path
    import json

    city_slug = city.lower().replace(' ', '-')
    poi_id = poi_name_to_id(poi_name)
    language_code = normalize_language_code(language)

    poi_path = Path(content_dir) / city_slug / poi_id

    # Check if POI has sectioned transcript
    metadata_file = poi_path / "metadata.json"
    if not metadata_file.exists():
        return []

    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        sections = metadata.get('transcript_sections', {}).get(language_code, [])
        if not sections:
            return []

        # Add audio URLs to each section
        audio_sections = []
        for section in sections:
            section_num = section.get('section_number')
            audio_file = f"audio_section_{section_num}_{language_code}.mp3"
            audio_path = poi_path / audio_file

            if audio_path.exists():
                audio_sections.append({
                    'section_number': section_num,
                    'title': section.get('title', ''),
                    'audio_url': f"/pois/{city_slug}/{poi_id}/audio/{audio_file}"
                })

        return audio_sections
    except Exception:
        return []
```

### 3. Enhance Tour Endpoint to Add Audio URLs

**File:** `src/api_server.py`

**In `get_tour()` function, after loading POI data:**

```python
# Around line 1428, after creating TourPOI objects
for day_data in tour_data.get('itinerary', []):
    pois = []
    for poi_data in day_data.get('pois', []):
        # Create POI object
        poi = TourPOI(**poi_data)

        # Add poi_id (NEW)
        poi.poi_id = poi_name_to_id(poi.poi)

        # Get city from tour path
        city = tour_path.parent.name

        # Check audio availability (NEW)
        audio_exists_flag = check_audio_exists(city, poi.poi, language)

        if audio_exists_flag:
            # Generate audio URL
            poi.audio_url = get_poi_audio_url(city, poi.poi, language)
            poi.audio_available = True

            # Check for sectioned audio
            sections = get_poi_audio_sections(city, poi.poi, language)
            if sections:
                poi.has_sectioned_audio = True
                poi.audio_sections = sections
            else:
                poi.has_sectioned_audio = False
        else:
            poi.audio_available = False

        pois.append(poi)
```

## Expected Result

### Enhanced Tour Response
```json
{
  "itinerary": [
    {
      "day": 1,
      "pois": [
        {
          "poi": "Colosseum",
          "poi_id": "colosseum",
          "reason": "...",
          "coordinates": {...},
          "audio_url": "/pois/rome/colosseum/audio/audio_zh-tw.mp3",
          "audio_available": true,
          "has_sectioned_audio": false
        },
        {
          "poi": "Basilica di San Clemente",
          "poi_id": "basilica-di-san-clemente",
          "reason": "...",
          "audio_url": "/pois/rome/basilica-di-san-clemente/audio/audio_zh-tw.mp3",
          "audio_available": true,
          "has_sectioned_audio": true,
          "audio_sections": [
            {
              "section_number": 1,
              "title": "Introduction",
              "audio_url": "/pois/rome/basilica-di-san-clemente/audio/audio_section_1_zh-tw.mp3"
            },
            {
              "section_number": 2,
              "title": "The Mithraeum",
              "audio_url": "/pois/rome/basilica-di-san-clemente/audio/audio_section_2_zh-tw.mp3"
            }
          ]
        }
      ]
    }
  ]
}
```

## Benefits

### For Client Apps
- ✅ No need to construct URLs manually
- ✅ Clear indication of audio availability
- ✅ Support for sectioned audio playback
- ✅ Resilient to server URL structure changes
- ✅ poi_id provided for direct POI access

### For API
- ✅ More RESTful design
- ✅ Self-documenting responses
- ✅ Better client experience
- ✅ Backward compatible (optional fields)

## Implementation Steps

1. ✅ Document the plan (this file)
2. ⏳ Add helper functions to `src/utils.py`
3. ⏳ Update TourPOI model in `src/api_models.py`
4. ⏳ Enhance tour endpoint in `src/api_server.py`
5. ⏳ Test with existing tour
6. ⏳ Update API documentation
7. ⏳ Update CLIENT_AUDIO_PLAYBACK.md with enhanced approach

## Testing

### Test Cases
```bash
# 1. Get tour with audio URLs
curl -s "http://localhost:8000/tours/rome-tour-20260320-175540-6b0704?language=zh-tw" \
  -H "Authorization: Bearer <token>" | jq '.itinerary[0].pois[0]'

# Expected:
# {
#   "poi": "Basilica di San Clemente",
#   "poi_id": "basilica-di-san-clemente",
#   "audio_url": "/pois/rome/basilica-di-san-clemente/audio/audio_zh-tw.mp3",
#   "audio_available": true,
#   ...
# }

# 2. Verify audio URL works
curl -I "http://localhost:8000/pois/rome/basilica-di-san-clemente/audio/audio_zh-tw.mp3"

# Expected: HTTP 200 OK
```

## Alternatives Considered

### Option 1: Client Constructs URLs (Current)
**Pros:** No backend changes
**Cons:** Client must know URL structure, breaks if server changes format

### Option 2: Separate Audio Metadata Endpoint
**Pros:** Separation of concerns
**Cons:** Extra API call needed, more complexity

### Option 3: Include Audio URLs in Tour Response (Chosen) ✅
**Pros:** Single API call, clear availability, flexible for future changes
**Cons:** Slightly larger response size

## Backward Compatibility

All new fields are **optional**, so:
- ✅ Old clients continue to work
- ✅ New clients get enhanced data
- ✅ No breaking changes

## Next Steps

1. Implement helper functions
2. Update models
3. Enhance tour endpoint
4. Test thoroughly
5. Update documentation
6. Deploy to production

---

**Status:** Ready for implementation
**Estimated Time:** 1-2 hours
**Risk:** Low (backward compatible)
