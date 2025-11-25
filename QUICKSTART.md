# Quick Start Guide

Get up and running with Pocket Guide CLI in 5 minutes!

## Step 0: Prerequisites

- Python 3.9 or higher
- At least ONE API key (OpenAI, Anthropic, or Google Gemini)

## Step 1: Setup (One-time)

```bash
# Run setup script
./setup.sh

# Copy example config
cp config.example.yaml config.yaml

# Edit config with your API keys
nano config.yaml
```

**Required:** Add at least ONE AI provider key:
- `openai.api_key` - OpenAI API key (GPT-4)
- `anthropic.api_key` - Anthropic API key (Claude)
- `google.api_key` - Google AI Studio API key (Gemini)

**Recommended default:** Set `defaults.ai_provider` to your preferred provider (e.g., `"google"` or `"anthropic"`)

## Step 2: Test Your API Keys

Before generating content, verify your API keys work:

```bash
python test-api-keys.py
```

You should see:
- ✅ = Provider working
- ⚠️ = Provider temporarily unavailable (retry later)
- ❌ = API key issue or quota exceeded

## Step 3: Generate Your First Tour Content

### Quick Test (Easiest)

```bash
./pocket-guide generate \
  --city "Paris" \
  --poi "Eiffel Tower" \
  --provider google
```

This generates:
- **Transcript** (300-750 words, 2-5 minutes of speech)
- **Summary Points** (3-5 key takeaways)
- **Metadata** (generation details)

### Interactive Mode

```bash
./pocket-guide generate
```

The CLI will prompt you for:
- City name
- POI name
- AI provider (if not using default)
- Optional description
- Optional interests

### Full Command (Most Control)

```bash
./pocket-guide generate \
  --city "Rome" \
  --poi "Colosseum" \
  --provider google \
  --description "Ancient Roman amphitheater built in 70-80 AD. Originally held 50,000-80,000 spectators. Used for gladiatorial contests and public spectacles." \
  --interests "History,Architecture,Ancient Rome"
```

**Pro tip:** More detailed descriptions and interests result in richer, longer transcripts (up to 5 minutes).

### Research Mode (New!)

The system now includes recursive research that automatically discovers dramatic stories and physical details:

```bash
# First generation - performs research (takes ~2 minutes)
./pocket-guide generate \
  --city "Thessaloniki" \
  --poi "Arch of Galerius" \
  --provider anthropic \
  --interests "drama"

# Second generation - uses cached research (fast)
./pocket-guide generate \
  --city "Thessaloniki" \
  --poi "Arch of Galerius" \
  --provider anthropic \
  --interests "architecture"

# Force new research even if cached
./pocket-guide generate \
  --city "Thessaloniki" \
  --poi "Arch of Galerius" \
  --provider anthropic \
  --interests "drama" \
  --force-research

# Skip research entirely (fastest, uses description only)
./pocket-guide generate \
  --city "Paris" \
  --poi "Eiffel Tower" \
  --provider google \
  --description "Iron tower built in 1889" \
  --skip-research
```

**How Research Works:**
- **First run**: Performs 3-layer recursive research (~10 API calls, ~2 minutes)
- **Cached**: Research saved to `poi_research/{city}/{poi}.yaml`
- **Subsequent runs**: Reuses cached research (instant)
- **Core Features**: Always extracts 2-5 physical facts about what visitors see/experience
- **Filtering**: Historical details filtered by `--interests`, but core features always included

**Research Flags:**
- `--force-research` - Force new research even if cached
- `--skip-research` - Skip research entirely, use description only (fastest)

## Step 4: Generate Audio (TTS)

Convert your transcript to MP3:

```bash
./pocket-guide tts \
  --city "paris" \
  --poi "eiffel-tower" \
  --provider edge
```

**TTS Provider Options:**
- `edge` - **FREE**, no API key needed, good quality (recommended for testing)
- `openai` - High quality, requires OpenAI credits
- `google` - Google Cloud TTS, requires Google Cloud API key

**Note:** City and POI names are case-insensitive and auto-converted to URL-friendly format.

