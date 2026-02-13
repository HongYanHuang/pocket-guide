# Google Maps Opening Hours Integration

## Overview

The ILP optimizer now uses **Google Maps Places API opening hours format** for time window constraints. This eliminates the need for custom time window formats and leverages data already collected by the POI metadata agent.

---

## Google Maps Format

### operation_hours.periods

Google Maps provides opening hours in a structured format:

```yaml
operation_hours:
  weekday_text:
    - "Monday: 8:00 AM – 8:00 PM"
    - "Tuesday: 8:00 AM – 8:00 PM"
    - "Wednesday: 8:00 AM – 8:00 PM"
    - "Thursday: 8:00 AM – 8:00 PM"
    - "Friday: 8:00 AM – 8:00 PM"
    - "Saturday: 8:00 AM – 8:00 PM"
    - "Sunday: Closed"
  periods:
    - open:
        day: 1  # Day of week: 0=Sunday, 1=Monday, ..., 6=Saturday
        time: "0800"  # Time in HHMM format (24-hour)
      close:
        day: 1
        time: "2000"  # 8:00 PM
    - open:
        day: 2
        time: "0800"
      close:
        day: 2
        time: "2000"
    # ... continues for each day
```

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `weekday_text` | Array[String] | Human-readable opening hours |
| `periods` | Array[Object] | Machine-readable time periods |
| `periods[].open.day` | Integer | Day of week (0=Sunday, 6=Saturday) |
| `periods[].open.time` | String | Opening time in HHMM format |
| `periods[].close.day` | Integer | Closing day (usually same as open) |
| `periods[].close.time` | String | Closing time in HHMM format |

---

## Implementation

### 1. Reading Opening Hours

The ILP optimizer reads directly from `operation_hours.periods`:

```python
def _add_time_window_constraints(self, model, visit_vars, pois,
                                 duration_days, start_time="09:00",
                                 trip_start_date=None):
    for i, poi in enumerate(pois):
        # Get Google Maps opening hours
        operation_hours = poi.get('metadata', {}).get('operation_hours', {})
        periods = operation_hours.get('periods', [])

        if not periods:
            continue  # No restrictions if no opening hours data

        for day in range(duration_days):
            # Calculate day of week
            trip_date = trip_start_date + timedelta(days=day)
            google_day_of_week = (trip_date.weekday() + 1) % 7  # Convert to Google format

            # Find periods for this day
            day_periods = [p for p in periods if p.get('open', {}).get('day') == google_day_of_week]

            if not day_periods:
                # Closed on this day - cannot visit
                for pos in range(max_pois_per_day):
                    model.Add(visit_vars[i][day][pos] == 0)
                continue

            # Check if estimated arrival time falls within opening hours
            for pos in range(max_pois_per_day):
                estimated_arrival = calculate_arrival_time(pos)
                is_open = check_if_open(estimated_arrival, day_periods)

                if not is_open:
                    model.Add(visit_vars[i][day][pos] == 0)
```

### 2. Day of Week Conversion

**Google Maps Format**: 0=Sunday, 1=Monday, ..., 6=Saturday

**Python datetime.weekday()**: 0=Monday, 1=Tuesday, ..., 6=Sunday

**Conversion**:
```python
python_weekday = trip_date.weekday()  # 0=Monday, 6=Sunday
google_day = (python_weekday + 1) % 7  # 0=Sunday, 6=Saturday
```

### 3. Time Format Conversion

**Google Maps**: HHMM string (e.g., "0800", "1430", "2000")

**Internal**: Minutes since midnight integer (e.g., 480, 870, 1200)

**Conversion**:
```python
def parse_hhmm_to_minutes(time_str: str) -> int:
    """Convert HHMM to minutes since midnight"""
    hhmm = int(time_str)
    hours = hhmm // 100
    minutes = hhmm % 100
    return hours * 60 + minutes

# Example:
parse_hhmm_to_minutes("0800")  # → 480 (8:00 AM)
parse_hhmm_to_minutes("1430")  # → 870 (2:30 PM)
parse_hhmm_to_minutes("2000")  # → 1200 (8:00 PM)
```

