# Daily Hour Constraint Issue - Diagnosis

## Problem

Tour `rome-tour-20260303-174552-fcf057` violates daily hour constraints:

**Day 1: 11.0 hours** (Limit: 7.5h for normal pace)
- Colosseum: 2.0h
- Baths of Caracalla: 1.5h
- Palatine Hill: 1.5h
- Roman Forum: 2.0h
- Pantheon: 0.8h
- Capitoline Museums: 2.0h
- Travel time: ~1.2h
- **Total: 11.0 hours**

**Day 2: 5.4 hours** (Under limit)
- Basilica di San Clemente: 1.2h
- National Roman Museum: 1.5h
- Galleria Borghese: 2.0h
- Travel time: ~0.7h
- **Total: 5.4 hours**

The tour shows `constraints_violated: ["Day 1: Exceeds 7.5h limit (11.0h scheduled)"]` but the violation was not prevented during optimization.

## Root Cause

### Issue 1: ILP Optimizer Missing Daily Hour Constraint

**File:** `src/trip_planner/ilp_optimizer.py`

**Current State:**
- Line 42: Hardcoded `self.max_hours_per_day = 8` is defined but **NEVER USED in constraints**
- The ILP model has NO constraint enforcing maximum daily hours

**Existing Constraints:**
1. ✅ TSP constraints (each POI visited exactly once)
2. ✅ Time window constraints (respects opening hours)
3. ✅ Precedence constraints (storytelling order)
4. ✅ Combo ticket constraints (same-day visits)
5. ✅ Start/end location hints
6. ❌ **MISSING: Daily hour limit constraint**

**Why Day 1 Got Overloaded:**
1. Combo ticket constraint forces Colosseum, Roman Forum, Palatine Hill on same day (6.5h total)
2. Distance optimization adds nearby Pantheon (0.8h) and Capitoline Museums (2.0h)
3. No constraint stops the optimizer from packing all 6 POIs into Day 1
4. Day 1 ends up with 11.0h because the optimizer prioritizes distance + coherence scores

### Issue 2: Validation Happens Too Late

**File:** `src/trip_planner/itinerary_optimizer.py`

**Line 198:** `violations = self._validate_constraints(itinerary, max_hours_per_day)`

This validation runs AFTER the itinerary is created. It detects violations but doesn't prevent them.

**Current Flow:**
```
1. ILP optimizer creates itinerary (no hour constraints)
2. Itinerary returned to optimizer agent
3. _validate_constraints() checks hours → finds violation
4. Violation added to result['constraints_violated']
5. User receives tour with violations already present
```

## Why This Is Critical

**User Impact:**
- Unrealistic schedules (11 hours of sightseeing = exhausting)
- Poor user experience (can't complete Day 1 as planned)
- Trust issue (system knows it's violated but delivers it anyway)

**Cascade Effects:**
- Combo tickets become problematic (3 POIs = 6.5h minimum)
- Can't fit combo tickets + 2 more POIs in one day with normal pace
- Need smarter distribution or multi-day combo tickets

## Solution Required

### Add Daily Hour Constraint to ILP Optimizer

**Location:** `src/trip_planner/ilp_optimizer.py`

**New Constraint Needed:**
```python
def _add_daily_hour_constraints(
    self,
    model: cp_model.CpModel,
    visit_vars: Dict,
    pois: List[Dict[str, Any]],
    duration_days: int,
    max_hours_per_day: float,
    distance_matrix: Dict[Tuple[str, str], float]
):
    """
    Add constraints to enforce maximum hours per day.

    For each day:
        sum(POI.estimated_hours + travel_time) <= max_hours_per_day
    """
```

**Implementation Approach:**
1. For each day `d`:
   - Calculate total_hours = sum of:
     - Each POI's `estimated_hours`
     - Travel time between consecutive POIs (distance / walking_speed)
   - Add constraint: `total_hours <= max_hours_per_day`

2. This requires:
   - Tracking which POIs are on each day (already have via `visit_vars`)
   - Calculating travel time based on sequence (need pair tracking)
   - Converting to integer arithmetic (CP-SAT requirement)

**Challenges:**
- Travel time depends on POI order (which POI comes before which)
- Need to model: `if POI_i at pos AND POI_j at pos+1, add travel_time(i,j)`
- Similar to how distance objective is calculated (lines 368-389)

**Integration Point:**
- Add call in `optimize_sequence()` after combo ticket constraints (line 121)
- Pass `max_hours_per_day` from preferences (calculate same way as itinerary_optimizer)

### Benefits of Fix

1. **Prevents violations proactively** - ILP solver won't create invalid schedules
2. **Better day distribution** - Forces optimizer to spread POIs across days
3. **Realistic schedules** - Respects user's pace preference (relaxed/normal/packed)
4. **Combo ticket handling** - May trigger automatic adjustment or fallback to greedy mode

### Potential Side Effects

**Risk: Infeasibility**
- If combo tickets require 7+ hours and max_hours_per_day = 6 (relaxed pace)
- ILP solver may fail to find solution (status: INFEASIBLE)
- **Mitigation:** Already have fallback to greedy mode (line 204-213)

**Risk: Longer solve times**
- Adding constraints increases problem complexity
- **Mitigation:** Already have timeout (30s) and 5% gap limit (line 164)

## Test Case After Fix

**Expected Behavior:**
```
Input: Rome, 2 days, normal pace (7.5h/day max)
Combo constraint: Colosseum + Roman Forum + Palatine Hill same day (6.5h)

Day 1 (7.5h max):
- Colosseum: 2.0h
- Roman Forum: 2.0h
- Palatine Hill: 1.5h
- Pantheon: 0.8h (nearby, fits in remaining 1.0h with travel)
- Total: ~7.3h ✓

Day 2 (7.5h max):
- Capitoline Museums: 2.0h
- Basilica di San Clemente: 1.2h
- National Roman Museum: 1.5h
- Galleria Borghese: 2.0h
- Baths of Caracalla: 1.5h (if time permits)
- Total: ~7.2h ✓

No violations!
```

## Implementation Plan

1. **Add daily hour constraint method** in `ilp_optimizer.py`
2. **Calculate max_hours_per_day** from preferences in `optimize_sequence()`
3. **Call constraint method** in model building phase
4. **Test with existing tours** to verify:
   - No violations in output
   - Solver still finds OPTIMAL/FEASIBLE solutions
   - Fallback works if infeasible
5. **Update documentation** in docstrings and README

## Files to Modify

1. **src/trip_planner/ilp_optimizer.py**
   - Add `_add_daily_hour_constraints()` method
   - Call it in `optimize_sequence()` (after line 121)
   - Pass `max_hours_per_day` parameter through call chain

2. **src/trip_planner/itinerary_optimizer.py** (optional)
   - Pass `max_hours_per_day` to ILP optimizer
   - Currently it's calculated but not passed to ILP

3. **config.yaml** (optional)
   - May want to make max_hours configurable per pace level
   - Currently hardcoded in itinerary_optimizer.py lines 91-96

## Success Criteria

✅ No tours with `constraints_violated` for daily hours
✅ ILP solver produces balanced day schedules
✅ Combo ticket constraints still work correctly
✅ Solver doesn't timeout or become infeasible
✅ Test tour `rome-tour-20260303-174552-fcf057` case redistributes POIs

---

**Status:** Diagnosis complete, ready for implementation
**Priority:** High (affects user experience and tour quality)
**Estimated Complexity:** Medium (need to model travel time in constraints)
