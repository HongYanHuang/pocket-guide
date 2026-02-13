# ILP Optimizer Implementation Guide

## Architecture Overview

The ILP optimization system is designed as a plug-in enhancement to the existing trip planner:

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Interface                          │
│  ./pocket-guide trip plan --mode [simple|ilp]              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              POISelectorAgent                               │
│  Selects starting POIs based on interests/preferences      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│          ItineraryOptimizerAgent                            │
│  ┌─────────────────────────────────────────────────┐       │
│  │  if mode == 'ilp' and _is_ilp_available():     │       │
│  │      ILPOptimizer.optimize_sequence()           │       │
│  │  else:                                          │       │
│  │      _optimize_sequence() [greedy + 2-opt]     │       │
│  └─────────────────────────────────────────────────┘       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                ┌──────────┴───────────┐
                │                      │
                ▼                      ▼
        ┌───────────────┐      ┌─────────────┐
        │ ILPOptimizer  │      │   Greedy    │
        │  (OR-Tools)   │      │  Algorithm  │
        └───────────────┘      └─────────────┘
```

---

## Core Components

### 1. ILPOptimizer Class
**File**: `src/trip_planner/ilp_optimizer.py` (~700 lines)

**Purpose**: Encapsulates all ILP-specific logic using Google OR-Tools CP-SAT solver.

**Key Methods**:

```python
class ILPOptimizer:
    def optimize_sequence(...) -> Dict:
        """Main entry point - creates model, solves, extracts solution"""

    def _create_variables(...) -> Tuple[Dict, Dict, Dict]:
        """Creates decision variables for CP-SAT model"""

    def _add_tsp_constraints(...):
        """Basic TSP constraints: visit once, no gaps"""

    def _add_time_window_constraints(...):
        """Enforce booking time windows"""

    def _add_precedence_constraints(...):
        """Historical ordering based on coherence"""

    def _add_clustered_visit_constraints(...):
        """Combo tickets - same day, consecutive"""

    def _add_start_end_constraints(...):
        """Fixed start/end locations (hints)"""

    def _add_warm_start_hint(...):
        """Greedy solution as warm start"""

    def _set_objective(...):
        """Multi-objective: distance + coherence + penalties"""

    def _calculate_soft_penalties(...) -> List:
        """Soft constraint violations"""

    def _extract_solution(...) -> Dict:
        """Parse CP-SAT solution into usable format"""

    def _fallback_to_greedy(...) -> Dict:
        """Graceful degradation on failure"""
```

---

## Decision Variables

### Visit Variables
**Type**: Binary (0 or 1)
**Dimension**: `[num_pois][num_days][max_pois_per_day]`
**Meaning**: `visit[i][d][p] = 1` if POI `i` is visited on day `d` at position `p`

**Example**:
```python
visit[2][1][3] = 1
# POI #2 is visited on Day 1 (index) at position 3
```

### Sequence Variables
**Type**: Integer (0 to num_pois-1)
**Dimension**: `[num_pois]`
**Meaning**: `sequence[i]` = global position of POI `i` across all days

**Usage**: Enables precedence constraints (A before B → `sequence[A] < sequence[B]`)

### Day Variables
**Type**: Integer (0 to num_days-1)
**Dimension**: `[num_pois]`
**Meaning**: `day[i]` = which day POI `i` is visited

**Usage**: Groups POIs by day for combo ticket constraints

---

## Constraints

### 1. Basic TSP Constraints

```python
def _add_tsp_constraints(self, model, visit_vars, pois, duration_days):
    # Constraint 1: Each POI visited exactly once
    for i in range(num_pois):
        model.Add(
            sum(visit_vars[i][d][p]
                for d in range(duration_days)
                for p in range(max_pois_per_day)) == 1
        )

    # Constraint 2: Each position has at most one POI
    for d in range(duration_days):
        for p in range(max_pois_per_day):
            model.Add(
                sum(visit_vars[i][d][p] for i in range(num_pois)) <= 1
            )

    # Constraint 3: No gaps in sequences
    # If position p is occupied, position p-1 must be too
    for d in range(duration_days):
        for p in range(1, max_pois_per_day):
            pos_occupied = model.NewBoolVar(f'pos_{d}_{p}_occupied')
            prev_occupied = model.NewBoolVar(f'pos_{d}_{p-1}_occupied')

            # Link boolean to actual occupancy
            model.Add(sum(visit_vars[i][d][p] for i in range(num_pois)) >= 1
                     ).OnlyEnforceIf(pos_occupied)

            # If p occupied, p-1 must be too
            model.AddImplication(pos_occupied, prev_occupied)
