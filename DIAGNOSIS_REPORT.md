# ILP INFEASIBLE Root Cause Analysis

**Tour**: rome-tour-20260227-102356-126fc9
**POIs**: 23
**Duration**: 5 days
**Status**: INFEASIBLE → GREEDY_FALLBACK

---

## Executive Summary

The INFEASIBLE status is caused by **time window constraints (opening hours) combined with combo ticket same-day requirements**. Specifically:

1. **16 POIs** have opening hour restrictions
2. **130 position blocks** are added by time window constraints
3. Many POIs close at **16:30 (4:30 PM)**
4. Position-based timing: **Position 3 = 16:30 arrival** (past closing time for early-closing POIs)
5. **Combo tickets** force 3 early-closing POIs onto the SAME day
6. Result: **Not enough early positions** to accommodate all early-closing POIs + combo requirements

---

## Bug Fixed During Investigation

### Original Bug
**File**: `src/trip_planner/ilp_optimizer.py` line 483
**Issue**: Operation hours accessed from wrong location

```python
# BEFORE (WRONG):
operation_hours = poi.get('metadata', {}).get('operation_hours', {})
```

**Impact**: Time window constraints were SILENTLY DISABLED (operation_hours always empty)

### Fix Applied
```python
# AFTER (CORRECT):
operation_hours = poi.get('operation_hours', {})
```

**Impact**: Time window constraints now work correctly, revealing the INFEASIBLE issue

---

## Technical Details

### Position-Based Time Estimation

The ILP model uses a crude approximation:

```python
# Line 519 in ilp_optimizer.py
estimated_arrival_minutes = start_minutes + (pos * 150)
```

**Position timing**:
- Position 0: 09:00 (540 min)
- Position 1: 11:30 (690 min)
- Position 2: 14:00 (840 min)
- Position 3: 16:30 (990 min) ← **PAST 4:30 PM CLOSING**
- Position 4: 19:00 (1140 min)
- ...

### POIs Closing at 16:30 (4:30 PM)

From tour data:
- **Colosseum** (closes 16:30)
- **Roman Forum** (closes 16:30)
- **Palatine Hill** (closes 16:30)
- **Baths of Caracalla** (closes 16:30)
- **Ara Pacis** (closes 16:30)
- **Largo di Torre Argentina** (closes 16:30)
- **Galleria Doria Pamphilj** (closes 16:30)
- **Galleria Borghese** (closes 16:30)

**Total**: 8 POIs can only use positions 0-2 (blocked from position 3+)

### Combo Ticket Requirements

**Archaeological Pass** (same-day required):
- Colosseum (closes 16:30)
- Roman Forum (closes 16:30)
- Palatine Hill (closes 16:30)

**Vatican Combo** (same-day required):
- Vatican Museums (closes 18:00)
- Sistine Chapel (closes 18:00)

### The Constraint Conflict

**Scenario**:
1. Days: 5
2. Max POIs per day: 5
3. **Total position slots**: 5 days × 5 positions = 25 slots
4. **Early positions (0-2)**: 5 days × 3 positions = **15 early slots**

**Demand for early positions**:
- 8 POIs close at 16:30 → need positions 0-2
- Archaeological Pass forces 3 of these onto SAME day
- That day uses 3 of its 3 early positions for combo POIs
- But 5 OTHER POIs also need early positions
- **Result**: 8 POIs competing for 15 early slots, but combo constraint reduces flexibility → INFEASIBLE

---

## Why The Approximation Is Problematic

### Reality vs Model

**Reality**:
```
Colosseum (2.5h) + Roman Forum (1.5h) + Palatine Hill (1.5h) = 5.5h
Start: 09:00
End: 09:00 + 5.5h = 14:30 (well before 16:30 closing)
✅ FITS COMFORTABLY
```

**ILP Model**:
```
Position 0: Colosseum (09:00 arrival)
Position 1: Roman Forum (11:30 arrival)  ← Assumes 2.5h gap
Position 2: Palatine Hill (14:00 arrival) ← Assumes 2.5h gap
Total time slots: 3 × 150min = 7.5h
❌ WASTEFUL - doesn't account for actual walking time/duration
```

The 150-minute-per-position assumption:
1. Doesn't account for actual POI visit duration
2. Doesn't account for actual walking distance between POIs
3. Creates artificial position scarcity
4. Makes feasible schedules appear infeasible

---

## Verification

### Test Results

**Without time windows**: ✅ FEASIBLE
```bash
python test_tour_no_timewindows.py
# Status: OPTIMAL
# Archaeological Pass: All 3 on Day 1 ✅
```

**With time windows**: ❌ INFEASIBLE
```bash
python test_tour_rome_20260227.py
# Status: INFEASIBLE
# Fallback: GREEDY_FALLBACK
```

**Incremental test** (without enrichment): ✅ FEASIBLE
```bash
python test_incremental_pois.py
# 23 POIs → FEASIBLE (no operation_hours loaded)
```

---

## Solutions

### Option 1: Improve Time Window Logic (RECOMMENDED)

Replace crude 150-min approximation with actual duration calculation:

```python
# Instead of:
estimated_arrival = start_time + (position * 150)

# Use:
estimated_arrival = start_time + sum(actual_poi_durations[0:position]) + sum(walking_times[0:position])
```

**Pros**:
- Accurate scheduling
- Maintains time window constraints
- Resolves INFEASIBLE issue

**Cons**:
- More complex implementation
- Requires distance/duration data

### Option 2: Relax Position Scarcity

Increase max_pois_per_day or adjust position timing:

```python
# Instead of 150 min/position:
position_gap = 120  # 2 hours instead of 2.5 hours
```

**Pros**:
- Simple change
- May resolve INFEASIBLE

**Cons**:
- Still inaccurate
- May create over-packed days

### Option 3: Disable Time Windows (NOT RECOMMENDED)

Remove time window constraints entirely.

**Pros**:
- Solves INFEASIBLE

**Cons**:
- Ignores real-world opening hours
- May create invalid itineraries

---

## Metrics

```
POIs total: 23
POIs with opening hours: 16
Position blocks added: 130
POIs closing at 16:30: 8
Combo ticket groups: 2 (5 POIs total)
Solver status: INFEASIBLE → GREEDY_FALLBACK
```

---

## Conclusion

The user asked: *"can you tell me the exact constraint is because the open hour or the length of time?"*

**Answer**: It's **BOTH**.

1. **Opening hours** restrict 8 POIs to early positions (0-2)
2. **Position timing (150-min approximation)** creates artificial scarcity
3. **Combo tickets** force 3 early-closing POIs onto same day
4. **Interaction**: Not enough early position slots to satisfy all constraints

The root cause is the **crude position-based time estimation** that doesn't reflect actual visit durations. Fixing this will resolve INFEASIBLE while keeping time window constraints active.
