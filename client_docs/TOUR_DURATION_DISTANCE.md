# Tour Duration & Walking Distance API

## Overview

The tour detail API now includes duration and walking distance data at both the tour level and per-day level. This allows Flutter clients to display total tour statistics and breakdown by day.

**Endpoint**: `GET /tours/{tour_id}?language=en`

---

## What's New

### Tour-Level Totals (NEW)

```json
{
  "total_duration_hours": 17.2,
  "total_walking_km": 9.46
}
```

These are calculated by summing all days in the tour.

### Per-Day Data (Already Existed)

```json
{
  "itinerary": [
    {
      "day": 1,
      "total_hours": 8.1,
      "total_walking_km": 1.15,
      "pois": [...]
    },
    {
      "day": 2,
      "total_hours": 9.1,
      "total_walking_km": 8.31,
      "pois": [...]
    }
  ]
}
```

---

## API Response Structure

```json
{
  "metadata": {
    "tour_id": "rome-tour-20260304-095656-185fb3",
    "city": "Rome",
    "title_display": "Ancient Rome History · 2 Days"
  },
  "itinerary": [
    {
      "day": 1,
      "pois": [
        {
          "poi": "Colosseum",
          "poi_id": "colosseum",
          "estimated_hours": 2.0,
          "coordinates": {
            "latitude": 41.8902102,
            "longitude": 12.4922309
          }
        }
      ],
      "total_hours": 8.1,
      "total_walking_km": 1.15,
      "start_time": "09:00"
    },
    {
      "day": 2,
      "pois": [...],
      "total_hours": 9.1,
      "total_walking_km": 8.31,
      "start_time": "09:00"
    }
  ],
  "total_duration_hours": 17.2,
  "total_walking_km": 9.46,
  "optimization_scores": {...},
  "images": {...}
}
```

---

## Flutter Data Models

### Tour Detail Model

```dart
class TourDetail {
  final TourMetadata metadata;
  final List<TourDay> itinerary;
  final double totalDurationHours;  // NEW
  final double totalWalkingKm;      // NEW
  final Map<String, dynamic> inputParameters;
  final OptimizationScores optimizationScores;
  final Map<String, dynamic>? images;

  TourDetail({
    required this.metadata,
    required this.itinerary,
    required this.totalDurationHours,
    required this.totalWalkingKm,
    required this.inputParameters,
    required this.optimizationScores,
    this.images,
  });

  factory TourDetail.fromJson(Map<String, dynamic> json) {
    return TourDetail(
      metadata: TourMetadata.fromJson(json['metadata']),
      itinerary: (json['itinerary'] as List)
          .map((day) => TourDay.fromJson(day))
          .toList(),
      totalDurationHours: (json['total_duration_hours'] as num).toDouble(),
      totalWalkingKm: (json['total_walking_km'] as num).toDouble(),
      inputParameters: json['input_parameters'],
      optimizationScores: OptimizationScores.fromJson(json['optimization_scores']),
      images: json['images'],
    );
  }
}
```

### Tour Day Model

```dart
class TourDay {
  final int day;
  final List<TourPOI> pois;
  final double totalHours;        // Already existed
  final double totalWalkingKm;    // Already existed
  final String startTime;

  TourDay({
    required this.day,
    required this.pois,
    required this.totalHours,
    required this.totalWalkingKm,
    required this.startTime,
  });

  factory TourDay.fromJson(Map<String, dynamic> json) {
    return TourDay(
      day: json['day'],
      pois: (json['pois'] as List)
          .map((poi) => TourPOI.fromJson(poi))
          .toList(),
      totalHours: (json['total_hours'] as num).toDouble(),
      totalWalkingKm: (json['total_walking_km'] as num).toDouble(),
      startTime: json['start_time'],
    );
  }
}
```

---

## Usage Examples

### Display Tour Overview