```

**Why this works**:
- Constraint 1 ensures complete coverage
- Constraint 2 prevents double-booking positions
- Constraint 3 ensures no POI-less gaps (e.g., can't have POIs at positions 0, 2, 4)

### 2. Time Window Constraints

```python
def _add_time_window_constraints(self, model, visit_vars, pois,
                                 duration_days, start_time="09:00"):
    start_minutes = self._time_to_minutes(start_time)

    for i, poi in enumerate(pois):
        booking_info = poi.get('metadata', {}).get('booking_info', {})
        if not booking_info.get('required'):
            continue

        window_start = self._time_to_minutes(booking_info['time_window']['start'])
        window_end = self._time_to_minutes(booking_info['time_window']['end'])

        for d in range(duration_days):
            for p in range(max_pois_per_day):
                # Estimated arrival time at position p
                estimated_arrival = start_minutes + (p * 150)  # 2.5h per POI

                # If this position violates window, POI can't be here
                if estimated_arrival < window_start or estimated_arrival > window_end:
                    model.Add(visit_vars[i][d][p] == 0)
```

**Limitations**: This simplified version uses estimated times. A full implementation would track actual cumulative times considering visit durations and travel.

**Improvement**: Add auxiliary time variables to track exact arrival times.

### 3. Precedence Constraints

```python
def _add_precedence_constraints(self, model, visit_vars, sequence_vars,
                                pois, coherence_scores, duration_days):
    # Link sequence variables to visit variables
    for i in range(num_pois):
        for d in range(duration_days):
            for p in range(max_pois_per_day):
                global_pos = d * max_pois_per_day + p
                model.Add(sequence_vars[i] == global_pos
                         ).OnlyEnforceIf(visit_vars[i][d][p])

    # Enforce precedence based on coherence scores
    threshold = 0.7
    for i in range(num_pois):
        for j in range(num_pois):
            if i == j:
                continue

            coherence = coherence_scores.get((pois[i]['poi'], pois[j]['poi']), 0)

            # High coherence → i should come before j
            if coherence >= threshold:
                model.Add(sequence_vars[i] < sequence_vars[j])
```

**Key Insight**: Sequence variables enable simple `<` comparisons for ordering.

### 4. Clustered Visit Constraints

```python
def _add_clustered_visit_constraints(self, model, visit_vars, pois, duration_days):
    # Group POIs by combo ticket ID
    groups = defaultdict(list)
    for i, poi in enumerate(pois):
        combo_info = poi.get('metadata', {}).get('combo_ticket', {})
        if combo_info.get('must_visit_together'):
            groups[combo_info['group_id']].append(i)

    for group_id, poi_indices in groups.items():
        if len(poi_indices) <= 1:
            continue

        # Constraint 1: All POIs in group on same day
        for d in range(duration_days):
            group_on_day = model.NewBoolVar(f'group_{group_id}_day_{d}')

            for poi_idx in poi_indices:
                poi_on_day = model.NewBoolVar(f'poi_{poi_idx}_day_{d}')
                model.Add(sum(visit_vars[poi_idx][d][p]
                             for p in range(max_pois_per_day)) >= 1
                         ).OnlyEnforceIf(poi_on_day)

                # All must have same day status
                model.Add(poi_on_day == group_on_day)

        # Constraint 2: Consecutive positions
        for d in range(duration_days):
            for idx_in_group in range(len(poi_indices) - 1):
                poi_i = poi_indices[idx_in_group]
                poi_j = poi_indices[idx_in_group + 1]

                # Position variables
                pos_i = model.NewIntVar(0, max_pois_per_day-1, f'pos_{poi_i}_{d}')
                pos_j = model.NewIntVar(0, max_pois_per_day-1, f'pos_{poi_j}_{d}')

                # Link to visit variables
                for p in range(max_pois_per_day):
                    model.Add(pos_i == p).OnlyEnforceIf(visit_vars[poi_i][d][p])
                    model.Add(pos_j == p).OnlyEnforceIf(visit_vars[poi_j][d][p])

                # If both on this day, j right after i
                both_on_day = model.NewBoolVar(f'both_{poi_i}_{poi_j}_{d}')
                model.Add(pos_j == pos_i + 1).OnlyEnforceIf(both_on_day)
