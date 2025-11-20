#!/usr/bin/env python3
"""
Progressive test to identify what causes Google Gemini to return 0 parts
Starts with working simple case, adds complexity step by step
"""
import sys
sys.path.insert(0, 'src')

from utils import load_config
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

print("=" * 70)
print("PROGRESSIVE GOOGLE GEMINI TEST")
print("=" * 70)

# Load config
config = load_config()
ai_config = config.get('ai_providers', {}).get('google', {})
api_key = ai_config.get('api_key')
model_name = ai_config.get('model', 'gemini-pro')

print(f"\nModel: {model_name}")
print(f"API Key: {api_key[:20]}..." if api_key else "No API key")

genai.configure(api_key=api_key)

def test_response(test_name, model, prompt, generation_config):
    """Helper to test and display results"""
    print(f"\n{'=' * 70}")
    print(f"TEST: {test_name}")
    print(f"{'=' * 70}")
    print(f"Prompt length: {len(prompt)} chars")
    max_tokens = getattr(generation_config, 'max_output_tokens', 'default')
    print(f"Max tokens: {max_tokens}")
    print(f"\nPrompt preview (first 200 chars):")
    print(f"  {prompt[:200]}...")

    try:
        response = model.generate_content(prompt, generation_config=generation_config)

        print(f"\n[RESULT]")
        print(f"  Finish reason: {response.candidates[0].finish_reason if response.candidates else 'N/A'}")
        print(f"  Parts count: {len(response.candidates[0].content.parts) if response.candidates and response.candidates[0].content.parts else 0}")

        if response.candidates and response.candidates[0].content.parts:
            first_part = response.candidates[0].content.parts[0]
            if hasattr(first_part, 'text'):
                text_preview = first_part.text[:100] if len(first_part.text) > 100 else first_part.text
                print(f"  Text preview: '{text_preview}'")
                print(f"  ✅ SUCCESS - Got content!")
            else:
                print(f"  ⚠️  Part has no text attribute")
        else:
            print(f"  ❌ FAILED - 0 parts returned")

        return response

    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return None


# TEST 1: Simple prompt, minimal config (KNOWN WORKING)
print("\n" + "🧪" * 35)
print("STARTING PROGRESSIVE TESTS")
print("🧪" * 35)

model_simple = genai.GenerativeModel(model_name)
test_response(
    "1. BASELINE - Simple prompt, 100 tokens (working test)",
    model_simple,
    "Say Hello and nothing else.",
    genai.types.GenerationConfig(
        temperature=0.7,
        max_output_tokens=100,
    )
)


# TEST 2: Same simple prompt but with 8192 tokens
model_simple = genai.GenerativeModel(model_name)
test_response(
    "2. Simple prompt with 8192 max tokens",
    model_simple,
    "Say Hello and nothing else.",
    genai.types.GenerationConfig(
        temperature=0.7,
        max_output_tokens=8192,
    )
)


# TEST 3: Add safety settings (BLOCK_NONE)
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

model_with_safety = genai.GenerativeModel(model_name, safety_settings=safety_settings)
test_response(
    "3. Simple prompt + safety settings (BLOCK_NONE)",
    model_with_safety,
    "Say Hello and nothing else.",
    genai.types.GenerationConfig(
        temperature=0.7,
        max_output_tokens=8192,
    )
)


# TEST 4: Add system prompt (like content_generator does)
system_prompt = """You are an expert tour guide creating engaging audio scripts for tourists.
Your narration should be warm, informative, and conversational.

Generate content in TWO sections:
1. TRANSCRIPT: The main audio narration
2. SUMMARY POINTS: 3-5 bullet points of key takeaways"""

user_prompt = "Create a brief tour guide script about the Eiffel Tower."
combined_prompt = f"{system_prompt.strip()}\n\n{user_prompt}"

model_with_safety = genai.GenerativeModel(model_name, safety_settings=safety_settings)
test_response(
    "4. System prompt + user prompt (content_generator style)",
    model_with_safety,
    combined_prompt,
    genai.types.GenerationConfig(
        temperature=0.7,
        max_output_tokens=8192,
    )
)


# TEST 5: Full config from content_generator with realistic prompt
# Load actual system prompt from config
content_config = config.get('content_generation', {})
actual_system_prompt = content_config.get('system_prompt', '')
style_guidelines = content_config.get('style_guidelines', [])

if style_guidelines:
    actual_system_prompt += "\n\nStyle Guidelines:\n" + "\n".join(f"- {g}" for g in style_guidelines)

actual_system_prompt += """

IMPORTANT: Your response must have TWO sections:

1. TRANSCRIPT:
[The main audio narration goes here]

2. SUMMARY POINTS:
- Point 1
- Point 2
- Point 3"""

full_user_prompt = """POI: Eiffel Tower
City: Paris
Description: The iconic iron tower built in 1889
Interests: Architecture, History
Language: English"""

full_combined_prompt = f"{actual_system_prompt.strip()}\n\n{full_user_prompt}"

model_with_safety = genai.GenerativeModel(model_name, safety_settings=safety_settings)
test_response(
    "5. FULL CONFIG - Actual content_generator configuration",
    model_with_safety,
    full_combined_prompt,
    genai.types.GenerationConfig(
        temperature=0.7,
        max_output_tokens=8192,
    )
)

print("\n" + "=" * 70)
print("PROGRESSIVE TEST COMPLETE")
print("=" * 70)
print("\nAnalysis:")
print("- Check which test first shows finish_reason: 2 with 0 parts")
print("- That identifies what configuration causes the issue")
