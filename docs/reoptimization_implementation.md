# POI Replacement Re-Optimization Implementation

## Overview

This document describes the implementation of the smart re-optimization system for POI replacements in the Pocket Guide application.

## Architecture

The re-optimization system uses a **3-tier strategy** that automatically selects the optimal algorithm based on the scope of changes:

### Tier 1: Local Swap
- **When**: Single POI replacement on a day with ≤5 POIs
- **Algorithm**: Position enumeration within the same day
- **Time**: ~0.1s
- **Use case**: Quick adjustments for small changes

### Tier 2: Day-Level Optimization
- **When**: Multiple replacements on 1-2 days
- **Algorithm**: Greedy nearest-neighbor + 2-opt improvement
- **Time**: ~0.3-0.5s
- **Use case**: Medium scope changes affecting specific days

### Tier 3: Full Tour Re-Optimization
- **When**: Replacements across 3+ days
- **Algorithm**: Full itinerary optimizer (existing `ItineraryOptimizerAgent`)
- **Time**: ~1-2s
- **Use case**: Major tour restructuring

## Components

### 1. ItineraryReoptimizer (`src/trip_planner/itinerary_reoptimizer.py`)

Main re-optimization engine that:
- Manages distance caching for performance
- Determines optimal strategy based on replacement scope
- Executes the selected optimization tier
- Tracks optimization history

**Key Methods:**
- `reoptimize()`: Main entry point
- `_determine_strategy()`: Selects Tier 1/2/3
- `_update_distance_cache()`: Incremental distance caching
- `_local_swap_optimization()`: Tier 1 implementation
- `_day_level_optimization()`: Tier 2 with greedy + 2-opt
- `_full_tour_optimization()`: Tier 3 full optimizer

### 2. API Integration (`src/api_server.py`)

Two endpoints support re-optimization:

#### Single POI Replacement
```python
POST /tours/{tour_id}/replace-poi
{
  "original_poi": "Theater of Marcellus",
  "replacement_poi": "Colosseum",
  "day": 1,
  "mode": "reoptimize",  # or "simple"
  "language": "en"
}
```

#### Batch POI Replacement
```python
POST /tours/{tour_id}/replace-pois-batch
{
  "replacements": [
    {"original_poi": "POI1", "replacement_poi": "POI2", "day": 1},
    {"original_poi": "POI3", "replacement_poi": "POI4", "day": 2}
  ],
  "mode": "reoptimize",  # or "simple"
  "language": "en"
}
```

**Updated Functions:**
- `reoptimize_with_replacement()`: Now uses `ItineraryReoptimizer`
- Batch endpoint: Passes all replacements to reoptimizer at once

### 3. Utility Functions (`src/utils.py`)

Added `load_poi_metadata_from_research()` for loading POI data from YAML files.

## Distance Caching Strategy

### Cache Structure
```python
tour_data['distance_cache'] = {
    ('POI1', 'POI2'): 1.2,  # km
    ('POI2', 'POI1'): 1.2,  # symmetric
    # ...
}
```

### Cache Updates
- **Incremental**: Only calculates distances for new POIs
- **Persistent**: Saved with tour data
- **Fallback**: Uses 2.0km default if coordinates missing

### Performance Benefits
- O(N) update instead of O(N²) recalculation
- Reused across multiple re-optimizations
- No external API calls (Haversine formula)

## 2-Opt Algorithm Details

The 2-opt algorithm improves tour sequences by swapping edges:

```
Original: A → B → C → D → E
Try swap: A → C → B → D → E (reverse B-C segment)
If shorter: Accept new sequence
```

**Implementation:**
- Maximum 10 iterations to prevent infinite loops
- Greedy edge swapping (accepts first improvement)
- Distance-based scoring using cached distances

## Optimization Metadata

Each re-optimization adds a history entry:

```json
{
  "reoptimization_history": [
    {
      "timestamp": "2026-02-10T14:30:00",
      "strategy_used": "day_level",
      "replacements": [
        {"original_poi": "POI1", "replacement_poi": "POI2", "day": 1}
      ],
      "scores": {
        "distance_score": 0.85,
        "coherence_score": 0.78,
        "overall_score": 0.81
      }
    }
  ]
}
```

## Testing

### Test Script: `test_reoptimizer.py`

Run tests:
```bash
python test_reoptimizer.py
```

The test script:
1. Loads an existing tour from `tours/` directory
2. Tests Tier 1: Single POI replacement
3. Tests Tier 2: Multiple replacements on same day (if available)
4. Tests Tier 3: Replacements across multiple days (if available)
5. Validates results and scores

