# Taiwan Accent & Fast Speech Configuration Guide

Complete guide to configure TTS for authentic Taiwan accent with faster speech.

---

## 🎯 Current Status

### Issues with Default Setup
- ❌ Qwen quality not good enough
- ❌ No authentic Taiwan accent
- ❌ Speech too slow

### Solutions Provided
- ✅ Taiwan accent configuration (台灣腔調)
- ✅ Faster speech speed (語速加快)
- ✅ Multiple options to try

---

## 📊 TTS Provider Comparison for Taiwan

| Provider | Taiwan Accent | Speed Control | Quality | Status |
|----------|---------------|---------------|---------|--------|
| **Qwen3-TTS (Custom Voice)** | Via instruction | Via instruction | Good | ✅ Working |
| **Qwen3-TTS (Voice Design)** | Native support | Built-in | Excellent | ✅ Working |
| **EdgeTTS** | Native voices | Rate parameter | Very Good | ⚠️ 403 errors |
| **OpenAI TTS** | No Taiwan voice | Speed parameter | Excellent | ⚠️ Paid |

---

## 🎤 Option 1: Qwen Custom Voice (Currently Active)

**Status**: ✅ Configured and ready

**Configuration** (`config.yaml`):
```yaml
qwen:
  enabled: true
  model: "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
  mode: "custom_voice"
  device: "auto"
  dtype: "bfloat16"
  speaker: "Dylan"  # Young male, energetic
  instruction: "用台灣口音的幽默風趣男性導遊語氣快速說話，語速要快，帶著戲劇性和諷刺感，像在講述有趣的歷史八卦，語調生動活潑，節奏明快，就像台灣的脫口秀主持人在講笑話"
```

**Pros**:
- ✅ Fast generation (model already loaded)
- ✅ Taiwan accent specified in instruction
- ✅ Faster speech via instruction
- ✅ Humorous tone

**Cons**:
- ⚠️ Taiwan accent may not be very authentic (relies on instruction)
- ⚠️ Limited control over exact accent

**Usage**:
```bash
./pocket-guide trip tts <tour-id> --city rome --provider qwen
```

---

## 🎨 Option 2: Qwen Voice Design (RECOMMENDED for Best Taiwan Accent)

**Status**: ⭐ **Highest quality Taiwan accent**

To enable this, edit `config.yaml`:

```yaml
qwen:
  enabled: true
  # Comment out custom_voice settings
  # model: "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
  # mode: "custom_voice"
  # speaker: "Dylan"
  # instruction: "..."

  # Enable voice_design instead
  model: "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
  mode: "voice_design"
  device: "auto"
  dtype: "bfloat16"
  voice_design:
    description: "台灣男性聲音，30歲左右，帶有明顯的台灣腔調和台灣國語的特色發音，說話速度很快，節奏明快，語調活潑幽默，像台灣的旅遊節目主持人或綜藝節目主持人，充滿活力和感染力，帶著台灣特有的親切感和輕鬆感"
```

**Key improvements in description**:
- `台灣腔調` (Taiwan accent)
- `台灣國語的特色發音` (Taiwan Mandarin pronunciation)
- `說話速度很快` (very fast speech speed)
- `節奏明快` (brisk pace)
- `台灣的旅遊節目主持人` (Taiwan travel show host style)

**Pros**:
- ✅ **Most authentic Taiwan accent**
- ✅ Custom-designed voice specifically for Taiwan
- ✅ Full control over voice characteristics
- ✅ Native Taiwan Mandarin pronunciation

**Cons**:
- ⚠️ Slightly slower generation (voice design takes longer)
- ⚠️ First time will download different model

**Usage**:
```bash
./pocket-guide trip tts <tour-id> --city rome --provider qwen
```

---

## 🏃 Option 3: Even Faster Speech

If you want **VERY FAST** speech (like auction announcer speed), use these instructions:

### For Custom Voice Mode:
```yaml
instruction: "用極快的台灣口音快速說話，語速要非常快像拍賣官或體育播報員，保持幽默風趣的男性導遊風格，節奏超快但咬字清晰，就像在趕時間講笑話"
```

### For Voice Design Mode:
```yaml
voice_design:
  description: "台灣男性聲音，30歲左右，說話速度極快像體育播報員或拍賣官，帶有明顯台灣腔調，節奏超快但咬字清晰，語調活潑幽默，充滿台灣特色的親切感"
```

**Speed levels**:
- 快速說話 (fast): ~1.2x normal
- 說話速度很快 (very fast): ~1.5x normal
- 速度極快 (extremely fast): ~1.8-2x normal

---

## 🎯 Option 4: EdgeTTS with Taiwan Voice (When 403 Fixed)

**Status**: ⚠️ Currently blocked by Microsoft (403 errors)

Once Microsoft fixes the blocking issue, you can use:

**Configuration** (`config.yaml`):
```yaml
edge:
  enabled: true
  voice: "zh-TW-YunJheNeural"  # Taiwan male voice
  rate: "+30%"  # 30% faster than normal
```

**Available Taiwan voices**:
- `zh-TW-YunJheNeural`: Male voice (雲哲)
- `zh-TW-HsiaoChenNeural`: Female voice (曉臻)
- `zh-TW-HsiaoYuNeural`: Female voice (曉雨)

**Speed control** (rate parameter):
- `-50%` to `+100%` (relative to normal speed)
- `+0%`: Normal speed
- `+20%`: 20% faster (recommended)
- `+30%` to `+50%`: Very fast

**Usage**:
```bash
./pocket-guide trip tts <tour-id> --city rome --provider edge
```

---

## 🎭 Recommended Setup by Priority

### Best Quality Taiwan Accent:
1. **Qwen Voice Design Mode** ⭐ (best Taiwan accent)
2. EdgeTTS with YunJheNeural (when 403 fixed)
3. Qwen Custom Voice Mode (current)