---

## Booking Info Extension

While opening hours come from Google Maps, **booking requirements** and **preferred time slots** are custom additions:

```yaml
metadata:
  operation_hours:
    # From Google Maps API (automatic)
    periods: [...]

  booking_info:
    # Custom additions (manual or from other sources)
    required: true
    advance_booking_days: 7
    booking_url: "https://example.com/book"
    notes: "Advance booking highly recommended"

    # Preferred time slots within opening hours
    preferred_time_slots:
      - start: "08:00"
        end: "10:00"
        notes: "Best time to avoid crowds"
      - start: "10:00"
        end: "12:00"
        notes: "Moderate crowds"
```

### How It Works

1. **Opening Hours** (from Google Maps): POI is *allowed* to be visited during these times
2. **Preferred Slots** (custom): If `booking_info.required = true`, POI is *preferred* to be in these narrower windows

**Logic**:
```python
if booking_required and preferred_slots:
    # Must be BOTH open AND in preferred slot
    is_allowed = is_open(arrival_time, periods) and in_preferred_slot(arrival_time, slots)
else:
    # Just need to be open
    is_allowed = is_open(arrival_time, periods)
```

---

## CLI Usage

### Basic (No Date Specified)

```bash
./pocket-guide trip plan --city Rome --days 3 --mode ilp
```

**Behavior**: Uses current date/time to determine day of week for opening hours.

### With Start Date

```bash
./pocket-guide trip plan --city Rome --days 3 \
  --mode ilp \
  --start-date "2026-03-15"
```

**Behavior**:
- Day 1 = Sunday, March 15, 2026
- Day 2 = Monday, March 16, 2026
- Day 3 = Tuesday, March 17, 2026
- Checks Sunday/Monday/Tuesday opening hours for each POI

**Why It Matters**:
- Museums often closed on Sundays or Mondays
- Restaurant hours differ on weekends
- Some attractions have limited hours on specific days

---

## Example: Vatican Museums

### POI Metadata

```yaml
poi:
  name: Vatican Museums
  metadata:
    operation_hours:
      weekday_text:
        - "Monday: 8:00 AM – 8:00 PM"
        - "Tuesday: 8:00 AM – 8:00 PM"
        - "Wednesday: 8:00 AM – 8:00 PM"
        - "Thursday: 8:00 AM – 8:00 PM"
        - "Friday: 8:00 AM – 8:00 PM"
        - "Saturday: 8:00 AM – 8:00 PM"
        - "Sunday: Closed"
      periods:
        - open: {day: 1, time: "0800"}
          close: {day: 1, time: "2000"}
        - open: {day: 2, time: "0800"}
          close: {day: 2, time: "2000"}
        - open: {day: 3, time: "0800"}
          close: {day: 3, time: "2000"}
        - open: {day: 4, time: "0800"}
          close: {day: 4, time: "2000"}
        - open: {day: 5, time: "0800"}
          close: {day: 5, time: "2000"}
        - open: {day: 6, time: "0800"}
          close: {day: 6, time: "2000"}
        # No period for day 0 (Sunday) = Closed

    booking_info:
      required: true
      advance_booking_days: 7
      booking_url: "https://www.museivaticani.va/..."
      preferred_time_slots:
        - start: "08:00"
          end: "10:00"
          notes: "Best time to avoid crowds"
        - start: "10:00"
          end: "12:00"
          notes: "Moderate crowds"
```

### Optimization Behavior

**Trip: 3 days starting Sunday, March 15, 2026**

