# Trip Planner CLI Usage Guide

The trip planner generates optimized day-by-day itineraries for your city tours.

## Quick Start

```bash
# Plan a 3-day trip to Rome with history interests
./pocket-guide trip plan --city Rome --days 3 --interests history --save

# Plan a relaxed 2-day trip with multiple interests
./pocket-guide trip plan --city Athens --days 2 \
  --interests architecture --interests art \
  --pace relaxed --walking low

# Plan with must-see POIs
./pocket-guide trip plan --city Istanbul --days 4 \
  --must-see "Hagia Sophia" --must-see "Blue Mosque" \
  --interests history --save
```

## Commands

### `trip plan` - Generate Optimized Itinerary

Creates an AI-optimized day-by-day itinerary based on your preferences.

**Required Options:**
- `--city TEXT` - City name (e.g., Rome, Athens, Istanbul)
- `--days INTEGER` - Number of days for the trip

**Optional Options:**
- `--interests TEXT` - Interests (can specify multiple)
  - Examples: `history`, `architecture`, `art`, `food`, `nature`
  - Use multiple: `--interests history --interests art`

- `--provider [openai|anthropic|google]` - AI provider for POI selection (default: anthropic)

- `--must-see TEXT` - POIs that must be included (can specify multiple)
  - Example: `--must-see "Colosseum" --must-see "Roman Forum"`

- `--pace [relaxed|normal|packed]` - Trip pace (default: normal)
  - `relaxed` - 2-3 POIs per day, more break time
  - `normal` - 3-4 POIs per day, balanced
  - `packed` - 4-6 POIs per day, intensive

- `--walking [low|moderate|high]` - Walking tolerance (default: moderate)
  - `low` - Minimize walking, prefer nearby POIs
  - `moderate` - Balanced walking distance
  - `high` - Comfortable with longer walks between POIs

- `--save` - Save the generated tour for later reference

**Example Output:**
```
Planning 3-day trip to Rome...

Step 1: Selecting POIs...
✓ Selected 12 POIs for itinerary
  + 8 backup POIs available

Step 2: Optimizing itinerary...
✓ Itinerary optimized
  Distance score: 0.85
  Coherence score: 0.78
  Overall score: 0.81

Day 1 (7.5h total, 3.2km walking)
  1. Colosseum (2.0h)
  2. Roman Forum (1.5h) ← 10min walk
  3. Palatine Hill (1.0h) ← 5min walk
  4. Capitoline Museums (2.0h) ← 15min walk

Day 2 (7.8h total, 4.1km walking)
  1. Vatican Museums (3.0h)
  2. St. Peter's Basilica (1.5h) ← 5min walk
  3. Castel Sant'Angelo (1.3h) ← 20min walk
  4. Piazza Navona (1.0h) ← 15min walk

...
```

### `trip list` - List Saved Tours

Shows all saved tours, optionally filtered by city.

```bash
# List all saved tours
./pocket-guide trip list

# List tours for specific city
./pocket-guide trip list --city Rome
```

**Output:**
```
Saved Tours
┏━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┓
┃ Tour ID        ┃ City ┃ Days ┃ Version ┃ Score ┃ Updated    ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━┩
│ rome_20260127  │ Rome │ 3    │ v1      │ 0.81  │ 2026-01-27 │
│ athens_user123 │ Athe │ 2    │ v2      │ 0.89  │ 2026-01-26 │
└────────────────┴──────┴──────┴─────────┴───────┴────────────┘

Total: 2 tour(s)
```

### `trip show` - Show Tour Details

Displays detailed information about a saved tour.

```bash
# Show latest version of a tour
./pocket-guide trip show rome_20260127 --city Rome

# Show specific version
./pocket-guide trip show rome_20260127 --city Rome --version 1
```

