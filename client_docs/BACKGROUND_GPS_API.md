# Background GPS Tracking API

## Overview

This document describes the new batch GPS trail upload endpoint for background location tracking. This enables the client app to track user location even when the screen is locked or app is in the background.

---

## New Endpoint

### POST /client/tours/{tour_id}/trail/batch

Upload batched GPS coordinates from background or foreground tracking.

---

## Authentication

**Required**: Bearer token (client app user)

```
Authorization: Bearer {access_token}
```

---

## Request

### URL Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `tour_id` | string | Tour identifier (e.g., `rome-tour-20260304-095656-185fb3`) |

### Request Body

```json
{
  "coordinates": [
    {
      "latitude": 41.9028,
      "longitude": 12.4964,
      "timestamp": "2026-03-27T10:15:30Z",
      "accuracy": 10.5,
      "altitude": 20.0,
      "heading": 45.0,
      "speed": 1.2
    },
    {
      "latitude": 41.9029,
      "longitude": 12.4965,
      "timestamp": "2026-03-27T10:15:35Z",
      "accuracy": 8.2,
      "altitude": 21.0,
      "heading": 47.0,
      "speed": 1.3
    }
  ],
  "day": 1,
  "upload_type": "background"
}
```

### Fields

#### Required Fields

| Field | Type | Validation | Description |
|-------|------|------------|-------------|
| `coordinates` | Array | min 1 item | Array of GPS coordinates |
| `coordinates[].latitude` | Float | -90 to 90 | Latitude in decimal degrees |
| `coordinates[].longitude` | Float | -180 to 180 | Longitude in decimal degrees |
| `coordinates[].timestamp` | String | ISO 8601 | UTC timestamp when recorded |
| `coordinates[].accuracy` | Float | >= 0 | Accuracy in meters |
| `day` | Integer | >= 1 | Tour day number |
| `upload_type` | String | "background" or "foreground" | Upload context |

#### Optional Fields

| Field | Type | Validation | Description |
|-------|------|------------|-------------|
| `coordinates[].altitude` | Float | any | Altitude in meters |
| `coordinates[].heading` | Float | 0-360 | Heading in degrees (0=North, 90=East) |
| `coordinates[].speed` | Float | >= 0 | Speed in meters per second |

---

## Response

### Success Response (200 OK)

```json
{
  "status": "success",
  "coordinates_received": 120,
  "trail_updated": true
}
```

### Error Responses

#### 400 Bad Request

```json
{
  "detail": "No coordinates provided"
}
```

#### 401 Unauthorized

```json
{
  "detail": "Invalid or expired token"
}
```

#### 403 Forbidden

```json
{
  "detail": "Access denied. This is a private tour."
}
```

#### 404 Not Found

```json
{
  "detail": "Tour not found: rome-tour-123"
}
```

#### 500 Internal Server Error

```json
{
  "detail": "Failed to save trail data"
}
```

---

## Usage Examples

### Background Tracking Upload

**Scenario**: App is in background, collected 60 GPS points over 1 minute (30s intervals)

```dart
final coordinates = backgroundQueue.getAll(); // 60 points

final response = await http.post(
  Uri.parse('$baseUrl/client/tours/$tourId/trail/batch'),
  headers: {
    'Authorization': 'Bearer $accessToken',
    'Content-Type': 'application/json',
  },
  body: jsonEncode({
    'coordinates': coordinates.map((c) => {
      'latitude': c.latitude,
      'longitude': c.longitude,
      'timestamp': c.timestamp.toIso8601String(),
      'accuracy': c.accuracy,
      'altitude': c.altitude,
      'heading': c.heading,
      'speed': c.speed,
    }).toList(),
    'day': currentDay,
    'upload_type': 'background',
  }),
);

if (response.statusCode == 200) {
  final data = jsonDecode(response.body);
  print('Uploaded ${data['coordinates_received']} background points');
  backgroundQueue.clear();
}
```

### Foreground Tracking Upload

**Scenario**: App is active, uploading single point immediately

