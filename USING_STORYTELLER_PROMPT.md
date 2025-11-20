# Using the Storyteller Prompt System

## Quick Start

### Option 1: Replace Your Current Config

```bash
# Backup your current config
cp config.yaml config.backup.yaml

# Copy the storyteller config
cp config.storyteller.yaml config.yaml

# Add your API keys to config.yaml
nano config.yaml
```

### Option 2: Update Just the Content Generation Section

Open your existing `config.yaml` and replace the `content_generation:` section with the one from `config.storyteller.yaml`.

---

## What You Get

### The Storyteller Prompt Creates:

✅ **Engaging narratives** with drama, humor, and human stories
✅ **Modern analogies** connecting history to today's world
✅ **8-part structure** that hooks, informs, and surprises
✅ **Conversational tone** like a witty friend, not a textbook
✅ **Visible evidence** pointing to real details they can see
✅ **Propaganda reveals** showing "fake news" from 2000 years ago
✅ **Ironic twists** that make the story memorable

---

## How to Use It

### Basic Generation

```bash
python src/cli.py generate \
  --city "Rome" \
  --poi "Colosseum" \
  --provider openai \
  --description "Built by Emperor Vespasian on site of Nero's Golden House to win public favor"
```

The AI will automatically follow the storyteller structure!

### For Best Results

**Provide "juicy context" in the description:**

```bash
python src/cli.py generate \
  --city "Rome" \
  --poi "Colosseum" \
  --provider anthropic \
  --description "Built 80 AD by Emperor Vespasian. The twist: he built it on the exact spot of Nero's hated Golden House palace. It was ancient Rome's biggest PR stunt—tearing down a tyrant's mansion to build a stadium for the people. Vespasian died before it was finished; his son Titus took all the credit." \
  --interests "politics,propaganda,irony"
```

**The richer the context, the better the story!**

---

## Example Output

### Input:
```bash
python src/cli.py generate \
  --city "Paris" \
  --poi "Eiffel Tower" \
  --description "Built 1889 for World's Fair by Gustave Eiffel. Parisians hated it, called it ugly. Almost torn down in 1909 but saved because it made a good radio tower." \
  --interests "engineering,controversy"
```

### Output:
```
Summary - What visitors will learn:
  1. The tower was almost torn down—saved only because it was useful for radio
  2. Built 135 years ago as a "temporary" World's Fair entrance that became permanent
  3. Used revolutionary iron lattice engineering—ancient Rome's concrete of the 19th century
  4. Parisians hated it at first, calling it an "metal monstrosity"
  5. Modern irony: The "eyesore" is now the symbol of Paris

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRANSCRIPT:

Before we begin, three things you'll learn today:
• This "symbol of Paris" was almost torn down
• The engineer who built it never meant it to be permanent
• What looks like cutting-edge design was actually recycled technology

Two questions: Who was Gustave Eiffel? And why is this tower still here?

Imagine it's 1889. You're not at a peaceful park—you're at the entrance
to the World's Fair, and this metal tower rising 300 meters is supposed
to prove France is the world's engineering superpower. It's as tall as
an 81-story building, using a technique Eiffel "borrowed" from railway
bridges.

Here's the drama: Eiffel wasn't trying to build an icon. He was trying
to win a competition. The Eiffel Tower was supposed to be temporary—
like a World's Fair booth. But here's where it gets interesting: Parisians
HATED it. Artists wrote petitions calling it a "metal monstrosity."
Newspapers compared it to a half-finished factory. Eiffel's ego was crushed.

Now look at those iron beams. See how they're assembled? That's not
artistry—that's efficiency. Eiffel claimed he was creating a new architectural
style. The reality? He was recycling his bridge-building technique because
it was cheap and fast. The "elegant curves"? Those are just physics—the
optimal shape to handle wind. He marketed engineering as art. The 19th
century's first Instagram filter.

So, who was Eiffel? A brilliant marketer who sold functional design as
revolutionary. Why is the tower still here? Because in 1909, just as Paris
was about to tear it down, someone realized it made an excellent radio
antenna. Saved by technology, not beauty.

The final irony: The "temporary eyesore" is now the permanent symbol of
Paris, visited by 7 million people a year. Eiffel got the last laugh.

Next stop? Walk 500 meters to Trocadéro for the best photo angle—the
one Eiffel himself never got to see.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Tips for Maximum Impact

### 1. **Provide Rich Context**
Don't just say "historic building"—give the drama:
```
❌ "A temple built in 500 BC"
✅ "Built after a humiliating military defeat to beg the gods for help.
    The general who commissioned it died in battle before seeing it finished."
