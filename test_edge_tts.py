"""
Test script to debug Edge TTS for Taiwanese Mandarin
"""
import asyncio
from pathlib import Path


async def test_edge_tts():
    """Test Edge TTS with Taiwan voices"""
    try:
        import edge_tts
        print("✓ edge-tts library imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import edge-tts: {e}")
        return

    # Test text in Traditional Chinese
    test_text = "歡迎來到台北101。這是台灣最著名的地標之一，高度達到508公尺。"

    # Taiwan voices to test
    taiwan_voices = [
        'zh-TW-HsiaoChenNeural',  # Female, clear, young
        'zh-TW-HsiaoYuNeural',    # Female, warm, friendly
        'zh-TW-YunJheNeural'      # Male, clear, professional
    ]

    output_dir = Path("test_audio")
    output_dir.mkdir(exist_ok=True)

    print(f"\nTesting Edge TTS with Taiwan voices...")
    print(f"Test text: {test_text}\n")

    for voice in taiwan_voices:
        try:
            output_file = output_dir / f"test_{voice}.mp3"
            print(f"Testing voice: {voice}")

            # Create Edge TTS communicate object
            communicate = edge_tts.Communicate(test_text, voice, rate="+0%")

            # Generate audio
            await communicate.save(str(output_file))

            if output_file.exists():
                size_kb = output_file.stat().st_size / 1024
                print(f"  ✓ Success! File: {output_file.name} ({size_kb:.1f} KB)\n")
            else:
                print(f"  ✗ Failed: File not created\n")

        except Exception as e:
            print(f"  ✗ Error: {e}\n")

    # Also list all available Taiwan voices
    print("\nListing all available Taiwan (zh-TW) voices...")
    try:
        voices = await edge_tts.list_voices()
        taiwan_voices_full = [v for v in voices if v['Locale'].startswith('zh-TW')]

        print(f"Found {len(taiwan_voices_full)} Taiwan voices:\n")
        for v in taiwan_voices_full:
            print(f"  {v['ShortName']}")
            print(f"    Gender: {v['Gender']}")
            print(f"    Locale: {v['Locale']}")
            print(f"    Name: {v['Name']}\n")
    except Exception as e:
        print(f"✗ Failed to list voices: {e}")


def main():
    """Run the async test"""
    print("=" * 60)
    print("Edge TTS Test for Taiwanese Mandarin")
    print("=" * 60 + "\n")

    try:
        asyncio.run(test_edge_tts())
    except RuntimeError as e:
        if "Event loop is closed" in str(e) or "asyncio.run()" in str(e):
            print("\n⚠️  Event loop issue detected!")
            print("This might be the problem. Trying alternative approach...\n")

            # Try with explicit event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(test_edge_tts())
            finally:
                loop.close()
        else:
            raise

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
