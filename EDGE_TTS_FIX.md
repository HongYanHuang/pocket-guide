# Edge TTS Fix for Taiwanese Mandarin

## Problem

Edge TTS was returning **403 Forbidden** errors when trying to generate audio for Taiwanese Mandarin:

```
403, message='Invalid response status', url='wss://speech.platform.bing.com/...'
```

## Root Cause

The `edge-tts` library version **6.1.19** was outdated. Microsoft frequently updates their authentication tokens and API endpoints, which caused the old version to fail.

## Solution

Upgraded `edge-tts` from **6.1.19** to **7.2.7**:

```bash
pip install --upgrade edge-tts
```

Updated `requirements.txt` to prevent future issues:
```
edge-tts>=7.2.7
```

## Verification

All three Taiwan voices now work perfectly:

| Voice | Gender | Quality | File Size (3 sentences) |
|-------|--------|---------|-------------------------|
| **zh-TW-HsiaoChenNeural** | Female | Clear, young | ~110 KB |
| **zh-TW-HsiaoYuNeural** | Female | Warm, friendly | ~135 KB |
| **zh-TW-YunJheNeural** | Male | Professional | ~107 KB |

## Usage

### Default Taiwan Voice

```python
from tts_generator import TTSGenerator
from utils import load_config

config = load_config()
tts = TTSGenerator(config)

# Uses default zh-TW-HsiaoChenNeural
audio_file = tts.generate(
    text="歡迎來到台北101",
    output_path=Path("output"),
    provider='edge',
    language='zh-TW'
)
```

### Specific Voice

```python
# Use warmer female voice (HsiaoYu)
audio_file = tts.generate(
    text="歡迎來到台北101",
    output_path=Path("output"),
    provider='edge',
    language='zh-TW',
    voice='zh-TW-HsiaoYuNeural'
)

# Use male voice (YunJhe)
audio_file = tts.generate(
    text="歡迎來到台北101",
    output_path=Path("output"),
    provider='edge',
    language='zh-TW',
    voice='zh-TW-YunJheNeural'
)
```

### CLI Usage

Generate transcripts with Edge TTS (default for zh-TW):

```bash
# Generate Taiwan Mandarin transcript with audio
python src/cli.py create-transcript \
  --city taipei \
  --poi-id taipei-101 \
  --language zh-tw \
  --provider edge

# Force regenerate with specific voice
python src/cli.py create-transcript \
  --city taipei \
  --poi-id taipei-101 \
  --language zh-tw \
  --provider edge \
  --voice zh-TW-HsiaoYuNeural \
  --force
```

## Advantages of Edge TTS

1. **FREE** - No API key or credentials needed
2. **Fast** - Cloud-based, generates in ~1-3 seconds
3. **High Quality** - Neural voices sound natural
4. **Taiwan Accent** - Native Taiwanese Mandarin pronunciation
5. **No Rate Limits** - Unlimited usage

## Comparison vs Other Providers

| Provider | Cost | Taiwan Accent | Setup | Speed |
|----------|------|---------------|-------|-------|
| **Edge TTS** | FREE | ✅ Excellent | None | Fast (1-3s) |
| OpenAI TTS | $15/1M chars | ❌ Mainland only | API key | Very fast |
| Google Cloud TTS | $4/1M chars (1M free) | ✅ Excellent | GCP setup | Fast |
| Qwen3-TTS | FREE | ⚠️ Customizable | GPU required | Very slow (CPU) |

## Recommended Configuration

In `config.yaml`, Edge TTS is already configured as the default for Taiwanese Mandarin:

```yaml
tts_providers:
  edge:
    enabled: true
    # No API key needed
    # Auto-selects zh-TW-HsiaoChenNeural for zh-TW language
```

## Testing

Run the test scripts to verify:

```bash
# Test Edge TTS directly
python test_edge_tts.py

# Test TTS generator integration
python test_tts_integration.py
```

## Files Changed

- `requirements.txt` - Updated `edge-tts==6.1.19` → `edge-tts>=7.2.7`
- Created test scripts: `test_edge_tts.py`, `test_tts_integration.py`

## Next Steps

1. Remove old Qwen TTS configuration (too slow without GPU)
2. Generate Taiwan audio for existing POIs
3. Update backstage to allow voice selection per language

---

**Issue Resolved**: Edge TTS now works perfectly for Taiwanese Mandarin audio generation. ✓
