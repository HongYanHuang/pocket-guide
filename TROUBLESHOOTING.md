# Troubleshooting Guide

## Issue: `./pocket-guide generate` hangs/freezes

### The Problem
The wrapper script was filtering output with `grep`, which **broke interactive prompts**. The CLI was asking you questions, but you couldn't see them!

### ✅ Fixed!

I updated the wrapper to only filter warnings (stderr), not interactive prompts (stdout).

---

## How to Use the CLI Now

### Option 1: Use the Fixed Wrapper (Recommended)
```bash
./pocket-guide generate
```

This should now show interactive prompts asking for:
- City name
- POI name
- AI provider selection
- Description/interests

### Option 2: Use the No-Filter Wrapper (If Option 1 doesn't work)
```bash
./pocket-guide-nofilter generate
```

Shows all output including warnings, but **guarantees interactivity**.

### Option 3: Provide All Arguments (Skip Interactive Mode)
```bash
./pocket-guide generate \
  --city "Rome" \
  --poi "Colosseum" \
  --provider openai \
  --description "Built by Emperor Vespasian in 80 AD" \
  --interests "history,architecture"
```

When you provide all arguments, no interactive prompts appear!

### Option 4: Use Python Directly
```bash
source venv/bin/activate
python src/cli.py generate
# Shows warnings but works perfectly
```

---

## Quick Test

Try this to verify it works:

```bash
# Test 1: Check help (should be instant)
./pocket-guide-nofilter --help

# Test 2: Generate with all arguments (no prompts needed)
./pocket-guide-nofilter generate \
  --city "Test" \
  --poi "Monument" \
  --provider openai \
  --description "A test monument"

# Test 3: Interactive mode (should prompt you)
./pocket-guide-nofilter generate
# You should see: "City name:" prompt
```

---

## Common Issues

### Issue: "Config file not found"
**Solution:** Create config.yaml from template
```bash
cp config.example.yaml config.yaml
nano config.yaml  # Add your API keys
```

### Issue: "API key not configured"
**Solution:** Edit config.yaml and add your API key
```bash
nano config.yaml
# Find the provider you want (openai, anthropic, google)
# Replace "your-api-key-here" with your actual key
```

### Issue: Hangs after showing prompts
**Solution:** Just type your answer and press Enter!
```
City name: Rome
POI name: Colosseum
```

### Issue: Hangs with no output at all
**Solution:** Use the no-filter wrapper
```bash
./pocket-guide-nofilter generate
```

### Issue: "Failed to generate content"
**Possible causes:**
1. **No API key** - Check config.yaml has your key
2. **Invalid API key** - Verify key is correct
3. **Network issue** - Check internet connection
4. **Rate limit** - Wait a few seconds and retry

---

## Debugging Steps

### Step 1: Verify Setup
```bash
# Check config exists
ls -la config.yaml

# Check venv exists
ls -la venv/

# Check Python version
source venv/bin/activate
python --version  # Should be 3.9+
```

### Step 2: Test Simple Command
```bash
# This should list "No cities found" immediately
./pocket-guide-nofilter cities
```

### Step 3: Test with Full Arguments
```bash
# This should generate content (takes 10-30 seconds)
./pocket-guide-nofilter generate \
  --city "Paris" \
  --poi "Eiffel Tower" \
  --provider openai \
  --description "Built in 1889 for World's Fair"
```

If this hangs:
- Check your API key in config.yaml
- Make sure you have internet connection
- Try a different provider (anthropic or google)

### Step 4: Check Logs
```bash
# Run with verbose output
source venv/bin/activate
python src/cli.py generate --city "Test" --poi "Test" --provider openai 2>&1 | tee debug.log
```

---

## What Each Wrapper Does

| Wrapper | Filters Warnings | Interactive | When to Use |
|---------|------------------|-------------|-------------|
| `./pocket-guide` | ✅ Yes (stderr only) | ✅ Yes | Default - clean output |
| `./pocket-guide-nofilter` | ❌ No | ✅ Yes | If main wrapper has issues |
| `python src/cli.py` | ❌ No | ✅ Yes | For debugging |

---

## Expected Behavior

### Interactive Mode (no arguments)
```bash
$ ./pocket-guide-nofilter generate

City name: Rome
POI name: Colosseum

Let's gather some information about this POI:
Brief description (or press Enter to skip): Ancient amphitheater
Focus areas (e.g., history, architecture, food) - comma separated: history,architecture
Want to provide a custom prompt instead? [y/N]: n

Select AI provider:
1. OpenAI (GPT-4)
2. Anthropic (Claude)
3. Google (Gemini)
Choose provider [1/2/3] (1): 1

⠋ Generating content for Colosseum...

✓ Content generated successfully!

Summary - What visitors will learn:
  1. Point 1
  2. Point 2
  ...
```

### With Arguments (no prompts)
```bash
$ ./pocket-guide-nofilter generate --city "Rome" --poi "Colosseum" --provider openai

⠋ Generating content for Colosseum...

✓ Content generated successfully!
...
```

---

## Performance Expectations

| Operation | Expected Time |
|-----------|---------------|
| `--help` | Instant (< 1 second) |
| `cities` / `pois` | Instant (< 1 second) |
| `generate` (with AI) | 10-30 seconds |
| `tts` (audio generation) | 5-15 seconds |

If `generate` takes > 60 seconds, something is wrong (likely API timeout).

---

## Still Having Issues?

1. **Try the no-filter wrapper first:**
   ```bash
   ./pocket-guide-nofilter generate
   ```

2. **Provide all arguments to skip interactive mode:**
   ```bash
   ./pocket-guide-nofilter generate \
     --city "City" \
     --poi "POI" \
     --provider openai
   ```

3. **Check config.yaml has valid API keys:**
   ```bash
   cat config.yaml | grep api_key
   ```

4. **Run Python directly for full error messages:**
   ```bash
   source venv/bin/activate
   python src/cli.py generate --city "Test" --poi "Test" --provider openai
   ```

5. **Create a debug log:**
   ```bash
   ./pocket-guide-nofilter generate --city "Test" --poi "Test" 2>&1 | tee error.log
   # Share error.log for help
   ```

---

## Quick Fix Summary

**What was broken:** Original wrapper filtered all output, hiding interactive prompts

**What I fixed:**
- Updated `./pocket-guide` to only filter stderr (warnings)
- Created `./pocket-guide-nofilter` as fallback (shows everything)

**What to use now:**
```bash
# Try this first (clean output)
./pocket-guide generate

# If that doesn't work, use this (shows warnings)
./pocket-guide-nofilter generate

# Or provide all arguments (skip prompts entirely)
./pocket-guide generate --city "Rome" --poi "Colosseum" --provider openai
```

---

**You're all set! The hanging issue should be fixed.** 🎉
