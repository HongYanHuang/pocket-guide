# Client-Side Audio Playback Guide

## Overview

This document outlines how client-side applications (mobile apps, web apps) can access and play audio files for POIs and tours.

## Current Audio API

### Endpoint

**GET** `/pois/{city}/{poi_id}/audio/{filename}`

**Example:**
```
GET http://localhost:8000/pois/rome/colosseum/audio/audio_zh-tw.mp3
```

**Response:**
- Media Type: `audio/mpeg`
- Content: MP3 audio file
- Authentication: **Not required** (public endpoint)

### Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `city` | string | City name (kebab-case) | `rome`, `paris`, `athens` |
| `poi_id` | string | POI identifier (kebab-case) | `colosseum`, `pantheon` |
| `filename` | string | Audio filename | `audio_zh-tw.mp3`, `audio_en.mp3` |

### Filename Pattern

- **Full audio**: `audio_{language}.mp3`
- **Sectioned audio**: `audio_section_{number}_{language}.mp3`

Examples:
- `audio_en.mp3` - English full audio
- `audio_zh-tw.mp3` - Traditional Chinese (Taiwan) full audio
- `audio_section_1_en.mp3` - English section 1
- `audio_section_2_zh-tw.mp3` - Chinese section 2

---

## Client-Side Options

### Option 1: Direct Audio URL (Recommended)

**How it works:**
- Client constructs audio URL from city, POI ID, and language
- Plays audio directly using native media player

**Advantages:**
- ✅ Simple implementation
- ✅ Works on all platforms (iOS, Android, Web)
- ✅ Native media controls
- ✅ Supports seeking, pause, resume
- ✅ No authentication needed
- ✅ CORS enabled for web apps

**Example Implementation:**

#### Flutter/Dart (Mobile)
```dart
import 'package:audioplayers/audioplayers.dart';

class AudioService {
  final AudioPlayer _player = AudioPlayer();
  final String baseUrl = 'http://your-api.com';

  Future<void> playPOIAudio({
    required String city,
    required String poiId,
    required String language,
  }) async {
    final audioUrl = '$baseUrl/pois/$city/$poiId/audio/audio_$language.mp3';

    await _player.play(UrlSource(audioUrl));
  }

  Future<void> playSectionAudio({
    required String city,
    required String poiId,
    required int sectionNumber,
    required String language,
  }) async {
    final audioUrl = '$baseUrl/pois/$city/$poiId/audio/audio_section_${sectionNumber}_$language.mp3';

    await _player.play(UrlSource(audioUrl));
  }

  Future<void> pause() async {
    await _player.pause();
  }

  Future<void> resume() async {
    await _player.resume();
  }

  Future<void> stop() async {
    await _player.stop();
  }

  // Listen to playback state
  void onPlayerStateChanged(Function(PlayerState) callback) {
    _player.onPlayerStateChanged.listen(callback);
  }

  // Listen to playback position
  void onPositionChanged(Function(Duration) callback) {
    _player.onPositionChanged.listen(callback);
  }

  // Seek to position
  Future<void> seek(Duration position) async {
    await _player.seek(position);
  }
}
```

**Package:** `audioplayers: ^5.0.0`

#### React Native (Mobile)
```javascript
import Sound from 'react-native-sound';

const BASE_URL = 'http://your-api.com';

class AudioService {
  constructor() {
    this.sound = null;
  }

  playPOIAudio(city, poiId, language) {
    const audioUrl = `${BASE_URL}/pois/${city}/${poiId}/audio/audio_${language}.mp3`;

    if (this.sound) {
      this.sound.release();
    }

    this.sound = new Sound(audioUrl, '', (error) => {
      if (error) {
        console.error('Failed to load audio:', error);
        return;
      }

      // Play the sound
      this.sound.play((success) => {
        if (!success) {
          console.error('Playback failed');
        }
      });
    });
  }

  pause() {
    if (this.sound) {
      this.sound.pause();
    }
  }

  resume() {
    if (this.sound) {
      this.sound.play();
    }
  }

  stop() {
    if (this.sound) {
      this.sound.stop();
      this.sound.release();
      this.sound = null;
    }
  }

  seek(seconds) {
    if (this.sound) {
      this.sound.setCurrentTime(seconds);
    }
  }
}

export default new AudioService();
```