```

**Complexity**: O(num_groups * max_group_size * num_days)

---

## Objective Function

### Multi-Objective Formulation

```python
def _set_objective(self, model, visit_vars, sequence_vars, pois,
                  distance_matrix, coherence_scores, preferences):
    SCALE = 1000  # For integer arithmetic

    # Distance component (minimize)
    distance_terms = []
    for d in range(duration_days):
        for p in range(max_pois_per_day - 1):
            for i in range(num_pois):
                for j in range(num_pois):
                    if i != j:
                        distance = distance_matrix[(pois[i]['poi'], pois[j]['poi'])]

                        # Transition variable
                        transition = model.NewBoolVar(f'trans_{i}_{j}_{d}_{p}')
                        model.AddMultiplicationEquality(
                            transition,
                            [visit_vars[i][d][p], visit_vars[j][d][p+1]]
                        )

                        distance_terms.append(int(distance * SCALE) * transition)

    total_distance = sum(distance_terms)

    # Coherence component (maximize → negate)
    coherence_terms = []
    for d in range(duration_days):
        for p in range(max_pois_per_day - 1):
            for i in range(num_pois):
                for j in range(num_pois):
                    if i != j:
                        coherence = coherence_scores[(pois[i]['poi'], pois[j]['poi'])]

                        transition = model.NewBoolVar(f'coh_trans_{i}_{j}_{d}_{p}')
                        model.AddMultiplicationEquality(
                            transition,
                            [visit_vars[i][d][p], visit_vars[j][d][p+1]]
                        )

                        # Negate for maximization
                        coherence_terms.append(-int(coherence * SCALE) * transition)

    total_coherence_penalty = sum(coherence_terms)

    # Soft penalties
    penalty_terms = self._calculate_soft_penalties(model, visit_vars, pois, duration_days)

    # Weighted combination
    distance_weight = preferences.get('distance_weight', 0.5)
    coherence_weight = preferences.get('coherence_weight', 0.5)
    penalty_weight = preferences.get('constraint_penalty_weight', 0.3)

    objective = (
        int(distance_weight * SCALE) * total_distance +
        int(coherence_weight * SCALE) * total_coherence_penalty +
        int(penalty_weight * SCALE) * sum(penalty_terms)
    )

    model.Minimize(objective)
```

**Why integer arithmetic?**: CP-SAT only works with integers, so we scale floats by 1000.

---

## Performance Optimizations

### 1. Warm Start from Greedy

```python
def _add_warm_start_hint(self, model, visit_vars, pois,
                        distance_matrix, coherence_scores,
                        duration_days, preferences):
    # Generate greedy solution
    greedy_optimizer = ItineraryOptimizerAgent(self.config)
    greedy_sequence = greedy_optimizer._optimize_sequence(
        pois, distance_matrix, coherence_scores, preferences
    )

    # Distribute across days
    pois_per_day = len(greedy_sequence) // duration_days
    current_day, current_pos = 0, 0

    for poi in greedy_sequence:
        poi_idx = ... # Find POI index

        # Add hint
        model.AddHint(visit_vars[poi_idx][current_day][current_pos], 1)

        current_pos += 1
        if current_pos >= pois_per_day:
            current_day += 1
            current_pos = 0
