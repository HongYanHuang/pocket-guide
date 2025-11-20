# Customizing Content Generation Prompts

This guide explains how to customize the AI prompts used for generating tour guide content.

## Overview

The content generation system has two customizable parts:
1. **System Prompt** - Defines the AI's role and personality
2. **Style Guidelines** - Specific rules the AI should follow

Both are configured in `config.yaml` and apply to all AI providers (OpenAI, Claude, Gemini).

## Location

Edit these settings in your `config.yaml` file:

```yaml
content_generation:
  system_prompt: |
    Your system prompt here...

  style_guidelines:
    - "Guideline 1"
    - "Guideline 2"
    - "etc..."
```

## System Prompt

The system prompt sets the AI's role and overall behavior. This is sent to the AI before any specific POI information.

### Default System Prompt

```yaml
system_prompt: |
  You are an expert tour guide creating engaging audio scripts for tourists.
  Your narration should be warm, informative, and conversational.
```

### Examples of Custom System Prompts

**For kid-friendly tours:**
```yaml
system_prompt: |
  You are a fun, enthusiastic tour guide creating audio scripts for families with children.
  Your narration should be engaging for kids ages 8-12, using simple language and fun facts.
  Make history exciting and relatable to young minds!
```

**For academic/detailed tours:**
```yaml
system_prompt: |
  You are a scholarly tour guide with deep expertise in history and architecture.
  Create detailed, informative audio scripts for educated tourists who want in-depth knowledge.
  Include specific dates, architectural terms, and historical context.
```

**For quick/casual tours:**
```yaml
system_prompt: |
  You are a friendly local showing tourists around your favorite spots.
  Keep it casual, fun, and focused on the most interesting highlights.
  Speak like you're chatting with friends, not giving a lecture.
```

## Style Guidelines

Style guidelines are specific rules that appear in every content generation request. They're formatted as bullet points.

### Default Style Guidelines

```yaml
style_guidelines:
  - "Write in a conversational, engaging tone suitable for audio"
  - "Length: 200-300 words (about 1-2 minutes when spoken)"
  - "Include interesting facts, historical context, and practical tips"
  - "Use natural speech patterns with appropriate pauses"
  - "Avoid overly formal or academic language"
  - "Make dates and numbers relatable - say '1700 years ago' instead of '300 AD'"
  - "Use relative timeframes that connect to the listener's experience"
  - "DO NOT include any stage directions, sound effects, or meta-commentary"
  - "Write ONLY the spoken narration"
```

### Customizing Guidelines

You can add, remove, or modify any guidelines. Here are some useful additions:

**Make it more relatable:**
```yaml
style_guidelines:
  # ... existing guidelines ...
  - "Make dates and numbers relatable - say '1700 years ago' instead of '300 AD'"
  - "Use comparisons to familiar things (e.g., 'as tall as a 30-story building')"
  - "Relate historical events to modern contexts"
```

**Control the length:**
```yaml
style_guidelines:
  - "Length: 100-150 words (about 45-60 seconds when spoken)"  # Shorter
  # OR
  - "Length: 400-500 words (about 3-4 minutes when spoken)"    # Longer
```

**Add personality:**
```yaml
style_guidelines:
  - "Use humor where appropriate, but stay respectful"
  - "Tell stories and anecdotes, not just facts"
  - "Create a sense of wonder and excitement"
```

**Add specific focus areas:**
```yaml
style_guidelines:
  - "Always mention practical visitor information (hours, tickets, accessibility)"
  - "Include photo opportunities and best viewing spots"
  - "Mention nearby restaurants or facilities if relevant"
```

**Language-specific guidelines:**
```yaml
style_guidelines:
  - "Use simple, clear language suitable for non-native speakers"
  - "Avoid idioms and cultural references that may not translate"
  - "Define any specialized terms when first used"
```

## Complete Examples

### Example 1: Family-Friendly Tours

