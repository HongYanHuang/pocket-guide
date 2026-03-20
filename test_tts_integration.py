"""
Test TTS Generator integration with Taiwanese Mandarin
"""
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, 'src')

from tts_generator import TTSGenerator
from utils import load_config


def main():
    print("=" * 60)
    print("TTS Generator Integration Test")
    print("=" * 60 + "\n")

    # Load config
    try:
        config = load_config()
        print("✓ Config loaded successfully\n")
    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        return

    # Initialize TTS generator
    tts = TTSGenerator(config)
    print("✓ TTS Generator initialized\n")

    # Test text in Traditional Chinese
    test_text = """歡迎來到台北101。這座摩天大樓高508公尺，曾是世界最高建築。
從89樓觀景台，您可以360度俯瞰整個台北市的美景。
晴天時，甚至能看到遠處的陽明山和淡水河。"""

    # Create output directory
    output_dir = Path("test_audio_integration")
    output_dir.mkdir(exist_ok=True)

    print("Testing Edge TTS with language code: zh-TW")
    print(f"Test text preview: {test_text[:50]}...\n")

    # Test 1: Default Taiwan voice
    print("Test 1: Using default Taiwan voice (zh-TW-HsiaoChenNeural)")
    try:
        audio_file = tts.generate(
            text=test_text,
            output_path=output_dir,
            provider='edge',
            language='zh-TW'
        )
        print(f"  ✓ Success! Generated: {audio_file}")

        # Check file size
        file_path = Path(audio_file)
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            print(f"  ✓ File size: {size_kb:.1f} KB\n")
        else:
            print(f"  ✗ File not found: {audio_file}\n")
    except Exception as e:
        print(f"  ✗ Error: {e}\n")

    # Test 2: Specific voice (HsiaoYu - warmer voice)
    print("Test 2: Using specific voice (zh-TW-HsiaoYuNeural)")
    try:
        audio_file = tts.generate(
            text=test_text,
            output_path=output_dir,
            provider='edge',
            language='zh-TW',
            voice='zh-TW-HsiaoYuNeural'
        )
        print(f"  ✓ Success! Generated: {audio_file}")

        file_path = Path(audio_file)
        if file_path.exists():
            # Rename to avoid overwrite
            new_path = output_dir / "audio_zh-tw_HsiaoYu.mp3"
            file_path.rename(new_path)
            size_kb = new_path.stat().st_size / 1024
            print(f"  ✓ File size: {size_kb:.1f} KB")
            print(f"  ✓ Renamed to: {new_path.name}\n")
    except Exception as e:
        print(f"  ✗ Error: {e}\n")

    # Test 3: Male voice
    print("Test 3: Using male voice (zh-TW-YunJheNeural)")
    try:
        audio_file = tts.generate(
            text=test_text,
            output_path=output_dir,
            provider='edge',
            language='zh-TW',
            voice='zh-TW-YunJheNeural'
        )
        print(f"  ✓ Success! Generated: {audio_file}")

        file_path = Path(audio_file)
        if file_path.exists():
            # Rename to avoid overwrite
            new_path = output_dir / "audio_zh-tw_YunJhe.mp3"
            file_path.rename(new_path)
            size_kb = new_path.stat().st_size / 1024
            print(f"  ✓ File size: {size_kb:.1f} KB")
            print(f"  ✓ Renamed to: {new_path.name}\n")
    except Exception as e:
        print(f"  ✗ Error: {e}\n")

    print("=" * 60)
    print("All tests completed!")
    print(f"Audio files saved in: {output_dir.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