**Package:** `react-native-sound`

#### Web (HTML5 Audio)
```javascript
class AudioService {
  constructor() {
    this.audio = new Audio();
    this.baseUrl = 'http://your-api.com';
  }

  playPOIAudio(city, poiId, language) {
    const audioUrl = `${this.baseUrl}/pois/${city}/${poiId}/audio/audio_${language}.mp3`;

    this.audio.src = audioUrl;
    this.audio.load();
    this.audio.play().catch(error => {
      console.error('Playback failed:', error);
    });
  }

  playSectionAudio(city, poiId, sectionNumber, language) {
    const audioUrl = `${this.baseUrl}/pois/${city}/${poiId}/audio/audio_section_${sectionNumber}_${language}.mp3`;

    this.audio.src = audioUrl;
    this.audio.load();
    this.audio.play().catch(error => {
      console.error('Playback failed:', error);
    });
  }

  pause() {
    this.audio.pause();
  }

  resume() {
    this.audio.play();
  }

  stop() {
    this.audio.pause();
    this.audio.currentTime = 0;
  }

  seek(seconds) {
    this.audio.currentTime = seconds;
  }

  // Event listeners
  onPlaying(callback) {
    this.audio.addEventListener('playing', callback);
  }

  onPause(callback) {
    this.audio.addEventListener('pause', callback);
  }

  onEnded(callback) {
    this.audio.addEventListener('ended', callback);
  }

  onTimeUpdate(callback) {
    this.audio.addEventListener('timeupdate', callback);
  }

  // Get duration
  getDuration() {
    return this.audio.duration;
  }

  // Get current position
  getCurrentTime() {
    return this.audio.currentTime;
  }
}

export default new AudioService();
```

#### React Component Example
```jsx
import React, { useState, useEffect } from 'react';
import audioService from './audioService';

function POIAudioPlayer({ city, poiId, language }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    // Set up event listeners
    audioService.onPlaying(() => setIsPlaying(true));
    audioService.onPause(() => setIsPlaying(false));
    audioService.onTimeUpdate(() => {
      setCurrentTime(audioService.getCurrentTime());
      setDuration(audioService.getDuration());
    });

    return () => {
      audioService.stop();
    };
  }, []);

  const handlePlay = () => {
    if (isPlaying) {
      audioService.pause();
    } else {
      if (currentTime === 0) {
        audioService.playPOIAudio(city, poiId, language);
      } else {
        audioService.resume();
      }
    }
  };

  const handleSeek = (e) => {
    const seekTime = parseFloat(e.target.value);
    audioService.seek(seekTime);
    setCurrentTime(seekTime);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="audio-player">
      <button onClick={handlePlay}>
        {isPlaying ? 'Pause' : 'Play'}
      </button>

      <input
        type="range"
        min="0"
        max={duration || 0}
        value={currentTime}
        onChange={handleSeek}
      />

      <span>
        {formatTime(currentTime)} / {formatTime(duration)}
      </span>
    </div>
  );
}
```

---

### Option 2: Download and Cache (Offline Support)

**How it works:**
- Download audio files to local storage
- Play from local cache
- Update cache when needed

**Advantages:**
- ✅ Offline playback
- ✅ Faster loading after first download
- ✅ Reduced bandwidth usage
- ✅ Better user experience in poor network

**Disadvantages:**
- ❌ More complex implementation
- ❌ Storage management required
- ❌ Need to handle cache expiration

