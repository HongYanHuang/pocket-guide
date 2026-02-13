# ILP Optimization Guide

## Overview

The Pocket Guide trip planner supports two optimization modes:

1. **Simple Mode** (default): Fast greedy algorithm with 2-opt improvements
2. **ILP Mode**: Integer Linear Programming using Google OR-Tools CP-SAT solver

ILP mode provides optimal solutions with support for advanced constraints like booking time windows, combo tickets, and historical ordering.

---

## When to Use ILP Mode

Use `--mode ilp` when you have:

### 1. **Time Windows (Booking Requirements)**
POIs that must be visited during specific time slots:
```bash
./pocket-guide trip plan --city Rome --days 3 --interests history --mode ilp
```

Example: Vatican Museums requires advance booking for 9:00-12:00 AM slots.

### 2. **Combo Tickets**
Multiple POIs that must be visited together on the same day:
- Colosseum + Roman Forum + Palatine Hill (archaeological pass)
- Museum passes with same-day entry requirements

### 3. **Storytelling Order**
When chronological historical flow is important:
- Ancient Rome → Medieval → Renaissance → Modern
- ILP enforces precedence constraints based on historical periods

### 4. **Complex Itineraries**
When you need:
- Optimal solutions (guaranteed best or within 5% of optimal)
- Fixed start/end locations
- Balance between multiple objectives

---

## Usage

### Basic Usage

```bash
# Simple mode (default - fast)
./pocket-guide trip plan --city Rome --days 3 --interests history

# ILP mode (optimal - slower)
./pocket-guide trip plan --city Rome --days 3 --interests history --mode ilp
```

### With Start/End Locations

```bash
# Start from hotel, end at airport
./pocket-guide trip plan --city Rome --days 3 \
  --mode ilp \
  --start-location "41.9028,12.4964" \
  --end-location "Fiumicino Airport"
```

### With Specific Start Date (Opening Hours)

```bash
# Plan trip starting March 15, 2026 (checks day-of-week opening hours)
./pocket-guide trip plan --city Rome --days 3 \
  --mode ilp \
  --start-date "2026-03-15"
```

**Why specify start date?**
- POIs have different opening hours on different days (Mon-Sat vs Sunday)
- Some museums closed on Mondays
- Restaurant hours vary by day of week
- The optimizer uses the actual day of week to check `operation_hours.periods`

### Performance

| POIs | Simple Mode | ILP Mode |
|------|------------|----------|
| 5    | <1s        | <2s      |
| 10   | <1s        | <10s     |
| 15   | <2s        | <30s     |
| 20+  | <3s        | May timeout, returns best found |

---

## Constraints

### Time Windows (Google Maps Format)

The optimizer uses **Google Maps Places API opening hours format** (`operation_hours.periods`) to enforce visit times. This format is automatically collected by the POI metadata agent.

#### Google Maps Opening Hours Format

```yaml
# poi_research/rome/vatican_museums.yaml
metadata:
  operation_hours:
    weekday_text:
      - "Monday: 8:00 AM – 8:00 PM"
      - "Tuesday: 8:00 AM – 8:00 PM"
      # ...
      - "Sunday: Closed"
    periods:
      - open:
          day: 1  # 0=Sunday, 1=Monday, ..., 6=Saturday
          time: "0800"  # HHMM format
        close:
          day: 1
          time: "2000"  # 8:00 PM
      - open:
          day: 2
          time: "0800"
        close:
          day: 2
          time: "2000"
      # ... more periods
```

#### Preferred Time Slots (Booking Requirements)

For POIs with advance booking, add preferred time slots:

```yaml
metadata:
  booking_info:
    required: true
    advance_booking_days: 7
    booking_url: https://example.com/book
    preferred_time_slots:
      - start: "08:00"
        end: "10:00"
        notes: "Best time to avoid crowds"
      - start: "10:00"
        end: "12:00"
        notes: "Moderate crowds"
```

**Effect**:
- POI will only be scheduled during opening hours (from `operation_hours.periods`)
- If `booking_info.required = true`, will prefer slots in `preferred_time_slots`
- Closed days (no periods for that day) are automatically excluded

**Example**: Vatican Museums
- Open Mon-Sat 8:00 AM - 8:00 PM, Closed Sunday
- Booking required with preferred slots 8-10 AM or 10 AM-12 PM
- Will be scheduled early in the day during preferred times

### Combo Tickets

POIs that must be visited together:

```yaml
# poi_research/rome/colosseum.yaml
metadata:
  combo_ticket:
    group_id: archaeological_pass_rome
    must_visit_together: true
    members:
      - Colosseum
      - Roman Forum
      - Palatine Hill
    max_separation_hours: 4
```

**Effect**: All three sites scheduled consecutively on the same day.

### Precedence (Storytelling Order)

Automatic precedence based on historical periods:
- POIs from earlier periods come before later periods
- Coherence score > 0.7 triggers precedence constraint

Explicit precedence can also be specified:

```yaml
metadata:
  precedence:
    must_visit_after:
      - "Roman Forum"
    must_visit_before:
      - "Trevi Fountain"
```

### Fixed Start/End

```bash
--start-location "Piazza Navona"
--end-location "41.8902,12.4922"  # Coordinates format: lat,lng
```

**Effect**: First POI will be close to start location, last POI close to end location.

---

## Configuration

### Optimization Settings

Edit `config.yaml`:

```yaml
optimization:
  # Enable ILP optimization (requires OR-Tools)
  ilp_enabled: true

  # Maximum solver time in seconds
  ilp_max_seconds: 30

  # Objective weights (sum should = 1.0)
  distance_weight: 0.5      # Minimize walking distance
  coherence_weight: 0.5     # Maximize storytelling flow

  # Constraint penalty weight
  constraint_penalty_weight: 0.3

  # Fallback to simple mode if ILP fails
  ilp_fallback_enabled: true

  # Soft constraint flexibility
  time_window_flexibility_minutes: 30
  precedence_soft_threshold: 0.7  # Coherence threshold for precedence
```

### Tuning for Different Use Cases

**Tourist (minimize walking)**:
```yaml
distance_weight: 0.7
coherence_weight: 0.3
```

**History buff (chronological order)**:
```yaml
distance_weight: 0.3
coherence_weight: 0.7
```

**Tight schedule (find optimal quickly)**:
```yaml
ilp_max_seconds: 60
relative_gap_limit: 0.10  # Stop within 10% of optimal
```

---

## How It Works

### 1. Problem Formulation

The trip planning problem is formulated as a **Team Orienteering Problem with Time Windows (TOPTW)**:

- **Decision Variables**: Binary variables `visit[poi][day][position]`
- **Objectives**: Minimize total distance + maximize coherence
- **Constraints**:
  - Visit each POI exactly once
  - No gaps in sequences
  - Respect time windows
  - Enforce precedence
  - Keep combo groups together

### 2. Solver Process

```
1. Generate greedy solution → use as warm start hint
2. Break symmetry by fixing first POI
3. CP-SAT solver searches for optimal solution
4. Stop when optimal found OR timeout OR within 5% gap
5. If solver fails → fallback to greedy algorithm
```

### 3. Performance Optimizations

- **Warm Start**: Greedy solution guides solver to good region quickly
- **Symmetry Breaking**: Reduces equivalent solutions by 80%
- **Parallel Search**: 4 worker threads explore solution space
- **Early Stopping**: Stops at 5% gap instead of waiting for proven optimal
- **Presolve**: Simplifies model before search

---

## Fallback Behavior

ILP mode gracefully degrades:

1. **Solver Timeout**: Returns best solution found so far
2. **Infeasible Constraints**: Relaxes constraints and retries
3. **OR-Tools Not Installed**: Falls back to simple mode with warning
4. **Config Disabled**: Uses simple mode even if `--mode ilp` specified

---

## Troubleshooting

### "ILP mode requested but not available"

**Cause**: OR-Tools not installed or `ilp_enabled: false` in config

**Solution**:
```bash
pip install ortools>=9.11.4210
# Edit config.yaml: set ilp_enabled: true
```

### "Solver failed with status INFEASIBLE"

**Cause**: Constraints are too strict (e.g., all POIs require same time window)

**Solutions**:
1. Use `flexible: true` in time_window constraints
2. Reduce precedence threshold in config
3. Remove conflicting constraints

### Slow Solving (>60s)

**Causes**:
- Too many POIs (>20)
- Complex constraints
- Tight time windows

**Solutions**:
1. Increase `ilp_max_seconds` in config
2. Relax constraints
3. Use simple mode for large problems
4. Split into multiple days

---

## Examples

### Example 1: Rome 3-Day Tour with Constraints

```bash
./pocket-guide trip plan \
  --city Rome \
  --days 3 \
  --interests history architecture \
  --mode ilp \
  --start-location "41.9028,12.4964" \
  --must-see "Vatican Museums" "Colosseum"
```

**Result**:
- Day 1: Vatican Museums (09:00-12:00 enforced)
- Day 2: Colosseum → Roman Forum → Palatine Hill (consecutive, same day)
- Chronological ordering within each day
- Starts near provided coordinates

### Example 2: Auto-Detection in Reoptimization

When replacing POIs, the system auto-detects constraints:

```python
# If any POI has constraints, ILP mode is used automatically
reoptimizer.reoptimize(
    tour_data=tour,
    replacements=[replacement],
    city='Rome',
    mode='auto'  # Auto-detects constraints
)
```

---

## Comparison: Simple vs ILP

| Feature | Simple Mode | ILP Mode |
|---------|------------|----------|
| Speed | Very fast (<3s) | Slower (5-30s) |
| Quality | Good (greedy + 2-opt) | Optimal or near-optimal |
| Time Windows | Not supported | ✅ Enforced |
| Combo Tickets | Not supported | ✅ Consecutive same-day |
| Precedence | Not supported | ✅ Historical order |
| Start/End | Not supported | ✅ Hints to solver |
| Dependencies | None | Requires OR-Tools |
| Fallback | N/A | Falls back to simple |

---

## Advanced: Custom Constraints

### Adding Custom Constraints

To add new constraint types:

1. **Update POI Metadata Schema**:
```yaml
metadata:
  your_constraint:
    enabled: true
    parameters: {...}
```

2. **Implement in ILPOptimizer**:
```python
def _add_your_constraint(self, model, visit_vars, pois):
    # Define decision variables
    # Add constraints to model
    # Return penalty variables (if soft)
```

3. **Call in Model Creation**:
```python
# In optimize_sequence()
self._add_your_constraint(model, visit_vars, pois)
```

4. **Test**:
```python
# Add test in test_ilp_optimizer.py
def test_your_constraint():
    # Verify constraint works
```

See `docs/ILP_IMPLEMENTATION.md` for developer guide.

---

## References

- [Google OR-Tools](https://developers.google.com/optimization)
- [CP-SAT Solver Documentation](https://developers.google.com/optimization/cp/cp_solver)
- [Team Orienteering Problem](https://en.wikipedia.org/wiki/Team_orienteering_problem)

---

**Next**: See `TRIP_PLANNER_USAGE.md` for general trip planning guide.
