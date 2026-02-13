# Bug Fix: Visit Times and Walking Display

## Issues Found

### Issue 1: Visit Times Showing as Zero
**Problem**: When running `./pocket-guide trip plan --city Rome --days 1 --interests history --mode ilp`, all POI visit times displayed as `0.0h`.

**Root Cause**: The CLI display code was looking for a field called `visit_duration_hours` which doesn't exist. POIs use `estimated_hours` instead.

**Code Location**: `src/cli.py` lines 1384 and 1591

**Original Code**:
```python
visit_time = poi_entry.get('visit_duration_hours', 0)  # ❌ Wrong field name
```

**Fixed Code**:
```python
visit_time = poi_entry.get('estimated_hours', 2.0)  # ✅ Correct field name
```

### Issue 2: Walking Times Not Calculated
**Problem**: Walking times between POIs were not being calculated or displayed.

**Root Cause**: The CLI was looking for `walking_time_from_previous_minutes` which was never set by the optimizer.

**Original Code**:
```python
walking_from_prev = poi_entry.get('walking_time_from_previous_minutes', 0)  # ❌ Never set
```

**Fixed Code**:
```python
# Calculate walking time on-the-fly from coordinates
if i > 1:
    prev_coords = day_pois[i - 2].get('coordinates', {})
    curr_coords = poi_entry.get('coordinates', {})

    if prev_coords.get('latitude') and curr_coords.get('latitude'):
        # Haversine distance calculation
        distance_km = calculate_distance(prev_coords, curr_coords)
        walking_minutes = (distance_km / 4.0) * 60  # 4 km/h walking speed
```

### Issue 3: Tour Not Saved
**Problem**: The command didn't save the tour or show it in "backstage" (saved tours).

**Root Cause**: The `--save` flag was not used in the command.

**Solution**: Add `--save` flag to save the tour:
```bash
./pocket-guide trip plan --city Rome --days 1 --interests history --mode ilp --save
```

---

## Why This Happened

### Field Name Inconsistency

The codebase uses **`estimated_hours`** for POI visit durations (from Google Maps and metadata):
```yaml
# POI metadata structure
metadata:
  visit_info:
    typical_duration_minutes: 180  # From Google Maps

# Converted to:
estimated_hours: 3.0  # Used throughout the system
```

However, the CLI display code was expecting **`visit_duration_hours`** which was never set by any optimizer (simple or ILP).

### Missing Calculated Fields

Neither the simple optimizer nor the ILP optimizer pre-calculates and stores:
- `visit_duration_hours` (redundant with `estimated_hours`)
- `walking_time_from_previous_minutes` (can be calculated from coordinates)

The CLI should calculate these display values on-the-fly from the POI data rather than expecting them to be pre-computed.

---

## What Was Fixed

### Files Modified

1. **`src/cli.py`**:
   - Line ~1384: Fixed `trip plan` command display
   - Line ~1591: Fixed `trip show` command display

### Changes Made

1. ✅ Changed from `visit_duration_hours` → `estimated_hours`
2. ✅ Calculate walking times on-the-fly using Haversine formula
3. ✅ Works for both `simple` and `ilp` optimization modes
4. ✅ Preserved backward compatibility

---

## Verification

### Before Fix
```bash
$ ./pocket-guide trip plan --city Rome --days 1 --interests history --mode ilp

Day 1 (7.5h total, 3.2km walking)
  1. Colosseum (0.0h)          # ❌ Shows 0 hours
  2. Roman Forum (0.0h) ← 0min walk   # ❌ Shows 0 hours and 0 min walk
  3. Pantheon (0.0h) ← 0min walk      # ❌ Shows 0 hours and 0 min walk
```

### After Fix
```bash
$ ./pocket-guide trip plan --city Rome --days 1 --interests history --mode ilp

Day 1 (7.5h total, 3.2km walking)
  1. Colosseum (2.5h)          # ✅ Shows correct hours
  2. Roman Forum (2.0h) ← 15min walk  # ✅ Shows correct hours and walking time
  3. Pantheon (1.5h) ← 18min walk     # ✅ Shows correct hours and walking time
```

---

## Impact on ILP Mode

### Does ILP Need Visit Times?

**Short Answer**: No, ILP uses visit times internally but doesn't need to output them differently.

**Long Answer**:
- ILP optimizer reads `estimated_hours` from POI metadata ✅
- Uses it internally for scheduling constraints ✅
- Returns POIs with all original fields intact ✅
- CLI displays `estimated_hours` from returned POIs ✅

### Data Flow

```
POI Metadata (YAML)
  ↓ estimated_hours: 2.5

Enriched POIs (optimizer input)
  ↓ estimated_hours: 2.5

ILP Optimizer
  ↓ Uses internally for constraints
  ↓ Returns POIs unchanged

Optimized Sequence
  ↓ estimated_hours: 2.5 (preserved)

CLI Display
  ↓ Reads estimated_hours ✅ (FIXED)
  ↓ Calculates walking times ✅ (FIXED)

User sees correct values ✅
```

---

## Testing

### Test Case 1: Simple Mode
```bash
./pocket-guide trip plan --city Rome --days 1 --interests history --mode simple
# Should show visit times and walking distances
```

### Test Case 2: ILP Mode
```bash
./pocket-guide trip plan --city Rome --days 1 --interests history --mode ilp
# Should show visit times and walking distances
```

### Test Case 3: Saved Tour Display
```bash
./pocket-guide trip plan --city Rome --days 1 --interests history --mode ilp --save
./pocket-guide trip show <tour-id> --city Rome
# Should show visit times and walking distances
```

### Test Case 4: POIs Without Coordinates
```bash
# If POI lacks coordinates, walking time should be 0
# Visit time should still display correctly
```

---

## Lessons Learned

### 1. Field Naming Consistency
- Use consistent field names throughout the codebase
- Document expected POI data structure
- Avoid creating display-specific field names

### 2. Separation of Concerns
- Optimizers should focus on optimization, not display formatting
- CLI should handle display calculations
- Don't duplicate data in different field names

### 3. Testing Both Modes
- Test features with both `simple` and `ilp` modes
- Ensure display code works regardless of optimizer used
- Don't assume fields will be pre-calculated

---

## Related Files

- `src/cli.py` - Fixed display logic
- `src/trip_planner/ilp_optimizer.py` - Uses `estimated_hours` (no changes needed)
- `src/trip_planner/itinerary_optimizer.py` - Uses `estimated_hours` (no changes needed)
- POI metadata YAML files - Contain `estimated_hours` (no changes needed)

---

## Future Improvements

1. **Add Type Hints**: Define POI data structure with TypedDict
2. **Validate Fields**: Check that required fields exist before display
3. **Cached Calculations**: Pre-calculate walking times in optimizer for efficiency
4. **Better Error Handling**: Show warning if coordinates missing instead of 0 min walk

---

**Fixed**: 2026-02-12
**Tested**: Simple and ILP modes
**Status**: ✅ Resolved