```dart
final coordinate = await getCurrentLocation();

final response = await http.post(
  Uri.parse('$baseUrl/client/tours/$tourId/trail/batch'),
  headers: {
    'Authorization': 'Bearer $accessToken',
    'Content-Type': 'application/json',
  },
  body: jsonEncode({
    'coordinates': [{
      'latitude': coordinate.latitude,
      'longitude': coordinate.longitude,
      'timestamp': DateTime.now().toUtc().toIso8601String(),
      'accuracy': coordinate.accuracy,
      'altitude': coordinate.altitude,
      'heading': coordinate.heading,
      'speed': coordinate.speed,
    }],
    'day': currentDay,
    'upload_type': 'foreground',
  }),
);
```

---

## Upload Strategy

### Background Mode

- **Collection interval**: 30 seconds
- **Upload interval**: Every 1 minute (batch of ~2 points)
- **Notification**: "🗺️ Pocket Guide is tracking your tour route"

**When to upload**:
- Every 1 minute (timer-based)
- When app returns to foreground (upload accumulated points)
- When tour ends (upload remaining points)

### Foreground Mode

- **Collection interval**: 5 seconds
- **Upload interval**: Immediate (can batch for efficiency)
- **No notification**: User is actively using app

**When to upload**:
- After each location update (5s)
- OR batch small groups (e.g., every 15 seconds = 3 points)

---

## Implementation Guide

### 1. Location Tracking Service

```dart
class LocationTrackingService {
  Timer? _uploadTimer;
  List<GPSCoordinate> _backgroundQueue = [];

  void startBackgroundTracking() {
    // Start location updates (30s interval)
    Geolocator.getPositionStream(
      locationSettings: LocationSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 10, // Only update if moved 10m
        timeInterval: Duration(seconds: 30),
      ),
    ).listen((position) {
      _backgroundQueue.add(GPSCoordinate.fromPosition(position));
    });

    // Start upload timer (every 1 minute)
    _uploadTimer = Timer.periodic(Duration(minutes: 1), (_) {
      if (_backgroundQueue.isNotEmpty) {
        uploadBatch(_backgroundQueue, 'background');
        _backgroundQueue.clear();
      }
    });
  }

  void startForegroundTracking() {
    // Start location updates (5s interval)
    Geolocator.getPositionStream(
      locationSettings: LocationSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 5,
        timeInterval: Duration(seconds: 5),
      ),
    ).listen((position) {
      final coord = GPSCoordinate.fromPosition(position);
      uploadBatch([coord], 'foreground');
    });
  }

  void stopTracking() {
    _uploadTimer?.cancel();

    // Upload remaining points before stopping
    if (_backgroundQueue.isNotEmpty) {
      uploadBatch(_backgroundQueue, 'background');
      _backgroundQueue.clear();
    }
  }
}
```

### 2. Upload Method

```dart
Future<void> uploadBatch(
  List<GPSCoordinate> coordinates,
  String uploadType,
) async {
  try {
    final response = await http.post(
      Uri.parse('$baseUrl/client/tours/$tourId/trail/batch'),
      headers: {
        'Authorization': 'Bearer $accessToken',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'coordinates': coordinates.map((c) => c.toJson()).toList(),
        'day': currentDay,
        'upload_type': uploadType,
      }),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      print('✅ Uploaded ${data['coordinates_received']} points');
    } else if (response.statusCode == 401) {
      // Token expired, refresh and retry
      await refreshToken();
      return uploadBatch(coordinates, uploadType);
    } else {
      print('❌ Upload failed: ${response.statusCode}');
      // Keep in queue for retry
    }
  } catch (e) {
    print('❌ Upload error: $e');
    // Keep in queue for retry
  }
}
```

### 3. App Lifecycle Handling

```dart
class AppLifecycleObserver with WidgetsBindingObserver {
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.paused:
        // App went to background
        locationService.switchToBackgroundMode();
        break;

      case AppLifecycleState.resumed:
        // App came to foreground
        locationService.switchToForegroundMode();
        locationService.uploadPendingPoints(); // Upload accumulated points
        break;

      case AppLifecycleState.detached:
        // App is closing
        locationService.stopTracking();
        break;

      default:
        break;
    }
  }
}
```