### Expected Output
```
Testing with tour: rome-tour-20260205-121250-11edf4 in rome

Original tour:
  Days: 3
  Total POIs: 10
  Current score: 0.42

Test replacement:
  Original POI: Theater of Marcellus
  Replacement POI: Colosseum
  Day: 1

============================================================
TEST 1: Local Swap (Tier 1)
============================================================
  [CACHE] Updated distance cache, now has 20 entries
  [REOPTIMIZER] Using strategy: local_swap
  [TIER 1] Local swap optimization for day 1
  ✓ Local swap complete. Score: 0.61

Result:
  Strategy used: local_swap
  New score: 0.61 (improved from 0.42!)
  Distance score: 0.47
  Coherence score: 0.75
  Total distance: 16.0 km
```

## Frontend Integration (Planned)

The frontend needs to be updated to:

1. Add mode selector back to TourDetail.vue
2. Show estimated time for re-optimization
3. Display optimization strategy used
4. Show before/after scores

Example UI:
```vue
<el-radio-group v-model="saveMode">
  <el-radio-button label="simple">
    Simple Save (~0.1s)
  </el-radio-button>
  <el-radio-button label="reoptimize">
    Re-optimize Route (~0.5-2s)
  </el-radio-button>
</el-radio-group>
```

## Performance Benchmarks

Based on initial testing:

| Tier | Scope | POIs | Time | Quality |
|------|-------|------|------|---------|
| 1 | Single POI, small day | 3-5 | 0.1s | Good |
| 2 | 2 POIs, same day | 5-8 | 0.3s | Better |
| 3 | 3+ days affected | 10-20 | 1-2s | Best |

## Edge Cases Handled

1. **Missing Coordinates**: Uses 2.0km default distance
2. **Empty Distance Cache**: Initializes on first use
3. **Single POI Day**: Skips optimization (nothing to optimize)
4. **No Backups Available**: Returns 400 error
5. **Constraint Violations**: Falls back to full tour optimization

## Future Enhancements

### Phase 2: Integer Linear Programming (ILP)

For advanced constraint support:
- Time windows (booking times)
- Precedence constraints (storytelling order)
- Clustered visits (combo tickets)
- Fixed start/end points

**Implementation:**
- Use OR-Tools CP-SAT solver
- Add constraint modeling
- Handle multi-objective optimization
- Fallback to greedy+2-opt for simple cases

**Estimated Time:** 28-35 hours across 4 phases

### Other Improvements

- **Coherence Scoring**: Implement full coherence calculation in 2-opt
- **Parallel Processing**: Run multiple 2-opt iterations in parallel
- **Adaptive Thresholds**: Dynamically adjust tier selection based on results
- **Score Comparison UI**: Show before/after optimization scores

## References

### Algorithm Sources
- **2-opt Algorithm**: Classic TSP local search (Croes, 1958)
- **Greedy Nearest Neighbor**: TSP heuristic (Rosenkrantz et al., 1977)
- **Haversine Formula**: Great-circle distance calculation

### Related Files
- `src/trip_planner/itinerary_optimizer.py`: Original optimizer
- `src/trip_planner/itinerary_reoptimizer.py`: New reoptimizer
- `src/api_server.py`: API endpoints
- `src/utils.py`: Shared utilities
- `test_reoptimizer.py`: Test script

## Deployment Notes

### Prerequisites
- Python 3.9+
- Existing tour data in `tours/` directory
- POI research data in `poi_research/` directory

### Installation
No new dependencies required (uses existing packages).

### Configuration
No configuration changes needed.

### Backward Compatibility
- ✅ Simple mode still works (no re-optimization)
- ✅ Old tours without distance_cache still work
- ✅ API endpoints unchanged (mode parameter optional)

## Troubleshooting

### Issue: "No coordinates found"
**Cause**: POI research YAML missing coordinates
**Solution**: System uses 2.0km default distance (non-blocking)

### Issue: Score doesn't improve
**Cause**: Local optima or greedy algorithm limitations
**Solution**: Try Tier 3 (full tour) or accept current result

### Issue: Slow re-optimization
**Cause**: Large tour with many POIs
**Solution**: Normal for Tier 3; consider optimizing fewer days at once

## Changelog

### Version 1.0 (2026-02-10)
- ✅ Implemented 3-tier optimization strategy
- ✅ Added distance caching
- ✅ Integrated with API endpoints
- ✅ Created test script
- ✅ Documentation complete

### Future Versions
- 1.1: Frontend mode selector
- 1.2: Coherence scoring in 2-opt
- 2.0: ILP constraint support
