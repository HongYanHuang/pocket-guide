# Pocket Guide CLI Cheatsheet

Quick reference for all CLI commands in the Pocket Guide project.

## ⚠️ Important: How to Run Commands

All commands in this cheatsheet use `./pocket-guide` which must be run from the project root directory:

```bash
# Make sure you're in the project directory
cd /path/to/pocket-guide

# Run commands with ./
./pocket-guide poi research Rome --count 50
```

**Alternative: Add to PATH** (optional)
```bash
# Add project directory to PATH in ~/.zshrc or ~/.bashrc
export PATH="/path/to/pocket-guide:$PATH"

# Then you can run without ./
pocket-guide poi research Rome --count 50
```

---

## 🎯 Quick Start: Complete Workflow

```bash
# Step 1: Research POIs (AI discovers top attractions)
./pocket-guide poi research Rome --count 30 --provider anthropic
# ↓ Creates: poi_research/Rome/research_candidates.json

# Step 2: Check for duplicates (optional, skip for new cities)
./pocket-guide poi check-redundancy Rome
# ↓ Updates: research_candidates.json with skip:true for duplicates

# Step 3: Create input file (one POI name per line)
python3 extract_pois.py Rome > rome_pois.txt

# Step 4: Generate content (5-10 min per POI)
./pocket-guide poi batch-generate rome_pois.txt --city Rome
# ↓ Creates: content/rome/<poi-id>/{transcript.txt, summary.txt, metadata.json}
```

**That's it!** Now you have full tour guide content for your POIs.

---

## 📋 Table of Contents