**Example (Flutter):**
```dart
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'dart:io';

class CachedAudioService {
  Future<String> getCachedAudioPath({
    required String city,
    required String poiId,
    required String language,
  }) async {
    final dir = await getApplicationDocumentsDirectory();
    final cacheDir = Directory('${dir.path}/audio_cache');
    if (!await cacheDir.exists()) {
      await cacheDir.create(recursive: true);
    }

    final filename = 'audio_${city}_${poiId}_$language.mp3';
    final filePath = '${cacheDir.path}/$filename';
    final file = File(filePath);

    // Check if already cached
    if (await file.exists()) {
      return filePath;
    }

    // Download and cache
    final url = '$baseUrl/pois/$city/$poiId/audio/audio_$language.mp3';
    final response = await http.get(Uri.parse(url));

    if (response.statusCode == 200) {
      await file.writeAsBytes(response.bodyBytes);
      return filePath;
    } else {
      throw Exception('Failed to download audio');
    }
  }

  Future<void> playPOIAudio({
    required String city,
    required String poiId,
    required String language,
  }) async {
    final audioPath = await getCachedAudioPath(
      city: city,
      poiId: poiId,
      language: language,
    );

    await _player.play(DeviceFileSource(audioPath));
  }

  Future<void> clearCache() async {
    final dir = await getApplicationDocumentsDirectory();
    final cacheDir = Directory('${dir.path}/audio_cache');
    if (await cacheDir.exists()) {
      await cacheDir.delete(recursive: true);
    }
  }

  Future<int> getCacheSize() async {
    final dir = await getApplicationDocumentsDirectory();
    final cacheDir = Directory('${dir.path}/audio_cache');
    if (!await cacheDir.exists()) return 0;

    int totalSize = 0;
    await for (var entity in cacheDir.list(recursive: true)) {
      if (entity is File) {
        totalSize += await entity.length();
      }
    }
    return totalSize;
  }
}
```

---

### Option 3: Streaming with Range Requests

**How it works:**
- Request audio in chunks using HTTP Range headers
- Support seeking without downloading full file
- Progressive download as user plays

**Status:** ✅ **Already Supported**

FastAPI's `FileResponse` automatically supports HTTP Range requests, enabling:
- Seeking in audio without full download
- Progressive loading
- Better bandwidth usage

**Client Implementation (Automatic):**
Most media players automatically use range requests when available. No special client code needed.

**Verification:**
```bash
# Test range request support
curl -I -H "Range: bytes=0-1023" http://localhost:8000/pois/rome/colosseum/audio/audio_zh-tw.mp3

# Expected response headers:
# HTTP/1.1 206 Partial Content
# Content-Range: bytes 0-1023/2200000
# Content-Length: 1024
```

---

## Tour Integration

### Current Situation

Tours currently return POI data **without** audio URLs. Clients must construct URLs manually.

**Tour Response (current):**
```json
{
  "itinerary": [
    {
      "day": 1,
      "pois": [
        {
          "poi": "Colosseum",
          "poi_id": "colosseum",  // ❌ Not included currently
          "coordinates": {...},
          "reason": "..."
        }
      ]
    }
  ]
}
```

### Proposed Enhancement

**Option A: Add audio_url to tour responses**

```json
{
  "itinerary": [
    {
      "day": 1,
      "pois": [
        {
          "poi": "Colosseum",
          "poi_id": "colosseum",
          "audio_url": "/pois/rome/colosseum/audio/audio_zh-tw.mp3",
          "audio_available": true,
          "sections": [
            {
              "section_number": 1,
              "title": "Introduction",
              "audio_url": "/pois/rome/colosseum/audio/audio_section_1_zh-tw.mp3"
            }
          ]
        }
      ]
    }
  ]
}
```

**Advantages:**
- ✅ Client doesn't need to know URL structure
- ✅ Server can change URL format without breaking clients
- ✅ Clear indication of audio availability

**Option B: Client constructs URLs (current approach)**

```javascript
// Client constructs URL from POI name and language
function getAudioUrl(city, poiName, language) {
  const poiId = poiName.toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');

  return `/pois/${city}/${poiId}/audio/audio_${language}.mp3`;
}

// Usage
const audioUrl = getAudioUrl('rome', 'Colosseum', 'zh-tw');
// Result: /pois/rome/colosseum/audio/audio_zh-tw.mp3
```

**Advantages:**
- ✅ No backend changes needed
- ✅ Works immediately

**Disadvantages:**
- ❌ Client must know naming convention
- ❌ Breaks if server changes URL structure
- ❌ Can't easily detect if audio exists

---

## Recommended Approach

### For Immediate Use (No Backend Changes)

**Client constructs URLs manually:**