## Step 5: Check Your Files

```bash
# List all cities
./pocket-guide cities

# List POIs in a city
./pocket-guide pois --city "paris"

# View POI details (shows summary points)
./pocket-guide info --city "paris" --poi "eiffel-tower"

# Browse files directly
ls -la content/paris/eiffel-tower/
```

You should see:
- `metadata.json` - Summary points and metadata
- `transcript.txt` - Plain text narration
- `transcript.ssml` - SSML formatted version (for TTS)
- `audio.mp3` - Generated audio file (after running `tts` command)

## Common Workflows

### Complete POI Setup (Content + Audio)

```bash
# 1. Generate content
./pocket-guide generate \
  --city "Tokyo" \
  --poi "Senso-ji Temple" \
  --provider google \
  --description "Ancient Buddhist temple, Tokyo's oldest, founded in 628 AD" \
  --interests "History,Religion,Architecture"

# 2. Generate audio
./pocket-guide tts \
  --city "tokyo" \
  --poi "senso-ji-temple" \
  --provider edge

# 3. Check result
./pocket-guide info --city "tokyo" --poi "senso-ji-temple"
```

### Batch Processing Multiple POIs

Create a script `batch-generate.sh`:

```bash
#!/bin/bash
CITY="Barcelona"
PROVIDER="google"

generate_poi() {
  POI="$1"
  DESC="$2"
  INTERESTS="$3"

  echo "Generating: $POI"
  ./pocket-guide generate \
    --city "$CITY" \
    --poi "$POI" \
    --provider "$PROVIDER" \
    --description "$DESC" \
    --interests "$INTERESTS"

  echo "Creating audio: $POI"
  POI_SLUG=$(echo "$POI" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
  ./pocket-guide tts \
    --city "$(echo $CITY | tr '[:upper:]' '[:lower:]')" \
    --poi "$POI_SLUG" \
    --provider edge

  echo "✓ Completed: $POI"
  echo "---"
}

generate_poi "Sagrada Familia" \
  "Gaudi's iconic unfinished basilica, started in 1882" \
  "Architecture,Art,History,Religion"

generate_poi "Park Guell" \
  "Gaudi's colorful park with mosaic art and city views" \
  "Architecture,Nature,Art"

generate_poi "Gothic Quarter" \
  "Medieval city center with Roman ruins and narrow streets" \
  "History,Culture,Architecture"
```

Run it:
```bash
chmod +x batch-generate.sh
./batch-generate.sh
```

### Testing Longer 5-Minute Transcripts

```bash
./pocket-guide generate \
  --city "Rome" \
  --poi "Roman Forum" \
  --provider google \
  --description "Ancient Roman marketplace and civic center. Heart of ancient Rome with temples, basilicas, and public spaces. Discuss its political importance, daily life, famous speeches, and archaeological significance." \
  --interests "History,Architecture,Ancient Rome,Politics,Daily Life,Archaeology"

# Check word count (should be 300-750 words)
wc -w content/rome/roman-forum/transcript.txt
```

## Available Commands

| Command | Description |
|---------|-------------|
| `generate` | Generate tour content for a POI |
| `tts` | Convert transcript to MP3 audio |
| `cities` | List all cities with content |
| `pois` | List POIs in a specific city |
| `info` | Show POI details and summary points |
| `voices` | List available TTS voices by provider |

## Get Help

Get help for any command:

```bash
./pocket-guide --help
./pocket-guide generate --help
./pocket-guide tts --help
```

## Troubleshooting

### "Config file not found"
```bash
cp config.example.yaml config.yaml
nano config.yaml  # Add your API keys
```

### "API key not configured"
1. Open `config.yaml`
2. Add your API key for the provider you're using
3. Test with: `python test-api-keys.py`

### "Module not found" or Import Errors
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Python 3.9 Warnings
These are normal and don't affect functionality:
```
FutureWarning: You are using a Python version (3.9.6) past its end of life...
```
You can safely ignore them, or upgrade to Python 3.10+.

