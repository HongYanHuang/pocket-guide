# TTS Setup Guide

Complete guide to setting up and configuring Text-to-Speech providers for Pocket Guide.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Provider Comparison](#provider-comparison)
- [EdgeTTS Setup (Free)](#edgetts-setup-free)
- [Qwen3-TTS Setup (Free, Local)](#qwen3-tts-setup-free-local)
- [OpenAI TTS Setup](#openai-tts-setup)
- [Google Cloud TTS Setup](#google-cloud-tts-setup)
- [Configuration Guide](#configuration-guide)
- [Advanced Voice Control](#advanced-voice-control)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Fastest Setup (No Installation Required)

**EdgeTTS** works out of the box:

```bash
# Install edge-tts
pip install "edge-tts>=6.1.0,<7.0.0"

# Generate TTS
./pocket-guide trip tts <tour-id> --city <city>
```

### Best Quality (Free, Requires GPU)

**Qwen3-TTS** offers superior voice control:

```bash
# Install PyTorch with CUDA
pip install torch --index-url https://download.pytorch.org/whl/cu118

# Install Qwen3-TTS
pip install qwen-tts soundfile

# Generate TTS
./pocket-guide trip tts <tour-id> --city <city> --provider qwen
```

---

## 📊 Provider Comparison

| Provider | Cost | Quality | Setup | GPU | Languages | Voice Control |
|----------|------|---------|-------|-----|-----------|---------------|
| **EdgeTTS** | Free | Good | Easy | No | 100+ | Basic (voice selection) |
| **Qwen3-TTS** | Free | Excellent | Moderate | Yes | 10 | Advanced (emotion, tone, speed) |
| **OpenAI** | Paid | Excellent | Easy | No | 50+ | Moderate (voice, speed) |
| **Google Cloud** | Paid | Excellent | Complex | No | 40+ | Advanced (pitch, rate, volume) |

### When to Use Each Provider

- **EdgeTTS**: Quick testing, no GPU available, simple use cases
- **Qwen3-TTS**: Production quality, need emotional control, multilingual, have GPU
- **OpenAI**: Need API convenience, don't want to manage local models
- **Google Cloud**: Enterprise deployment, need precise voice control

---

## 🎯 EdgeTTS Setup (Free)

### Installation

```bash
pip install "edge-tts>=6.1.0,<7.0.0"
```

### Configuration

EdgeTTS is configured in `config.yaml`:

```yaml
tts_providers:
  edge:
    enabled: true
    # voice: "en-US-AriaNeural"  # Optional: hardcode a voice
```

**Comment out the `voice` setting** to enable automatic language-based voice selection.

### Available Voices

List all voices:
```bash
python -m edge_tts --list-voices
```

Popular voices by language:
- **English (US)**: `en-US-AriaNeural` (friendly female), `en-US-GuyNeural` (male)
- **Chinese (Simplified)**: `zh-CN-XiaoxiaoNeural` (female)
- **Chinese (Traditional)**: `zh-TW-HsiaoChenNeural` (female)
- **Japanese**: `ja-JP-NanamiNeural` (female)
- **Korean**: `ko-KR-SunHiNeural` (female)

### Usage

```bash
# Use default provider (EdgeTTS)
./pocket-guide trip tts <tour-id> --city <city>

# Explicit provider selection
./pocket-guide trip tts <tour-id> --city <city> --provider edge

# With specific language
./pocket-guide trip tts <tour-id> --city <city> --language zh-tw
```

### Limitations

- Basic tone control (choose appropriate voice)
- No emotion/instruction parameters
- Occasional 403 errors (Microsoft rate limiting)

---

## 🎨 Qwen3-TTS Setup (Free, Local)

### System Requirements

- **GPU**: NVIDIA GPU with CUDA support
- **VRAM**:
  - 1GB for 0.6B model
  - 3GB for 1.7B model (recommended)
- **Storage**: ~5GB for model download
- **RAM**: 8GB+ recommended

### Installation

#### Step 1: Install PyTorch with CUDA

```bash
# For CUDA 11.8
pip install torch --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch --index-url https://download.pytorch.org/whl/cu121

# Verify CUDA is available
python -c "import torch; print(torch.cuda.is_available())"
```

#### Step 2: Install Qwen3-TTS

```bash
pip install qwen-tts soundfile pydub
```

#### Step 3: Verify Installation

```bash
python << EOF
from qwen_tts import Qwen3TTSModel
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}")
print("Qwen3-TTS installed successfully!")
EOF
```

### Configuration

#### Basic Configuration (`config.yaml`)

```yaml
tts_providers:
  qwen:
    enabled: true
    model: "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
    mode: "custom_voice"
    device: "cuda:0"
    dtype: "bfloat16"
    speaker: "Vivian"
    instruction: ""
```

#### Advanced Configuration (`tts_config.yaml`)

See the comprehensive `tts_config.yaml` file for detailed settings including:
- Multiple generation modes
- Voice design parameters
- Voice cloning settings
- Emotion and tone control
- Use case examples

### Available Modes

#### 1. Custom Voice Mode (Recommended)

Use pre-defined speakers with instruction-based control:

```yaml
qwen:
  mode: "custom_voice"
  model: "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
  speaker: "Vivian"  # or Serena, Uncle_Fu, Dylan, Eric, etc.
  instruction: "Speak in an enthusiastic, friendly tour guide voice"
```

**Available Speakers:**
- **Vivian**: Young female, clear pronunciation
- **Serena**: Mature female, warm tone
- **Uncle_Fu**: Middle-aged male, deep voice
- **Dylan**: Young male, energetic
- **Eric**: Mature male, authoritative
- **Ryan**: Young male, casual
- **Aiden**: Young male, friendly
- **Ono_Anna**: Female, Japanese accent
- **Sohee**: Female, Korean accent

#### 2. Voice Design Mode

Create custom voices with natural language descriptions:

```yaml
qwen:
  mode: "voice_design"
  model: "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
  voice_design:
    description: "Middle-aged female voice with British accent, warm and motherly tone, gentle speaking style, clear enunciation, slightly slower pace"
```

#### 3. Voice Clone Mode

Clone voices from reference audio:

```yaml
qwen:
  mode: "voice_clone"
  model: "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
  voice_clone:
    ref_audio: "path/to/reference.wav"
    ref_text: "Exact transcript of reference audio"
```

### Emotion & Tone Control

Qwen3-TTS supports natural language instructions for fine-grained control:

```yaml
# Examples of instruction parameter

# Emotions
instruction: "Speak in a very excited and enthusiastic tone, as if discovering something amazing"
instruction: "Use a calm, soothing voice with gentle reassurance"
instruction: "Angry and frustrated tone with harsh emphasis"
instruction: "Mysterious and enigmatic voice, hushed and secretive"

# Speaking characteristics
instruction: "Fast-paced energetic narration with dramatic emphasis"
instruction: "Slow, contemplative reading with long pauses"
instruction: "Professional news anchor voice, clear and authoritative"
instruction: "Warm storyteller voice with varied emotional expression"

# Combined
instruction: "Young female voice, cheerful and friendly, speaking at moderate pace with clear pronunciation"
```

### Usage

```bash
# Basic usage with Qwen
./pocket-guide trip tts <tour-id> --city <city> --provider qwen

# Specific POI with Qwen
./pocket-guide trip tts <tour-id> --city <city> --poi colosseum --provider qwen

# Force regeneration
./pocket-guide trip tts <tour-id> --city <city> --provider qwen --force
```

### Model Selection

Choose model based on your GPU:

```yaml
# Small model - 1GB VRAM, faster, good quality
model: "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"

# Large model - 3GB VRAM, best quality (recommended)
model: "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
```

First run will download the model (~5GB). Subsequent runs are fast as model stays cached.

---

## 💳 OpenAI TTS Setup

### Prerequisites

- OpenAI account with API access
- API key from https://platform.openai.com/api-keys

### Installation

```bash
pip install "openai>=1.12.0"
```

### Configuration

Add API key to `config.yaml`:

```yaml
tts_providers:
  openai:
    enabled: true
    api_key: "sk-proj-your-api-key-here"
    voice: "alloy"
    model: "tts-1-hd"
    speed: 1.0
```

### Available Voices

- **alloy**: Neutral, balanced (good for general use)
- **echo**: Warm, conversational male
- **fable**: Energetic, expressive British accent
- **onyx**: Deep, authoritative male
- **nova**: Vibrant, enthusiastic female
- **shimmer**: Warm, clear female

### Usage

```bash
./pocket-guide trip tts <tour-id> --city <city> --provider openai
```

### Pricing

- **tts-1**: $15 per 1M characters (~667 hours of audio)
- **tts-1-hd**: $30 per 1M characters (~667 hours of audio)

For a 500-word tour script (~3000 characters):
- Cost: ~$0.045 per tour (tts-1) or $0.09 per tour (tts-1-hd)

---

## ☁️ Google Cloud TTS Setup

### Prerequisites

1. Google Cloud account
2. Enable Cloud Text-to-Speech API
3. Create service account and download JSON key

### Installation

```bash
pip install "google-cloud-texttospeech>=2.14.0"
```

### Configuration

```yaml
tts_providers:
  google:
    enabled: true
    credentials_file: "path/to/service-account-key.json"
    voice_name: "en-US-Neural2-F"
    language_code: "en-US"
    speaking_rate: 1.0
    pitch: 0.0
    volume_gain_db: 0.0
```

### Setup Steps

1. Go to https://console.cloud.google.com
2. Create new project or select existing
3. Enable "Cloud Text-to-Speech API"
4. Create service account:
   - IAM & Admin > Service Accounts > Create Service Account
   - Grant role: "Cloud Text-to-Speech User"
   - Create key (JSON) and download
5. Set path in config.yaml

### Usage

```bash
./pocket-guide trip tts <tour-id> --city <city> --provider google
```

---

## ⚙️ Configuration Guide

### Main Config File (`config.yaml`)

Basic TTS provider settings live in the main config file:

```yaml
# Default TTS provider
defaults:
  tts_provider: "edge"  # edge, qwen, openai, google

# Provider configurations
tts_providers:
  edge:
    enabled: true

  qwen:
    enabled: true
    model: "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
    mode: "custom_voice"
    device: "cuda:0"
    dtype: "bfloat16"
    speaker: "Vivian"
    instruction: ""

  openai:
    enabled: true
    api_key: "${OPENAI_API_KEY}"
    voice: "alloy"

  google:
    enabled: false
    credentials_file: ""
```

### Advanced TTS Config (`tts_config.yaml`)

Comprehensive settings for fine-tuned control:

- Voice characteristics for each provider
- Emotion and tone guides
- Language-specific recommendations
- Use case examples
- Performance optimization

See `tts_config.yaml` for complete documentation.

---

## 🎭 Advanced Voice Control

### Qwen3-TTS Instruction Examples

#### Tour Guide Scenarios

```yaml
# Enthusiastic Discovery
instruction: "Very excited and amazed tone, as if discovering something incredible for the first time, fast-paced energetic speech with dramatic emphasis"

# Professional Museum Guide
instruction: "Clear, authoritative voice with professional demeanor, moderate pace with deliberate emphasis on key facts, warm but formal"

# Dramatic Storyteller
instruction: "Engaging storytelling voice with varied emotional expression, building suspense with strategic pauses, theatrical delivery"

# Casual Friend
instruction: "Warm, friendly conversational tone as if chatting with a friend, relaxed pace, natural enthusiasm without being overly excited"
```

#### Emotion-Specific

```yaml
# Mystery & Intrigue
instruction: "Mysterious, hushed voice with secretive undertones, slow deliberate speech, building tension"

# Joy & Celebration
instruction: "Delighted, celebratory tone with bright energy, upbeat pacing, infectious enthusiasm"

# Solemnity & Reverence
instruction: "Solemn, respectful tone with gentle reverence, slow measured pace, quiet strength"

# Urgency & Excitement
instruction: "Urgent, breathless delivery with rising excitement, fast pace with dramatic emphasis"
```

#### Character Voices

```yaml
# Wise Elder
instruction: "Elderly wise voice, deep and experienced, slow contemplative speech with gravitas, slight raspy quality"

# Young Explorer
instruction: "Young enthusiastic voice, energetic and curious, fast-paced excited speech with wonder"

# Scholar/Professor
instruction: "Mature authoritative academic voice, clear precise pronunciation, measured intellectual tone"
```

### Voice Design Examples

Create completely custom voices:

```yaml
voice_design:
  # Vintage Radio Announcer
  description: "1940s radio announcer style, male voice with that classic mid-Atlantic accent, warm nostalgic tone, slightly deeper pitch with theatrical emphasis, as if narrating a documentary"

  # ASMR Narrator
  description: "Soft, intimate female voice with gentle whisper quality, very slow deliberate pace, warm soothing tone, minimal variation for calming effect"

  # Epic Movie Trailer
  description: "Deep powerful male voice, dramatic and intense, varied pacing with strategic pauses, building from quiet to intense, movie trailer narrator style"
```

---

## 🔧 Troubleshooting

### EdgeTTS Issues

**Problem**: 403 Forbidden errors

**Solutions**:
1. Upgrade edge-tts: `pip install --upgrade edge-tts`
2. Try different provider: `--provider qwen` or `--provider openai`
3. Wait and retry (Microsoft rate limiting)

**Problem**: Wrong voice for language

**Solution**:
1. Comment out hardcoded voice in `config.yaml`:
   ```yaml
   edge:
     # voice: "en-US-AriaNeural"  # Comment this out
   ```

### Qwen3-TTS Issues

**Problem**: CUDA out of memory

**Solutions**:
1. Use smaller model:
   ```yaml
   model: "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
   ```
2. Use float16 instead of bfloat16:
   ```yaml
   dtype: "float16"
   ```
3. Clear GPU memory:
   ```python
   import torch
   torch.cuda.empty_cache()
   ```

**Problem**: Model download fails

**Solutions**:
1. Check internet connection
2. Verify HuggingFace access (no login required for Qwen models)
3. Manual download:
   ```bash
   git lfs install
   git clone https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice
   ```

**Problem**: CPU too slow

**Solution**:
- Qwen3-TTS requires GPU for practical use
- Use EdgeTTS or OpenAI for CPU-only systems

### OpenAI Issues

**Problem**: Invalid API key

**Solutions**:
1. Verify key at https://platform.openai.com/api-keys
2. Check key in config.yaml is correct
3. Ensure key has TTS permissions
4. Check billing/credits

**Problem**: Rate limit exceeded

**Solutions**:
1. Wait and retry
2. Upgrade to paid tier
3. Use free alternative (EdgeTTS or Qwen)

### General Issues

**Problem**: Audio file not generated

**Solutions**:
1. Check transcript exists: `cat content/city/poi/transcript_lang.txt`
2. Verify output directory writable
3. Check for error messages in console
4. Try with `--force` flag

**Problem**: Poor audio quality

**Solutions**:
1. Use HD model (OpenAI: tts-1-hd, Google: Neural2 voices)
2. Adjust bitrate in config
3. Try different provider
4. For Qwen: use 1.7B model with bfloat16

---

## 📚 Additional Resources

- **Qwen3-TTS GitHub**: https://github.com/QwenLM/Qwen3-TTS
- **EdgeTTS Documentation**: https://github.com/rany2/edge-tts
- **OpenAI TTS API**: https://platform.openai.com/docs/guides/text-to-speech
- **Google Cloud TTS**: https://cloud.google.com/text-to-speech/docs

---

## 🎯 Recommended Setup by Use Case

### Personal/Testing
- **Provider**: EdgeTTS
- **Why**: Free, no setup, good quality
- **Setup time**: 2 minutes

### Production (with GPU)
- **Provider**: Qwen3-TTS
- **Why**: Free, excellent quality, full control
- **Setup time**: 15 minutes

### Production (no GPU)
- **Provider**: OpenAI TTS
- **Why**: API convenience, consistent quality
- **Setup time**: 5 minutes
- **Cost**: ~$0.05 per tour

### Enterprise
- **Provider**: Google Cloud TTS
- **Why**: Enterprise SLA, advanced control
- **Setup time**: 30 minutes
- **Cost**: Variable, enterprise pricing

---

**Need help?** Check the troubleshooting section or open an issue on GitHub.