- **Day 1 (Sunday)**: Vatican Museums cannot be scheduled (no period for day=0)
- **Day 2 (Monday)**: Vatican Museums can be scheduled 8:00 AM - 8:00 PM
  - Preferred: 8:00-12:00 PM (booking required)
  - Optimizer will schedule early in day (position 0 or 1) to hit 8-10 AM slot
- **Day 3 (Tuesday)**: Same as Monday

**Result**: Vatican Museums scheduled on Day 2 or 3, early morning position.

---

## Benefits of Google Maps Integration

### 1. Automatic Data Collection
✅ Opening hours already collected by POI metadata agent
✅ No manual entry of time windows
✅ Always up-to-date with Google's data

### 2. Accurate Day-of-Week Handling
✅ Respects different hours on different days
✅ Handles closed days (Sundays, Mondays)
✅ Supports split shifts (morning + evening hours)

### 3. Standardized Format
✅ Uses industry-standard Google Maps format
✅ Compatible with other travel tools
✅ Well-documented API structure

### 4. Flexibility
✅ Works without booking info (just opening hours)
✅ Optional preferred slots for booking requirements
✅ Soft constraints possible (prefer but don't require)

---

## Migration from Custom Format

### Old Format (DEPRECATED)

```yaml
metadata:
  booking_info:
    required: true
    time_window:
      start: "09:00"
      end: "12:00"
      flexible: false
```

### New Format (CURRENT)

```yaml
metadata:
  operation_hours:
    periods:
      - open: {day: 1, time: "0800"}
        close: {day: 1, time: "2000"}
      # ... for each day

  booking_info:
    required: true
    preferred_time_slots:
      - start: "08:00"
        end: "10:00"
      - start: "10:00"
        end: "12:00"
```

### Migration Steps

1. Remove `booking_info.time_window` (no longer used)
2. Ensure `operation_hours.periods` exists (usually already present)
3. Add `booking_info.preferred_time_slots` if booking required
4. Update any custom scripts that referenced old format

---

## Testing

### Unit Tests

```python
def test_google_maps_format():
    """Test parsing of Google Maps periods format"""
    poi = {
        'metadata': {
            'operation_hours': {
                'periods': [
                    {'open': {'day': 1, 'time': '0800'}, 'close': {'day': 1, 'time': '1800'}},
                ]
            }
        }
    }

    optimizer = ILPOptimizer(config)
    monday = datetime(2026, 3, 16)  # Monday

    result = optimizer.optimize_sequence(
        pois=[poi],
        ...,
        trip_start_date=monday
    )

    # POI should be schedulable on Monday
    assert len(result['sequence']) > 0
```

### Integration Tests

See `test_opening_hours.py` for comprehensive test suite:
- Morning-only POIs
- Afternoon-only POIs
- Closed day handling
- Preferred time slot enforcement
- Multi-day opening hours
- Real-world Vatican Museums scenario

---

## Troubleshooting

### "POI not scheduled on any day"

**Cause**: POI might be closed on all days in trip date range.

**Solution**:
1. Check `operation_hours.periods` for POI
2. Verify trip start date aligns with open days
3. Use `--start-date` to start on a different day of week

### "Opening hours not respected"

**Cause**: `trip_start_date` not provided or invalid.

**Solution**:
```bash
# Specify start date explicitly
./pocket-guide trip plan --city Rome --days 3 \
  --mode ilp \
  --start-date "2026-03-16"  # Monday
```

### "Preferred time slots ignored"

**Cause**: `booking_info.required` might be false.

**Solution**: Set `booking_info.required: true` in POI metadata.

---

## References

- [Google Maps Places API - Opening Hours](https://developers.google.com/maps/documentation/places/web-service/details#PlaceOpeningHours)
- [Places API Opening Hours Format](https://developers.google.com/maps/documentation/javascript/reference/places-service#PlaceOpeningHours)
- Implementation: `src/trip_planner/ilp_optimizer.py:_add_time_window_constraints()`

---

**Updated**: 2026-02-12
**Author**: Claude Sonnet 4.5