```dart
Widget buildTourOverview(TourDetail tour) {
  return Card(
    child: Padding(
      padding: EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            tour.metadata.titleDisplay ?? '${tour.metadata.city} Tour',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          SizedBox(height: 16),
          Row(
            children: [
              Icon(Icons.schedule, size: 20),
              SizedBox(width: 8),
              Text('${formatDuration(tour.totalDurationHours)}'),
            ],
          ),
          SizedBox(height: 8),
          Row(
            children: [
              Icon(Icons.directions_walk, size: 20),
              SizedBox(width: 8),
              Text('${tour.totalWalkingKm.toStringAsFixed(2)} km walking'),
            ],
          ),
        ],
      ),
    ),
  );
}

String formatDuration(double hours) {
  int totalMinutes = (hours * 60).round();
  int h = totalMinutes ~/ 60;
  int m = totalMinutes % 60;
  if (m == 0) {
    return '$h hours';
  }
  return '$h hours $m min';
}
```

### Display Per-Day Breakdown

```dart
Widget buildDayBreakdown(TourDay day) {
  return Card(
    child: Padding(
      padding: EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Day ${day.day}',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          SizedBox(height: 8),
          Row(
            children: [
              Icon(Icons.schedule, size: 16),
              SizedBox(width: 4),
              Text('${formatDuration(day.totalHours)}'),
              SizedBox(width: 16),
              Icon(Icons.directions_walk, size: 16),
              SizedBox(width: 4),
              Text('${day.totalWalkingKm.toStringAsFixed(2)} km'),
            ],
          ),
          SizedBox(height: 8),
          Text('${day.pois.length} POIs'),
        ],
      ),
    ),
  );
}
```

### Display Statistics Card

```dart
Widget buildTourStatistics(TourDetail tour) {
  return Card(
    child: Padding(
      padding: EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Tour Statistics',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          SizedBox(height: 16),
          _buildStatRow(
            icon: Icons.calendar_today,
            label: 'Duration',
            value: '${tour.itinerary.length} days',
          ),
          SizedBox(height: 8),
          _buildStatRow(
            icon: Icons.schedule,
            label: 'Total Time',
            value: formatDuration(tour.totalDurationHours),
          ),
          SizedBox(height: 8),
          _buildStatRow(
            icon: Icons.directions_walk,
            label: 'Walking Distance',
            value: '${tour.totalWalkingKm.toStringAsFixed(2)} km',
          ),
          SizedBox(height: 8),
          _buildStatRow(
            icon: Icons.place,
            label: 'Total POIs',
            value: '${_countTotalPOIs(tour)} places',
          ),
        ],
      ),
    ),
  );
}

Widget _buildStatRow({
  required IconData icon,
  required String label,
  required String value,
}) {
  return Row(
    children: [
      Icon(icon, size: 20, color: Colors.grey[600]),
      SizedBox(width: 8),
      Text(
        '$label: ',
        style: TextStyle(color: Colors.grey[600]),
      ),
      Text(
        value,
        style: TextStyle(fontWeight: FontWeight.bold),
      ),
    ],
  );
}

int _countTotalPOIs(TourDetail tour) {
  return tour.itinerary.fold(0, (sum, day) => sum + day.pois.length);
}
```

---

## API Request Example

### Dart HTTP Request

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

Future<TourDetail> fetchTourDetail(String tourId, String language) async {
  final response = await http.get(
    Uri.parse('https://your-api.com/tours/$tourId?language=$language'),
    headers: {
      'Authorization': 'Bearer $yourToken',
      'Accept': 'application/json',
    },
  );

  if (response.statusCode == 200) {
    final json = jsonDecode(response.body);
    return TourDetail.fromJson(json);
  } else {
    throw Exception('Failed to load tour detail');
  }
}

