# ILP Retry Debug Improvements

## Changes Implemented

### Fix 1: Handle 'ERROR' Status in Retry Loop

**Problem:** When `_try_optimize()` encountered any error (exception), it returned `{'status': 'ERROR'}`. The retry loop treated this the same as TIMEOUT/MODEL_INVALID, immediately raising an exception and jumping to greedy fallback, bypassing all retry logic.

**Solution:** Added specific handling for 'ERROR' status before the generic `else` clause.

**Location:** `src/trip_planner/ilp_optimizer.py:136-140`

**Code Added:**
```python
elif result['status'] == 'ERROR':
    # Error during model building - log and fail
    error_msg = result.get('error', 'Unknown error')
    print(f"  [ILP] ❌ Error during model building: {error_msg}", flush=True)
    raise Exception(f"Model building error: {error_msg}")
```

**Benefits:**
- Clear distinction between different failure modes
- Better error messages for debugging
- Prevents ERROR status from being confused with TIMEOUT/MODEL_INVALID

---

### Fix 2: Add More Debug Logging

**Problem:** When retries happened (or failed to happen), there was no visibility into:
- How many POIs were being attempted each time
- Which POIs remained after removal
- Whether retry loop was even executing

**Solution:** Added debug print statements before each optimization attempt.

**Location:** `src/trip_planner/ilp_optimizer.py:97-101`

**Code Added:**
```python
# Debug: Show current POI count before attempting
print(f"  [ILP] Attempting optimization with {len(current_pois)} POIs", flush=True)
if attempt > 0:
    poi_names = [p.get('poi', 'Unknown') for p in current_pois]
    print(f"  [ILP] Current POIs: {', '.join(poi_names)}", flush=True)
```

**Benefits:**
- Always shows POI count before each attempt (attempt 0, 1, 2, ...)
- On retries, shows complete list of remaining POIs
- Makes it obvious if retry loop is executing or being bypassed
- Helps diagnose which POIs are being kept/removed

---

## Expected Output Examples

### Example 1: Successful Retry

```
  [ILP] Max hours per day: 7.5h (pace: normal)
  [ILP] Attempting optimization with 9 POIs

  [ILP] ===== STEP 6: DAILY HOUR CONSTRAINTS =====
  [ILP] Solver finished with status: INFEASIBLE
  [ILP] Model is INFEASIBLE - too many POIs for time constraints
  [ILP] Removing: 'Baths of Caracalla' (priority=medium, hours=1.5h)

  [ILP] ===== RETRY ATTEMPT 1/2 =====
  [ILP] Attempting optimization with 8 POIs
  [ILP] Current POIs: Colosseum, Arch of Constantine, Palatine Hill, Roman Forum, Capitoline Museums, Pantheon, Basilica di San Clemente, Galleria Borghese

  [ILP] Solver finished with status: OPTIMAL
  [ILP] ✓ Found solution after removing 1 POI(s)
```

### Example 2: Error During Model Building

```
  [ILP] Max hours per day: 7.5h (pace: normal)
  [ILP] Attempting optimization with 9 POIs

  [ILP] ===== STEP 6: DAILY HOUR CONSTRAINTS =====
  [ILP] ❌ Error during model building: 'coordinates' key not found in POI metadata

  ⚠️  [FALLBACK] ILP optimization failed - switching to greedy mode
  [FALLBACK] Reason: Model building error: 'coordinates' key not found in POI metadata
```

### Example 3: All High Priority (Can't Remove)