```

### 2. **Include the Irony**
Every good story has a twist:
```
❌ "It's now a museum"
✅ "The palace built to show off the king's power is now a museum
    where tourists mock his excess."
```

### 3. **Mention Visible Evidence**
Point to what they can actually see:
```
✅ "Notice the crack in the left column—that's from the 1755 earthquake"
✅ "See the inscription? Half of it was chiseled off when the new regime took over"
```

### 4. **Use the Right Provider**
- **Claude (Anthropic)**: Best for creative storytelling, humor, and emotional depth
- **GPT-4 (OpenAI)**: Best for balanced, well-structured narratives
- **Gemini (Google)**: Best for multilingual and culturally sensitive stories

```bash
# For maximum storytelling flair
--provider anthropic

# For consistency and reliability
--provider openai
```

---

## Customizing the Storyteller Prompt

### Add Your Own Rules

Edit `config.yaml` and add to `style_guidelines`:

```yaml
style_guidelines:
  # ... existing rules ...
  - "Always include a food or drink reference if relevant to the culture"
  - "Mention at least one woman or minority historical figure if possible"
  - "End with a question that makes them think"
```

### Adjust the Tone

Edit the `system_prompt` in `config.yaml`:

**For more humor:**
```yaml
system_prompt: |
  You are a hilariously witty tour guide who uses sarcasm and irony
  to make history unforgettable. Think Jon Stewart meets history professor.
```

**For families:**
```yaml
system_prompt: |
  You are an enthusiastic tour guide who makes history exciting for both
  kids (age 8-12) and adults. Use simple analogies and fun facts that
  make everyone say "Wow!"
```

**For deep dives:**
```yaml
system_prompt: |
  You are a scholarly yet engaging tour guide for serious history buffs.
  Provide depth and nuance while maintaining narrative flow and drama.
```

---

## Comparing Default vs. Storyteller

### Default Prompt Output:
```
The Colosseum is an ancient amphitheater in Rome, built between 70-80 AD
by Emperor Vespasian. It could hold 50,000 spectators and was used for
gladiatorial contests and public spectacles. The structure is made of
concrete and stone, featuring 80 arched entrances. It's one of Rome's
most iconic landmarks and a testament to Roman engineering.
```

### Storyteller Prompt Output:
```
Three things you'll learn: This building was ancient Rome's biggest PR
stunt, it was built on top of a hated emperor's palace, and the "generous"
emperor who built it never saw it finished.

Two questions: Who was Vespasian? And why build a stadium on this exact spot?

Imagine it's 72 AD. You're not at a quiet ruin—you're standing where Nero's
Golden House stood, a palace so massive it literally stole land from Roman
citizens. Vespasian just won a civil war, but he has a problem: nobody
trusts him. His solution? The world's first "give back to the community"
campaign. Tear down the tyrant's mansion, build a stadium FOR the people,
ON THE SAME SPOT. It's like turning a dictator's palace into a public park—
and making sure everyone knows about it.

See that marble? Looks expensive, right? Get closer. It's brick with a
thin marble veneer. The ancient version of a movie set—impressive from
far away, budget-friendly up close...
```

---

## Full Documentation

- **`STORYTELLER_PROMPT_GUIDE.md`** - Complete system with examples and techniques
- **`config.storyteller.yaml`** - Ready-to-use configuration file
- **This file** - Quick start guide

---

## Troubleshooting

### "The AI is ignoring the structure"
- Make sure you're using the full config from `config.storyteller.yaml`
- Try using Claude (`--provider anthropic`)—it follows complex instructions better
- Check that your `config.yaml` has the complete `style_guidelines` list

### "The output is too long/short"
Adjust the word count in `style_guidelines`:
```yaml
- "Total length: 150-200 words (60-90 seconds when spoken)"  # Shorter
- "Total length: 400-500 words (3-4 minutes when spoken)"    # Longer
```

### "Not enough humor/drama"
Make the system prompt more emphatic:
```yaml
system_prompt: |
  You are a WICKEDLY witty tour guide who NEVER misses a chance for
  irony, drama, or a perfectly-timed modern comparison.
```

### "Missing the ironic twist"
Provide the irony in your description:
```bash
--description "Built by King Louis XIV to show his power. Irony: 100 years
later, revolutionaries used it as a prison for the next king before executing him."
```

---

## Next Steps

1. **Copy the config**: `cp config.storyteller.yaml config.yaml`
2. **Add your API keys**
3. **Test it**: Generate content for a POI with rich context
4. **Refine**: Adjust the system prompt to match your preferred style
5. **Read the full guide**: `STORYTELLER_PROMPT_GUIDE.md` for advanced techniques

**Make history come alive!** 🎭🎪✨
