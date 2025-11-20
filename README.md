# Pocket Guide CLI

AI-powered walking tour content generator. Create customized tour guide transcripts and audio for any city's points of interest using multiple AI providers.

## Features

- 🤖 **Multiple AI Providers**: Choose between OpenAI (GPT-4), Anthropic (Claude), or Google (Gemini) for content generation
- 🎙️ **Multiple TTS Options**: Generate audio using OpenAI TTS, Google Cloud TTS, or free Edge TTS
- 📁 **Organized Structure**: Automatic directory organization by city and POI
- 🌍 **Multilingual Support**: Generate content and audio in multiple languages
- 💾 **Multiple Formats**: Saves plain text, SSML, and MP3 audio files
- 🎨 **Beautiful CLI**: Rich terminal interface with colors and interactive prompts

## Installation

### 1. Clone the repository

```bash
cd pocket-guide
```

### 2. Set up Python environment

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API keys

```bash
# Copy example config
cp config.example.yaml config.yaml

# Edit config.yaml and add your API keys
nano config.yaml  # or use your preferred editor
```

**API Keys needed:**

- **OpenAI**: Get from https://platform.openai.com/api-keys
- **Anthropic**: Get from https://console.anthropic.com/
- **Google AI**: Get from https://makersuite.google.com/app/apikey
- **Google Cloud TTS**: (Optional) Set up at https://console.cloud.google.com/
- **Edge TTS**: No API key needed - it's free!

## Usage

### Basic Workflow

The typical workflow is:
1. Generate content (text) for a POI
2. Generate audio (TTS) from the content

### Commands

#### Generate Content for a POI

```bash
python src/cli.py generate --city "Paris" --poi "Eiffel Tower"
```

**Interactive mode** (will prompt for details):
```bash
python src/cli.py generate
```

**With options:**
```bash
python src/cli.py generate \
  --city "Paris" \
  --poi "Eiffel Tower" \
  --provider openai \
  --description "Iconic iron lattice tower built in 1889" \
  --interests "history,architecture" \
  --language "English"
```

**Available providers**: `openai`, `anthropic`, `google`

#### Generate Audio (TTS)

```bash
python src/cli.py tts --city "Paris" --poi "Eiffel Tower"
```

**With options:**
```bash
python src/cli.py tts \
  --city "Paris" \
  --poi "Eiffel Tower" \
  --provider edge \
  --language "en-US"
```

**Available TTS providers**: `openai`, `google`, `edge`

#### List Cities

```bash
python src/cli.py cities
```

#### List POIs in a City

```bash
python src/cli.py pois Paris
```

#### Show POI Information

```bash
python src/cli.py info --city "Paris" --poi "Eiffel Tower"
```

#### List Available Voices (Edge TTS)

```bash
python src/cli.py voices
```

## Directory Structure

After generating content, your files will be organized like this:

```
content/
├── paris/
│   ├── eiffel-tower/
│   │   ├── metadata.json      # POI metadata and generation settings
│   │   ├── transcript.txt     # Plain text transcript
│   │   ├── transcript.ssml    # SSML formatted for TTS
│   │   └── audio.mp3          # Generated audio
│   └── louvre/
│       ├── metadata.json
│       ├── transcript.txt
│       ├── transcript.ssml
│       └── audio.mp3
└── tokyo/
    └── senso-ji/
        └── ...
```

## Examples

### Example 1: Quick Start with Free Options

```bash
# Generate content using OpenAI (requires API key)
python src/cli.py generate \
  --city "Tokyo" \
  --poi "Senso-ji Temple" \
  --provider openai \
  --description "Ancient Buddhist temple in Asakusa"

# Generate audio using free Edge TTS
python src/cli.py tts \
  --city "Tokyo" \
  --poi "Senso-ji Temple" \
  --provider edge \
  --language "en-US"
```

### Example 2: High Quality with Claude + OpenAI TTS

```bash
# Generate content with Claude (best for conversational tone)
python src/cli.py generate \
  --city "Barcelona" \
  --poi "Sagrada Familia" \
  --provider anthropic \
  --interests "architecture,history,art"

# Generate audio with OpenAI TTS
python src/cli.py tts \
  --city "Barcelona" \
  --poi "Sagrada Familia" \
  --provider openai \
  --voice "nova"
```

### Example 3: Multilingual Content

