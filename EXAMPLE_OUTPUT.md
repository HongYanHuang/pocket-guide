# Example Output

This document shows what the generated content looks like with the summary points feature.

## Command

```bash
python src/cli.py generate \
  --city "Paris" \
  --poi "Eiffel Tower" \
  --provider openai \
  --interests "history,engineering"
```

## Terminal Output

```
✓ Content generated successfully!

Summary - What visitors will learn:
  1. The Eiffel Tower was built about 135 years ago for the 1889 World's Fair
  2. It was the world's tallest structure until 1930, standing 330 meters tall
  3. Gustave Eiffel used innovative iron lattice engineering techniques
  4. Initially criticized, it's now the most visited paid monument in the world
  5. Best views are at sunset, and you can visit three different levels

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Eiffel Tower - Paris
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Welcome to the iconic Eiffel Tower! Built about 135 years ago
for the 1889 World's Fair, this magnificent iron lattice tower
was designed by engineer Gustave Eiffel. At the time, it stood
as the world's tallest structure at 330 meters, holding that
title for over 40 years until 1930.

What makes this tower truly remarkable is the engineering
innovation behind it. Eiffel used a revolutionary iron lattice
design that was both strong and lightweight - a technique that
influenced modern architecture worldwide. The tower uses over
18,000 metal parts held together by 2.5 million rivets!

Interestingly, when it was first built, many Parisians hated
it, calling it an eyesore. But today, it's the most visited
paid monument in the world, with about 7 million visitors each
year. For the best experience, visit at sunset when the city
lights begin to twinkle. You can explore three levels, with
restaurants on the first and second levels, and an observation
deck at the top offering breathtaking views of Paris.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files saved to: content/paris/eiffel-tower
```

## Generated Files

### metadata.json
```json
{
  "city": "Paris",
  "poi": "Eiffel Tower",
  "provider": "openai",
  "language": "English",
  "description": null,
  "interests": [
    "history",
    "engineering"
  ],
  "summary_points": [
    "The Eiffel Tower was built about 135 years ago for the 1889 World's Fair",
    "It was the world's tallest structure until 1930, standing 330 meters tall",
    "Gustave Eiffel used innovative iron lattice engineering techniques",
    "Initially criticized, it's now the most visited paid monument in the world",
    "Best views are at sunset, and you can visit three different levels"
  ]
}
```

### transcript.txt
```
Welcome to the iconic Eiffel Tower! Built about 135 years ago
for the 1889 World's Fair, this magnificent iron lattice tower
was designed by engineer Gustave Eiffel...

[Full transcript as shown above]
```

### transcript.ssml
```xml
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
    <prosody rate="medium" pitch="medium">
        Welcome to the iconic Eiffel Tower! Built about 135 years ago
        for the 1889 World's Fair, this magnificent iron lattice tower
        was designed by engineer Gustave Eiffel...
    </prosody>
</speak>
```

### audio.mp3
(Generated audio file after running TTS command)

## Viewing POI Information

```bash
python src/cli.py info --city "Paris" --poi "Eiffel Tower"
```

Output:
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃           Eiffel Tower - Paris            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property   ┃ Value                        ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ city       │ Paris                        │
│ poi        │ Eiffel Tower                 │
│ provider   │ openai                       │
│ language   │ English                      │
│ interests  │ ['history', 'engineering']   │
│ Transcript │ ✓                            │
│ SSML       │ ✓                            │
│ Audio      │ ✓                            │
└────────────┴──────────────────────────────┘

Summary - What visitors will learn:
  1. The Eiffel Tower was built about 135 years ago for the 1889 World's Fair
  2. It was the world's tallest structure until 1930, standing 330 meters tall
  3. Gustave Eiffel used innovative iron lattice engineering techniques
  4. Initially criticized, it's now the most visited paid monument in the world
  5. Best views are at sunset, and you can visit three different levels
```

## Benefits of Summary Points

1. **Quick Overview** - Instantly see what the POI covers without reading the full transcript
2. **Content Validation** - Verify the AI included the topics you wanted
3. **User Interface** - Can be used to show preview/highlights in a future web app
4. **Content Organization** - Makes it easy to categorize and search POIs by topics
5. **Quality Control** - Ensure each POI has 3-5 clear learning points

## Customization

The AI automatically generates these points based on the transcript content. The number and style can be influenced by your system prompt in `config.yaml`:

```yaml
content_generation:
  style_guidelines:
    # ... other guidelines ...
    - "Generate 3-5 clear, actionable summary points"
    - "Summary points should highlight unique or surprising facts"
    - "Include at least one practical visitor tip in the summary"
```
