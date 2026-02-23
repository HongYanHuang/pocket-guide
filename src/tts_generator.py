"""
Text-to-Speech Generation
Supports: OpenAI TTS, Google Cloud TTS, Edge TTS (free)
"""
import asyncio
from pathlib import Path
from typing import Dict, Any
import os


class TTSGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tts_config = config.get('tts_providers', {})

    def generate(
        self,
        text: str,
        output_path: Path,
        provider: str = None,
        language: str = None,
        voice: str = None
    ) -> str:
        """
        Generate audio from text using specified TTS provider

        Args:
            text: Text to convert to speech
            output_path: Path where MP3 file should be saved
            provider: TTS provider (openai, google, edge)
            language: Language code (e.g., en-US, es-ES)
            voice: Voice name/ID (provider-specific)

        Returns:
            Path to generated audio file
        """
        if provider is None:
            provider = self.config.get('defaults', {}).get('tts_provider', 'edge')

        if language is None:
            language = self.config.get('defaults', {}).get('language', 'en-US')

        # Generate audio based on provider
        if provider == 'openai':
            return self._generate_openai(text, output_path, voice)
        elif provider == 'google':
            return self._generate_google(text, output_path, language, voice)
        elif provider == 'edge':
            return self._generate_edge(text, output_path, language, voice)
        elif provider == 'qwen':
            return self._generate_qwen(text, output_path, language, voice)
        else:
            raise ValueError(f"Unsupported TTS provider: {provider}")

    def _generate_openai(self, text: str, output_path: Path, voice: str = None) -> str:
        """Generate audio using OpenAI TTS"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("OpenAI library not installed. Run: pip install openai")

        config = self.tts_config.get('openai', {})
        api_key = config.get('api_key')

        if not api_key:
            raise ValueError("OpenAI API key not configured")

        if voice is None:
            voice = config.get('voice', 'alloy')

        client = OpenAI(api_key=api_key)

        # OpenAI TTS supports: alloy, echo, fable, onyx, nova, shimmer
        response = client.audio.speech.create(
            model="tts-1",  # or tts-1-hd for higher quality
            voice=voice,
            input=text
        )

        # Language-specific audio file naming
        if language:
            lang_code = language.lower().replace('_', '-')
            output_file = output_path / f"audio_{lang_code}.mp3"
        else:
            output_file = output_path / "audio.mp3"
        response.stream_to_file(str(output_file))

        return str(output_file)

    def _generate_google(
        self,
        text: str,
        output_path: Path,
        language: str = "en-US",
        voice: str = None
    ) -> str:
        """Generate audio using Google Cloud TTS"""
        try:
            from google.cloud import texttospeech
        except ImportError:
            raise ImportError(
                "Google Cloud TTS library not installed. "
                "Run: pip install google-cloud-texttospeech"
            )

        config = self.tts_config.get('google', {})
        credentials_file = config.get('credentials_file')

        if credentials_file:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_file

        if voice is None:
            voice = config.get('voice_name', 'en-US-Neural2-F')

        client = texttospeech.TextToSpeechClient()

        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice_params = texttospeech.VoiceSelectionParams(
            language_code=language,
            name=voice
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config
        )

        # Language-specific audio file naming
        if language:
            lang_code = language.lower().replace('_', '-')
            output_file = output_path / f"audio_{lang_code}.mp3"
        else:
            output_file = output_path / "audio.mp3"
        with open(output_file, 'wb') as out:
            out.write(response.audio_content)

        return str(output_file)

    def _generate_edge(
        self,
        text: str,
        output_path: Path,
        language: str = "en-US",
        voice: str = None
    ) -> str:
        """Generate audio using Edge TTS (free, no API key needed)"""
        try:
            import edge_tts
        except ImportError:
            raise ImportError("Edge TTS library not installed. Run: pip install edge-tts")

        config = self.tts_config.get('edge', {})

        if voice is None:
            voice = config.get('voice', self._get_default_edge_voice(language))

        # Language-specific audio file naming
        if language:
            lang_code = language.lower().replace('_', '-')
            output_file = output_path / f"audio_{lang_code}.mp3"
        else:
            output_file = output_path / "audio.mp3"

        # Edge TTS requires async
        asyncio.run(self._edge_tts_async(text, str(output_file), voice))

        return str(output_file)

    @staticmethod
    async def _edge_tts_async(text: str, output_file: str, voice: str):
        """Async helper for Edge TTS"""
        import edge_tts

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)

    def _get_default_edge_voice(self, language: str) -> str:
        """Get default Edge TTS voice for a language"""
        # Map language codes to default Edge voices
        voice_map = {
            'en-US': 'en-US-AriaNeural',
            'en-GB': 'en-GB-SoniaNeural',
            'es-ES': 'es-ES-ElviraNeural',
            'es-MX': 'es-MX-DaliaNeural',
            'fr-FR': 'fr-FR-DeniseNeural',
            'de-DE': 'de-DE-KatjaNeural',
            'it-IT': 'it-IT-ElsaNeural',
            'pt-PT': 'pt-PT-RaquelNeural',
            'pt-BR': 'pt-BR-FranciscaNeural',
            'zh-CN': 'zh-CN-XiaoxiaoNeural',
            'zh-TW': 'zh-TW-HsiaoChenNeural',
            'ja-JP': 'ja-JP-NanamiNeural',
            'ko-KR': 'ko-KR-SunHiNeural',
            'ru-RU': 'ru-RU-SvetlanaNeural',
            'ar-SA': 'ar-SA-ZariyahNeural',
            'hi-IN': 'hi-IN-SwaraNeural',
            'nl-NL': 'nl-NL-ColetteNeural',
            'pl-PL': 'pl-PL-ZofiaNeural',
            'tr-TR': 'tr-TR-EmelNeural',
            'vi-VN': 'vi-VN-HoaiMyNeural',
            'th-TH': 'th-TH-PremwadeeNeural',
        }
        return voice_map.get(language, 'en-US-AriaNeural')

    @staticmethod
    def list_edge_voices() -> list:
        """List all available Edge TTS voices"""
        try:
            import edge_tts
        except ImportError:
            raise ImportError("Edge TTS library not installed. Run: pip install edge-tts")

        voices = asyncio.run(edge_tts.list_voices())
        return voices

    def _generate_qwen(
        self,
        text: str,
        output_path: Path,
        language: str = "Chinese",
        voice: str = None
    ) -> str:
        """Generate audio using Qwen3-TTS (free, local model)"""
        try:
            from qwen_tts import Qwen3TTSModel
            import torch
            import soundfile as sf
        except ImportError:
            raise ImportError(
                "Qwen TTS library not installed. Run: pip install qwen-tts\n"
                "Note: Requires PyTorch with GPU support (CUDA for NVIDIA, MPS for Apple Silicon)"
            )

        config = self.tts_config.get('qwen', {})

        # Get configuration
        model_name = config.get('model', 'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice')
        mode = config.get('mode', 'custom_voice')  # custom_voice, voice_design, or voice_clone

        # Auto-detect device if not specified
        device_config = config.get('device', 'auto')
        if device_config == 'auto':
            if torch.cuda.is_available():
                device = 'cuda:0'
            elif torch.backends.mps.is_available():
                device = 'mps'
            else:
                device = 'cpu'
                print("[WARNING] No GPU acceleration available. Qwen3-TTS will be very slow on CPU.")
        else:
            device = device_config

        dtype_str = config.get('dtype', 'bfloat16')
        speaker = config.get('speaker', voice or 'Vivian')
        instruction = config.get('instruction', '')

        # Convert dtype string to torch dtype
        dtype_map = {
            'float32': torch.float32,
            'float16': torch.float16,
            'bfloat16': torch.bfloat16,
        }
        dtype = dtype_map.get(dtype_str, torch.bfloat16)

        # Map language locale to Qwen language name
        qwen_language = self._get_qwen_language(language)

        # Load model (cached after first load)
        if not hasattr(self, '_qwen_model') or self._qwen_model is None:
            print(f"Loading Qwen3-TTS model: {model_name}...")
            self._qwen_model = Qwen3TTSModel.from_pretrained(
                model_name,
                device_map=device,
                dtype=dtype,
            )
            print("Model loaded successfully!")

        # Generate audio based on mode
        if mode == 'custom_voice':
            wavs, sr = self._qwen_model.generate_custom_voice(
                text=text,
                language=qwen_language,
                speaker=speaker,
                instruct=instruction
            )
        elif mode == 'voice_design':
            wavs, sr = self._qwen_model.generate_voice_design(
                text=text,
                language=qwen_language,
                instruct=instruction or "Natural, clear voice"
            )
        elif mode == 'voice_clone':
            ref_audio = config.get('ref_audio', '')
            ref_text = config.get('ref_text', '')
            if not ref_audio or not ref_text:
                raise ValueError(
                    "voice_clone mode requires 'ref_audio' and 'ref_text' in config"
                )
            wavs, sr = self._qwen_model.generate_voice_clone(
                text=text,
                language=qwen_language,
                ref_audio=ref_audio,
                ref_text=ref_text
            )
        else:
            raise ValueError(f"Unsupported Qwen mode: {mode}")

        # Language-specific audio file naming
        if language:
            lang_code = language.lower().replace('_', '-')
            output_file = output_path / f"audio_{lang_code}.mp3"
        else:
            output_file = output_path / "audio.mp3"

        # Save audio (convert to mp3 using soundfile + pydub)
        temp_wav = output_path / "temp_qwen.wav"
        sf.write(str(temp_wav), wavs[0], sr)

        # Convert WAV to MP3
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_wav(str(temp_wav))
            audio.export(str(output_file), format="mp3", bitrate="192k")
            temp_wav.unlink()  # Remove temp WAV file
        except ImportError:
            # If pydub not available, just save as WAV
            import shutil
            shutil.move(str(temp_wav), str(output_file.with_suffix('.wav')))
            output_file = output_file.with_suffix('.wav')

        return str(output_file)

    def _get_qwen_language(self, language: str) -> str:
        """Convert language code to Qwen3-TTS language name"""
        # Map language codes to Qwen supported languages
        language_map = {
            'en-US': 'English',
            'en-GB': 'English',
            'zh-CN': 'Chinese',
            'zh-TW': 'Chinese',
            'ja-JP': 'Japanese',
            'ko-KR': 'Korean',
            'de-DE': 'German',
            'fr-FR': 'French',
            'ru-RU': 'Russian',
            'pt-PT': 'Portuguese',
            'pt-BR': 'Portuguese',
            'es-ES': 'Spanish',
            'es-MX': 'Spanish',
            'it-IT': 'Italian',
        }
        return language_map.get(language, 'English')