```bash
# Generate Spanish content
python src/cli.py generate \
  --city "Madrid" \
  --poi "Prado Museum" \
  --provider google \
  --language "Spanish"

# Generate Spanish audio
python src/cli.py tts \
  --city "Madrid" \
  --poi "Prado Museum" \
  --provider edge \
  --language "es-ES"
```

### Example 4: Custom Prompt

```bash
python src/cli.py generate \
  --city "New York" \
  --poi "Statue of Liberty" \
  --custom-prompt "Create a fun, kid-friendly tour guide script about the Statue of Liberty. Include interesting facts that children would enjoy, keep it under 200 words, and use simple language."
```

## Cost Comparison

| Service | Cost | Quality | Notes |
|---------|------|---------|-------|
| **Content Generation** |
| OpenAI GPT-4 | ~$0.03 per POI | Excellent | Best balance |
| Claude Sonnet | ~$0.015 per POI | Excellent | Great for nuanced content |
| Gemini Pro | ~$0.002 per POI | Good | Most cost-effective |
| **Text-to-Speech** |
| Edge TTS | FREE | Good | No API key needed |
| OpenAI TTS | ~$0.0075 per POI | Very Good | Simple to use |
| Google Cloud TTS | ~$0.008 per POI | Excellent | Best multilingual |

*Estimates based on ~500 words per POI*

## Recommended Combos

### For Development/Testing
- Content: Gemini Pro (cheap)
- TTS: Edge TTS (free)
- **Total: ~$0.002 per POI**

### For Production (Budget)
- Content: Claude Sonnet
- TTS: OpenAI TTS
- **Total: ~$0.023 per POI**

### For Production (Premium)
- Content: GPT-4
- TTS: Google Cloud TTS
- **Total: ~$0.038 per POI**

## File Formats

### metadata.json
Contains POI information and generation settings:
```json
{
  "city": "Paris",
  "poi": "Eiffel Tower",
  "provider": "openai",
  "language": "English",
  "description": "...",
  "interests": ["history", "architecture"]
}
```

### transcript.txt
Plain text transcript suitable for reading:
```
Welcome to the Eiffel Tower, one of the most iconic structures in the world...
```

### transcript.ssml
SSML formatted transcript for advanced TTS control:
```xml
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
    <prosody rate="medium" pitch="medium">
        Welcome to the Eiffel Tower, one of the most iconic structures...
    </prosody>
</speak>
```

### audio.mp3
Generated audio file ready for playback.

## Troubleshooting

### ImportError: No module named 'openai'

Make sure you've installed dependencies:
```bash
pip install -r requirements.txt
```

### API Key Error

Check that your `config.yaml` has the correct API keys and they're not expired.

### Google Cloud TTS: Authentication Error

Set up Google Cloud credentials:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

Or specify the path in `config.yaml`:
```yaml
tts_providers:
  google:
    credentials_file: "/path/to/service-account-key.json"
```

### Edge TTS: No voices available

Edge TTS requires an internet connection. Make sure you're online.

## Advanced Usage

### Batch Processing

Create a script to generate multiple POIs:

```bash
#!/bin/bash

CITY="Paris"
POIS=("Eiffel Tower" "Louvre Museum" "Notre-Dame" "Arc de Triomphe")

for POI in "${POIS[@]}"; do
  echo "Processing: $POI"
  python src/cli.py generate --city "$CITY" --poi "$POI" --provider openai
  python src/cli.py tts --city "$CITY" --poi "$POI" --provider edge
done
```

### Using Different Voices

List available Edge TTS voices:
```bash
python src/cli.py voices
```

Use a specific voice:
```bash
python src/cli.py tts \
  --city "Paris" \
  --poi "Eiffel Tower" \
  --provider edge \
  --voice "en-GB-SoniaNeural"  # British accent
```

## Roadmap

See [PRD.md](PRD.md) for the full product roadmap. Phase 1 (this CLI) focuses on:
- ✅ Content generation with multiple AI providers
- ✅ TTS generation with multiple services
- ✅ Organized file structure
- ✅ Interactive CLI interface

Future phases will include:
- Progressive Web App (PWA)
- User preference customization
- Interactive maps
- Real-time tour guidance
- Offline mode

## Contributing

Contributions welcome! This is the foundation for a larger walking tour guide platform.

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Open an issue on GitHub
- Check [PRD.md](PRD.md) for project context