### API Provider Issues

**OpenAI 429 Error (Quota Exceeded):**
- Add credits to your OpenAI account
- Or switch to `--provider google` or `--provider anthropic`

**Anthropic 529 Error (Overloaded):**
- Wait a few minutes and retry
- Automatic retry with exponential backoff is built-in
- Or temporarily use `--provider google`

**Google Finish Reason 2 (MAX_TOKENS):**
- Fixed! All providers now support 4096-8192 tokens
- Regenerate content to get full 5-minute transcripts

### CLI Hanging or No Output

Use the no-filter wrapper to see debug output:
```bash
./pocket-guide-nofilter generate --city "Test" --poi "Debug"
```

## Pro Tips

1. **Start with `test-api-keys.py`** - Always verify your APIs work before generating content

2. **Use Edge TTS for free audio** - No API key needed, good quality:
   ```bash
   ./pocket-guide tts --city "paris" --poi "louvre" --provider edge
   ```

3. **Google Gemini is fast and cheap** - Great for testing and batch generation

4. **Anthropic Claude has best tone** - Most conversational and engaging narration

5. **Add detailed descriptions** - More context = richer, more engaging content:
   ```bash
   --description "Long detailed description with historical facts, dates, and significance"
   ```

6. **Use multiple interests** - Results in more comprehensive coverage:
   ```bash
   --interests "History,Architecture,Art,Culture,Daily Life"
   ```

7. **Check summary points** - Use `info` command to see what visitors will learn:
   ```bash
   ./pocket-guide info --city "rome" --poi "colosseum"
   ```

8. **Custom voices** - List available voices and choose your favorite:
   ```bash
   ./pocket-guide voices --provider edge
   ./pocket-guide tts --city "paris" --poi "louvre" --provider edge --voice "en-US-AriaNeural"
   ```

9. **Content length** - Now supports 2-5 minute transcripts (300-750 words)

10. **Batch operations** - Script multiple POIs to save time (see Batch Processing section)

11. **Use research mode for richer content** - First run takes ~2 minutes but discovers dramatic stories automatically:
   ```bash
   ./pocket-guide generate --city "Rome" --poi "Colosseum" --provider anthropic --interests "drama"
   ```

12. **Skip research for speed** - If you just need quick content generation without research:
   ```bash
   ./pocket-guide generate --city "Paris" --poi "Louvre" --provider google --description "Famous museum" --skip-research
   ```

13. **Force fresh research** - When you want updated research data:
   ```bash
   ./pocket-guide generate --city "Rome" --poi "Colosseum" --provider anthropic --force-research
   ```

## Current Provider Status

| Provider | Status | Max Tokens | Best For |
|----------|--------|------------|----------|
| **Google Gemini** | ✅ Working | 8,192 | Fast generation, free tier available |
| **Anthropic Claude** | ✅ Working | 4,096 | Most natural conversational tone |
| **OpenAI GPT** | ⚠️ Requires credits | 4,096 | High quality, widely available |

**Recommendation:** Start with Google Gemini (`--provider google`) for testing, then switch to Anthropic Claude for production if you prefer more engaging narration.

## What's Next?

- Read the full [README.md](README.md) for detailed documentation
- Check [PRD.md](PRD.md) for the product roadmap
- See [STORYTELLER_PROMPT_GUIDE.md](STORYTELLER_PROMPT_GUIDE.md) for advanced prompt engineering
- Experiment with different AI providers and compare results
- Create comprehensive walking tours for your favorite cities!

## Quick Reference

**Minimal command:**
```bash
./pocket-guide generate --city "Paris" --poi "Louvre"
```

**Full workflow:**
```bash
# 1. Test APIs
python test-api-keys.py

# 2. Generate content
./pocket-guide generate --city "Paris" --poi "Louvre" --provider google

# 3. Create audio
./pocket-guide tts --city "paris" --poi "louvre" --provider edge

# 4. Check result
./pocket-guide info --city "paris" --poi "louvre"
```

---

**Need help?** Check [README.md](README.md) or open an issue on GitHub
