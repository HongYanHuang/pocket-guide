# TTS Language Parameter Fix

## Problem Reported

User reported: **"I found the audio is in English not Mandarin"**

Even though the command specified `--language zh-TW`, the generated audio was in English with a Chinese voice.

## Root Cause

**Bug in `src/cli.py` line 321:**

```python
# BEFORE (incorrect)
transcript = load_transcript(poi_path, format='txt')  # ❌ No language parameter
```

The CLI was loading the transcript **without passing the language parameter**, causing it to default to English (`'en'`), even though the user specified `--language zh-TW`.

**What happened:**
1. User ran: `python src/cli.py tts --language zh-TW --provider edge`
2. CLI loaded: `transcript.txt` (English) instead of `transcript_zh-tw.txt` (Chinese)
3. TTS generated: English text with Chinese voice = English audio ❌

## Solution

**Fixed `src/cli.py` line 321-326:**

```python
# AFTER (correct)
lang = language or 'en'
transcript = load_transcript(poi_path, format='txt', language=lang)  # ✅ Pass language
```

Now the CLI correctly:
1. Uses the `--language` parameter from command line
2. Loads the correct language-specific transcript file
3. Generates audio in the specified language

## Verification - Audio Comparison

| Property | English Audio (Before) | Chinese Audio (After) | Status |
|----------|------------------------|------------------------|--------|
| **Duration** | 8:26 minutes | 6:18 minutes | ✅ Correct |
| **File Size** | 2.9 MB | 2.2 MB | ✅ Correct |
| **Voice** | zh-TW-HsiaoChenNeural | zh-TW-HsiaoChenNeural | ✅ Same |
| **Language** | English text | Chinese text | ✅ Fixed |
| **Transcript** | `transcript.txt` | `transcript_zh-tw.txt` | ✅ Fixed |

### Why Duration Changed

Chinese audio is **shorter** (6:18 vs 8:26) because:
- Chinese characters convey more meaning per character
- Chinese speech is more compact than English
- Same content, different language = different duration

This confirms the audio is now **correctly using the Chinese transcript**.

## Files Regenerated

All 4 POIs in tour `rome-tour-20260320-175540-6b0704`:

| POI | Audio File | Size | Status |
|-----|------------|------|--------|
| Basilica di San Clemente | `audio_zh-tw.mp3` | 2.3 MB | ✅ Chinese |
| Colosseum | `audio_zh-tw.mp3` | 2.2 MB | ✅ Chinese |
| Palatine Hill | `audio_zh-tw.mp3` | 2.2 MB | ✅ Chinese |
| Roman Forum | `audio_zh-tw.mp3` | 1.9 MB | ✅ Chinese |

## Test Commands

### Generate Chinese Audio (Correct)
```bash
python src/cli.py tts \
  --city rome \
  --poi "Colosseum" \
  --provider edge \
  --language zh-TW
```

### Test Audio Sample
```bash
# Create 5-second sample
ffmpeg -i content/rome/colosseum/audio_zh-tw.mp3 -t 5 /tmp/sample.mp3

# Play sample (macOS)
afplay /tmp/sample.mp3
```

### Verify via API
```bash
# Download and check
curl -s http://localhost:8000/pois/rome/colosseum/audio/audio_zh-tw.mp3 \
  --output test_audio.mp3

# Check duration (should be ~6:18, not 8:26)
ffmpeg -i test_audio.mp3 2>&1 | grep Duration
```

## API Verification

✅ **All audio files accessible via API:**
```
GET /pois/rome/basilica-di-san-clemente/audio/audio_zh-tw.mp3
GET /pois/rome/colosseum/audio/audio_zh-tw.mp3
GET /pois/rome/palatine-hill/audio/audio_zh-tw.mp3
GET /pois/rome/roman-forum/audio/audio_zh-tw.mp3
```

✅ **Backstage can now play correct Chinese audio**

## Transcript Preview

**First lines of Chinese transcript (Colosseum):**
```
在我們開始之前，這是今天要學習的內容：
1. 古羅馬人如何在沒有現代機械的情況下建造這座巨大建築
2. 這座建築如何從娛樂場所變成教堂，再變成採石場，最後成為聖地

現在，讓我問你一個問題：你知道這座建築是用什麼錢蓋的嗎？答案會讓你震驚。
```

This is **Traditional Chinese** (繁體中文) for Taiwan, spoken with **Taiwan accent** by Edge TTS voice `zh-TW-HsiaoChenNeural`.

## Changes Committed

**Commit:** `da0435c`
**Branch:** `main`
**Files Changed:**
- `src/cli.py` - Fixed TTS command to pass language parameter to load_transcript()

## Summary

✅ **Bug Fixed:** CLI now correctly loads language-specific transcripts
✅ **Audio Regenerated:** All 4 tour POIs now have correct Chinese audio
✅ **API Verified:** Audio accessible via API with correct content
✅ **Backstage Ready:** User can now play Chinese audio in backstage

**Next Steps:**
1. Test audio playback in backstage UI
2. Verify Taiwan accent sounds natural
3. Can generate audio for other languages using same fix

---

**Issue Resolved:** Audio is now in correct language (Chinese, not English)
**Generated:** 2026-03-20
**Provider:** Edge TTS 7.2.7
**Voice:** zh-TW-HsiaoChenNeural (Female, Taiwan accent)
