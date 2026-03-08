# Daily Hour Constraint - Implementation Summary

## What Was Implemented

Successfully added daily hour constraints to the ILP optimizer with smart retry logic to handle infeasible schedules.

## Changes Made

### File: `src/trip_planner/ilp_optimizer.py`

#### 1. Added Daily Hour Constraint Method

**Method:** `_add_daily_hour_constraints()`

**Location:** Line ~893 (after combo ticket constraints)

**What it does:**
- For each day, enforces: `total_hours <= max_hours_per_day`
- Total hours = sum of (POI visit hours + travel time between POIs)
- Uses integer arithmetic (SCALE=100 for 0.01h precision)
- max_hours_per_day based on pace:
  - Relaxed: 6.0 hours/day
  - Normal: 7.5 hours/day
  - Packed: 9.0 hours/day

**Code:**
```python
# For each day
total_hours = sum(
    poi.estimated_hours * visit_vars[i][day][pos]  # Visit time
    + travel_time(i,j) * transition_vars[i][j][day][pos]  # Travel time
)
model.Add(total_hours <= max_hours_per_day * SCALE)
```

#### 2. Refactored optimize_sequence() with Retry Loop

**What changed:**
- Extract max_hours_per_day from preferences (based on pace)
- Retry up to `duration_days` times when INFEASIBLE
- Each retry removes one low-priority POI
- If still INFEASIBLE after all retries → fallback to greedy

**Retry Logic:**
```python
max_retries = duration_days  # 1 day = 1 retry, 5 days = 5 retries

for attempt in range(max_retries + 1):
    result = _try_optimize(current_pois, ...)

    if result['status'] == 'OPTIMAL' or 'FEASIBLE':
        return result  # Success!

    elif result['status'] == 'INFEASIBLE':
        # Remove lowest priority POI
        removable = _find_removable_poi(current_pois)

        if removable is None:
            # All POIs are high priority or in combo tickets
            fallback to greedy

        current_pois.remove(removable)
        # Retry with fewer POIs

    else:
        # TIMEOUT, ERROR, etc
        fallback to greedy
```

#### 3. Created _try_optimize() Helper

**What it does:**
- Extracted model building + solving logic from optimize_sequence()
- Returns dict with 'status' field for retry logic to check
- Allows rebuilding model with different POI sets

#### 4. Added _find_removable_poi() Helper

