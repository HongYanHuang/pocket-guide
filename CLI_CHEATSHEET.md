# Pocket Guide CLI Cheatsheet

Quick reference for the Pocket Guide CLI - optimized for readability and quick lookup.

---

## 🚀 Quick Start

### Complete Workflow (30 minutes)

```bash
# 1. Research POIs (AI discovers attractions)
./pocket-guide poi research Rome --count 30

# 2. Check for duplicates (auto-marks skip: true)
./pocket-guide poi check-redundancy Rome

# 3. Extract unique POI names to file
python3 extract_unique_pois.py rome > unique_pois_rome.txt

# 4. Generate content (5-10 min per POI)
./pocket-guide poi batch-generate unique_pois_rome.txt --city Rome

# 5. Plan a trip (choose optimization mode)
./pocket-guide trip plan --city Rome --days 3 --interests history --mode simple --save

# 6. Generate audio for tour (optional)
./pocket-guide trip tts <tour-id> --city Rome --language zh-tw
```

**That's it!** You now have a complete tour guide with optimized itinerary and optional audio narration.

---

## 📚 Table of Contents

- [Quick Decision Guide](#-quick-decision-guide)
- [Server Management](#-server-management)
- [POI Operations](#-poi-operations)
- [Trip Planning](#-trip-planning)
- [Common Workflows](#-common-workflows)
- [Troubleshooting](#-troubleshooting)
- [Appendix: Workflow Diagrams](#-appendix-workflow-diagrams)

---

## 🎯 Quick Decision Guide

### Which Trip Planning Mode Should I Use?

```bash
# ✅ MOST USERS: Use Simple Mode (fast, 95-98% optimal)
./pocket-guide trip plan --city Rome --days 3 --mode simple --save

# 🏆 PERFECTIONISTS: Use ILP Mode (slower, mathematically optimal)
./pocket-guide trip plan --city Rome --days 5 --mode ilp --save
```

**Simple Mode** = Greedy algorithm + 2-opt (1-5 seconds)
**ILP Mode** = Integer Linear Programming (10-60 seconds)

### Which TTS Provider Should I Use?

```bash
# 🆓 FREE + FAST: EdgeTTS (cloud, may have blocking issues)
trip tts <tour-id> --city rome --provider edge

# 🆓 FREE + CUSTOMIZABLE: Qwen3-TTS (local, Taiwan accent, emotion control)
trip tts <tour-id> --city rome --provider qwen

# 💰 PAID: OpenAI (premium quality)
trip tts <tour-id> --city rome --provider openai
```

**EdgeTTS** = Free, fast, cloud
**Qwen3-TTS** = Free, local, natural Taiwan accent (configure in config.yaml)
**OpenAI/Google** = Paid, premium quality

---

## 🖥️ Server Management

### Start/Stop Development Servers

```bash
# Start both backend + frontend
./start-dev.sh

# Stop both servers
./stop-dev.sh
```

**Access:**
- Backend API: http://localhost:8000/docs
- Frontend: http://localhost:5173

---

## 🔍 POI Operations

### Research POIs

Discover top attractions using AI.

```bash
./pocket-guide poi research <city> --count <number>

# Examples
./pocket-guide poi research Paris --count 20
./pocket-guide poi research Tokyo --count 50 --provider anthropic
```

**Output:** `poi_research/<City>/research_candidates.json`

**Next steps:**
1. Check duplicates: `./pocket-guide poi check-redundancy <city>`
2. Extract unique names: `python3 extract_unique_pois.py <city>`
3. Generate content: `./pocket-guide poi batch-generate unique_pois_<city>.txt --city <city>`

---

### Generate POI Content

#### Single POI
```bash
./pocket-guide generate \
  --poi-name "Eiffel Tower" \
  --city "Paris" \
  --language en

# Skip research (faster, basic content)
./pocket-guide generate \
  --poi-name "Eiffel Tower" \
  --city "Paris" \
  --skip-research

# Force re-research (update existing research data)
./pocket-guide generate \
  --poi-name "Eiffel Tower" \
  --city "Paris" \
  --force-research

# Enable verification (checks 60-100% coverage, costs more)
./pocket-guide generate \
  --poi-name "Eiffel Tower" \
  --city "Paris" \
  --verify
```

**Options:**
- `--skip-research`: Skip research phase (fast, basic content)
- `--force-research`: Re-do research even if cached
- `--verify`: Enable transcript verification (60-100% coverage check, increases cost)

#### Batch Generation (Recommended)
```bash
./pocket-guide poi batch-generate <file> --city <city>

# Examples
./pocket-guide poi batch-generate pois.txt --city Rome
./pocket-guide poi batch-generate pois.txt --city Rome --skip-research  # Faster
./pocket-guide poi batch-generate pois.txt --city Rome --force  # Regenerate all
./pocket-guide poi batch-generate pois.txt --city Rome --verify  # Enable verification
```

**Options:**
- `--skip-research`: Skip research phase (faster, less rich)
- `--force`: Force regeneration even if content exists
- `--verify`: Enable transcript verification (60-100% coverage, costs more)

**Features:**
- ✅ Auto-resumes from failures
- ✅ Smart verification (optional with `--verify`)
- ✅ API retry logic (5 attempts)
- ⏱️ ~5-10 minutes per POI
- 📊 Coverage check: 60-100% of research (with `--verify`)

**Output:**
- `content/<city>/<poi-id>/transcript_{language}.txt`
- `content/<city>/<poi-id>/summary.txt`
- `content/<city>/<poi-id>/metadata.json`

---

### Check for Duplicates

```bash
./pocket-guide poi check-redundancy <city>

# Example
./pocket-guide poi check-redundancy Athens
```

Marks duplicates with `skip: true` in research_candidates.json.

---

## 🗺️ Trip Planning

### Plan Itinerary

```bash
./pocket-guide trip plan \
  --city <city> \
  --days <number> \
  --interests <interest> \
  --language <lang> \
  --mode <simple|ilp> \
  --save

# Examples - Simple Mode (Fast, Good Quality)
./pocket-guide trip plan --city Rome --days 3 --interests history --mode simple --save

# Example - ILP Mode (Slower, Optimal Route)
./pocket-guide trip plan --city Athens --days 2 --interests mythology --mode ilp --save

# Example - Multilingual with Taiwan accent
./pocket-guide trip plan --city Rome --days 3 --interests history --language zh-tw --mode simple --save
```

**Required Options:**
- `--city`: City name
- `--days`: Trip duration

**Optimization Mode (Important!):**
- `--mode simple`: **Recommended** - Greedy algorithm + 2-opt optimization (fast, 1-5 seconds)
  - Uses smart heuristics to minimize walking distance
  - Great for most use cases
  - Default mode
- `--mode ilp`: **Advanced** - Integer Linear Programming (slower, 10-60 seconds)
  - Finds mathematically optimal route
  - Use for complex multi-day trips or when perfection matters
  - Requires solver (CBC or similar)

**Other Options:**
- `--interests`: Multiple allowed (`--interests history --interests art`)
- `--language`: ISO 639-1 code (default: `en`)
- `--pace`: `relaxed`, `normal`, `packed`
- `--walking`: `low`, `moderate`, `high`
- `--must-see`: POIs to include (multiple allowed)
- `--start-location`: Starting point (POI name or "lat,lng")
- `--end-location`: Ending point (POI name or "lat,lng")
- `--start-date`: Trip start date (YYYY-MM-DD format)
- `--save`: Save the tour

**What happens:**
1. AI selects 8-12 POIs matching interests
2. Provides 2-3 backup POIs per selection
3. Optimizes daily schedule (minimize walking, maximize coherence)
4. Auto-generates missing transcripts in target language
5. Saves language-specific tour files

**Output:**
```
Day 1 (7.5h, 3.2km walking)
  1. Colosseum (2.5h)
  2. Roman Forum (2.0h) ← 10min walk
  3. Palatine Hill (1.5h) ← 5min walk

✓ Tour saved: tours/rome/rome-tour-20260129-111100-aa7baf/
```

---

### View Saved Tours

```bash
# List all tours
./pocket-guide trip list --city <city>

# Show specific tour
./pocket-guide trip show <tour-id> --city <city> --language <lang>

# Examples
./pocket-guide trip list --city Rome
./pocket-guide trip show rome-tour-20260129-111100-aa7baf --city Rome --language zh-tw
```

---

## 🔑 Common Workflows

### Workflow 1: New City Setup (Complete)

```bash
# 1. Research POIs
./pocket-guide poi research "New York" --count 30

# 2. Check for duplicates
./pocket-guide poi check-redundancy "New York"

# 3. Extract unique POI names
python3 extract_unique_pois.py "New York"

# 4. Generate content for all unique POIs
./pocket-guide poi batch-generate unique_pois_new_york.txt --city "New York"

# 5. Plan a trip with simple mode (fast)
./pocket-guide trip plan --city "New York" --days 3 --interests culture --mode simple --save

# 6. Collect metadata (optional - requires Google Maps API)
curl -X POST http://localhost:8000/cities/new-york/collect
```

---

### Workflow 2: Plan Multilanguage Trip with Audio

```bash
# 1. Research POIs (English - always)
./pocket-guide poi research Rome --count 50

# 2. Check duplicates and extract unique
./pocket-guide poi check-redundancy Rome
python3 extract_unique_pois.py rome

# 3. Generate content for unique POIs
./pocket-guide poi batch-generate unique_pois_rome.txt --city Rome

# 4. Plan trip in Chinese (Traditional)
./pocket-guide trip plan \
  --city Rome \
  --days 2 \
  --interests history \
  --language zh-tw \
  --mode simple \
  --save

# 5. Generate audio narration (with Taiwan accent)
./pocket-guide trip tts <tour-id> --city Rome --language zh-tw --provider qwen

# Auto-generates Chinese transcripts if missing!
# Qwen3-TTS provides natural Taiwan accent (configure in config.yaml)
```

---

### Workflow 3: Add Single POI

```bash
./pocket-guide generate \
  --poi-name "Notre-Dame Cathedral" \
  --city "Paris" \
  --language fr
```

---

### Workflow 4: Resume Failed Batch

```bash
# If batch fails, just run again - it auto-resumes!
./pocket-guide poi batch-generate pois.txt --city Rome

# Shows:
# ⊘ Colosseum (already exists)
# ⊘ Roman Forum (already exists)
# ⚡ Pantheon (generating...)  ← Resumes here
```

---

## 🆘 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Module not found" | `source venv/bin/activate` |
| "Port already in use" | `./stop-dev.sh` |
| "Research data not found" | Check `poi_research/<City>/<poi>.yaml` exists |
| API rate limit | Auto-handled (5 retries + 500ms delays) |
| Batch fails midway | Just run again - auto-resumes |

---

### Check API Logs

```bash
# View backend logs
python src/api_server.py

# Test API keys
python test-api-keys.py
```

---

## 📂 File Structure

```
pocket-guide/
├── content/<city>/<poi-id>/       # Generated content
│   ├── transcript_{lang}.txt      # Tour narration
│   ├── summary.txt                # Key points
│   └── metadata.json              # Version history
│
├── poi_research/<City>/           # Research data
│   ├── research_candidates.json   # AI-discovered POIs
│   └── <poi_name>.yaml            # Detailed research
│
└── tours/<city>/<tour-id>/        # Saved tours
    ├── tour_{lang}.json           # Language-specific tour
    └── generation_record_{lang}.json
```

---

## 🎯 Key Features

### POI Generation
- ✅ **Smart verification loop** - 60-100% coverage
- ✅ **API retry logic** - 5 attempts with backoff
- ✅ **Auto-resume** - Skips completed POIs
- ✅ **Multi-language** - 40+ languages supported

### Trip Planning
- ✅ **AI-powered selection** - Matches interests
- ✅ **Backup POIs** - Alternatives if needed
- ✅ **Route optimization** - Minimize walking
- ✅ **Auto-transcripts** - Generates missing languages
- ✅ **Full transparency** - See why POIs were chosen/rejected

### Quality
- ⚡ **Fast**: 5-10 min per POI with research
- 🎭 **Dramatic**: Storytelling-focused narration
- 📊 **Complete**: Research + transcript + metadata
- 🔄 **Versioned**: Full history tracking

---

## 🔗 Quick Links

**Documentation:**
- [API Docs](http://localhost:8000/docs) (when server running)
- [QUICKSTART.md](QUICKSTART.md) - Detailed getting started
- [TRIP_PLANNER_USAGE.md](TRIP_PLANNER_USAGE.md) - Trip planner deep dive

**Troubleshooting:**
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [DEBUG_INSTRUCTIONS.md](DEBUG_INSTRUCTIONS.md)

---

## 📖 Command Reference

### POI Commands

```bash
# Research
poi research <city> [--count N] [--provider NAME]

# Generate single
generate --poi-name "NAME" --city "CITY" [--language LANG] [--skip-research] [--force-research] [--verify]

# Generate batch
poi batch-generate <file> --city <city> [--skip-research] [--force] [--verify]

# Check duplicates
poi check-redundancy <city>
```

### Trip Commands

```bash
# Plan trip with optimization mode
trip plan --city <city> --days <N> --mode <simple|ilp> [--interests X] [--language LANG] [--save]

# Examples - Different optimization modes:
trip plan --city Rome --days 3 --mode simple --save              # Fast (recommended)
trip plan --city Rome --days 3 --mode ilp --save                 # Optimal (slower)
trip plan --city Rome --days 3 --mode simple --interests history # With interests
trip plan --city Rome --days 3 --language zh-tw --mode simple    # Multilingual

# List tours
trip list --city <city>

# Show tour
trip show <tour-id> --city <city> [--language LANG]

# Generate TTS audio for tour (all POIs or specific POI)
trip tts <tour-id> --city <city> [--poi POI_ID] [--language LANG] [--provider edge|openai|google|qwen] [--force]

# TTS Examples:
trip tts rome-tour-123 --city rome                           # All POIs, EdgeTTS (free, default)
trip tts rome-tour-123 --city rome --provider qwen           # All POIs, Qwen3-TTS (free, Taiwan accent)
trip tts rome-tour-123 --city rome --poi colosseum           # Single POI only
trip tts rome-tour-123 --city rome --language zh-tw --force  # Chinese, force regenerate
```

### Utility Scripts

```bash
# Extract unique POI names (skips duplicates)
python3 extract_unique_pois.py <city> [output_file]

# Examples:
python3 extract_unique_pois.py rome                    # Output: unique_pois_rome.txt
python3 extract_unique_pois.py paris my_pois.txt       # Custom output file

# Generate missing research
python3 generate_missing_research.py
```

---

## 🌐 Language Support

**Supported codes**: `en`, `zh-tw`, `zh-cn`, `es`, `es-mx`, `pt-br`, `fr`, `de`, `it`, `ja`, `ko`, `ar`, etc.

**How it works:**
- Research data: Always English
- Transcripts: Language-specific (`transcript_zh-tw.txt`)
- Tours: Language-specific (`tour_zh-tw.json`)
- Auto-generation: Missing transcripts created on-demand

---

## 🎓 Tips

### Trip Planning: Optimization Mode Comparison

| Feature | Simple Mode (`--mode simple`) | ILP Mode (`--mode ilp`) |
|---------|------------------------------|------------------------|
| **Speed** | ⚡ Fast (1-5 seconds) | 🐌 Slower (10-60 seconds) |
| **Quality** | ✅ Very good (95-98% optimal) | 🏆 Mathematically optimal |
| **Algorithm** | Greedy + 2-opt heuristic | Integer Linear Programming |
| **Use Case** | Most trips, quick planning | Complex trips, perfectionist |
| **When to Use** | Default, everyday use | Multi-day trips, critical routes |
| **Requirements** | None | Solver (CBC, included) |

**Recommendation:** Start with `simple` mode. Only use `ilp` if you need the absolute best route or have complex constraints.

### POI Generation: Speed vs Quality
- **With research** (default): Rich content, ~10 min/POI
- **Without research** (`--skip-research`): Fast, ~2 min/POI, basic content
- **Re-research** (`--force-research`): Update existing research data
- **With verification** (`--verify`): Ensures 60-100% coverage, costs more (extra API calls)

### AI Provider Comparison
- **Anthropic (Claude)**: Best storytelling, most dramatic
- **OpenAI (GPT-4)**: Balanced, reliable
- **Google (Gemini)**: Fast, cost-effective

### TTS Provider Comparison
- **EdgeTTS** (free): Fast, cloud-based, may have blocking issues
- **Qwen3-TTS** (free, local): Natural Taiwan accent, customizable emotion/tone
- **OpenAI TTS** (paid): High quality, cloud-based
- **Google TTS** (paid): Good quality, many voices

### File Naming Conventions
- Content: `kebab-case` (`blue-mosque/`)
- Research: `snake_case` (`blue_mosque.yaml`)
- Cities: `TitleCase` in research, `kebab-case` in content

---

## 📊 Appendix: Workflow Diagrams

### Complete POI Generation Workflow

```mermaid
flowchart TD
    Start([Start: Generate POI Content]) --> Research{Research Phase}

    Research -->|--skip-research| NoResearch[Use description only]
    Research -->|Default| CheckCache{Research cached?}

    CheckCache -->|Yes + --force-research| DoResearch[Run Research Agent<br/>11 API calls]
    CheckCache -->|Yes| UseCache[Use cached research]
    CheckCache -->|No| DoResearch

    NoResearch --> Generate[Generate Transcript<br/>1 API call]
    UseCache --> Generate
    DoResearch --> Generate

    Generate --> Verify{--verify flag?}

    Verify -->|No| Save[Save transcript<br/>Create new version]
    Verify -->|Yes| CheckCoverage{Coverage ≥ 60%?}

    CheckCoverage -->|Yes| Save
    CheckCoverage -->|No| Refine[Refine transcript<br/>+1 API call]

    Refine --> ReCheck{Coverage ≥ 60%?}
    ReCheck -->|Yes| Save
    ReCheck -->|No, retry < 3| Refine
    ReCheck -->|No, retry = 3| Save

    Save --> End([Done: Content Saved])

    style Start fill:#e1f5e1
    style End fill:#e1f5e1
    style DoResearch fill:#fff4e6
    style Generate fill:#e3f2fd
    style Refine fill:#f3e5f5
    style Save fill:#e8f5e9
```

### Batch Generation Workflow

```mermaid
flowchart TD
    Start([Start: Batch Generate]) --> LoadFile[Load POI names from file]
    LoadFile --> CheckCity{City specified?}

    CheckCity -->|No| Error1[Error: --city required]
    CheckCity -->|Yes| LoadCandidates[Load research_candidates.json]

    LoadCandidates --> FilterSkipped[Filter skip: true POIs]
    FilterSkipped --> Loop{For each POI}

    Loop --> CheckExists{Transcript exists<br/>for language?}

    CheckExists -->|Yes + no --force| Skip[⊘ Skip POI]
    CheckExists -->|Yes + --force| GenPOI[⚡ Generate POI]
    CheckExists -->|No| GenPOI

    GenPOI --> Research{--skip-research?}
    Research -->|Yes| QuickGen[Generate without research<br/>~2 min]
    Research -->|No| FullGen[Generate with research<br/>~10 min]

    QuickGen --> VerifyCheck{--verify?}
    FullGen --> VerifyCheck

    VerifyCheck -->|Yes| DoVerify[Verify coverage<br/>60-100%]
    VerifyCheck -->|No| SavePOI[✓ Save POI]

    DoVerify --> SavePOI
    SavePOI --> Track[Track success/failure]
    Skip --> Track

    Track --> More{More POIs?}
    More -->|Yes| Loop
    More -->|No| Summary[Show summary:<br/>✓ Succeeded<br/>✗ Failed<br/>⊘ Skipped]

    Summary --> End([Done: Batch Complete])
    Error1 --> End

    style Start fill:#e1f5e1
    style End fill:#e1f5e1
    style GenPOI fill:#e3f2fd
    style QuickGen fill:#fff4e6
    style FullGen fill:#fff4e6
    style SavePOI fill:#e8f5e9
    style Skip fill:#f5f5f5
```

### Trip Planning Workflow

```mermaid
flowchart TD
    Start([Start: Plan Trip]) --> Params[Get parameters:<br/>city, days, interests,<br/>language, pace]

    Params --> LoadPOIs[Load all POIs from<br/>poi_research/City/]

    LoadPOIs --> SelectPOIs[AI selects 8-12 POIs<br/>matching interests<br/>1 API call]

    SelectPOIs --> Backups[AI provides 2-3<br/>backup POIs per selection]

    Backups --> Optimize[Optimize itinerary:<br/>- Minimize walking<br/>- Maximize coherence<br/>- 8h per day]

    Optimize --> CheckLang{Language = en?}

    CheckLang -->|Yes| SaveTour[Save tour]
    CheckLang -->|No| CheckTranscripts{Check POI transcripts<br/>for target language}

    CheckTranscripts --> Loop{For each POI}

    Loop --> TransExists{Transcript exists<br/>in target language?}

    TransExists -->|Yes| NextPOI[✓ Use existing]
    TransExists -->|No| GenTrans[⚡ Generate transcript<br/>in target language<br/>~10 min]

    NextPOI --> MorePOIs{More POIs?}
    GenTrans --> MorePOIs

    MorePOIs -->|Yes| Loop
    MorePOIs -->|No| SaveTour

    SaveTour --> Display[Display itinerary:<br/>- Day-by-day schedule<br/>- Walking distances<br/>- Optimization scores]

    Display --> SaveFlag{--save flag?}

    SaveFlag -->|Yes| CreateFiles[Create tour files:<br/>- tour_lang.json<br/>- generation_record_lang.json<br/>- metadata.json]
    SaveFlag -->|No| End([Done: Display Only])

    CreateFiles --> End2([Done: Tour Saved])

    style Start fill:#e1f5e1
    style End fill:#e1f5e1
    style End2 fill:#e1f5e1
    style SelectPOIs fill:#e3f2fd
    style GenTrans fill:#fff4e6
    style SaveTour fill:#e8f5e9
```

### Research Phase Detail

```mermaid
flowchart TD
    Start([Research Phase]) --> Agent1[1. Research Agent<br/>Basic info + categories]

    Agent1 --> Agent2[2. Historical Context<br/>Period, date, significance]

    Agent2 --> Agent3[3. Core Features<br/>5-7 key features]

    Agent3 --> Agent4[4. Feature Details<br/>Deep dive each feature]

    Agent4 --> Agent5[5. People & Stories<br/>Historical figures]

    Agent5 --> Agent6[6. Dramatic Moments<br/>Pivotal events]

    Agent6 --> Agent7[7. Sensory Details<br/>Sounds, smells, visuals]

    Agent7 --> Agent8[8. Modern Context<br/>Current state]

    Agent8 --> Agent9[9. Visitor Tips<br/>Practical info]

    Agent9 --> Agent10[10. Connections<br/>Related POIs]

    Agent10 --> Agent11[11. References<br/>Sources & links]

    Agent11 --> Save[Save research YAML<br/>poi_research/City/poi.yaml]

    Save --> End([Research Complete])

    style Start fill:#e1f5e1
    style End fill:#e8f5e9
    style Agent1 fill:#e3f2fd
    style Agent2 fill:#e3f2fd
    style Agent3 fill:#e3f2fd
    style Agent4 fill:#e3f2fd
    style Agent5 fill:#e3f2fd
    style Agent6 fill:#e3f2fd
    style Agent7 fill:#e3f2fd
    style Agent8 fill:#e3f2fd
    style Agent9 fill:#e3f2fd
    style Agent10 fill:#e3f2fd
    style Agent11 fill:#e3f2fd
    style Save fill:#e8f5e9
```

### Flag Decision Tree

```mermaid
flowchart TD
    Start([Choose Generation Mode]) --> Question1{Need full research?}

    Question1 -->|Yes| Question2{Research exists?}
    Question1 -->|No| UseSkip[Use --skip-research<br/>Fast: ~2 min/POI<br/>Basic content]

    Question2 -->|Yes, up-to-date| Default[Use default<br/>Medium: ~10 min/POI<br/>Rich content]
    Question2 -->|Yes, outdated| UseForce[Use --force-research<br/>Slow: ~10 min/POI<br/>Updated research]
    Question2 -->|No| Default

    Default --> Question3{Need quality check?}
    UseSkip --> Question3
    UseForce --> Question3

    Question3 -->|Yes, ensure coverage| AddVerify[Add --verify<br/>+1-2 API calls<br/>60-100% coverage]
    Question3 -->|No, trust output| NoVerify[No --verify<br/>Faster, lower cost]

    AddVerify --> Question4{Batch mode?}
    NoVerify --> Question4

    Question4 -->|Yes| Question5{Regenerate existing?}
    Question4 -->|No| Single[Single POI mode]

    Question5 -->|Yes| AddForceFlag[Add --force<br/>Regenerate all POIs]
    Question5 -->|No| AutoResume[Auto-resume<br/>Skip existing POIs]

    AddForceFlag --> End([Run Command])
    AutoResume --> End
    Single --> End

    style Start fill:#e1f5e1
    style End fill:#e8f5e9
    style UseSkip fill:#fff4e6
    style Default fill:#e3f2fd
    style UseForce fill:#f3e5f5
    style AddVerify fill:#fff3cd
    style NoVerify fill:#d1ecf1
```

---

**Last Updated**: February 2026
**Version**: 2.0.0

For detailed information, see [QUICKSTART.md](QUICKSTART.md) or [API Documentation](http://localhost:8000/docs).
