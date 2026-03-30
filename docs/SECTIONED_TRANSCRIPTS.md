# Sectioned Transcripts Feature

## Overview

All POI content generation now produces **multi-section transcripts** (2-5 sections), regardless of whether research data is used.

Previously, only POIs generated with research data would have multiple sections. POIs generated with `--skip-research` would create a single flat transcript.

## Changes

### Before (Prior Behavior)

```bash
# With research → 5 sections
./pocket-guide poi batch-generate pois.txt --city Rome

# With --skip-research → 1 section only
./pocket-guide poi batch-generate pois.txt --city Taipei --skip-research
```

### After (Current Behavior)

```bash
# With research → 5 sections (evidence-based)
./pocket-guide poi batch-generate pois.txt --city Rome

# With --skip-research → 2-5 sections (generic)
./pocket-guide poi batch-generate pois.txt --city Taipei --skip-research
```

## Section Output Comparison

### With Research (High Quality)

```json
{
  "sections": [
    {
      "section_number": 1,
      "title": "The Pee Tax Palace",
      "knowledge_point": "How the Colosseum was funded through urine taxation",
      "transcript": "Picture this: You're a Roman citizen in 72 AD...",
      "word_count": 231,
      "estimated_duration_seconds": 92
    },
    {
      "section_number": 2,
      "title": "Built on Blood",
      "knowledge_point": "The Jewish War prisoners who constructed it",
      "transcript": "Now, here's the dark twist...",
      "word_count": 221,
      "estimated_duration_seconds": 88
    }
  ]
}
```

**Characteristics:**
- ✅ Specific facts (measurements, dates, numbers)
- ✅ Evidence-based storytelling (from research data)
- ✅ Real historical events and characters
- ✅ 5 detailed sections with rich content

### With --skip-research (Medium Quality)

```json
{
  "sections": [
    {
      "section_number": 1,
      "title": "Colonial Architecture",
      "knowledge_point": "The building's Greek Revival style and its purpose",
      "transcript": "Standing before this magnificent building...",
      "word_count": 120,
      "estimated_duration_seconds": 48
    },
    {
      "section_number": 2,
      "title": "Museum Collections",
      "knowledge_point": "What visitors can see inside",
      "transcript": "As you step inside, you'll discover...",
      "word_count": 110,
      "estimated_duration_seconds": 44
    }
  ]
}
```

**Characteristics:**
- ⚠️ Generic descriptions (no specific measurements)
- ⚠️ Invented sections (AI creates logical breaks)
- ⚠️ No specific historical events or dates
- ✅ 2-3 sections with structured narrative

## Benefits

### User Experience
- **Consistent structure**: All tours have sectioned audio, not just research-based ones
- **Skip functionality**: Users can jump between sections in the audio player
- **Better organization**: Content is broken into logical segments

### Development
- **No breaking changes**: Existing parsing logic works unchanged
- **Backward compatible**: Old single-section transcripts still work
- **Faster than research**: Still ~2.5min vs 10min per POI

## Trade-offs

| Aspect | Impact | Details |
|--------|--------|---------|
| **Generation Time** | ⬆️ +25% | 2 min → 2.5 min per POI |
| **API Cost** | ⬆️ +100% | $0.01 → $0.02 per POI |
| **Prompt Tokens** | ⬆️ +30% | ~500 → ~650 tokens |
| **Response Tokens** | ⬆️ +100% | ~400 → ~800 tokens |
| **Section Quality** | ⬇️ Generic | No specific facts/dates |
| **Accuracy Risk** | ⚠️ Higher | AI may fabricate details |

## When to Use Each Mode

### Use WITH Research (No --skip-research)

**Best For:**
- Production tours for public use
- High-quality content with specific facts
- Tours where accuracy is critical

**Command:**
```bash
./pocket-guide poi batch-generate pois.txt --city Rome
```

**Cost:** ~$0.10/POI (11 API calls)
**Time:** ~10 min/POI
**Quality:** ⭐⭐⭐⭐⭐ Excellent

---

### Use WITH --skip-research

**Best For:**
- Quick prototyping and testing
- Personal tours where speed matters
- Low-budget projects
- Tours where generic content is acceptable

**Command:**
```bash
./pocket-guide poi batch-generate pois.txt --city Taipei --skip-research
```

**Cost:** ~$0.02/POI (1 API call)
**Time:** ~2.5 min/POI
**Quality:** ⭐⭐⭐ Medium

---

## Technical Details

### Code Changes

**File:** `src/content_generator.py`

**Method Modified:** `_build_prompt()`

**Before:**
```python
prompt_parts.extend([
    f"\nYour response should include TWO sections:",
    f"1. TRANSCRIPT: The spoken tour guide narration",
    f"2. SUMMARY POINTS: 3-5 bullet points"
])
```

**After:**
```python
prompt_parts.extend([
    "=" * 60,
    "OUTPUT FORMAT - SECTIONED NARRATIVE",
    "=" * 60,
    "",
    "Break your narrative into 2-5 SECTIONS. Each section should:",
    "- Be 60-150 seconds when spoken (100-250 words)",
    "- Have a clear, evocative title (3-8 words)",
    # ... full sectioning instructions ...
])
```

### Section Parsing

No changes to parsing logic. The existing `_parse_sectioned_response()` method handles both:
- Research-based sections (with rich data)
- Generic sections (without research data)

The parser looks for this pattern:
```
SECTION N:
TITLE: <title>
KNOWLEDGE: <knowledge point>
TRANSCRIPT:
<transcript text>
```

### Data Structures

No changes to JSON output format. Both modes produce:
```json
{
  "poi": "POI name",
  "language": "en",
  "total_sections": 3,
  "sections": [
    {
      "section_number": 1,
      "title": "...",
      "knowledge_point": "...",
      "transcript": "...",
      "estimated_duration_seconds": 90,
      "word_count": 225,
      "audio_file": "audio_section_1_en.mp3"
    }
  ],
  "summary_points": ["...", "...", "..."]
}
```

## Migration Guide

### Existing Content

No migration needed. Old single-section transcripts continue to work:
- Tours generated before this change: 1 section
- Tours generated after this change: 2-5 sections
- Both are valid and render correctly in the app

### Regenerating Content

To get sectioned transcripts for existing POIs:

```bash
# Option 1: Regenerate with --skip-research (faster, generic sections)
./pocket-guide poi batch-generate pois.txt --city Taipei --skip-research --force

# Option 2: Regenerate with research (slower, detailed sections)
./pocket-guide poi batch-generate pois.txt --city Taipei --force
```

Use `--force` flag to overwrite existing content.

## Testing

### Verify the Change

```bash
# Test prompt generation
python3 /tmp/test_prompt.py

# Expected output:
# ✅ SUCCESS: Prompt now requests sectioned output even without research!
```

### Test POI Generation

```bash
# Create test file
echo "Test Monument" > /tmp/test_poi.txt

# Generate with --skip-research
./pocket-guide poi batch-generate /tmp/test_poi.txt --city TestCity --skip-research

# Check output
cat content/TestCity/test-monument/sectioned_transcript_en.json

# Should see 2-5 sections (not 1)
```

## Future Enhancements

Possible improvements:
- Add `--min-sections` and `--max-sections` flags
- Provide section count hints based on POI type
- Add section quality scoring
- Support custom section templates

## Questions?

If you encounter issues:
1. Check that section parsing regex works
2. Verify AI provider supports longer responses
3. Check token limits aren't exceeded
4. Review prompt formatting in logs

---

**Last Updated:** 2026-03-29
**Branch:** feature/sections-without-research
**Status:** ✅ Implemented