**Removal Strategy:**
1. **Filter out combo ticket POIs** (protected, can't remove)
2. **Check if all remaining are "high" priority** → return None (can't reduce)
3. **Sort by:**
   - Priority: low → medium → high (remove lowest first)
   - Estimated hours: 0.5h → 1.0h → 2.0h (remove smallest first, more skippable)
4. **Return the POI** with lowest (priority, hours)

**Example:**
```
POIs:
- Colosseum (high, 2.0h) [combo ticket - protected]
- Pantheon (high, 0.8h)
- Baths of Caracalla (medium, 1.5h)
- Villa Borghese (medium, 2.0h)

Removable: Pantheon, Baths of Caracalla, Villa Borghese (Colosseum protected)
Lowest priority: medium
Among medium: Baths of Caracalla (1.5h) vs Villa Borghese (2.0h)
→ Remove: Baths of Caracalla (smaller, more skippable)
```

#### 5. Added _get_combo_ticket_poi_names() Helper

**What it does:**
- Returns set of POI names that are in combo ticket groups
- Checks both new format (`combo_ticket_groups`) and old format (`combo_ticket`)
- Used by `_find_removable_poi()` to protect combo POIs

## How It Works End-to-End

### Scenario: Rome 2-day tour, Normal pace (7.5h/day)

**Initial POIs (11h needed for Day 1):**
1. Colosseum (high, 2.0h) [combo]
2. Roman Forum (high, 2.0h) [combo]
3. Palatine Hill (high, 1.5h) [combo]
4. Pantheon (high, 0.8h)
5. Capitoline Museums (high, 2.0h)
6. Baths of Caracalla (medium, 1.5h)
7. More POIs...

**Execution:**

```
Attempt 0 (9 POIs):
  Add constraint: Day 1 total <= 7.5h, Day 2 total <= 7.5h
  Solve → INFEASIBLE (combo ticket needs 6.5h minimum, can't fit all 6 POIs in Day 1)

Attempt 1 (retry #1):
  Find removable POI:
    - Filter: Remove combo POIs → {Pantheon, Museums, Baths, ...}
    - Check priorities: Not all "high" (Baths is "medium")
    - Sort: medium priority comes first
    - Among medium: Baths (1.5h) is smallest
  Remove: "Baths of Caracalla"
  Rebuild model with 8 POIs
  Solve → OPTIMAL ✓

Result:
  Day 1: Colosseum, Forum, Palatine, Pantheon (~7.3h) ✓
  Day 2: Museums, National Museum, Basilica, ... (~7.0h) ✓
  No violations!
```

## Benefits

1. **Prevents over-packed days** - No more 11h schedules
2. **Automatic POI reduction** - Smartly removes least important POIs
3. **Respects combo tickets** - Never removes POIs that must be visited together
4. **Respects priorities** - Removes low/medium before high
5. **Configurable by pace** - Relaxed=6h, Normal=7.5h, Packed=9h
6. **Graceful degradation** - Falls back to greedy if can't solve

## Test Cases

### Test Case 1: Existing Problematic Tour

**Before:**
```
rome-tour-20260303-174552-fcf057
Day 1: 11.0 hours (VIOLATION)
Day 2: 5.4 hours
```

**After (expected):**
```
Day 1: 7.3 hours ✓
Day 2: 7.0 hours ✓
Removed: 1-2 medium-priority POIs
```

### Test Case 2: All High Priority + Combo Tickets

**Input:**
- 6 POIs, all "high" priority
- 3 are combo ticket (must visit together = 6.5h)
- Max 7.5h/day
- Can't fit all in 1 day

**Expected:**
```
Attempt 0: INFEASIBLE
Attempt 1: Try to remove POI → All are "high" priority → Return None
→ Fallback to greedy ✓
```

### Test Case 3: Normal Case (Works First Try)

**Input:**
- 8 POIs, mixed priorities
- Total 14h for 2 days
- Max 7.5h/day = 15h total available

**Expected:**
```
Attempt 0: OPTIMAL ✓ (no retry needed)
```

## Configuration

User controls via `--pace` parameter:

```bash
# Relaxed pace (6h/day max)
./pocket-guide trip plan --city Rome --days 2 --pace relaxed

# Normal pace (7.5h/day max) - default
./pocket-guide trip plan --city Rome --days 2 --pace normal

# Packed pace (9h/day max)
./pocket-guide trip plan --city Rome --days 2 --pace packed
```

## Files Modified

1. **src/trip_planner/ilp_optimizer.py** (+140 lines)
   - Added `_add_daily_hour_constraints()` method (~70 lines)
   - Refactored `optimize_sequence()` with retry loop (~40 lines)
   - Added `_try_optimize()` helper (~15 lines)
   - Added `_find_removable_poi()` helper (~35 lines)
   - Added `_get_combo_ticket_poi_names()` helper (~20 lines)

## Documentation Created

1. **DAILY_HOUR_CONSTRAINT_DIAGNOSIS.md** - Root cause analysis
2. **ILP_CONSTRAINT_DIAGNOSIS_ANALYSIS.md** - Technical feasibility analysis
3. **DAILY_HOUR_CONSTRAINT_IMPLEMENTATION.md** (this file) - Implementation summary

## Next Steps

1. **Test with existing problematic tour:**
   ```bash
   # Should no longer produce violations
   ./pocket-guide trip plan --city Rome --days 2 --interests history --mode ilp
   ```

2. **Verify metrics:**
   - No `constraints_violated` in output
   - Balanced day schedules (both days ~7-8h)
   - Solver still finds OPTIMAL solutions

3. **Edge case testing:**
   - All high priority POIs
   - Many combo tickets
   - Very short trips (1 day)
   - Very long trips (7+ days)

4. **Commit changes:**
   ```bash
   git add src/trip_planner/ilp_optimizer.py
   git add DAILY_HOUR_CONSTRAINT_*.md ILP_CONSTRAINT_DIAGNOSIS_ANALYSIS.md
   git commit -m "Add: Daily hour constraints with smart retry logic"
   ```

## Success Criteria

✅ Compilation successful (tested)
⏳ No tours with daily hour violations
⏳ ILP produces balanced schedules
⏳ Combo tickets still work correctly
⏳ Solver doesn't timeout
⏳ Smart POI removal works as expected

---

**Status:** Implementation complete, ready for testing
**Branch:** feature/daily-hour-constraints
**Next:** Test with real tours and verify results