```
  [ILP] Max hours per day: 7.5h (pace: normal)
  [ILP] Attempting optimization with 9 POIs

  [ILP] Solver finished with status: INFEASIBLE
  [ILP] Model is INFEASIBLE - too many POIs for time constraints
  [ILP] Removing: 'Arch of Constantine' (priority=medium, hours=0.3h)

  [ILP] ===== RETRY ATTEMPT 1/2 =====
  [ILP] Attempting optimization with 8 POIs
  [ILP] Current POIs: Colosseum, Palatine Hill, Roman Forum, Capitoline Museums, Pantheon, Basilica di San Clemente, Baths of Caracalla, Galleria Borghese

  [ILP] Solver finished with status: INFEASIBLE
  [ILP] Model is INFEASIBLE - too many POIs for time constraints
  [ILP] All removable POIs are 'high' priority, cannot reduce further

  ⚠️  [FALLBACK] ILP optimization failed - switching to greedy mode
  [FALLBACK] Reason: INFEASIBLE: All POIs are high priority, cannot reduce further
```

### Example 4: Exhausted Retries

```
  [ILP] Max hours per day: 7.5h (pace: normal)
  [ILP] Attempting optimization with 9 POIs

  [ILP] Solver finished with status: INFEASIBLE
  [ILP] Removing: 'Baths of Caracalla' (priority=medium, hours=1.5h)

  [ILP] ===== RETRY ATTEMPT 1/2 =====
  [ILP] Attempting optimization with 8 POIs
  [ILP] Current POIs: Colosseum, Arch of Constantine, Palatine Hill, Roman Forum, Capitoline Museums, Pantheon, Basilica di San Clemente, Galleria Borghese

  [ILP] Solver finished with status: INFEASIBLE
  [ILP] Removing: 'Arch of Constantine' (priority=medium, hours=0.3h)

  [ILP] ===== RETRY ATTEMPT 2/2 =====
  [ILP] Attempting optimization with 7 POIs
  [ILP] Current POIs: Colosseum, Palatine Hill, Roman Forum, Capitoline Museums, Pantheon, Basilica di San Clemente, Galleria Borghese

  [ILP] Solver finished with status: INFEASIBLE

  ⚠️  [FALLBACK] ILP optimization failed - switching to greedy mode
  [FALLBACK] Reason: INFEASIBLE: Could not find solution after 2 retries
```

---

## What This Fixes

### Previously (Before Fixes)

When the tour `rome-tour-20260303-223749-2676cb` was generated:
- ILP attempted with 9 POIs
- Something went wrong (likely an error during model building)
- Returned `{'status': 'ERROR'}`
- Immediately jumped to greedy fallback
- **No retry logs printed**
- **No POI removal attempted**
- Result: Tour with violations (Day 2: 9.5h)

### Now (After Fixes)

When the same scenario happens:
- ILP attempts with 9 POIs
- **Prints:** `Attempting optimization with 9 POIs`
- If ERROR: **Prints:** `❌ Error during model building: <error message>`
- If INFEASIBLE: **Prints:** `Removing: 'POI name' (priority=X, hours=Yh)`
- Retries with fewer POIs
- **Prints:** `Attempting optimization with 8 POIs`
- **Prints:** `Current POIs: <list>`
- Continues until OPTIMAL, FEASIBLE, or retries exhausted

**Full visibility into retry process!**

---

## Files Modified

1. **src/trip_planner/ilp_optimizer.py**
   - Added ERROR status handler (lines 136-140)
   - Added debug logging (lines 97-101)
   - Total changes: +8 lines

---

## Testing

To test the improvements, run:

```bash
# Test with a tour that should trigger retries
./pocket-guide trip plan --city Rome --days 2 --interests history --mode ilp --pace normal

# Expected: See retry logs with POI removal if infeasible
# Expected: See error messages if model building fails
# Expected: See exact POI count and names on each attempt
```

---

## Success Criteria

✅ Compilation successful (tested)
⏳ Retry logs appear when INFEASIBLE
⏳ POI removal messages show which POIs were removed
⏳ POI count shown before each attempt
⏳ POI names shown on retry attempts
⏳ ERROR status handled separately from other failures

---

**Status:** Implementation complete, ready for testing
**Branch:** feature/daily-hour-constraints
**Next:** Test with real tours to verify logs appear correctly