```yaml
content_generation:
  system_prompt: |
    You are an enthusiastic tour guide creating fun, educational audio scripts for families.
    Engage both kids (8-12) and adults with fascinating stories and cool facts.

  style_guidelines:
    - "Write in an upbeat, enthusiastic tone"
    - "Length: 150-200 words (about 1 minute)"
    - "Include 2-3 'fun facts' that kids will love"
    - "Use simple language but don't talk down to children"
    - "Make dates relatable - '100 years ago' not '1924'"
    - "Compare sizes to things kids know (school buses, basketball courts, etc.)"
    - "Ask rhetorical questions to engage listeners"
    - "Mention restrooms, snack areas, or kid-friendly facilities nearby"
    - "NO scary or violent details"
```

### Example 2: Photography Focus

```yaml
content_generation:
  system_prompt: |
    You are a tour guide who specializes in helping tourists capture amazing photos.
    Create audio scripts that highlight the best photo opportunities and visual features.

  style_guidelines:
    - "Conversational and helpful tone"
    - "Length: 200-250 words"
    - "Always mention the best photo spots and angles"
    - "Describe visual details: colors, lighting, composition"
    - "Suggest best times of day for photography"
    - "Note any photography restrictions or permits needed"
    - "Include interesting visual details tourists might miss"
    - "Mention Instagram-worthy features"
```

### Example 3: Historical Deep-Dive

```yaml
content_generation:
  system_prompt: |
    You are a historian creating detailed audio tours for educated tourists.
    Provide rich historical context with specific dates, names, and events.

  style_guidelines:
    - "Scholarly but accessible tone"
    - "Length: 400-500 words (3-4 minutes)"
    - "Include specific dates, names, and historical events"
    - "Provide both immediate and broader historical context"
    - "Mention architectural styles and artistic movements"
    - "Reference primary sources or historical documents when relevant"
    - "Connect to larger historical trends and themes"
    - "Still maintain a conversational flow for audio"
```

## How It Works

When you run the `generate` command, the system:

1. Takes your **system prompt** and sends it to the AI to establish its role
2. Builds a user prompt with:
   - POI name and location
   - Any description or interests you provided
   - All your **style guidelines** as requirements
3. The AI generates content following both the system prompt and guidelines

## Testing Your Changes

After updating `config.yaml`:

```bash
# Test with a simple POI
python src/cli.py generate \
  --city "Test City" \
  --poi "Test Monument" \
  --description "A famous landmark"

# Review the output to see if it matches your expectations
cat content/test-city/test-monument/transcript.txt
```

## Tips

1. **Start with defaults** - Modify incrementally rather than starting from scratch
2. **Be specific** - Vague guidelines like "be interesting" are less effective than "include 2-3 surprising facts"
3. **Test with different POIs** - Make sure your prompts work for various types of locations
4. **Consider your audience** - Tailor the system prompt to who will use your tours
5. **Balance length** - Longer doesn't always mean better; match length to use case
6. **Include examples** - In guidelines, show what you mean (e.g., "'1700 years ago' instead of '300 AD'")

## Advanced: Per-Generation Customization

You can also use custom prompts for individual POIs:

```bash
python src/cli.py generate \
  --city "Rome" \
  --poi "Colosseum" \
  --custom-prompt "Create an exciting, dramatic tour guide script about gladiator battles in the Colosseum. Make it thrilling but historically accurate. 200 words."
```

This overrides both the system prompt and style guidelines for that specific generation.

## Troubleshooting

**AI ignoring guidelines:**
- Make guidelines more specific and directive
- Use stronger language ("MUST" instead of "should")
- Reduce the number of guidelines (AI can only handle so many rules)

**Output too similar despite different prompts:**
- Make your system prompt more distinctive
- Add unique guidelines that create clear differences
- Consider using different AI providers (Claude vs GPT-4)

**Output in wrong language:**
- Explicitly specify language in both system prompt and guidelines
- Use the `--language` flag when generating

## Need Help?

- Check `config.example.yaml` for the default configuration
- See example outputs in the `content/` directory
- Open an issue on GitHub with your use case

---

Happy customizing! 🎨
