# Example Transcripts

This directory contains gold-standard examples of excellent tour guide transcripts. These examples demonstrate the storytelling quality we aim to achieve with AI-generated content.

## Files

### `arch-of-galerius-gold-standard.txt`
- **Location**: Arch of Galerius (Kamara), Thessaloniki, Greece
- **Quality**: ⭐⭐⭐⭐⭐ Gold Standard
- **Created**: Manually refined through multiple iterations
- **Why it's excellent**:
  - Opens with a clear "cheat sheet" of learning objectives
  - Frames narrative around two big questions
  - Gives historical figure (Galerius) a personality ("The Tough Guy")
  - Includes specific dramatic details (running in dust for a mile)
  - Uses modern analogies (Amazon managers, Instagram filters, Times Square)
  - Has clear emotional arc (humiliation → redemption → ironic ending)
  - Direct audience engagement ("Imagine...", "Close your eyes...")
  - Structured with clear parts (Part 1, Part 2, etc.)
  - Returns to opening questions for closure
  - Includes unexpected twist ending

## Usage

These examples are referenced in `config.yaml` as templates for the AI to follow:

```yaml
content_generation:
  system_prompt: |
    EXAMPLE OF GOLD STANDARD:
    See examples/arch-of-galerius-gold-standard.txt for a perfect example of this style.
    Your transcript should have similar energy, drama, and engagement.
```

## Contributing New Examples

When you create an excellent transcript (either manually or through AI generation), add it to this directory with:

1. Descriptive filename: `[poi-name]-[quality-level].txt`
2. Update this README with details about why it's excellent
3. Consider referencing it in your config.yaml prompts

## Quality Checklist

A gold-standard transcript should have:

- [ ] Opening "cheat sheet" with 2-3 learning objectives
- [ ] 1-2 "Big Questions" that frame the narrative
- [ ] Clear personality for main historical figure
- [ ] Specific dramatic details (numbers, distances, embarrassing moments)
- [ ] At least 2 modern analogies
- [ ] Emotional arc (setup → conflict → climax → resolution → twist)
- [ ] Direct engagement commands ("Imagine...", "Close your eyes...")
- [ ] Clear section structure (Part 1, Part 2, etc.)
- [ ] Twist or unexpected ending
- [ ] Callbacks to opening questions
- [ ] Zero empty adjectives ("magnificent", "impressive")
- [ ] Conversational, not academic tone