### Fastest Generation:
1. EdgeTTS (when working) - instant
2. Qwen Custom Voice (model cached) - ~10-20 sec
3. Qwen Voice Design (first time) - ~30-40 sec

### Best Overall Balance:
👉 **Qwen Voice Design Mode** - Best Taiwan accent with acceptable speed

---

## 🛠️ How to Switch Configuration

### Switch to Voice Design Mode (Recommended):

**Step 1**: Edit `config.yaml`:
```bash
nano config.yaml
# or
vim config.yaml
```

**Step 2**: Comment out custom_voice lines, uncomment voice_design:
```yaml
qwen:
  enabled: true

  # OPTION 1: Custom Voice Mode (faster, recommended)
  # model: "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
  # mode: "custom_voice"
  # device: "auto"
  # dtype: "bfloat16"
  # speaker: "Dylan"
  # instruction: "用台灣口音的幽默風趣男性導遊語氣快速說話..."

  # OPTION 2: Voice Design Mode (RECOMMENDED - better Taiwan accent)
  model: "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
  mode: "voice_design"
  device: "auto"
  dtype: "bfloat16"
  voice_design:
    description: "台灣男性聲音，30歲左右，帶有明顯的台灣腔調和台灣國語的特色發音，說話速度很快，節奏明快，語調活潑幽默，像台灣的旅遊節目主持人或綜藝節目主持人，充滿活力和感染力，帶著台灣特有的親切感和輕鬆感"
```

**Step 3**: Test it:
```bash
./pocket-guide trip tts <tour-id> --city rome --poi colosseum --provider qwen --force
```

---

## 📝 Quick Test Commands

### Test Current Setup (Custom Voice):
```bash
source pocket-guide-3.11/bin/activate
python3 << 'EOF'
import sys
sys.path.insert(0, 'src')
from pathlib import Path
from utils import load_config
from tts_generator import TTSGenerator

config = load_config()
tts_gen = TTSGenerator(config)

result = tts_gen.generate(
    text="嘿！羅馬競技場是古羅馬最大的作秀場所，皇帝們在這裡砸錢辦免費表演讓老百姓開心！",
    output_path=Path("/tmp"),
    language='zh-TW',
    provider='qwen'
)
print(f"Generated: {result}")
EOF
```

### Test Voice Design Mode:
(After switching config to voice_design)
```bash
source pocket-guide-3.11/bin/activate
python3 << 'EOF'
import sys
sys.path.insert(0, 'src')
from pathlib import Path
from utils import load_config
from tts_generator import TTSGenerator

config = load_config()
tts_gen = TTSGenerator(config)

result = tts_gen.generate(
    text="各位朋友大家好！今天要帶大家來看這個超酷的羅馬競技場，這可是兩千年前的超級巨蛋啊！",
    output_path=Path("/tmp"),
    language='zh-TW',
    provider='qwen'
)
print(f"Generated: {result}")
EOF
```

---

## 🎯 Fine-Tuning Tips

### For More Natural Taiwan Accent:

Add these keywords to voice_design description:
- `台灣國語` (Taiwan Mandarin)
- `捲舌音較輕` (lighter retroflex sounds)
- `輕聲使用較少` (less neutral tone)
- `語調較平緩` (flatter intonation pattern)
- `兒化音較少` (less -er suffixation)

### For Even Faster Speech:

Replace speed descriptions:
- `快速` → `極快` (fast → extremely fast)
- `說話速度很快` → `說話速度超快` (very fast → super fast)
- Add: `像體育播報員` (like sports commentator)
- Add: `像拍賣官` (like auctioneer)

### For Different Tones:

**Casual/Fun**:
```
像台灣綜藝節目主持人，輕鬆幽默，親切自然
```

**Professional but Entertaining**:
```
像Discovery頻道的台灣配音員，專業但生動有趣
```

**Very Energetic**:
```
像台灣的運動賽事播報員，充滿激情和活力
```

---

## ⚡ Performance Optimization

### Reduce Generation Time:

1. **Use smaller model** (if quality acceptable):
   ```yaml
   model: "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"  # Faster, 1GB VRAM
   ```

2. **Use float16 instead of bfloat16**:
   ```yaml
   dtype: "float16"  # Slightly faster, similar quality
   ```

3. **Keep model loaded** (automatic after first use):
   - First generation: ~10-30 seconds
   - Subsequent: ~5-10 seconds (model cached)

---

## 🐛 Troubleshooting

### "Quality not good" Issues:

**Problem**: Voice doesn't sound natural
**Solution**: Switch to voice_design mode for better accent control

**Problem**: Taiwan accent not authentic enough
**Solution**: Add more specific Taiwan characteristics to description:
```yaml
description: "標準的台灣國語發音，帶有台北腔調，輕捲舌，少兒化音，語調較平緩"
```

**Problem**: Speech too slow
**Solution**: Add speed keywords:
```yaml
description: "...說話速度極快，節奏超快，快速明快..."
```

**Problem**: Voice sounds robotic
**Solution**: Add emotional descriptors:
```yaml
description: "...充滿情感，自然親切，就像真人在面對面聊天..."
```

---

## 📞 Quick Reference

### Current Active Configuration:
- **Mode**: Custom Voice
- **Speaker**: Dylan
- **Taiwan Accent**: Via instruction
- **Speed**: Fast (specified in instruction)

### Recommended Next Step:
👉 **Switch to Voice Design Mode** for best Taiwan accent quality

### Command to Generate:
```bash
./pocket-guide trip tts <tour-id> --city rome --provider qwen
```

---

**Need help?** See the main `TTS_SETUP_GUIDE.md` or `tts_config.yaml` for more examples.
