// Flutter App Configuration for Mobile Testing
// Copy this to your Flutter app and update the baseUrl with your tunnel URL

class ApiConfig {
  // 🔧 UPDATE THIS with your Cloudflare tunnel URL
  // Get it from: ./scripts/start_tunnel.sh
  // Example: https://abc-xyz-123.trycloudflare.com
  static const String baseUrl = 'https://YOUR_TUNNEL_URL_HERE';

  // ⚠️ IMPORTANT:
  // - Don't include trailing slash
  // - Don't include /api or any path suffix
  // - Just the base URL from Cloudflare tunnel

  // For production, switch to your production URL
  // static const String baseUrl = 'https://api.yourproductiondomain.com';

  // Helper getters for common endpoints
  static String get toursUrl => '$baseUrl/tours';
  static String get authUrl => '$baseUrl/auth';

  // Map Mode API endpoints
  static String tourProgressUrl(String tourId) => '$baseUrl/tours/$tourId/progress';
  static String tourTrailUrl(String tourId) => '$baseUrl/tours/$tourId/trail';
}

// Usage Example in your service classes:

// Example 1: Get tour progress
Future<TourProgress> getTourProgress({
  required String tourId,
  String language = 'en',
}) async {
  final url = '${ApiConfig.tourProgressUrl(tourId)}?language=$language';

  final response = await http.get(
    Uri.parse(url),
    headers: {
      'Authorization': 'Bearer $jwtToken',
      'Content-Type': 'application/json',
    },
  );

  if (response.statusCode == 200) {
    return TourProgress.fromJson(jsonDecode(response.body));
  } else {
    throw Exception('Failed to load progress: ${response.body}');
  }
}

// Example 2: Mark POI complete
Future<void> markPOIComplete({
  required String tourId,
  required String poiId,
  required int day,
  required bool completed,
}) async {
  final response = await http.post(
    Uri.parse(ApiConfig.tourProgressUrl(tourId)),
    headers: {
      'Authorization': 'Bearer $jwtToken',
      'Content-Type': 'application/json',
    },
    body: jsonEncode({
      'poi_id': poiId,
      'day': day,
      'completed': completed,
    }),
  );

  if (response.statusCode != 200) {
    throw Exception('Failed to update progress: ${response.body}');
  }
}

// Example 3: Upload GPS trail (batch)
Future<void> uploadTrailPoints({
  required String tourId,
  required List<GPSPoint> points,
}) async {
  // Limit to 100 points per request
  final batch = points.take(100).toList();

  final response = await http.post(
    Uri.parse(ApiConfig.tourTrailUrl(tourId)),
    headers: {
      'Authorization': 'Bearer $jwtToken',
      'Content-Type': 'application/json',
    },
    body: jsonEncode({
      'points': batch.map((p) => {
        'lat': p.latitude,
        'lng': p.longitude,
        'timestamp': p.timestamp.toIso8601String(),
        'accuracy': p.accuracy,
      }).toList(),
    }),
  );

  if (response.statusCode != 200) {
    throw Exception('Failed to upload trail: ${response.body}');
  }
}

// Example 4: Get GPS trail
Future<List<TrailPoint>> getTrail({required String tourId}) async {
  final response = await http.get(
    Uri.parse(ApiConfig.tourTrailUrl(tourId)),
    headers: {
      'Authorization': 'Bearer $jwtToken',
    },
  );

  if (response.statusCode == 200) {
    final data = jsonDecode(response.body);
    return (data['points'] as List)
        .map((p) => TrailPoint.fromJson(p))
        .toList();
  } else {
    throw Exception('Failed to load trail: ${response.body}');
  }
}

// Example 5: Error handling
Future<void> safeApiCall(Future<void> Function() apiCall) async {
  try {
    await apiCall();
  } on SocketException {
    // No internet connection
    throw Exception('No internet connection');
  } on HttpException {
    // Server error
    throw Exception('Server error');
  } on FormatException {
    // Invalid response format
    throw Exception('Invalid response format');
  } catch (e) {
    // Unknown error
    throw Exception('Unexpected error: $e');
  }
}

// Example 6: Trail upload manager (batching)
class TrailUploadManager {
  final List<GPSPoint> _buffer = [];
  DateTime? _lastUpload;
  final String tourId;
  final String jwtToken;

  TrailUploadManager({required this.tourId, required this.jwtToken});

  void addPoint(GPSPoint point) {
    _buffer.add(point);

    // Upload if: 1 minute passed OR 20+ points
    final shouldUpload =
      _lastUpload == null ||
      DateTime.now().difference(_lastUpload!) > Duration(minutes: 1) ||
      _buffer.length >= 20;

    if (shouldUpload) {
      _uploadBatch();
    }
  }

  Future<void> _uploadBatch() async {
    if (_buffer.isEmpty) return;

    try {
      await uploadTrailPoints(
        tourId: tourId,
        points: _buffer.take(100).toList(),
      );
      _buffer.clear();
      _lastUpload = DateTime.now();
    } catch (e) {
      // Keep in buffer for retry
      print('Upload failed, will retry: $e');
    }
  }

  // Call this when tour ends or app closes
  Future<void> flush() async {
    await _uploadBatch();
  }
}
