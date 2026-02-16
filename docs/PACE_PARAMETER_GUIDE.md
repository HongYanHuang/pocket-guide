# Trip Pace Parameter Guide

## Overview

The `pace` parameter controls how many POIs are included in the itinerary by adjusting the daily time budget.

## How It Works

### Time Budget Formula

```
Total POI Visit Time = duration_days × hours_per_day
Total Walking Time = duration_days × walking_buffer
```

### Pace Settings

| Pace | Hours/Day | Walking Buffer | Philosophy |
|------|-----------|----------------|------------|
| **Relaxed** | 6.0 | 1.5h/day | Quality over quantity, deeper experiences |
| **Normal** | 7.5 | 1.0h/day | Balanced schedule, reasonable pace |
| **Packed** | 9.0 | 0.5h/day | Maximize sightseeing, efficient transitions |

---

## Examples

### 3-Day Rome Trip

#### Relaxed Pace
```
POI Time Budget: 18 hours (6h/day)
Walking Budget: 4.5 hours (1.5h/day)
Expected POIs: ~6-9 POIs
Result: Deeper visits, more rest time
```

**Sample Day:**
- 09:00 - 12:00: Vatican Museums (3h)
- 12:00 - 13:30: Lunch break (1.5h)
- 13:30 - 14:00: Walk to St. Peter's (0.5h)
- 14:00 - 16:00: St. Peter's Basilica (2h)
- 16:00+: Free time/rest

#### Normal Pace
```
POI Time Budget: 22.5 hours (7.5h/day)
Walking Budget: 3 hours (1h/day)
Expected POIs: ~9-12 POIs
Result: Balanced experience
```

**Sample Day:**
- 09:00 - 11:30: Colosseum (2.5h)
- 11:30 - 12:00: Walk to Roman Forum (0.5h)
- 12:00 - 13:30: Roman Forum (1.5h)
- 13:30 - 14:30: Lunch (1h)
- 14:30 - 15:00: Walk to Palatine Hill (0.5h)
- 15:00 - 16:30: Palatine Hill (1.5h)
- 16:30 - 17:00: Walk to Trevi Fountain (0.5h)
- 17:00 - 17:30: Trevi Fountain (0.5h)

#### Packed Pace
```
POI Time Budget: 27 hours (9h/day)
Walking Budget: 1.5 hours (0.5h/day)
Expected POIs: ~12-15 POIs
Result: Maximum coverage, fast-paced
```

**Sample Day:**
- 08:30 - 11:00: Vatican Museums (2.5h)
- 11:00 - 11:20: Walk to St. Peter's (0.2h)
- 11:20 - 12:50: St. Peter's Basilica (1.5h)
- 12:50 - 13:30: Quick lunch (0.7h)
- 13:30 - 14:00: Walk to Castel Sant'Angelo (0.5h)
- 14:00 - 15:30: Castel Sant'Angelo (1.5h)
- 15:30 - 15:45: Walk to Pantheon (0.25h)
- 15:45 - 16:45: Pantheon (1h)
- 16:45 - 17:00: Walk to Trevi Fountain (0.25h)
- 17:00 - 17:30: Trevi Fountain (0.5h)
- 17:30 - 18:00: Walk to Spanish Steps (0.5h)
- 18:00 - 18:30: Spanish Steps (0.5h)

---

## Implementation Details

### POI Selector Agent

The pace parameter affects the AI prompt:

```python
if pace == 'relaxed':
    total_visit_hours = 6.0 * duration_days
    guidance = "Select FEWER POIs for deeper, more relaxed experiences."

elif pace == 'packed':
    total_visit_hours = 9.0 * duration_days
    guidance = "Maximize number of POIs visited."

else:  # normal
    total_visit_hours = 7.5 * duration_days
    guidance = "Balanced number of POIs."
```

### AI Prompt Impact

The AI receives:
```
SELECTION CRITERIA - TIME BUDGET:
- CRITICAL: Sum of all selected POI visit times should be ≤ 22.5 hours total
- This is 7.5 hours per day for 3 day(s) at normal pace
- PACE GUIDANCE: Balanced number of POIs with reasonable time at each location.
```

---

## Walking Tolerance Parameter

**Status:** Currently NOT implemented

The `walking_tolerance` parameter (low/moderate/high) is:
- ✅ Collected in the UI
- ✅ Passed to the backend
- ❌ **Not used** in POI selection or optimization

### Why?

Geographic clustering is complex and depends on:
- Actual POI locations (coordinates)
- City layout (neighborhoods, districts)
- Transportation availability
- Real-world walking distances

**Current Behavior:** The parameter is ignored. POIs are selected based on interests and time budget only.

**Future Enhancement:** Could be implemented with:
- Clustering algorithms in optimizer
- Maximum daily walking distance limits
- Neighborhood-based grouping preferences

---

## Usage

### CLI
```bash
./pocket-guide trip plan \
  --city rome \
  --days 3 \
  --pace relaxed \
  --walking moderate  # Currently has no effect
```

### Backstage UI
1. Navigate to "Generate Tour"
2. Select pace: Relaxed / Normal / Packed
3. Walking tolerance: (cosmetic only, no effect)

### API
```python
POST /api/tour/generate
{
  "city": "rome",
  "days": 3,
  "pace": "packed",      # ← This works!
  "walking": "moderate"   # ← This doesn't affect anything
}
```

---

## Tips for Users

### When to use Relaxed
- First-time visitors who want to savor experiences
- Traveling with children or elderly
- Interest in museums/galleries (need more time)
- Prefer photography and exploration
- Want flexibility and downtime

### When to use Normal
- General tourism
- Balanced mix of must-sees and leisure
- Moderate energy levels
- Standard vacation schedule

### When to use Packed
- Return visitors who want to see everything
- Short trips (1-2 days)
- High energy travelers
- "Checklist" style tourism
- Business trips with limited sightseeing time

---

## See Also

- [ILP Optimization Guide](ILP_OPTIMIZATION.md)
- [Combo Ticket Guide](../schemas/combo_ticket_schema.yaml)
- [CLI Documentation](../README.md)
