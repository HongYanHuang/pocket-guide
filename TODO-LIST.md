# TODO List - Pocket Guide

## High Priority Tasks

### 1. ⚠️ Optimize Coherence Calculation Logic

**Status**: 🔴 Not Started
**Priority**: High
**Estimated Effort**: Medium

**Problem**:
The current coherence calculation creates symmetric scores (both directions equal), which:
- Doesn't make sense for storytelling order (A→B should differ from B→A)
- Required workarounds in precedence constraint logic
- Is currently disabled (precedence_soft_threshold: 1.0) because it conflicts with combo tickets

**Current Implementation**:
- **Location**: `src/trip_planner/itinerary_optimizer.py` lines 393-433
- **Function**: `_calculate_pair_coherence(poi1, poi2)`

**Current Logic**:
```python
score = 0.0

# 1. Same historical period? +0.3
if both_from_same_period:
    score += 0.3

# 2. Chronological order? +0.3 or +0.4
if poi1_before_poi2:
    score += 0.4

# 3. Built within similar timeframe? +0.1 to +0.3
if built_within_50_years:
    score += 0.3
```

**Issues**:
1. Scores are **symmetric**: coherence(A→B) = coherence(B→A)
2. Chronological order bonus is applied but results are still symmetric
3. Doesn't reflect actual storytelling flow (older → newer makes sense, but newer → older doesn't)
4. Conflicts with combo ticket requirements (groups by ticket type, not chronology)

**Proposed Solutions**:

**Option A: Make Coherence Directional (Recommended)**
```python
def _calculate_pair_coherence(poi1, poi2):
    score = 0.0

    # Only give bonus if poi1 comes BEFORE poi2 chronologically
    if poi1_before_poi2:
        score += 0.5  # Strong directional bonus
    elif same_period:
        score += 0.2  # Weak bonus for same period (order doesn't matter)
    else:
        score += 0.0  # No bonus for wrong direction

    # Same period and proximity are non-directional
    if same_period:
        score += 0.3
    if built_within_50_years:
        score += 0.2

    return score
```

**Benefits**:
- coherence(older→newer) > coherence(newer→older)
- No symmetric scores = no cycles
- Better reflects actual storytelling order
- Can re-enable precedence constraints if useful

**Option B: Keep Disabled**
- Current setting: `precedence_soft_threshold: 1.0` (disabled)
- Pro: Simple, no conflicts
- Con: Coherence calculation serves no purpose

**Option C: Use Coherence Only for Objective (Not Constraints)**
- Remove precedence constraints entirely
- Use coherence only in objective function to encourage thematic grouping
- Pro: Soft guidance without hard constraints
- Con: Less control over actual order

**Recommendation**: Implement **Option A** (directional coherence)
- Makes logical sense for storytelling
- Eliminates symmetric score problem
- Allows re-enabling precedence if desired
- More elegant solution than disabling entirely

**References**:
- See `COHERENCE_COMPLETE_EXPLANATION.md` for full analysis
- See `PRECEDENCE_CONSTRAINTS_EXPLAINED.md` for cycle problem details

**Acceptance Criteria**:
- [ ] Coherence scores are directional (A→B ≠ B→A)
- [ ] Older→Newer gets higher score than Newer→Older
- [ ] No symmetric high-coherence pairs (no cycles)
- [ ] Tests pass with precedence re-enabled (threshold 0.7)
- [ ] Combo tickets still work correctly
- [ ] Update documentation

---

### 2. 📝 Update Documentation for Coherence Changes

**Status**: 🔴 Not Started
**Priority**: Medium (after Task 1)
**Estimated Effort**: Low

**Files to Update**:
- `COHERENCE_COMPLETE_EXPLANATION.md` - Update with new directional logic
- `PRECEDENCE_CONSTRAINTS_EXPLAINED.md` - Update now that cycles are impossible
- `CONFIGURATION_CHANGES.md` - May be able to recommend 0.7 instead of 1.0

**Acceptance Criteria**:
- [ ] Documentation reflects new directional coherence
- [ ] Examples show asymmetric scores
- [ ] Configuration recommendation updated if precedence can be re-enabled

---

## Medium Priority Tasks

### 3. 🧪 Add Unit Tests for Coherence Calculation

**Status**: 🔴 Not Started
**Priority**: Medium
**Estimated Effort**: Medium

