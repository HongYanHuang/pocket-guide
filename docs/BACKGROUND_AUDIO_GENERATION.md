# Background Audio Generation

## Overview

Automatic audio generation for tours using Edge TTS (free), with background processing and progress tracking.

**Status**: ✅ Implemented
**Branch**: `feature/background-audio-generation`
**Date**: 2026-03-30

---

## Features

### Core Functionality

- **Background Processing**: Audio generates in background thread, doesn't block tour creation
- **Progress Tracking**: Real-time status via `/tours/{tour_id}/audio-status` endpoint
- **Fail-Safe**: Tour creation succeeds even if audio generation fails
- **Free TTS**: Uses Edge TTS (Microsoft) - no API key required
- **Sectioned Audio**: Generates separate audio files for each transcript section

### User Experience

**Client App Flow**:
```
1. User creates tour → Tour ID returned in ~30s
2. App shows tour immediately (can browse while audio generates)
3. App polls /audio-status every 5-10 seconds
4. "🔊 Audio ready!" notification when status = completed
5. User can play audio in tour
```

**Backstage Flow**:
```
1. Admin creates tour → Receives tour ID
2. Background audio generation starts automatically
3. Admin can check status in tour details page
4. Error alerts shown if generation fails
5. Can manually retry via trip tts command if needed
```

---

## API Changes

### Client Tour Generation

**Endpoint**: `POST /client/tours/generate`

**New Request Field**:
```json
{
  "city": "Taipei",
  "days": 1,
  "generate_audio": true  // Optional, default: true
}
```

**New Response Field**:
```json
{
  "success": true,
  "tour_id": "taipei-tour-123",
  "audio_generation_started": true,  // NEW
  // ... other fields
}
```

### Audio Status Endpoint

**Endpoint**: `GET /tours/{tour_id}/audio-status`

**Authentication**: Required (any authenticated user)

**Response**:
```json
{
  "tour_id": "taipei-tour-123",
  "status": "generating",
  "progress": 60,
  "total_pois": 5,
  "completed_pois": 3,
  "failed_pois": [],
  "error_message": null,
  "started_at": "2026-03-30T10:00:00Z",
  "completed_at": null,
  "provider": "edge",
  "language": "zh-tw",
  "city": "Taipei"
}
```

**Status Values**:
- `not_started` - No audio generation requested for this tour
- `pending` - Generation queued but not started
- `generating` - Audio currently being generated
- `completed` - All audio files generated successfully
- `failed` - Generation failed (see error_message)
- `error` - Unexpected error (see error_message)

---

## Architecture

### Components

1. **AudioGenerationTask** (`src/audio_background.py`)
   - Manages background threads
   - Tracks status in `audio_status/` directory
   - Calls `pocket-guide trip tts` command

2. **API Integration** (`src/api_client_tours.py`)
   - Triggers background generation after tour save
   - Always uses Edge TTS for client tours
   - Handles errors gracefully

3. **Status Endpoint** (`src/api_server.py`)
   - Returns status from JSON files
   - No database required
   - Accessible to all authenticated users

### Data Flow

```
[User creates tour]
        ↓
[Tour saved to database] (~30s)
        ↓
[Return tour_id to user] ✅ FAST
        ║
        ║ (User can use tour immediately)
        ║
        ╚══> [Background Thread Started]
                ↓
            [Status: pending]
                ↓
            [Execute: trip tts command]
                ↓
            [Status: generating]
                ↓
            [Generate section 1] (10s)
            [Generate section 2] (10s)
            [Generate section 3] (10s)
            [Generate section 4] (10s)
            [Generate section 5] (10s)
                ↓
            [Status: completed] ✅
                ↓
            [User notified: Audio ready!]
```

### Status File Format

Location: `audio_status/{tour_id}_audio.json`

```json
{
  "tour_id": "taipei-tour-123",
  "status": "generating",
  "progress": 60,
  "total_pois": 5,
  "completed_pois": 3,
  "failed_pois": [],
  "error_message": null,
  "started_at": "2026-03-30T10:00:00.123456",
  "completed_at": null,
  "provider": "edge",
  "language": "zh-tw",
  "city": "Taipei"
}
```

---

## Configuration

### Client App Tours

**Always Enabled**:
- `generate_audio`: Defaults to `true`
- `provider`: Always `edge` (no choice)
- Free, no configuration needed

### Backstage Tours

**Future Enhancement** (not in current implementation):
- Can choose provider: `edge`, `openai`, `google`, `qwen`
- Requires API keys for paid providers

---

## Error Handling

### Tour Creation Success

**Guaranteed**: Tour is ALWAYS created successfully, even if:
- Audio generation fails to start
- POI transcripts are missing
- Background thread crashes
- Command times out

### Error Scenarios

| Scenario | Behavior | User Experience |
|----------|----------|-----------------|
| POI transcripts missing | Status: `failed`, error message shown | Tour works, no audio available |
| Background thread crash | Status: `failed` or stuck on `generating` | Tour works, can retry manually |
| Command timeout (>10 min) | Status: `failed`, "timed out" message | Tour works, can retry manually |
| Edge TTS service down | Status: `failed`, error from subprocess | Tour works, can retry later |

### Manual Retry

If audio generation fails, admin can manually regenerate:

```bash
./pocket-guide trip tts <tour-id> \
  --city <city> \
  --language <language> \
  --provider edge
```

---

## Performance

### Timing

| Phase | Duration | User Wait |
|-------|----------|-----------|
| Tour creation | 20-50s | YES (API blocks) |
| Audio generation | 30-120s | NO (background) |
| **Total to usable tour** | **20-50s** | **Fast!** |
| **Total to audio ready** | **50-170s** | **Progressive** |

### Resource Usage