- [Quick Start: Complete Workflow](#quick-start-complete-workflow)
- [Server Management](#server-management)
- [POI Research & Discovery](#poi-research--discovery)
- [POI Content Generation](#poi-content-generation)
- [Batch Operations](#batch-operations)
- [Trip Planning](#trip-planning)
- [Metadata Management](#metadata-management)
- [Utility Scripts](#utility-scripts)

---

## 🚀 Server Management

### Start Development Servers

```bash
# Start both backend and frontend (simple)
./start-dev.sh

# Start both servers in tmux (advanced)
./start-dev-tmux.sh

# Start backend only
source venv/bin/activate && python src/api_server.py

# Start frontend only
cd backstage && npm run dev
```

### Stop Development Servers

```bash
# Stop both servers
./stop-dev.sh

# Stop backend only
lsof -ti:8000 | xargs kill -9

# Stop frontend only
lsof -ti:5173 | xargs kill -9
```

### Access Points

- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173

---

## 🔍 POI Research & Discovery

### Research POIs for a City

Discover and research top POIs in a city using AI.

```bash
./pocket-guide poi research <city> [OPTIONS]

# Examples:
./pocket-guide poi research Paris --count 15
./pocket-guide poi research Tokyo --provider anthropic
./pocket-guide poi research Rome --count 50 --provider anthropic
```

**Options:**
- `--count`: Number of POIs to research (default: 10, recommended: ≤30 for faster results)
- `--provider`: AI provider (`anthropic`, `openai`, `google`)

**Output:**
- Creates `poi_research/<City>/research_candidates.json`
- Lists POI candidates with metadata (name, description, category, historical_period)

**⚠️ Note:**
- Counts >30 may take 90+ seconds due to large response generation
- Uses streaming API to prevent timeouts on large requests (count=50 works!)
- Dynamic token allocation: `count × 250 + 500` tokens

**What to do next?**

1. **Review the results:**
   ```bash
   cat poi_research/Rome/research_candidates.json | python3 -m json.tool
   ```

2. **Check for duplicates** (if you have existing POIs):
   ```bash
   ./pocket-guide poi check-redundancy Rome
   ```

3. **Create input file** with POI names (one per line):
   ```bash
   # Option A: Use the extraction script (recommended - fastest!)
   python3 extract_pois.py Rome > rome_pois.txt

   # Option B: Manually create the file
   cat > rome_pois.txt << EOF
   Colosseum
   Roman Forum
   Pantheon
   EOF
   ```

4. **Generate content** for all POIs:
   ```bash
   ./pocket-guide poi batch-generate rome_pois.txt --city Rome
   ```

### Check for Duplicates

Check if research candidates duplicate existing POIs.

```bash
./pocket-guide poi check-redundancy <city> [OPTIONS]

# Examples:
./pocket-guide poi check-redundancy Athens
./pocket-guide poi check-redundancy Istanbul --provider anthropic
```

**What it does:**
- Compares candidates against existing POIs in `content/<city>/`
- Marks duplicates with `skip: true` in research_candidates.json
- Shows unique POIs ready for generation

### Extract POI Names to Text File

Automatically extract POI names from research_candidates.json to create input file for batch generation.

```bash
python3 extract_pois.py <city> > <output_file>

# Examples:
python3 extract_pois.py Rome > rome_pois.txt
python3 extract_pois.py Athens > athens_pois.txt

# Include duplicates/skipped POIs
python3 extract_pois.py Istanbul --include-skipped > istanbul_all_pois.txt
```

**Options:**
- `--include-skipped`: Include POIs marked as duplicates (skip: true)

**What it does:**
- Reads `poi_research/<City>/research_candidates.json`
- Extracts POI names (one per line)
- By default, excludes duplicates (skip: true)
- Prints to stdout (use `>` to save to file)

**Output example** (rome_pois.txt):
```
Colosseum
Roman Forum
Pantheon
Vatican Museums
...
```

---

## 📝 POI Content Generation

### Generate Single POI

Generate tour guide content for one POI with full research.

```bash
./pocket-guide generate \
  --poi-name "Eiffel Tower" \
  --city "Paris" \
  --provider anthropic \
  --language English

# With custom description:
./pocket-guide generate \
  --poi-name "Colosseum" \
  --city "Rome" \
  --description "Ancient amphitheater, gladiator battles" \
  --provider openai
```

**Options:**
- `--poi-name`: POI name (required)
- `--city`: City name (optional but recommended)
- `--provider`: AI provider (`anthropic`, `openai`, `google`)
- `--description`: Brief POI description
- `--language`: Target language (default: English)
- `--skip-research`: Skip research phase (faster but less rich)
- `--force-research`: Force re-research even if cached

**Output:**
- `content/<city>/<poi-id>/transcript.txt` - Tour narration
- `content/<city>/<poi-id>/summary.txt` - Key points
- `content/<city>/<poi-id>/metadata.json` - Version history
- `poi_research/<City>/<poi_name>.yaml` - Research data (unless skipped)

---

## 🔄 Batch Operations

### Batch Generate POIs

Generate multiple POIs from a text file (one POI name per line).

```bash
./pocket-guide poi batch-generate <input_file> --city <city> [OPTIONS]

# Examples:
./pocket-guide poi batch-generate pois.txt --city Istanbul
./pocket-guide poi batch-generate paris_pois.txt --city Paris --provider anthropic
./pocket-guide poi batch-generate quick_batch.txt --city Athens --skip-research
```

**Input file format** (`pois.txt`):
```
Süleymaniye Mosque
Blue Mosque
Topkapı Palace
Basilica Cistern
```

**Options:**
- `--city`: City name (required)
- `--provider`: AI provider (`anthropic`, `openai`, `google`)
- `--skip-research`: Skip research for faster generation (NOT recommended)
- `--force`: Force regeneration even if content already exists

**Features:**
- ✅ **Resumes from failures** - Skips POIs that already have content (use `--force` to regenerate)
- Automatically skips POIs marked with `skip: true` in research_candidates.json
- Creates versioned content with generation records
- Calculates distances if Google Maps API is configured
- Shows progress bar with success/failure tracking
- ✅ **Smart verification loop** - Automatically improves transcript coverage (60-100%)
- ✅ **API retry logic** - Handles rate limits & connection errors (5 retries with exponential backoff)
- ✅ **100% reliability** - No more batch failures due to connection issues

**⚠️ Important:**
- By default, research IS generated (rich historical content)
- Use `--skip-research` only for testing or when research exists
- Each POI takes ~5-10 minutes with full research (11 API calls)
- Automatic 500ms delays prevent API rate limiting

**Resuming after failures:**
```bash
# If batch-generate fails midway, just run it again!
# It will automatically skip POIs that already have content
./pocket-guide poi batch-generate rome_pois.txt --city Rome

# Output example:
# ⊘ Colosseum (already exists, use --force to regenerate)
# ⊘ Roman Forum (already exists, use --force to regenerate)
# [cyan]Generating: Pantheon[/cyan]  ← Resumes from here

# To regenerate ALL POIs (create new versions):
./pocket-guide poi batch-generate rome_pois.txt --city Rome --force
```

---

## 🗺️ Trip Planning

### Plan a Trip Itinerary

Generate an optimized trip itinerary by selecting POIs and creating a day-by-day schedule.

```bash
./pocket-guide trip plan --city <city> --days <days> [OPTIONS]

# Examples:
./pocket-guide trip plan --city Rome --days 3 --interests history --interests architecture
./pocket-guide trip plan --city Athens --days 2 --interests mythology --pace relaxed --save
./pocket-guide trip plan --city Paris --days 5 --must-see "Eiffel Tower" --walking high --save
```

**Required Options:**
- `--city`: City name (e.g., Rome, Athens, Paris)
- `--days`: Number of days for the trip

**Optional:**
- `--interests`: User interests (can specify multiple: `--interests history --interests art`)
- `--provider`: AI provider for POI selection (`anthropic`, `openai`, `google`, default: anthropic)
- `--must-see`: POIs that must be included (can specify multiple)
- `--pace`: Trip pace (`relaxed`, `normal`, `packed`, default: normal)
- `--walking`: Walking tolerance (`low`, `moderate`, `high`, default: moderate)
- `--save`: Save the generated tour for later

**What it does:**

**Step 1: POI Selection (AI-powered)**
- Loads all available POIs for the city from `poi_research/`
- Sends POI list + user preferences to Claude
- AI selects 8-12 starting POIs that match your interests
- AI provides 2-3 backup POIs for each selected POI (alternatives if closed/crowded)
- AI lists rejected POIs with reasons why they weren't selected
- Dynamic token calculation: `poi_count × 150 + 1000` tokens

**Step 2: Itinerary Optimization**
- Arranges selected POIs into optimal daily schedule
- Minimizes walking distance between POIs
- Maximizes thematic coherence (similar POIs on same day)
- Respects time constraints (8 hours per day)
- Calculates walking times and distances

**Output:**
- Day-by-day itinerary with POI order, visit duration, walking times
- Optimization scores (distance, coherence, overall)
- If `--save` used: Creates tour in `tours/<city>/<tour-id>/`

**Example Output:**
```
✓ Selected 10 POIs for itinerary
  + 25 backup POIs available
  + 12 POIs rejected

Day 1 (7.5h total, 3.2km walking)
  1. Colosseum (2.5h)
  2. Roman Forum (2.0h) ← 10min walk
  3. Palatine Hill (1.5h) ← 5min walk

Day 2 (8.0h total, 4.1km walking)
  1. Pantheon (1.0h)
  2. Trevi Fountain (0.5h) ← 8min walk
  ...
```

**Saved Tour Structure:**
```
tours/rome/rome-tour-20260129-111100-aa7baf/
├── tour_v1_2026-01-29.json              # Day-by-day itinerary
├── generation_record_v1_2026-01-29.json # Selection transparency
└── metadata.json                         # Tour version history
```

**Generation Record Contains:**
```json
{
  "input_parameters": {
    "city": "Rome",
    "duration_days": 3,
    "interests": ["history", "architecture"],
    "preferences": {...}
  },
  "poi_selection": {
    "backup_pois": {
      "Colosseum": [
        {
          "poi": "Baths of Trajan",
          "similarity_score": 0.85,
          "reason": "Similar Roman imperial architecture, nearby location"
        }
      ]
    },
    "rejected_pois": [
      {
        "poi": "Modern Art Museum",
        "reason": "Not historical/architectural focus"
      }
    ],
    "total_backup_pois": 25,
    "total_rejected_pois": 12
  },
  "optimization_scores": {
    "distance_score": 0.85,
    "coherence_score": 0.92,
    "overall_score": 0.89
  }
}
```

### List Saved Tours

View all saved tours for a city.

```bash
./pocket-guide trip list --city <city>

# Examples:
./pocket-guide trip list --city Rome
./pocket-guide trip list --city Athens
```

**Output:**
- Tour ID, creation date, duration, interests
- Latest version for each tour

### Show Tour Details

Display full itinerary for a saved tour.

```bash
./pocket-guide trip show --tour-id <tour-id>

# Examples:
./pocket-guide trip show --tour-id rome-tour-20260129-111100-aa7baf
```

**Output:**
- Complete day-by-day itinerary
- POI details, walking times, daily totals
- User preferences and constraints

**Features:**
- ✅ **Full transparency** - See which POIs were selected, which are backups, which were rejected and why
- ✅ **Smart POI selection** - AI matches POIs to your interests and preferences
- ✅ **Backup POIs** - Alternative POIs that can substitute if needed (NOT in the tour)
- ✅ **Optimization** - Minimizes walking distance while maximizing thematic coherence
- ✅ **Versioning** - Each tour can have multiple versions with full history
- ✅ **Dynamic scaling** - Token allocation scales with POI count (efficient for small cities, handles large cities)

**⚠️ Requirements:**
- City must have POIs in `poi_research/<City>/` directory
- Run `./pocket-guide poi research <city> --count 30` first if needed
- Distance matrix improves optimization but is optional

---

## 📊 Metadata Management

### Collect Metadata for City

Fetch POI metadata (coordinates, hours, etc.) from Google Maps.

```bash
# Via API endpoint:
curl -X POST http://localhost:8000/cities/<city>/collect

# Examples:
curl -X POST http://localhost:8000/cities/paris/collect
curl -X POST http://localhost:8000/cities/athens/collect
```

**Requirements:**
- Google Maps API key configured in `config.yaml`

**Output:**
- Updates `content/<city>/<poi-id>/metadata.json` for each POI
- Fetches: coordinates, address, hours, ratings, etc.
- Calculates distance matrix between POIs

### Recollect Single POI

Re-fetch metadata for one POI:

```bash
curl -X POST http://localhost:8000/pois/<city>/<poi-id>/recollect

# Example:
curl -X POST http://localhost:8000/pois/athens/acropolis/recollect
```

### Verify Metadata Completeness

Check which POIs have complete/incomplete metadata:

```bash
curl http://localhost:8000/cities/<city>/verify

# Example:
curl http://localhost:8000/cities/istanbul/verify | python3 -m json.tool
```

---

## 🛠️ Utility Scripts

### Generate Missing Research Data

Backfill research YAML files for POIs created with `--skip-research`.

```bash
# Use the custom script:
python3 generate_missing_research.py

# Or create custom script for specific POIs:
python3 -c "
from src.research_agent import ResearchAgent
from src.utils import load_config
import yaml
from pathlib import Path

config = load_config()
agent = ResearchAgent(config)

# Generate research for one POI
data = agent.research_poi_recursive('POI Name', 'City', '', 'anthropic')

# Save to file
path = Path('poi_research/City/poi_name.yaml')
path.parent.mkdir(parents=True, exist_ok=True)
with open(path, 'w') as f:
    yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
"
```

---

## 📂 File Structure Reference

```
pocket-guide/
├── content/                    # Generated POI content
│   └── <city>/                 # City folder (kebab-case)
│       └── <poi-id>/           # POI folder (kebab-case)
│           ├── transcript.txt  # Tour narration
│           ├── summary.txt     # Key points (numbered)
│           ├── metadata.json   # Version history + metadata
│           └── generation_record_v*.json
│
├── poi_research/               # Research data
│   └── <City>/                 # City folder (TitleCase)
│       ├── research_candidates.json
│       └── <poi_name>.yaml     # Research YAML (snake_case)
│
├── poi_distances/              # Distance matrices
│   └── <city>_distances.json
│
└── backstage/                  # Admin frontend
    └── src/
        ├── views/
        │   ├── TranscriptView.vue    # View/edit transcripts
        │   └── ResearchView.vue      # View research data
        └── components/
            ├── ResearchStructured.vue
            └── ResearchRaw.vue
```

---

## 🔑 Common Workflows

### Workflow 1: Generate Content for New City

```bash
# 1. Research POIs (discover top attractions using AI)
./pocket-guide poi research "New York" --count 30 --provider anthropic

# Output: poi_research/New York/research_candidates.json
# Contains: 30 POI candidates with names, descriptions, categories, historical periods

# 2. Review the research results
cat poi_research/New\ York/research_candidates.json | python3 -m json.tool

# 3. Check for duplicates (skip if this is a brand new city)
./pocket-guide poi check-redundancy "New York"

# Output: Updates research_candidates.json with skip:true for duplicates
# Shows: Which POIs are unique vs. duplicates

# 4. Create input file with POI names (one per line)
# Option A: Use extraction script (recommended - extracts all unique POIs)
python3 extract_pois.py "New York" > nyc_pois.txt

# Option B: Manually create from research results
cat > nyc_pois.txt << EOF
Statue of Liberty
Central Park
Empire State Building
Brooklyn Bridge
Times Square
EOF

# 5. Batch generate content (5-10 min per POI with full research)
./pocket-guide poi batch-generate nyc_pois.txt --city "New York" --provider anthropic

# Features: Smart verification loop + API retry (100% reliability)
# Output: transcript.txt, summary.txt, metadata.json for each POI

# 6. Collect metadata (requires Google Maps API key in config.yaml)
curl -X POST http://localhost:8000/cities/new-york/collect

# Output: Adds coordinates, hours, ratings, distance matrix

# 7. View in backstage UI
./start-dev.sh
open http://localhost:5173
```

### Workflow 2: Add Single POI to Existing City

```bash
# Generate with full research
./pocket-guide generate \
  --poi-name "Notre-Dame Cathedral" \
  --city "Paris" \
  --provider anthropic

# Verify it was created
ls content/paris/notre-dame-cathedral/
```

### Workflow 3: View/Edit Content in Backstage

```bash
# 1. Start servers
./start-dev.sh

# 2. Open browser
open http://localhost:5173

# 3. Navigate to POI → Click "View Transcript" or "View Research"
# 4. Edit transcript → Auto-backup created before saving
```

### Workflow 4: Fix Missing Research Data

```bash
# If POIs were generated with --skip-research, backfill research:
python3 generate_missing_research.py

# Or generate for specific POI:
./pocket-guide generate \
  --poi-name "Existing POI" \
  --city "City" \
  --force-research  # Re-research even if content exists
```

### Workflow 5: Plan a Trip Itinerary

```bash
# 1. Ensure you have POIs researched for the city
./pocket-guide poi research Rome --count 50 --provider anthropic

# Output: poi_research/Rome/research_candidates.json with 50 POIs

# 2. Plan a trip with your preferences
./pocket-guide trip plan \
  --city Rome \
  --days 3 \
  --interests history \
  --interests architecture \
  --pace normal \
  --walking moderate \
  --save

# AI will:
# - Select 8-12 POIs matching your interests
# - Provide 25+ backup POIs (alternatives, NOT in tour)
# - List rejected POIs with reasons
# - Optimize daily schedule to minimize walking
# - Group similar POIs on same day

# Output example:
# ✓ Selected 10 POIs for itinerary
#   + 25 backup POIs available
#   + 15 POIs rejected
#
# Day 1 (7.5h total, 3.2km walking)
#   1. Colosseum (2.5h)
#   2. Roman Forum (2.0h) ← 10min walk
#   3. Palatine Hill (1.5h) ← 5min walk

# 3. View saved tours
./pocket-guide trip list --city Rome

# Output: List of all tours with IDs and dates

# 4. Show tour details
./pocket-guide trip show --tour-id rome-tour-20260129-111100-aa7baf

# 5. Review selection transparency (why POIs were chosen/rejected)
cat tours/rome/rome-tour-20260129-111100-aa7baf/generation_record_v1_2026-01-29.json | python3 -m json.tool

# Shows:
# - Input parameters (interests, preferences)
# - Backup POIs with similarity scores and reasons
# - Rejected POIs with rejection reasons
# - Optimization scores
```

---

## 🎯 Quick Tips

**Speed vs Quality:**
- ✅ **With research** (default): Rich content, 5-10 min per POI
- ⚡ **Without research** (`--skip-research`): Fast, 1-2 min per POI, basic content

**Provider Comparison:**
- **Anthropic (Claude)**: Best storytelling, most dramatic
- **OpenAI (GPT-4)**: Balanced, reliable
- **Google (Gemini)**: Fast, cost-effective

**File Naming:**
- Content directory: `kebab-case` (e.g., `blue-mosque`)
- Research directory: `snake_case` (e.g., `blue_mosque.yaml`)
- City folders: `kebab-case` in content, `TitleCase` in research

**Backup Safety:**
- Transcript edits create timestamped backups automatically
- Format: `transcript_backup_YYYYMMDD_HHMMSS.txt`

---

## 🆘 Troubleshooting

### "Module not found" errors

```bash
# Activate virtual environment first:
source venv/bin/activate
```

### "Research data not found"

```bash
# Check if research file exists:
ls poi_research/<City>/<poi_name>.yaml

# Generate if missing:
python3 generate_missing_research.py
```

### "Port already in use"

```bash
# Kill processes on ports 8000 (backend) and 5173 (frontend):
./stop-dev.sh
```

### View API logs

```bash
# Backend is running - check terminal output
# Or restart with verbose logging:
source venv/bin/activate
python src/api_server.py
```

### API Rate Limit or Connection Errors

✅ **Automatically handled!** The system now includes:
- 5 retry attempts with exponential backoff (1s, 2s, 4s, 8s, 16s)
- 500ms delay between all API calls to prevent rate limiting
- Automatic handling of 429 (rate limit) and 529 (overload) errors
- Connection error recovery

**If batch generation still fails:**
```bash
# Check your network connection
ping anthropic.com

# Verify API key is valid
python test-api-keys.py

# Try with a different provider
./pocket-guide poi batch-generate pois.txt --city City --provider google
```

---

## 📚 API Endpoints Reference

### Transcript Endpoints

```bash
# Get transcript + summary
GET /pois/{city}/{poi_id}/transcript

# Update transcript (creates backup)
PUT /pois/{city}/{poi_id}/transcript
  Body: {"transcript": "Updated text..."}
```

### Research Endpoints

```bash
# Get research data (structured + raw YAML)
GET /pois/{city}/{poi_id}/research
```

### Metadata Endpoints

```bash
# List cities
GET /cities

# List POIs in city
GET /cities/{city}/pois

# Get POI details
GET /pois/{city}/{poi_id}

# Update POI metadata
PUT /pois/{city}/{poi_id}/metadata

# Get distance matrix
GET /distances/{city}
```

**Test with curl:**

```bash
# Get transcript
curl http://localhost:8000/pois/athens/acropolis/transcript | python3 -m json.tool

# Get research
curl http://localhost:8000/pois/istanbul/hagia-sophia-grand-mosque/research | python3 -m json.tool

# Update transcript
curl -X PUT http://localhost:8000/pois/athens/acropolis/transcript \
  -H "Content-Type: application/json" \
  -d '{"transcript": "Updated tour content..."}'
```

---

## 🔗 Related Documentation

- **API Documentation**: http://localhost:8000/docs (when server is running)
- **Frontend Routes**:
  - `/` - Dashboard (POI list)
  - `/poi/:city/:poiId` - POI detail
  - `/poi/:city/:poiId/transcript` - Transcript viewer
  - `/poi/:city/:poiId/research` - Research viewer

---

**Last Updated**: December 2025
**Version**: 1.0.0

For more information, see the README or visit the API docs at http://localhost:8000/docs