**What to Test**:
- [ ] Directional coherence (older→newer > newer→older)
- [ ] Same period bonus is symmetric (order doesn't matter)
- [ ] Date proximity bonus
- [ ] Edge cases (missing metadata, invalid dates, etc.)
- [ ] No cycles in high-coherence pairs

**Test File**: `tests/test_coherence_calculation.py` (create)

---

### 4. 🔍 Verify Combo Tickets Work Across All Cities

**Status**: 🟡 Partially Done (Rome tested)
**Priority**: Medium
**Estimated Effort**: Low

**Current Status**:
- ✅ Rome combo tickets tested and working
- ❓ Other cities not tested

**Cities to Test**:
- [ ] Athens (if has combo tickets)
- [ ] Paris (if has combo tickets)
- [ ] London (if has combo tickets)
- [ ] Other cities with combo_tickets.yaml

**Acceptance Criteria**:
- [ ] All combo ticket groups are on same day
- [ ] Solver returns FEASIBLE (not INFEASIBLE)
- [ ] Time windows respected

---

## Low Priority Tasks

### 5. 📊 Improve Position-Based Time Estimation

**Status**: 🔴 Not Started
**Priority**: Low
**Estimated Effort**: High

**Current Implementation**:
```python
# Line 533 in ilp_optimizer.py
estimated_arrival = start_time + (position * avg_position_duration)
```

**Issue**: Uses average duration for all positions (currently 110 min)

**Proposed Improvement**: Use actual POI durations
```python
estimated_arrival = start_time + sum(actual_durations[0:position]) + sum(walking_times[0:position])
```

**Complexity**: High - requires knowing which POI is at which position during constraint definition

**Benefits**: More accurate time window constraints

**Note**: Current approximation works well enough, so this is low priority

---

### 6. 🧹 Clean Up Debug/Test Files

**Status**: 🔴 Not Started
**Priority**: Low
**Estimated Effort**: Low

**Files to Clean**:
- [ ] test_tour_rome_20260227.py
- [ ] test_without_combo_constraints.py
- [ ] test_simple_combinations.py
- [ ] test_precedence_combo.py
- [ ] test_only_arch_pass.py
- [ ] test_minimal_combo.py
- [ ] test_incremental_pois.py
- [ ] test_debug_metadata.py
- [ ] test_without_channeling.py
- [ ] test_with_date.py
- [ ] diagnose_exact_conflict.py
- [ ] diagnose_position_blocking.py
- [ ] analyze_all_precedence.py
- [ ] explain_high_coherence.py

**Action**:
- Move to `tests/debug/` directory
- Or delete if no longer needed
- Keep only essential test files in root

---

## Completed Tasks ✅

### ✅ Fix Cyclic Precedence Constraints

**Completed**: 2026-02-28
**Solution**: Check only unique pairs (i < j) and pick stronger direction
**Files Modified**: `src/trip_planner/ilp_optimizer.py`
**Status**: ✅ Working - combo tickets now function correctly

### ✅ Fix Operation Hours Access Bug

**Completed**: 2026-02-28
**Solution**: Changed from `poi['metadata']['operation_hours']` to `poi['operation_hours']`
**Files Modified**: `src/trip_planner/ilp_optimizer.py`
**Status**: ✅ Working - time windows now apply correctly

### ✅ Fix Hardcoded 150-Minute Position Duration

**Completed**: 2026-02-28
**Solution**: Calculate average POI duration instead of hardcoded 150 min
**Files Modified**: `src/trip_planner/ilp_optimizer.py`
**Status**: ✅ Working - now uses 110 min average based on actual POIs

### ✅ Disable Precedence Constraints

**Completed**: 2026-02-28
**Solution**: Set `precedence_soft_threshold: 1.0` in config.yaml
**Status**: ✅ Working - combo tickets work without conflicts

---

## Branch Status

**Current Branch**: `debug/ilp-combo-tickets`
**Ready to Merge**: ✅ Yes (all combo ticket issues resolved)

**Next Steps**:
1. Merge to main (combo tickets working)
2. Create new branch for coherence optimization (Task 1)
3. Implement directional coherence
4. Test and merge

---

## Notes

- **Precedence constraints are currently disabled** (threshold 1.0)
- Can re-enable after implementing directional coherence (Task 1)
- All combo ticket functionality is working correctly
- Time window constraints are working correctly
- No blockers for merging current branch to main