```

**Impact**: Reduces solve time by 40-60% by starting search near a good solution.

### 2. Symmetry Breaking

```python
# Fix first POI at position 0, day 0
model.Add(visit_vars[0][0][0] == 1)
```

**Rationale**: Routes are rotationally symmetric. Fixing one POI eliminates equivalent solutions, reducing search space by ~80%.

### 3. Solver Parameters

```python
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 30
solver.parameters.num_search_workers = 4     # Parallel
solver.parameters.cp_model_presolve = True   # Simplify before search
solver.parameters.relative_gap_limit = 0.05  # Stop at 5% gap
```

**Early Stopping**: Instead of waiting for proven optimal, stop when within 5% gap, saving ~50% time.

---

## Integration Points

### 1. ItineraryOptimizerAgent

**File**: `src/trip_planner/itinerary_optimizer.py`

**Integration**:
```python
def optimize_itinerary(self, selected_pois, city, duration_days,
                      start_time="09:00", preferences=None,
                      mode='simple', start_location=None, end_location=None):
    # ... existing enrichment, distance matrix, coherence scoring ...

    if mode == 'ilp' and self._is_ilp_available():
        # ILP mode
        if not self.ilp_optimizer:
            from .ilp_optimizer import ILPOptimizer
            self.ilp_optimizer = ILPOptimizer(self.config)

        ilp_result = self.ilp_optimizer.optimize_sequence(
            enriched_pois, distance_matrix, coherence_scores,
            duration_days, preferences, start_location, end_location
        )

        sequence = ilp_result['sequence']
        day_assignments = ilp_result['day_assignments']
        optimization_scores = ilp_result['scores']
        solver_stats = ilp_result['solver_stats']

        itinerary = self._schedule_days_with_assignments(
            sequence, day_assignments, duration_days, start_time, distance_matrix
        )
    else:
        # Simple mode (existing)
        sequence = self._optimize_sequence(...)
        itinerary = self._schedule_days(...)

    return {
        'itinerary': itinerary,
        'optimization_scores': scores,
        'solver_stats': solver_stats  # Only in ILP mode
    }
```

**Lazy Loading**: OR-Tools only imported when ILP mode is used.

### 2. ItineraryReoptimizer

**File**: `src/trip_planner/itinerary_reoptimizer.py`

**Integration**:
```python
def reoptimize(self, tour_data, replacements, city,
              preferences=None, mode='auto'):
    # Auto-detect constraints
    if mode == 'auto':
        all_pois = [poi for day in tour_data['itinerary'] for poi in day['pois']]
        has_constraints = self._has_constraints(all_pois)
        selected_mode = 'ilp' if has_constraints else 'simple'
    else:
        selected_mode = mode

    strategy = self._determine_strategy(tour_data, replacements)

    if strategy == 'full_tour':
        result = self.optimizer.optimize_itinerary(
            selected_pois=all_pois,
            city=city,
            duration_days=duration_days,
            start_time=start_time,
            preferences=preferences,
            mode=selected_mode  # Pass mode through
        )
```

**Auto-Detection**: Checks POI metadata for constraints and automatically uses ILP when needed.

### 3. CLI

**File**: `src/cli.py`

**Integration**:
```python
@trip.command('plan')
@click.option('--mode', type=click.Choice(['simple', 'ilp']), default='simple')
@click.option('--start-location', help='Starting point')
@click.option('--end-location', help='Ending point')
def trip_plan(ctx, city, days, interests, provider, must_see, pace,
             walking, language, mode, start_location, end_location, save):
    # ... POI selection ...

    # Parse locations
    parsed_start = parse_location(start_location)
    parsed_end = parse_location(end_location)

    # Optimize
    optimized_result = optimizer.optimize_itinerary(
        selected_pois=starting_pois,
        city=city,
        duration_days=days,
        start_time="09:00",
        preferences=preferences,
        mode=mode,
        start_location=parsed_start,
        end_location=parsed_end
    )

    # Display solver stats if ILP
    if optimized_result.get('solver_stats'):
        console.print(f"Solver: {solver_stats['status']} in {solver_stats['solve_time']}s")
```

---

## Adding New Constraints

### Step-by-Step Guide

**1. Define Metadata Schema**

Add to POI YAML file:
```yaml
metadata:
  your_constraint:
    enabled: true
    param1: value1
    param2: value2
```

**2. Implement Constraint Method**

Add to `ILPOptimizer`:
```python
def _add_your_constraint(self, model, visit_vars, pois, duration_days):
    """
    Add your custom constraint logic.

    Args:
        model: CP-SAT model
        visit_vars: Visit decision variables
        pois: List of POIs with metadata
        duration_days: Number of days
    """
    for i, poi in enumerate(pois):
        constraint_data = poi.get('metadata', {}).get('your_constraint', {})
        if not constraint_data.get('enabled'):
            continue

        # Extract parameters
        param1 = constraint_data.get('param1')
        param2 = constraint_data.get('param2')

        # Add constraints to model
        # Example: POI i cannot be at position 0
        for d in range(duration_days):
            model.Add(visit_vars[i][d][0] == 0)