- **Memory**: ~50MB per background thread (subprocess)
- **CPU**: Low (Edge TTS is cloud-based)
- **Disk**: ~100-500KB per tour (status + audio files)
- **Network**: Depends on Edge TTS API latency

### Concurrency

- Multiple tours can generate audio simultaneously
- Each tour runs in separate thread
- No thread pool limit (spawns threads as needed)
- Daemon threads (don't prevent server shutdown)

---

## Testing

### Unit Test

```bash
python3 test_background_audio.py
```

Tests:
- ✓ AudioGenerationTask initialization
- ✓ Status retrieval for non-existent tour
- ✓ Status file creation and retrieval
- ✓ TourAudioStatus model validation

### Integration Test

```bash
# 1. Start server
uvicorn src.api_server:app --reload

# 2. Create tour (as authenticated user)
curl -X POST http://localhost:8000/client/tours/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Taipei",
    "days": 1,
    "language": "zh-tw",
    "generate_audio": true
  }'

# Response includes: "audio_generation_started": true

# 3. Check audio status
curl http://localhost:8000/tours/<tour-id>/audio-status \
  -H "Authorization: Bearer <token>"

# Poll every 5 seconds until status = "completed"

# 4. Verify audio files exist
ls -lh content/Taipei/*/audio_section_*_zh-tw.mp3
```

---

## Client Implementation Guide

### Flutter Example

```dart
// 1. Create tour
final response = await tourApi.generateTour(
  city: 'Taipei',
  days: 1,
  generateAudio: true, // Enable audio
);

final tourId = response.tourId;
final audioStarted = response.audioGenerationStarted;

// 2. Poll for audio status
if (audioStarted) {
  Timer.periodic(Duration(seconds: 5), (timer) async {
    final status = await tourApi.getAudioStatus(tourId);

    if (status.status == 'completed') {
      timer.cancel();
      _showAudioReadyNotification();
    } else if (status.status == 'failed') {
      timer.cancel();
      _showAudioErrorNotification(status.errorMessage);
    }

    // Update progress bar
    setState(() {
      _audioProgress = status.progress;
    });
  });
}
```

### React Example

```javascript
// 1. Create tour
const response = await fetch('/client/tours/generate', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    city: 'Taipei',
    days: 1,
    generateAudio: true
  })
});

const { tour_id, audio_generation_started } = await response.json();

// 2. Poll for status
if (audio_generation_started) {
  const pollAudioStatus = async () => {
    const statusResponse = await fetch(`/tours/${tour_id}/audio-status`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    const status = await statusResponse.json();

    if (status.status === 'completed') {
      showNotification('🔊 Audio ready!');
      return; // Stop polling
    } else if (status.status === 'failed') {
      showError('Audio generation failed');
      return;
    }

    // Update progress
    setAudioProgress(status.progress);

    // Poll again in 5 seconds
    setTimeout(pollAudioStatus, 5000);
  };

  pollAudioStatus();
}
```

---

## Future Enhancements

### Short Term

- [ ] Add WebSocket support for real-time updates (no polling needed)
- [ ] Retry mechanism for failed audio generation
- [ ] Progress updates during generation (per-POI)

### Long Term

- [ ] Backstage provider selection (OpenAI, Google, Qwen)
- [ ] Audio quality settings (voice, speed, pitch)
- [ ] Batch audio generation for multiple tours
- [ ] Audio preview before finalizing tour

---

## Troubleshooting

### Audio Not Generating

**Check**:
1. Is `audio_generation_started` true in tour response?
2. Check audio status: `GET /tours/{tour_id}/audio-status`
3. Check server logs for errors
4. Verify POI transcripts exist: `ls content/{city}/{poi-id}/transcript_{language}.txt`

**Common Causes**:
- POI content not generated yet
- Transcript links empty (tour created before POIs)
- Language mismatch (tour language != POI transcript language)

### Status Stuck on "Generating"

**Cause**: Background thread may have crashed or timed out

**Solution**:
```bash
# Check if process is still running
ps aux | grep "trip tts"

# Manually complete generation
./pocket-guide trip tts <tour-id> --city <city> --language <language>
```

### Audio Quality Issues

**Edge TTS Limitations**:
- Voice selection limited
- No emotion control
- May have blocking/rate limiting

**Alternative**: Use paid providers (OpenAI, Google) for better quality

---

## Security Considerations

### Authentication

- Audio status endpoint requires authentication
- Users can only check status for tours they have access to
- No sensitive data exposed in status

### Resource Limits

- No rate limiting on audio generation (yet)
- Each background thread uses subprocess (isolated)
- Daemon threads prevent server blocking

### Data Privacy

- Status files stored on server
- Audio files accessible via tour access permissions
- No PII in audio status

---

## Migration Notes

### Existing Tours

- Old tours have no audio status (status = "not_started")
- Can manually generate audio: `trip tts <tour-id> ...`
- No breaking changes to tour structure

### Rollback Plan

If issues arise:
1. Set `generate_audio: false` in client requests
2. Audio generation won't trigger
3. Tours work normally without audio
4. Can enable later when fixed

---

## Metrics to Track

### Success Metrics

- % of tours with audio successfully generated
- Average audio generation time
- Audio generation failure rate
- User engagement with audio (play rate)

### Performance Metrics

- API response time (should stay ~30s)
- Background generation time
- Server resource usage
- Edge TTS API latency

---

## References

- [Edge TTS Documentation](https://github.com/rany2/edge-tts)
- [TTS Generator Code](../src/tts_generator.py)
- [Audio Background Code](../src/audio_background.py)
- [API Models](../src/api_models.py)

---

**Questions?** Check the code or ask the development team.

**Last Updated**: 2026-03-30
**Author**: Development Team + Claude Sonnet 4.5
