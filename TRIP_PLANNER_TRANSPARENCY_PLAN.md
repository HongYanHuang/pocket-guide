# Trip Planner Transparency Plan - See What AI Selected & Why

## Current Problem: Black Box Behavior

You ran trip planner and got a tour, but you can't see:
1. ❌ Which of the 47 Rome POIs were sent to Claude
2. ❌ Which POIs Claude selected vs discarded
3. ❌ What backup POIs Claude suggested
4. ❌ How optimizer ordered the selected POIs
5. ❌ Why optimizer made specific sequencing decisions

**Example from your tour:**
- **Input:** 47 Rome POIs available
- **Output:** 10 POIs in itinerary (Colosseum, Roman Forum, Pantheon...)
- **Missing:** What happened to the other 37 POIs? Why were they discarded?

## Analysis of Your Generated Tour

**Tour ID:** `rome-tour-20260127-172422-142114`

**Your Interests:**
```json
{
  "interests": [
    "architecture",
    "The-History-of-the-Decline-and-Fall-of-the-Roman-Empire"
  ]
}
```

**Selected POIs (10 total):**
1. Colosseum - "Iconic symbol of Roman Empire's architectural and engineering prowess"
2. Baths of Caracalla - "Colossal public bathing complex exemplifying imperial Rome"
3. Pantheon - "Architectural masterpiece of Hadrianic Rome"
4. Roman Forum - "Political heart of ancient Rome for 1000+ years"
5. Palatine Hill - "Imperial palace complex showing Rome's evolution"
6. Ara Pacis - "Augustan Age monument celebrating peace"
7. Castel Sant'Angelo - "Originally Hadrian's mausoleum"
8. Via Appia Antica - "Ancient Rome's first superhighway"
9. Basilica di San Clemente - "Time-machine church descending through 2000 years"
10. Capitoline Museums - "World's oldest museum housing ancient Roman sculptures"

**Missing Information:**
- ❌ Which 37 POIs were NOT selected?
- ❌ What backup POIs did Claude suggest?
- ❌ Why were these 10 chosen over others?

## What We Need to Add

### 1. POI Selection Transparency

**Save the complete selection response from Claude:**

```json
{
  "selection": {
    "total_pois_available": 47,
    "pois_sent_to_ai": ["Colosseum", "Roman Forum", ... all 47],
    "starting_pois": [
      {
        "poi": "Colosseum",
        "reason": "Iconic symbol...",
        "priority": "high",
        "estimated_hours": 2.5
      },
      ... (10 total)
    ],
    "backup_pois": {
      "Colosseum": [
        {
          "poi": "Circus Maximus",
          "similarity_score": 0.85,
          "reason": "Ancient entertainment venue, same period",
          "substitute_scenario": "If Colosseum is too crowded"
        }
      ]
    },
    "rejected_pois": [
      {
        "poi": "Vatican Museums",
        "reason": "Renaissance/Christian, doesn't match Roman Empire decline focus"
      },
      ... (37 total)
    ]
  }
}
```

**What this shows:**
- ✅ All 47 POIs that were sent to Claude
- ✅ Why each of the 10 were selected
- ✅ What backup alternatives exist
- ✅ Why the other 37 were NOT selected

### 2. Optimization Transparency

**Save the sequence optimization decisions:**

```json
{
  "optimization": {
    "initial_sequence": ["Roman Forum", "Palatine Hill", ...],
    "optimized_sequence": ["Colosseum", "Baths of Caracalla", ...],
    "optimization_steps": [
      {
        "step": 1,
        "action": "Started with Roman Forum (oldest period)",
        "reasoning": "Chronological storytelling: Republic → Empire"
      },
      {
        "step": 2,
        "action": "Next: Palatine Hill",
        "distance_score": 0.95,
        "coherence_score": 0.85,
        "combined_score": 0.91,
        "reasoning": "Very close (0.3km), same period, natural progression"
      },
      {
        "step": 3,
        "action": "Next: Colosseum",
        "distance_score": 0.88,
        "coherence_score": 0.70,
        "combined_score": 0.81,
        "reasoning": "Walking distance 0.8km, continues imperial Rome theme"
      }
    ],
    "alternatives_considered": [
      {
        "current_poi": "Palatine Hill",
        "options": [
          {"poi": "Colosseum", "score": 0.81, "chosen": true},
          {"poi": "Pantheon", "score": 0.65, "chosen": false, "reason": "Further away (2.5km)"},
          {"poi": "Vatican", "score": 0.45, "chosen": false, "reason": "Wrong period, far"}
        ]
      }
    ]
  }
}
```

**What this shows:**
- ✅ How optimizer ordered the 10 POIs
- ✅ Score calculation for each decision
- ✅ What alternatives were considered
- ✅ Why one option was chosen over another