// Usage
void loadTour() async {
  try {
    final tour = await fetchTourDetail('rome-tour-20260304-095656-185fb3', 'en');
    print('Total duration: ${tour.totalDurationHours} hours');
    print('Total walking: ${tour.totalWalkingKm} km');

    for (var day in tour.itinerary) {
      print('Day ${day.day}: ${day.totalHours}h, ${day.totalWalkingKm}km');
    }
  } catch (e) {
    print('Error: $e');
  }
}
```

---

## Data Interpretation

### Duration (`total_hours` / `total_duration_hours`)

- Includes **visit time at POIs** + **walking time between POIs**
- Represents active touring time (not including meals, rest breaks, or evening activities)
- Example: 8.1 hours = roughly 9am to 5pm with breaks

### Walking Distance (`total_walking_km` / `totalWalkingKm`)

- **Point-to-point distance** between POIs
- Does NOT include walking within POI sites (e.g., walking around inside the Colosseum)
- Based on Google Maps walking directions
- Example: 1.15 km = ~15 minutes walking

---

## Important Notes

1. **Per-Day Always Exists**: The `total_hours` and `total_walking_km` fields have always existed in each day's data

2. **Tour-Level is NEW**: The top-level `total_duration_hours` and `total_walking_km` are newly added for convenience

3. **Calculation**: Tour-level totals are simply the sum of all days:
   ```
   total_duration_hours = sum(day.total_hours for each day)
   total_walking_km = sum(day.total_walking_km for each day)
   ```

4. **Backward Compatibility**: Old API clients will still work - they just won't see the tour-level totals

5. **Rounding**: Hours may have floating point precision issues (e.g., 13.100000000000001). Round for display:
   ```dart
   double rounded = (hours * 10).round() / 10; // 1 decimal place
   ```

---

## Testing

Test with different tours to verify data:

```bash
# 2-day Rome tour
curl "http://localhost:8000/tours/rome-tour-20260304-095656-185fb3?language=en"
# Expected: ~17.2 hours, ~9.46 km

# Another tour
curl "http://localhost:8000/tours/rome-tour-20260313-020105-d1b246?language=en"
# Expected: ~13.1 hours, ~4.25 km
```

---

## UI Design Recommendations

### Tour List View (Summary Cards)

Show tour-level totals:
```
┌─────────────────────────────┐
│ Ancient Rome · 2 Days       │
│ 🕐 17 hours  🚶 9.5 km     │
│ 📍 12 POIs                  │
└─────────────────────────────┘
```

### Tour Detail View (Header)

Show tour-level and per-day:
```
┌─────────────────────────────┐
│ Tour Overview               │
│ Duration: 17.2 hours        │
│ Walking: 9.46 km            │
│                             │
│ Day 1: 8.1h, 1.15km         │
│ Day 2: 9.1h, 8.31km         │
└─────────────────────────────┘
```

### Day Detail View

Show day-specific data:
```
┌─────────────────────────────┐
│ Day 1 - Ancient Rome        │
│ Start: 9:00 AM              │
│ Duration: 8.1 hours         │
│ Walking: 1.15 km            │
│ POIs: 5 places              │
└─────────────────────────────┘
```

---

## Migration Guide

If you already have tour display code:

### Before (Manual Calculation)

```dart
// Had to calculate totals manually
double totalHours = 0;
double totalKm = 0;
for (var day in tour.itinerary) {
  totalHours += day.totalHours;
  totalKm += day.totalWalkingKm;
}
```

### After (Use API Data)

```dart
// Use pre-calculated totals from API
double totalHours = tour.totalDurationHours;
double totalKm = tour.totalWalkingKm;
```

**Benefit**: Less code, consistent calculation, same across all clients.

---

## Questions?

If you have questions or find issues with the tour duration/distance data:
1. Check this documentation
2. Test with the API directly using curl
3. Verify your Flutter models match the API response structure
4. Report issues to backend team

---

**Last Updated**: 2026-03-29
**API Version**: v1
**Status**: ✅ Live in production
