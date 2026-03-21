# Client Audio API - Simple Guide

## Overview

**Super simple API for client apps to get audio URLs for tours.**

We handle all the complexity on the backend - client just calls one endpoint and gets all the audio URLs ready to use!

---

## The Endpoint

```
GET /tours/{tour_id}/audio?language={language}
```

**That's it!** One simple endpoint gives you everything you need.

---

## Example Usage

### Request

```bash
GET http://your-api.com/tours/rome-tour-20260320-175540-6b0704/audio?language=zh-tw
```

### Response

```json
{
  "tour_id": "rome-tour-20260320-175540-6b0704",
  "language": "zh-tw",
  "city": "rome",
  "total_pois": 4,
  "pois": [
    {
      "poi": "Basilica di San Clemente",
      "poi_id": "basilica-di-san-clemente",
      "day": 1,
      "audio_url": "/pois/rome/basilica-di-san-clemente/audio/audio_zh-tw.mp3",
      "audio_available": true
    },
    {
      "poi": "Colosseum",
      "poi_id": "colosseum",
      "day": 1,
      "audio_url": "/pois/rome/colosseum/audio/audio_zh-tw.mp3",
      "audio_available": true
    },
    {
      "poi": "Palatine Hill",
      "poi_id": "palatine-hill",
      "day": 1,
      "audio_url": "/pois/rome/palatine-hill/audio/audio_zh-tw.mp3",
      "audio_available": true
    },
    {
      "poi": "Roman Forum",
      "poi_id": "roman-forum",
      "day": 1,
      "audio_url": "/pois/rome/roman-forum/audio/audio_zh-tw.mp3",
      "audio_available": true
    }
  ]
}
```

---

## Client Implementation

### Flutter/Dart

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:audioplayers/audioplayers.dart';

class TourAudioService {
  final String baseUrl = 'http://your-api.com';
  final AudioPlayer player = AudioPlayer();

  // Step 1: Get audio URLs for tour
  Future<List<POIAudio>> getTourAudioUrls(String tourId, String language) async {
    final url = '$baseUrl/tours/$tourId/audio?language=$language';
    final response = await http.get(Uri.parse(url));

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return (data['pois'] as List)
          .map((poi) => POIAudio.fromJson(poi))
          .toList();
    }
    throw Exception('Failed to load audio URLs');
  }

  // Step 2: Play audio
  Future<void> playAudio(String audioUrl) async {
    final fullUrl = '$baseUrl$audioUrl';
    await player.play(UrlSource(fullUrl));
  }

  // Complete example
  Future<void> playTourPOI(String tourId, int day, int poiIndex) async {
    // Get all audio URLs
    final pois = await getTourAudioUrls(tourId, 'zh-tw');

    // Filter POIs by day
    final dayPois = pois.where((p) => p.day == day).toList();

    // Play selected POI
    if (poiIndex < dayPois.length && dayPois[poiIndex].audioAvailable) {
      await playAudio(dayPois[poiIndex].audioUrl);
    }
  }
}

class POIAudio {
  final String poi;
  final String poiId;
  final int day;
  final String? audioUrl;
  final bool audioAvailable;

  POIAudio({
    required this.poi,
    required this.poiId,
    required this.day,
    this.audioUrl,
    required this.audioAvailable,
  });

  factory POIAudio.fromJson(Map<String, dynamic> json) {
    return POIAudio(
      poi: json['poi'],
      poiId: json['poi_id'],
      day: json['day'],
      audioUrl: json['audio_url'],
      audioAvailable: json['audio_available'],
    );
  }
}
```

### React Native / JavaScript

```javascript
import Sound from 'react-native-sound';

const BASE_URL = 'http://your-api.com';

class TourAudioService {
  constructor() {
    this.currentSound = null;
  }

  // Step 1: Get audio URLs
  async getTourAudioUrls(tourId, language = 'zh-tw') {
    const url = `${BASE_URL}/tours/${tourId}/audio?language=${language}`;
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error('Failed to load audio URLs');
    }

    const data = await response.json();
    return data.pois;
  }

  // Step 2: Play audio
  playAudio(audioUrl) {
    // Stop current sound if playing
    if (this.currentSound) {
      this.currentSound.stop();
      this.currentSound.release();
    }

    // Full URL
    const fullUrl = BASE_URL + audioUrl;

    // Play new sound
    this.currentSound = new Sound(fullUrl, '', (error) => {
      if (error) {
        console.error('Failed to load audio:', error);
        return;
      }
      this.currentSound.play();
    });
  }

  pause() {
    if (this.currentSound) {
      this.currentSound.pause();
    }
  }

  stop() {
    if (this.currentSound) {
      this.currentSound.stop();
      this.currentSound.release();
      this.currentSound = null;
    }
  }
}

// Usage Example
const audioService = new TourAudioService();

async function playTourDay(tourId, day) {
  // Get audio URLs
  const pois = await audioService.getTourAudioUrls(tourId, 'zh-tw');

  // Find POIs for this day
  const dayPois = pois.filter(p => p.day === day);

  // Play first POI
  if (dayPois.length > 0 && dayPois[0].audio_available) {
    audioService.playAudio(dayPois[0].audio_url);
  }
}

export default audioService;
```

### Web / React

```javascript
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BASE_URL = 'http://your-api.com';