### 3. Day Scheduling Transparency

**Save how POIs were divided into days:**

```json
{
  "scheduling": {
    "algorithm": "greedy_fill_8_hours_per_day",
    "days": [
      {
        "day": 1,
        "pois": ["Colosseum", "Baths of Caracalla", "Pantheon"],
        "reasoning": "Filled 7.0 hours (under 8 hour limit)",
        "attempts": [
          {
            "poi": "Castel Sant'Angelo",
            "attempted": true,
            "rejected": true,
            "reason": "Would exceed 8 hours (9.5 total)"
          }
        ]
      }
    ]
  }
}
```

## Implementation Plan

### Phase 1: Capture Selection Data (High Priority)

**File:** `src/trip_planner/poi_selector_agent.py`

**Changes needed:**

1. **Save raw AI response** (Line 108):
```python
# After parsing AI response
selection = self._parse_and_validate(response, available_pois)

# NEW: Save complete selection data
selection['raw_response'] = response  # Full JSON from Claude
selection['pois_sent_to_ai'] = [p['name'] for p in available_pois]
selection['total_pois_available'] = len(available_pois)

# NEW: Calculate rejected POIs
selected_names = {p['poi'] for p in selection['starting_pois']}
selection['rejected_pois'] = [
    {
        'poi': poi['name'],
        'period': poi.get('period'),
        'description_preview': poi.get('description', '')[:100]
    }
    for poi in available_pois
    if poi['name'] not in selected_names
]
```

2. **Save selection to tour generation record:**

**File:** `src/trip_planner/tour_manager.py` (Line 92-105)

```python
generation_record = {
    'version': version_num,
    'version_string': version_string,
    'timestamp': timestamp,
    'user_info': user_info or {'user_id': 'anonymous'},
    'input_parameters': input_parameters,

    # NEW: Add selection details
    'poi_selection': {
        'total_available': tour_data.get('selection_metadata', {}).get('total_pois_available'),
        'selected_count': len(tour_data.get('starting_pois', [])),
        'backup_count': len(tour_data.get('backup_pois', {})),
        'starting_pois': tour_data.get('starting_pois', []),
        'backup_pois': tour_data.get('backup_pois', {}),
        'rejected_pois': tour_data.get('rejected_pois', [])
    },

    'optimization_scores': tour_data.get('optimization_scores', {}),
    'constraints_violated': tour_data.get('constraints_violated', []),
    'metadata': tour_data.get('metadata', {}),
    'total_pois': len(tour_data.get('itinerary', [])),
    'total_days': len(tour_data.get('itinerary', []))
}
```

### Phase 2: Capture Optimization Steps (Medium Priority)

**File:** `src/trip_planner/itinerary_optimizer.py`

**Add tracking to `_optimize_sequence()` method:**

```python
def _optimize_sequence(self, pois, distance_matrix, coherence_scores, preferences):
    """Optimize POI sequence with detailed tracking"""

    optimization_log = {
        'initial_pois': [p['poi'] for p in pois],
        'steps': [],
        'alternatives_per_step': []
    }

    sequence = []
    remaining = pois.copy()

    # Start with first POI
    current = remaining.pop(0)
    sequence.append(current)

    optimization_log['steps'].append({
        'step': 1,
        'action': f"Started with {current['poi']}",
        'reasoning': "Initial POI (highest priority or chronologically first)"
    })

    # Greedy selection
    while remaining:
        # Calculate scores for all remaining POIs
        candidates = []

        for next_poi in remaining:
            dist_score = self._calc_distance_score(current, next_poi, distance_matrix)
            coh_score = coherence_scores.get((current['poi'], next_poi['poi']), 0.5)
            combined = (dist_score * 0.6) + (coh_score * 0.4)

            candidates.append({
                'poi': next_poi['poi'],
                'distance_score': dist_score,
                'coherence_score': coh_score,
                'combined_score': combined,
                'distance_km': distance_matrix.get((current['poi'], next_poi['poi']), 999)
            })

        # Sort by combined score
        candidates.sort(key=lambda x: x['combined_score'], reverse=True)

        # Choose best
        best = candidates[0]
        next_poi = next((p for p in remaining if p['poi'] == best['poi']), None)

        # Log decision
        optimization_log['steps'].append({
            'step': len(sequence) + 1,
            'from': current['poi'],
            'to': best['poi'],
            'distance_score': best['distance_score'],
            'coherence_score': best['coherence_score'],
            'combined_score': best['combined_score'],
            'distance_km': best['distance_km'],
            'reasoning': f"Best combined score ({best['combined_score']:.2f})"
        })

        # Log top 3 alternatives
        optimization_log['alternatives_per_step'].append({
            'after': current['poi'],
            'options': candidates[:3]  # Top 3
        })

        # Move to next
        remaining.remove(next_poi)
        sequence.append(next_poi)
        current = next_poi

    # Return both sequence and log
    return sequence, optimization_log
```

