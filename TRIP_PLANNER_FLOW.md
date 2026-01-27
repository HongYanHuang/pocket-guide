# Trip Planner Flow - How Interests Work

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│ USER INPUT                                                              │
│ ./pocket-guide trip plan --city Rome --days 3                          │
│   --interests history --interests architecture                         │
│   --pace normal --walking moderate                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 1: CLI COMMAND HANDLER (cli.py)                                   │
│                                                                         │
│ What it does:                                                          │
│ • Parses command line arguments                                        │
│ • Converts interests tuple → list: ['history', 'architecture']        │
│ • Packages preferences: {pace: 'normal', walking: 'moderate'}         │
│ • Prepares must_see and avoid lists                                    │
│                                                                         │
│ Output:                                                                │
│ • city = "Rome"                                                        │
│ • days = 3                                                             │
│ • interests = ['history', 'architecture']                             │
│ • preferences = {pace: 'normal', walking_tolerance: 'moderate'}       │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 2: LOAD AVAILABLE POIs (_load_city_pois)                         │
│                                                                         │
│ What it does:                                                          │
│ • Scans poi_research/Rome/ directory                                   │
│ • Reads ALL .yaml files (colosseum.yaml, roman_forum.yaml, etc.)      │
│ • Extracts POI metadata from research files:                           │
│   - name: "Colosseum"                                                  │
│   - description: "Ancient amphitheater..."                             │
│   - period: "Roman Empire (70-80 AD)"                                  │
│   - core_features: [architectural marvel, gladiator battles, ...]     │
│   - category: "monument"                                               │
│                                                                         │
│ Output:                                                                │
│ • available_pois = [                                                   │
│     {name: "Colosseum", period: "Roman Empire", ...},                 │
│     {name: "Roman Forum", period: "Roman Republic", ...},             │
│     {name: "Vatican Museums", period: "Renaissance", ...},            │
│     ... (20 POIs total)                                                │
│   ]                                                                     │
│                                                                         │
│ 💡 Note: At this stage, interests are NOT used yet!                   │
│    We just load ALL available POIs for the city.                      │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 3: BUILD AI PROMPT (_build_selection_prompt)                     │
│                                                                         │
│ What it does:                                                          │
│ • Creates a detailed prompt for the AI that includes:                  │
│                                                                         │
│   1. LIST OF ALL AVAILABLE POIs (formatted nicely):                   │
│      "1. Colosseum                                                     │
│          Description: Ancient amphitheater, gladiator contests...     │
│          Period: Roman Empire (70-80 AD)                               │
│          Features: 5 key features                                      │
│                                                                         │
│       2. Roman Forum                                                   │
│          Description: Heart of ancient Rome...                         │
│          Period: Roman Republic and Empire                             │
│          ..."                                                           │
│                                                                         │
│   2. USER PROFILE WITH INTERESTS:                                      │
│      "- Trip duration: 3 days                                          │
│       - Interests: history, architecture  ← YOUR INTERESTS HERE!      │
│       - Preferences:                                                   │
│         * Walking tolerance: moderate                                  │
│         * Trip pace: normal"                                           │
│                                                                         │
│   3. SELECTION CRITERIA (embeds interests):                            │
│      "- Match user interests: history, architecture                    │
│       - Balance famous must-sees with hidden gems                      │
│       - Consider geographic diversity                                  │
│       - Respect time budget (3 days = 24 hours activities)"           │
│                                                                         │
│   4. TASK INSTRUCTIONS:                                                │
│      "Select 8-12 Starting POIs that best match the user's profile"   │
│                                                                         │
│ Output:                                                                │
│ • A long text prompt containing all 20 POIs + user profile            │
│                                                                         │
│ 💡 Key: This is WHERE interests are injected into the AI context!     │
│    The AI will see: "Interests: history, architecture"                │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 4: AI POI SELECTION (_call_anthropic/openai/google)              │
│                                                                         │
│ What it does:                                                          │
│ • Sends prompt to AI (Anthropic Claude / OpenAI GPT / Google Gemini)  │
│ • AI reads all 20 POIs                                                 │
│ • AI analyzes which POIs match "history" and "architecture"            │
│                                                                         │
│ AI's Decision Process (conceptual):                                    │
│ • "Colosseum" - ✓ history (gladiators) + architecture (amphitheater)  │
│ • "Roman Forum" - ✓ history (Roman Republic) + some architecture      │
│ • "Pantheon" - ✓✓ architecture (dome) + history (temple)              │
│ • "Vatican Museums" - ✓ art + some history → maybe not perfect match  │
│ • "Trevi Fountain" - ✗ tourism but not strong history/architecture    │
│                                                                         │
│ AI selects POIs with:                                                  │
│ • High match to interests: history AND/OR architecture                 │
│ • Geographic diversity (not all in same area)                          │
│ • Time budget fit (can visit in 3 days)                               │
│ • Mix of famous + hidden gems                                          │
│                                                                         │
│ Output (JSON from AI):                                                 │
│ {                                                                       │
│   "starting_pois": [                                                   │
│     {                                                                   │
│       "poi": "Colosseum",                                              │
│       "reason": "Iconic Roman architecture, gladiator history",        │
│       "priority": "high",                                              │
│       "estimated_hours": 2.5                                           │
│     },                                                                  │
│     {                                                                   │
│       "poi": "Pantheon",                                               │
│       "reason": "Architectural marvel with 2000-year history",         │
│       "priority": "high",                                              │
│       "estimated_hours": 1.5                                           │
│     },                                                                  │
│     ... (10 more POIs selected)                                        │
│   ],                                                                    │
│   "backup_pois": {                                                     │
│     "Colosseum": [                                                     │
│       {"poi": "Roman Forum", "similarity": 0.85, ...},                │
│       {"poi": "Palatine Hill", "similarity": 0.80, ...}               │
│     ]                                                                   │
│   }                                                                     │
│ }                                                                       │
│                                                                         │
│ 💡 Key: AI filtered 20 POIs → 12 POIs based on your interests!        │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 5: PARSE & VALIDATE (_parse_and_validate)                        │
│                                                                         │
│ What it does:                                                          │
│ • Parses JSON response from AI                                         │
│ • Validates POI names exist in available_pois                          │
│ • Ensures backup POIs are valid                                        │
│ • Checks for required fields                                           │
│                                                                         │
│ Output:                                                                │
│ • selection_result = {                                                 │
│     starting_pois: [12 POIs selected by AI],                          │
│     backup_pois: {POI_name: [2-3 alternatives]},                      │
│     metadata: {interests, preferences, ...}                            │
│   }                                                                     │
│                                                                         │
│ 💡 From here, interests are stored in metadata but not actively used  │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 6: ENRICH POIs WITH METADATA (_enrich_pois_with_metadata)        │
│                                                                         │
│ What it does:                                                          │
│ • Takes 12 selected POIs (just names + basic info)                     │
│ • Loads FULL research data from poi_research/Rome/*.yaml               │
│ • Adds detailed info for optimization:                                 │
│   - period: "Roman Empire (70-80 AD)"                                  │
│   - date_built: "80 AD"                                                │
│   - coordinates: {lat: 41.890, lng: 12.492}                            │
│   - estimated_visit_duration: 2.5 hours                                │
│   - opening_hours: "9:00-19:00"                                        │
│   - category: "monument"                                               │
│                                                                         │
│ Output:                                                                │
│ • enriched_pois = [12 POIs with full metadata]                        │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 7: BUILD DISTANCE MATRIX (_build_distance_matrix)                │
│                                                                         │
│ What it does:                                                          │
│ • Loads rome_distances.json (pre-calculated distances)                 │
│ • Extracts walking distances between the 12 selected POIs              │
│                                                                         │
│ Example:                                                               │
│ • Colosseum → Roman Forum: 0.8 km, 10 min walk                        │
│ • Colosseum → Vatican: 4.5 km, 50 min walk                            │
│ • Roman Forum → Pantheon: 1.2 km, 15 min walk                         │
│                                                                         │
│ Output:                                                                │
│ • distance_matrix = {                                                  │
│     ('Colosseum', 'Roman Forum'): 0.8,  # km                          │
│     ('Colosseum', 'Vatican Museums'): 4.5,                            │
│     ...                                                                 │
│   }                                                                     │
│                                                                         │
│ 💡 Shorter distances = better for minimizing walking                  │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 8: CALCULATE COHERENCE SCORES (_calculate_coherence_scores)      │
│                                                                         │
│ What it does:                                                          │
│ • Analyzes STORYTELLING flow between POI pairs                         │
│ • Considers chronological order and thematic similarity                │
│                                                                         │
│ Scoring Logic:                                                         │
│ 1. Chronological Order (40%):                                          │
│    • Earlier period → Later period = +0.4                              │
│    • Example: Roman Republic (509 BC) → Roman Empire (27 BC)          │
│    • Visiting in historical order tells better story                   │
│                                                                         │
│ 2. Same Period (30%):                                                  │
│    • Both from "Roman Empire" period = +0.3                            │
│    • Thematically connected = easier to explain                        │
│                                                                         │
│ 3. Date Proximity (30%):                                               │
│    • Built within 100 years = +0.3                                     │
│    • Built within 500 years = +0.15                                    │
│                                                                         │
│ Example Scores:                                                        │
│ • Colosseum (80 AD) → Roman Forum (500 BC):                           │
│   Score = 0.0 (Forum is older, bad chronological flow)                │
│                                                                         │
│ • Roman Forum (500 BC) → Colosseum (80 AD):                           │
│   Score = 0.4 (good chronological flow) + 0.0 (different periods)     │
│   = 0.4 total                                                           │
│                                                                         │
│ • Pantheon (126 AD) → Colosseum (80 AD):                              │
│   Score = 0.0 (wrong order) + 0.3 (same period) + 0.3 (close dates)   │
│   = 0.6 total                                                           │
│                                                                         │
│ Output:                                                                │
│ • coherence_scores = {                                                 │
│     ('Roman Forum', 'Colosseum'): 0.4,                                │
│     ('Colosseum', 'Pantheon'): 0.6,                                   │
│     ...                                                                 │
│   }                                                                     │
│                                                                         │
│ 💡 Higher score = better storytelling flow                            │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 9: OPTIMIZE SEQUENCE (_optimize_sequence)                        │
│                                                                         │
│ What it does:                                                          │
│ • Finds the BEST ORDER to visit the 12 POIs                            │
│ • Uses greedy algorithm with hybrid scoring                            │
│                                                                         │
│ Algorithm:                                                             │
│ 1. Start with first POI (usually high priority)                        │
│ 2. For each remaining POI, calculate combined score:                   │
│    Score = (distance_score × 0.6) + (coherence_score × 0.4)           │
│                                                                         │
│    distance_score = inverted distance (closer = higher score)          │
│    coherence_score = from Step 8 (better story flow = higher)         │
│                                                                         │
│ 3. Pick POI with HIGHEST combined score                                │
│ 4. Repeat until all POIs ordered                                       │
│                                                                         │
│ Example Decision:                                                      │
│ Current POI: Colosseum                                                 │
│ Options:                                                               │
│ • Roman Forum:                                                         │
│   - Distance: 0.8km (very close) → distance_score = 0.9               │
│   - Coherence: 0.4 (good chronological) → coherence_score = 0.4       │
│   - Combined: (0.9 × 0.6) + (0.4 × 0.4) = 0.54 + 0.16 = 0.70         │
│                                                                         │
│ • Vatican Museums:                                                     │
│   - Distance: 4.5km (far) → distance_score = 0.3                      │
│   - Coherence: 0.8 (Renaissance after Roman) → coherence_score = 0.8  │
│   - Combined: (0.3 × 0.6) + (0.8 × 0.4) = 0.18 + 0.32 = 0.50         │
│                                                                         │
│ Winner: Roman Forum (0.70 > 0.50) → Visit next!                       │
│                                                                         │
│ Output:                                                                │
│ • optimized_sequence = [                                               │
│     "Roman Forum",     # Start (oldest)                                │
│     "Palatine Hill",   # Nearby, same period                           │
│     "Colosseum",       # Natural progression                           │
│     "Pantheon",        # Same era, short walk                          │
│     ...,                                                                │
│     "Vatican Museums"  # Different area, later period                  │
│   ]                                                                     │
│                                                                         │
│ 💡 Balances: Stay close (less walking) + Tell good story (chronology) │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 10: SCHEDULE INTO DAYS (_schedule_days)                          │
│                                                                         │
│ What it does:                                                          │
│ • Takes optimized sequence (12 POIs in order)                          │
│ • Divides into 3 days respecting time constraints                      │
│                                                                         │
│ Scheduling Rules:                                                      │
│ • Max 8 hours activities per day                                       │
│ • Start time: 09:00                                                    │
│ • Add visit duration + walking time                                    │
│ • Stop when day reaches 8 hours → start new day                        │
│                                                                         │
│ Example Calculation:                                                   │
│ Day 1:                                                                 │
│ • 09:00 - Roman Forum (1.5h) → ends 10:30                             │
│ • 10:30 - Walk 5min to Palatine Hill                                   │
│ • 10:35 - Palatine Hill (1.0h) → ends 11:35                           │
│ • 11:35 - Walk 10min to Colosseum                                      │
│ • 11:45 - Colosseum (2.5h) → ends 14:15                               │
│ • 14:15 - Walk 15min to Pantheon                                       │
│ • 14:30 - Pantheon (1.5h) → ends 16:00                                │
│ • Total: 7 hours (within 8 hour limit) ✓                              │
│                                                                         │
│ Day 2: Next POIs in sequence...                                        │
│ Day 3: Remaining POIs...                                               │
│                                                                         │
│ Output:                                                                │
│ • itinerary = [                                                        │
│     {                                                                   │
│       day: 1,                                                           │
│       pois: [                                                           │
│         {poi: "Roman Forum", visit_duration: 1.5h, walking_from_prev: 0},│
│         {poi: "Palatine Hill", visit_duration: 1.0h, walking_from_prev: 5min},│
│         {poi: "Colosseum", visit_duration: 2.5h, walking_from_prev: 10min},│
│         {poi: "Pantheon", visit_duration: 1.5h, walking_from_prev: 15min}│
│       ],                                                                │
│       total_hours: 7.0,                                                │
│       total_walking_km: 2.1                                            │
│     },                                                                  │
│     {day: 2, pois: [...], ...},                                        │
│     {day: 3, pois: [...], ...}                                         │
│   ]                                                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 11: CALCULATE FINAL SCORES (_calculate_scores)                   │
│                                                                         │
│ What it does:                                                          │
│ • Evaluates HOW GOOD the itinerary is                                  │
│                                                                         │
│ Metrics:                                                               │
│ 1. Distance Score (0.0-1.0):                                           │
│    • Measures walking efficiency                                       │
│    • Lower average distance = higher score                             │
│    • Formula: 1 - (avg_km_per_transition / 5.0)                       │
│    • Example: 1.5km average → 1 - (1.5/5) = 0.70                      │
│                                                                         │
│ 2. Coherence Score (0.0-1.0):                                          │
│    • Measures storytelling quality                                     │
│    • Average of all transition coherence scores                        │
│    • Example: avg 0.65 → 0.65 score                                    │
│                                                                         │
│ 3. Overall Score (0.0-1.0):                                            │
│    • Weighted average of both:                                         │
│    • (distance_score × 0.6) + (coherence_score × 0.4)                 │
│    • Example: (0.70 × 0.6) + (0.65 × 0.4) = 0.42 + 0.26 = 0.68       │
│                                                                         │
│ Output:                                                                │
│ • scores = {                                                           │
│     distance_score: 0.70,      # Good walking efficiency               │
│     coherence_score: 0.65,     # Decent story flow                     │
│     overall_score: 0.68        # Combined quality                      │
│   }                                                                     │
│                                                                         │
│ 💡 Higher score = better itinerary                                    │
│    0.8+ = Excellent, 0.6-0.8 = Good, <0.6 = Needs improvement         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ FINAL OUTPUT TO USER                                                   │
│                                                                         │
│ Day 1 (7.0h total, 2.1km walking)                                     │
│   1. Roman Forum (1.5h)                                                │
│   2. Palatine Hill (1.0h) ← 5min walk                                 │
│   3. Colosseum (2.5h) ← 10min walk                                    │
│   4. Pantheon (1.5h) ← 15min walk                                     │
│                                                                         │
│ Day 2 (7.8h total, 3.5km walking)                                     │
│   1. Capitoline Museums (2.0h)                                         │
│   2. Trevi Fountain (0.5h) ← 20min walk                               │
│   3. Spanish Steps (0.5h) ← 10min walk                                │
│   4. Vatican Museums (3.0h) ← 30min walk                              │
│   5. St. Peter's Basilica (1.5h) ← 5min walk                          │
│                                                                         │
│ Day 3 (6.5h total, 2.8km walking)                                     │
│   1. Castel Sant'Angelo (1.5h)                                         │
│   2. Piazza Navona (1.0h) ← 15min walk                                │
│   3. Baths of Caracalla (1.5h) ← 25min walk                           │
│   4. Galleria Borghese (2.0h) ← 20min walk                            │
│                                                                         │
│ Optimization Scores:                                                   │
│   Distance score: 0.70                                                 │
│   Coherence score: 0.65                                                │
│   Overall score: 0.68                                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Summary: How Interests Are Used

### Phase 1: POI Selection (Steps 1-5)
**Interests = PRIMARY FILTER**

Your interests `['history', 'architecture']` are:
1. **Embedded in AI prompt** (Step 3)
2. **Used by AI to filter POIs** (Step 4) - AI reads all 20 POIs and selects ~12 that best match "history" and "architecture"
3. **Stored in metadata** for reference

**Key Point:** Interests directly influence WHICH POIs are selected from the available 20.

### Phase 2: Itinerary Optimization (Steps 6-10)
**Interests = NO LONGER USED**

Once POIs are selected, optimization focuses on:
- **Geographic efficiency** (minimize walking)
- **Storytelling coherence** (chronological/thematic flow)
- **Time constraints** (fit within daily limits)

Interests are not consulted again because:
- POIs already match interests (pre-filtered by AI)
- Optimization is about ORDER and GROUPING, not selection

**Key Point:** Interests affect the INPUT (which POIs), not the optimization algorithm itself.

### If You Change Interests

**Example 1:** `--interests history`
- AI selects: Colosseum, Roman Forum, Pantheon (all historical)
- Skips: Modern museums, art galleries

**Example 2:** `--interests art --interests food`
- AI selects: Vatican Museums, Galleria Borghese, food markets
- Skips: Ancient ruins (less relevant to art/food)

**Example 3:** `--interests architecture`
- AI selects: Pantheon (dome), St. Peter's (baroque), Colosseum (engineering)
- Focuses on architectural significance over historical events

## Implementation Notes

**Where interests are used:**
- `_build_selection_prompt()` - Line 240: Embedded in user profile
- `_build_selection_prompt()` - Line 254: Embedded in selection criteria
- AI model processing - Pattern matching against POI descriptions

**Where interests are NOT used:**
- Distance matrix calculation
- Coherence score calculation
- Sequence optimization algorithm
- Day scheduling logic

**Why this design?**
- **Separation of concerns**: Selection (what) vs Optimization (how)
- **Reusability**: Same optimization works for any POI set
- **Flexibility**: Can manually adjust selected POIs without changing optimizer