function TourAudioPlayer({ tourId, language = 'zh-tw' }) {
  const [pois, setPois] = useState([]);
  const [currentPOI, setCurrentPOI] = useState(null);
  const [audio] = useState(new Audio());

  useEffect(() => {
    // Load audio URLs when component mounts
    loadAudioUrls();
  }, [tourId, language]);

  const loadAudioUrls = async () => {
    try {
      const response = await axios.get(
        `${BASE_URL}/tours/${tourId}/audio?language=${language}`
      );
      setPois(response.data.pois);
    } catch (error) {
      console.error('Failed to load audio URLs:', error);
    }
  };

  const playPOI = (poi) => {
    if (!poi.audio_available) return;

    // Set audio source
    audio.src = BASE_URL + poi.audio_url;
    audio.play();
    setCurrentPOI(poi);
  };

  const pause = () => {
    audio.pause();
  };

  const stop = () => {
    audio.pause();
    audio.currentTime = 0;
    setCurrentPOI(null);
  };

  return (
    <div className="tour-audio-player">
      <h2>Tour Audio</h2>

      {/* POI List */}
      {pois.map((poi, index) => (
        <div key={index} className="poi-item">
          <h3>
            Day {poi.day}: {poi.poi}
          </h3>

          {poi.audio_available ? (
            <button onClick={() => playPOI(poi)}>
              {currentPOI?.poi === poi.poi ? '⏸ Pause' : '▶ Play'}
            </button>
          ) : (
            <span>No audio available</span>
          )}
        </div>
      ))}

      {/* Player Controls */}
      {currentPOI && (
        <div className="player-controls">
          <p>Now playing: {currentPOI.poi}</p>
          <button onClick={pause}>Pause</button>
          <button onClick={stop}>Stop</button>
        </div>
      )}
    </div>
  );
}

export default TourAudioPlayer;
```

---

## Two Ways to Use

### Option 1: Dedicated Audio Endpoint (Recommended) ✅

**Use this endpoint:**
```
GET /tours/{tour_id}/audio?language=zh-tw
```

**Benefits:**
- ✅ One simple call
- ✅ Gets all audio URLs at once
- ✅ No URL construction needed
- ✅ Server handles all complexity

**Perfect for:**
- Loading tour audio when tour starts
- Preloading all audio URLs
- Simple implementation

---

### Option 2: Full Tour Endpoint (More Data)

**Use this endpoint:**
```
GET /tours/{tour_id}?language=zh-tw
```

**Returns:**
- Tour itinerary
- POI details
- **PLUS** audio URLs in each POI object

**Benefits:**
- ✅ Get tour data AND audio URLs in one call
- ✅ No extra request needed

**Perfect for:**
- When you need full tour details anyway
- Combined tour display + audio playback

---

## Error Handling

```dart
Future<void> loadTourAudio(String tourId) async {
  try {
    final pois = await getTourAudioUrls(tourId, 'zh-tw');

    // Check if any audio available
    final available = pois.where((p) => p.audioAvailable).length;
    print('Audio available for $available/${pois.length} POIs');

  } catch (e) {
    if (e.toString().contains('404')) {
      print('Tour not found');
    } else if (e.toString().contains('500')) {
      print('Server error - try again later');
    } else {
      print('Network error: $e');
    }
  }
}
```

---

## Performance Tips

### 1. Preload Audio URLs
```dart
// Load audio URLs when tour page opens
@override
void initState() {
  super.initState();
  loadTourAudio(widget.tourId);
}
```

### 2. Cache the Response
```dart
// Store audio URLs locally
class AudioCache {
  static final Map<String, List<POIAudio>> _cache = {};

  static Future<List<POIAudio>> get(String tourId) async {
    if (_cache.containsKey(tourId)) {
      return _cache[tourId]!;
    }

    final pois = await getTourAudioUrls(tourId, 'zh-tw');
    _cache[tourId] = pois;
    return pois;
  }
}
```

### 3. Preload Next POI
```dart
// When playing POI #1, preload POI #2
void preloadNext(int currentIndex, List<POIAudio> pois) {
  if (currentIndex + 1 < pois.length) {
    final nextPOI = pois[currentIndex + 1];
    if (nextPOI.audioAvailable) {
      // Preload in background
      player.setSourceUrl(BASE_URL + nextPOI.audioUrl!);
    }
  }
}
```

---

## Summary

### For Client Developers:

**It's super simple!**

1. **Call one endpoint**: `GET /tours/{tour_id}/audio?language=zh-tw`
2. **Get all audio URLs**: Response includes `audio_url` for each POI
3. **Play directly**: Use the URLs with your native audio player

**We handle:**
- ✅ Converting POI names to URLs
- ✅ Checking audio availability
- ✅ Providing the correct format
- ✅ Language-specific audio

**You just:**
- ✅ Call the API
- ✅ Get the URLs
- ✅ Play the audio

### No Complexity on Client Side! 🎉

---

## Quick Start

```bash
# 1. Get audio URLs
curl "http://your-api.com/tours/rome-tour-20260320-175540-6b0704/audio?language=zh-tw"

# 2. Pick a POI from response

# 3. Play it
curl "http://your-api.com/pois/rome/colosseum/audio/audio_zh-tw.mp3" --output colosseum.mp3
afplay colosseum.mp3
```

---

**Ready to use NOW!** 🚀