### Phase 3: CLI Output (Immediate - User-Facing)

**Add verbose output during trip planning:**

**File:** `src/cli.py` in `trip_plan` command:

```python
# After POI selection
console.print(f"[green]✓ Selected {len(starting_pois)} POIs for itinerary[/green]")
console.print(f"[dim]  + {len(backup_pois)} backup POIs available[/dim]")
console.print(f"[yellow]  - {len(available_pois) - len(starting_pois)} POIs not selected[/yellow]\n")

# Show selection breakdown
if len(starting_pois) > 0:
    console.print("[cyan]Selected POIs:[/cyan]")
    for poi_info in starting_pois:
        poi_name = poi_info.get('poi', 'Unknown')
        reason = poi_info.get('reason', 'N/A')
        priority = poi_info.get('priority', 'medium')

        # Color by priority
        priority_color = {"high": "green", "medium": "yellow", "low": "dim"}
        console.print(f"  [{priority_color.get(priority, 'white')}]● {poi_name}[/{priority_color.get(priority, 'white')}] - {reason[:80]}...")

# Show rejected POIs (first 5)
console.print(f"\n[dim]Not selected (showing first 5 of {len(rejected_pois)}):[/dim]")
for rejected in rejected_pois[:5]:
    console.print(f"  [dim]○ {rejected['poi']} ({rejected.get('period', 'unknown')})[/dim]")

console.print(f"\n[dim]💡 Full selection details saved in generation record[/dim]")
```

### Phase 4: Analysis Commands (Low Priority)

**Add CLI commands to analyze tours:**

```bash
# Show selection details
./pocket-guide trip analyze <tour_id> --city Rome --section selection

# Show optimization steps
./pocket-guide trip analyze <tour_id> --city Rome --section optimization

# Compare alternative sequences
./pocket-guide trip compare-sequences <tour_id1> <tour_id2> --city Rome
```

## Expected Output After Implementation

### During Trip Planning:

```
Planning 3-day trip to Rome...

Step 1: Selecting POIs...
  [POI SELECTOR] Loading POIs for Rome...
  [POI SELECTOR] Found 47 POIs
  [POI SELECTOR] Sending all 47 POIs to anthropic...
  [POI SELECTOR] Calling anthropic API for selection...
  [POI SELECTOR] Parsing AI response...
  ✓ Selected 10 Starting POIs
  ✓ Generated 20 Back-up POIs
  - 37 POIs not selected

Selected POIs:
  ● Colosseum (high) - Iconic symbol of Roman Empire's architectural...
  ● Roman Forum (high) - Political heart of ancient Rome for 1000+ years...
  ● Pantheon (high) - Architectural masterpiece of Hadrianic Rome...
  ● Baths of Caracalla (medium) - Colossal public bathing complex...
  [... 6 more]

Not selected (showing first 5 of 37):
  ○ Vatican Museums (Renaissance to Modern)
  ○ St. Peter's Basilica (Renaissance - Baroque)
  ○ Sistine Chapel (Renaissance)
  ○ Trevi Fountain (Baroque Period)
  ○ Spanish Steps (Baroque Period)

💡 Full selection details saved in generation record

Step 2: Optimizing itinerary...
  [OPTIMIZER] Loading metadata for 10 POIs...
  [OPTIMIZER] Calculating distances...
  [OPTIMIZER] Analyzing storytelling coherence...
  [OPTIMIZER] Optimizing sequence...
    → Start: Roman Forum (chronologically oldest)
    → Next: Palatine Hill (score: 0.91 - very close, same period)
    → Next: Colosseum (score: 0.81 - close distance, continues theme)
    → Next: Baths of Caracalla (score: 0.75 - same empire period)
    [... 6 more steps]
  [OPTIMIZER] Scheduling into 3 days...
  ✓ Optimized itinerary created
  ✓ Distance score: 0.40, Coherence: 0.43

[Itinerary display...]
```

### In generation_record.json:

```json
{
  "poi_selection": {
    "total_available": 47,
    "selected_count": 10,
    "backup_count": 20,
    "starting_pois": [
      {
        "poi": "Colosseum",
        "reason": "Iconic symbol of Roman Empire's architectural...",
        "priority": "high",
        "estimated_hours": 2.5,
        "matches_interests": ["architecture", "Roman-Empire-decline"]
      }
    ],
    "backup_pois": {
      "Colosseum": [
        {
          "poi": "Circus Maximus",
          "similarity_score": 0.85,
          "reason": "Ancient entertainment venue...",
          "substitute_scenario": "If Colosseum too crowded"
        }
      ]
    },
    "rejected_pois": [
      {
        "poi": "Vatican Museums",
        "period": "Renaissance to Modern",
        "reason_not_selected": "Focus on Roman Empire decline, not Renaissance"
      },
      ... (36 more)
    ]
  },
  "optimization": {
    "sequence_steps": [
      {
        "step": 1,
        "from": "Roman Forum",
        "to": "Palatine Hill",
        "distance_km": 0.3,
        "distance_score": 0.95,
        "coherence_score": 0.85,
        "combined_score": 0.91,
        "alternatives": [
          {"poi": "Colosseum", "score": 0.82},
          {"poi": "Pantheon", "score": 0.65}
        ]
      }
    ]
  }
}
```

## Priority Recommendation

**Implement in this order:**

1. **✅ Phase 3 First** (1-2 hours) - Immediate user feedback
   - Add console output showing selected vs rejected POIs
   - Add optimization step logging to console
   - User can see what's happening right away

2. **✅ Phase 1 Second** (2-3 hours) - Data capture
   - Save selection details to generation_record.json
   - Track rejected POIs
   - Save backup POIs

3. **⏳ Phase 2 Later** (3-4 hours) - Optimization transparency
   - Add optimization step tracking
   - Save alternatives considered
   - Show why sequences were chosen

4. **⏳ Phase 4 Future** (4-6 hours) - Analysis tools
   - CLI commands to analyze tours
   - Comparison tools
   - Visualization

## Your Specific Questions Answered

### Q1a: If these 47 all send into the prompt?

**Answer:** YES, all 47 POIs are loaded and sent to Claude.

**Proof in code:**
```python
# poi_selector_agent.py, line 128-181
def _load_city_pois(self, city: str):
    for yaml_file in poi_research_dir.glob("*.yaml"):
        # Loads ALL .yaml files in poi_research/Rome/
        pois.append(poi_summary)
    return pois  # Returns all 47

# poi_selector_agent.py, line 85-93
prompt = self._build_selection_prompt(
    available_pois=available_pois  # All 47 sent here
)

# poi_selector_agent.py, line 200-211
pois_formatted = "\n\n".join(poi_list)  # All 47 formatted
prompt = f"""...
AVAILABLE POIs IN {city.upper()}:
{pois_formatted}  # ← All 47 in prompt
..."""
```

### Q1b: Who is selected?

**Answer:** Claude selected these 10 POIs:
1. Colosseum
2. Roman Forum
3. Palatine Hill
4. Pantheon
5. Baths of Caracalla
6. Ara Pacis
7. Castel Sant'Angelo
8. Via Appia Antica
9. Basilica di San Clemente
10. Capitoline Museums

**Why these 10?** Match your interests:
- Architecture: Colosseum, Pantheon, Baths
- Roman Empire Decline: Roman Forum, Palatine Hill, Ara Pacis

**Not selected (37 POIs):** Probably includes Vatican, Renaissance churches, Baroque fountains, modern museums - things that don't match "Roman Empire decline" focus

### Q1c: Did AI return some candidate?

**Answer:** YES, but we don't currently save them!

Claude returns:
- **Starting POIs:** 10 selected
- **Backup POIs:** 2-3 alternatives for each Starting POI (20-30 total)

**But current code doesn't save backup POIs to generation_record!** Only to temporary variable.

### Q2: How did optimizer turn these into sequence?

**Current algorithm (simplified):**

```python
1. Start with first POI (Roman Forum - oldest)

2. For each remaining POI, calculate:
   - Distance score: closer = higher (0.0-1.0)
   - Coherence score: better story flow = higher (0.0-1.0)
   - Combined: (distance × 0.6) + (coherence × 0.4)

3. Pick POI with highest combined score

4. Repeat until all POIs ordered

5. Divide into days (8 hours max per day)
```

**Example decisions (reconstructed from your tour):**

Step 1: Start with Roman Forum (oldest period)
Step 2: Next → Palatine Hill (0.3km away, same period) score: ~0.90
Step 3: Next → Colosseum (0.8km away, continues empire) score: ~0.80
...

**But we don't currently save these decisions!**

## Summary

**What you found:**
- ✅ Tour works
- ❌ Can't see what was selected vs rejected
- ❌ Can't see why optimizer made decisions

**What we need:**
- ✅ Save selection details (47 sent, 10 selected, 37 rejected, backup POIs)
- ✅ Save optimization steps (why this order)
- ✅ Show it in CLI output
- ✅ Save to generation_record.json

**Next step:** Want me to implement Phase 1 + Phase 3 now?