1. Get tour data from API
2. Extract POI name from tour
3. Convert POI name to kebab-case (poi_id)
4. Construct audio URL: `/pois/{city}/{poi_id}/audio/audio_{language}.mp3`
5. Play using native media player

**Example:**
```dart
class TourAudioService {
  final String baseUrl = 'http://your-api.com';

  String getPOIId(String poiName) {
    return poiName
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'^-|-$'), '');
  }

  String getAudioUrl(String city, String poiName, String language) {
    final poiId = getPOIId(poiName);
    return '$baseUrl/pois/$city/$poiId/audio/audio_$language.mp3';
  }

  Future<void> playTourPOI({
    required String city,
    required String poiName,
    required String language,
  }) async {
    final audioUrl = getAudioUrl(city, poiName, language);
    await _player.play(UrlSource(audioUrl));
  }
}
```

### For Better Integration (Requires Backend Changes)

**Add audio URLs to tour API responses:**

1. Modify tour API to include `poi_id` and `audio_url` fields
2. Client uses provided URLs directly
3. No URL construction needed on client side

---

## Error Handling

### Check Audio Availability

**Before playing, verify audio exists:**

```dart
Future<bool> audioExists(String url) async {
  try {
    final response = await http.head(Uri.parse(url));
    return response.statusCode == 200;
  } catch (e) {
    return false;
  }
}

// Usage
final audioUrl = getAudioUrl('rome', 'Colosseum', 'zh-tw');
if (await audioExists(audioUrl)) {
  await playAudio(audioUrl);
} else {
  showError('Audio not available');
}
```

### Graceful Degradation

```dart
Future<void> playPOIAudio({
  required String city,
  required String poiName,
  required String preferredLanguage,
}) async {
  // Try preferred language first
  String audioUrl = getAudioUrl(city, poiName, preferredLanguage);

  if (await audioExists(audioUrl)) {
    await _player.play(UrlSource(audioUrl));
    return;
  }

  // Fallback to English
  audioUrl = getAudioUrl(city, poiName, 'en');

  if (await audioExists(audioUrl)) {
    await _player.play(UrlSource(audioUrl));
    showWarning('Audio not available in $preferredLanguage, playing English');
    return;
  }

  // No audio available
  showError('Audio not available for this POI');
}
```

---

## Performance Optimization

### Preload Audio

```dart
// Preload next POI audio in background
Future<void> preloadNextAudio(String url) async {
  await _player.setSourceUrl(url);
  // Audio is now cached and ready to play
}

// When user is viewing POI #1, preload POI #2
preloadNextAudio(getAudioUrl('rome', 'Roman Forum', 'zh-tw'));
```

### Progressive Loading Indicator

```dart
_player.onDuration.listen((duration) {
  setState(() {
    _totalDuration = duration;
  });
});

_player.onPositionChanged.listen((position) {
  setState(() {
    _currentPosition = position;
    _bufferedPercentage = (_currentPosition.inMilliseconds / _totalDuration.inMilliseconds) * 100;
  });
});
```

---

## Security Considerations

### CORS
✅ Already configured - allows requests from client apps

### Authentication
❌ Currently NOT required for audio files
✅ Audio files are publicly accessible

**If you need authentication:**
Add auth header to audio requests:

```dart
// Not currently needed, but if you add auth later:
final headers = {
  'Authorization': 'Bearer $accessToken',
};

await _player.play(
  UrlSource(audioUrl),
  headers: headers,
);
```

---

## Summary

### Current Status

| Feature | Status | Notes |
|---------|--------|-------|
| Audio API endpoint | ✅ Working | `/pois/{city}/{poi_id}/audio/{filename}` |
| Public access | ✅ Enabled | No auth required |
| CORS support | ✅ Enabled | Web apps can access |
| Range requests | ✅ Supported | Seeking works |
| Tour integration | ❌ Manual | Client must construct URLs |

### Recommended Client Implementation

**Immediate (No backend changes):**
1. Use direct URL playback with manual URL construction
2. Implement error handling for missing audio
3. Add caching for offline support (optional)

**Future Enhancement:**
1. Add `poi_id` and `audio_url` to tour API responses
2. Client uses provided URLs directly
3. Better audio availability detection

---

**Next Steps:** Choose client implementation approach and test with your mobile/web app.