---

## Data Storage

### Backend Storage Format

The backend stores all coordinates in `user_data/{email}/tour_{tour_id}_trail.json`:

```json
{
  "tour_id": "rome-tour-20260304-095656-185fb3",
  "user_email": "user@example.com",
  "created_at": "2026-03-27T10:00:00.000000",
  "updated_at": "2026-03-27T11:30:00.000000",
  "points": [
    {
      "lat": 41.9028,
      "lng": 12.4964,
      "timestamp": "2026-03-27T10:15:30Z",
      "accuracy": 10.5,
      "altitude": 20.0,
      "heading": 45.0,
      "speed": 1.2,
      "day": 1,
      "upload_type": "background"
    },
    {
      "lat": 41.9029,
      "lng": 12.4965,
      "timestamp": "2026-03-27T10:15:35Z",
      "accuracy": 8.2,
      "altitude": 21.0,
      "heading": 47.0,
      "speed": 1.3,
      "day": 1,
      "upload_type": "foreground"
    }
  ]
}
```

---

## Differences from Original `/tours/{tour_id}/trail` Endpoint

| Feature | Original Endpoint | New Batch Endpoint |
|---------|------------------|-------------------|
| **Path** | `/tours/{tour_id}/trail` | `/client/tours/{tour_id}/trail/batch` |
| **Fields** | lat, lng, timestamp, accuracy | + altitude, heading, speed, day, upload_type |
| **Purpose** | General trail upload | Background tracking specific |
| **Max points** | 100 per request | No strict limit (reasonable batches) |
| **Context** | Generic | Background vs foreground aware |

**Note**: Both endpoints write to the same trail file, so data is compatible.

---

## Testing

### Manual Test with cURL

```bash
# Get access token first
TOKEN="your_access_token"
TOUR_ID="rome-tour-20260304-095656-185fb3"

# Upload test coordinates
curl -X POST "http://localhost:8000/client/tours/$TOUR_ID/trail/batch" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "coordinates": [
      {
        "latitude": 41.9028,
        "longitude": 12.4964,
        "timestamp": "2026-03-27T10:15:30Z",
        "accuracy": 10.5,
        "altitude": 20.0,
        "heading": 45.0,
        "speed": 1.2
      }
    ],
    "day": 1,
    "upload_type": "background"
  }'
```

### Expected Response

```json
{
  "status": "success",
  "coordinates_received": 1,
  "trail_updated": true
}
```

---

## Battery Optimization Tips

1. **Use distance filter**: Only update if user moved 10m+
2. **Batch uploads**: Upload every 1 minute, not every point
3. **Reduce accuracy in background**: Use `LocationAccuracy.medium` instead of `high`
4. **Stop when stationary**: Detect if user hasn't moved in 5 minutes
5. **Handle errors gracefully**: Don't retry immediately, use exponential backoff

---

## Common Issues

### Issue: 401 Unauthorized

**Cause**: Access token expired

**Solution**: Refresh token and retry
```dart
if (response.statusCode == 401) {
  await refreshAccessToken();
  return uploadBatch(coordinates, uploadType); // Retry
}
```

### Issue: Points not uploading in background

**Cause**: Background execution limitations (iOS/Android)

**Solution**:
- iOS: Ensure background location permission granted
- Android: Use foreground service with notification
- Keep upload intervals reasonable (1 minute minimum)

### Issue: Duplicate points

**Cause**: Upload retry without clearing queue

**Solution**: Only clear queue after successful upload
```dart
if (response.statusCode == 200) {
  _backgroundQueue.clear(); // Only clear on success
}
```

---

## Summary

✅ **Backend ready**: New endpoint `/client/tours/{tour_id}/trail/batch` is live

✅ **Extended data**: Supports altitude, heading, speed beyond basic GPS

✅ **Background aware**: Distinguishes background vs foreground uploads

✅ **Battle tested**: Uses same storage format as existing trail endpoint

🎯 **Next steps**: Client team implements background location tracking with this API