**Output:**
```
Tour: rome_20260127
City: Rome | Latest version

Optimization Scores:
  Distance: 0.85
  Coherence: 0.78
  Overall: 0.81

Day 1 (7.5h, 3.2km)
  1. Colosseum (2.0h)
  2. Roman Forum (1.5h) ← 10min walk
  3. Palatine Hill (1.0h) ← 5min walk
  ...
```

## How It Works

### Step 1: POI Selection (AI-Powered)

The POI Selector Agent uses AI to intelligently select POIs based on:
- Your interests and preferences
- Trip duration and pace
- Walking tolerance
- Must-see requirements

It selects:
- **Starting POIs**: Core itinerary POIs optimized for your preferences
- **Backup POIs**: Alternative options for flexibility

### Step 2: Itinerary Optimization

The Itinerary Optimizer creates the optimal day-by-day schedule by:
- **Minimizing walking distances** - Groups nearby POIs together
- **Maximizing storytelling coherence** - Arranges POIs in chronological/thematic order
- **Respecting time constraints** - Fits visits within daily time limits
- **Balancing days** - Distributes POIs evenly across days

The optimizer considers:
- Geographic proximity (from distance matrix)
- Historical periods and thematic connections
- Visit durations and opening hours
- Walking times between POIs

### Step 3: Tour Storage (Optional)

If you use `--save`, the tour is stored with:
- Versioning (v1, v2, v3...)
- Full audit trail
- Input parameters tracking
- Optimization scores

## Prerequisites

**Required:**
- POI content must exist for the city
- Distance matrix should be calculated (for optimal routing)

**Generate POIs first:**
```bash
# Research POIs
./pocket-guide poi research Rome --count 30

# Generate content
python3 extract_pois.py Rome > rome_pois.txt
./pocket-guide poi batch-generate rome_pois.txt --city Rome

# Calculate distances (optional but recommended)
curl -X POST http://localhost:8000/cities/rome/collect
```

## Tips

1. **Start with general interests**: Let the AI suggest POIs rather than over-specifying
2. **Use must-see sparingly**: Too many constraints limit optimization
3. **Match pace to reality**: Don't overpack - you'll want breaks!
4. **Save successful tours**: Use `--save` to keep tours you like
5. **Try different providers**: Anthropic, OpenAI, and Google may suggest different POIs

## Common Use Cases

**First-time visitor, general tourism:**
```bash
./pocket-guide trip plan --city Paris --days 4 --pace normal
```

**Architecture enthusiast:**
```bash
./pocket-guide trip plan --city Barcelona --days 3 \
  --interests architecture --walking high
```

**Family trip with young kids:**
```bash
./pocket-guide trip plan --city London --days 2 \
  --pace relaxed --walking low \
  --must-see "British Museum"
```

**Intensive history tour:**
```bash
./pocket-guide trip plan --city Rome --days 5 \
  --interests history --interests archaeology \
  --pace packed --walking high --save
```

## Troubleshooting

**"No POIs found for city"**
- Generate POI content first using `poi research` and `batch-generate`

**"Distance calculation failed"**
- Distance matrix missing - run metadata collection
- Or the optimizer will use estimated distances

**"POI not found in must-see list"**
- Check POI name matches exactly (case-sensitive)
- Use `./pocket-guide pois --city Rome` to see available POIs

## File Structure

Saved tours are stored in:
```
tours/
├── rome/
│   ├── rome_20260127/
│   │   ├── tour.json              # Latest version
│   │   ├── tour_v1_2026-01-27.json
│   │   ├── generation_record_v1_2026-01-27.json
│   │   └── metadata.json          # Version history
│   └── rome_user123/
│       └── ...
└── athens/
    └── ...
```

## Next Steps

After generating a trip plan:
1. Review the suggested POIs and daily schedule
2. Adjust if needed and regenerate with different parameters
3. Use the tour as a guide for your actual trip
4. Reference POI transcripts for detailed tour content

---

**Need help?** Run `./pocket-guide trip --help` for command reference.
