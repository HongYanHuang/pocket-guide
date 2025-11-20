#!/usr/bin/env python3
"""
Direct test of Google Gemini API
"""
import sys
sys.path.insert(0, 'src')

from utils import load_config
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import json

print("Loading config...")
config = load_config()
ai_config = config.get('ai_providers', {}).get('google', {})
api_key = ai_config.get('api_key')
model_name = ai_config.get('model', 'gemini-pro')

print(f"Model: {model_name}")
print(f"API Key: {api_key[:20]}..." if api_key else "No API key")
print()

print("Configuring Gemini...")
genai.configure(api_key=api_key)

print("Listing available models...")
try:
    models = genai.list_models()
    print("\nAvailable models:")
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            print(f"  - {m.name} (supports: {m.supported_generation_methods})")
    print()
except Exception as e:
    print(f"Error listing models: {e}\n")

print(f"Creating model instance: {model_name}")
try:
    # Try without safety settings first
    model = genai.GenerativeModel(model_name)
    print("✓ Model created successfully\n")
except Exception as e:
    print(f"✗ Error creating model: {e}\n")
    sys.exit(1)

print("Testing simple prompt: 'Say Hello'")
print("-" * 60)

try:
    response = model.generate_content(
        "Say Hello and nothing else.",
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=100,
        )
    )

    print(f"\n[Response Object]")
    print(f"Type: {type(response)}")
    print(f"Has candidates: {hasattr(response, 'candidates')}")

    if hasattr(response, 'prompt_feedback'):
        print(f"\n[Prompt Feedback]")
        print(f"{response.prompt_feedback}")

    if response.candidates:
        print(f"\n[Candidates]: {len(response.candidates)}")
        candidate = response.candidates[0]

        print(f"\n[Candidate 0]")
        print(f"Finish reason: {candidate.finish_reason}")

        if hasattr(candidate, 'finish_message'):
            print(f"Finish message: {candidate.finish_message}")

        if hasattr(candidate, 'safety_ratings'):
            print(f"\n[Safety Ratings]")
            for rating in candidate.safety_ratings:
                print(f"  {rating.category}: {rating.probability}")

        if hasattr(candidate, 'content'):
            print(f"\n[Content]")
            print(f"Role: {candidate.content.role if hasattr(candidate.content, 'role') else 'N/A'}")

            if hasattr(candidate.content, 'parts'):
                print(f"Parts: {len(candidate.content.parts) if candidate.content.parts else 0}")
                if candidate.content.parts:
                    for i, part in enumerate(candidate.content.parts):
                        print(f"\n[Part {i}]")
                        print(f"Type: {type(part)}")
                        if hasattr(part, 'text'):
                            print(f"Text: '{part.text}'")
                        else:
                            print(f"Part object: {part}")
                else:
                    print("WARNING: Parts list is empty!")

    print(f"\n[Attempting response.text]")
    try:
        text = response.text
        print(f"✓ Success: '{text}'")
    except Exception as e:
        print(f"✗ Failed: {e}")

    print("\n" + "=" * 60)

except Exception as e:
    print(f"\n✗ Error during generation: {e}")
    import traceback
    traceback.print_exc()