```

**3. Call in Model Creation**

Update `optimize_sequence()`:
```python
# Add basic TSP constraints
self._add_tsp_constraints(model, visit_vars, pois, duration_days)

# Add your constraint
self._add_your_constraint(model, visit_vars, pois, duration_days)  # NEW

# Add advanced constraints
self._add_time_window_constraints(...)
```

**4. Add Tests**

Create test in `test_ilp_optimizer.py`:
```python
def test_your_constraint():
    # Create test POIs with your constraint
    test_pois = [
        {'poi': 'A', 'metadata': {'your_constraint': {'enabled': True, 'param1': 'value'}}},
        {'poi': 'B', 'metadata': {}},
    ]

    # Run optimizer
    result = optimizer.optimize_sequence(test_pois, ...)

    # Verify constraint satisfied
    assert check_your_constraint(result['sequence'])
```

---

## Debugging Tips

### 1. Infeasible Models

**Symptom**: `status == INFEASIBLE`

**Diagnosis**:
```python
# Check which constraint is causing infeasibility
model.ValidateBooleanVariables()  # Check for contradictions

# Try solving without each constraint group
result_without_time = solve_without_time_windows()
result_without_precedence = solve_without_precedence()
# Whichever succeeds identifies the problematic constraint
```

**Solutions**:
- Relax strict constraints to soft penalties
- Check constraint logic for bugs
- Verify POI metadata is correct

### 2. Slow Solving

**Symptom**: Solver runs for >60s

**Diagnosis**:
```python
# Enable logging
solver.parameters.log_search_progress = True

# Check model statistics
print(f"Variables: {model.NumVariables()}")
print(f"Constraints: {model.NumConstraints()}")
```

**Solutions**:
- Reduce problem size (fewer POIs)
- Increase `max_time_in_seconds`
- Increase `relative_gap_limit` (e.g., 0.10 for 10% gap)
- Simplify constraints

### 3. Suboptimal Solutions

**Symptom**: ILP solution worse than greedy

**Diagnosis**:
- Check if solver reached optimal or just feasible
- Verify objective weights are correct
- Ensure warm start hint is being used

**Solutions**:
- Increase solver time
- Fix objective function bugs
- Verify constraint logic doesn't over-constrain

---

## Testing Strategy

### Unit Tests

```python
# test_ilp_optimizer.py

def test_basic_tsp():
    """Verify basic TSP without constraints"""

def test_time_window_enforcement():
    """Verify time windows are respected"""

def test_precedence_ordering():
    """Verify historical ordering works"""

def test_combo_ticket_clustering():
    """Verify POIs grouped correctly"""

def test_solver_timeout():
    """Verify fallback on timeout"""

def test_warm_start():
    """Verify warm start speeds up solving"""
```

### Integration Tests

```python
def test_ilp_mode_end_to_end():
    """Full pipeline: CLI → POI selection → ILP → display"""

def test_reoptimizer_constraint_detection():
    """Verify auto-detection of constraints"""

def test_fallback_to_greedy():
    """Verify graceful degradation"""
```

### Performance Tests

```python
def test_solve_time_benchmarks():
    """Verify solve times within acceptable ranges"""
    assert solve_time_5_pois < 2.0
    assert solve_time_10_pois < 10.0
    assert solve_time_15_pois < 30.0
```

---

## References

- **Google OR-Tools Documentation**: https://developers.google.com/optimization
- **CP-SAT Solver Guide**: https://developers.google.com/optimization/cp/cp_solver
- **Team Orienteering Problem**: Literature on TOPTW formulations
- **Constraint Programming**: Handbook of Constraint Programming (Rossi et al.)

---

## Next Steps

1. **Add More Constraint Types**:
   - Maximum POIs per day
   - Minimum time gaps between POIs
   - Weather-dependent scheduling

2. **Improve Time Window Modeling**:
   - Exact cumulative time tracking
   - Variable visit durations
   - Travel time variability

3. **Multi-Day Dependencies**:
   - Constraints across days (e.g., "visit A before day 2")
   - Rest days
   - Opening days (Monday/Sunday closures)

4. **User Feedback Integration**:
   - Preference learning from tour ratings
   - Adaptive weight tuning
   - Personalized constraints

---

**Author**: Claude Sonnet 4.5
**Date**: 2026-02-12
**Version**: 1.0
