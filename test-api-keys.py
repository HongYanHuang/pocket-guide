#!/usr/bin/env python3
"""
Test script to verify all API keys work correctly
"""
import sys
sys.path.insert(0, 'src')

from utils import load_config
from rich.console import Console
from rich.table import Table

console = Console()

def test_openai(config):
    """Test OpenAI API"""
    try:
        import openai
        ai_config = config.get('ai_providers', {}).get('openai', {})
        api_key = ai_config.get('api_key')
        model = ai_config.get('model', 'gpt-4')

        if not api_key:
            return "❌", "No API key configured"

        console.print(f"  Testing OpenAI ({model})...")
        client = openai.OpenAI(api_key=api_key, timeout=30.0)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a test assistant."},
                {"role": "user", "content": "Say 'Hello' and nothing else."}
            ],
            max_tokens=100  # Increased from 10 to 100
        )

        result = response.choices[0].message.content.strip()
        console.print(f"  Response: {result}")
        return "✅", f"Working! Response: {result}"

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Incorrect API key" in error_msg:
            return "❌", "Invalid API key"
        elif "404" in error_msg or "does not exist" in error_msg:
            return "❌", f"Model '{model}' not found"
        else:
            return "❌", f"Error: {error_msg[:80]}"


def test_anthropic(config):
    """Test Anthropic API"""
    try:
        import anthropic
        ai_config = config.get('ai_providers', {}).get('anthropic', {})
        api_key = ai_config.get('api_key')
        model = ai_config.get('model', 'claude-3-5-sonnet-20241022')

        if not api_key:
            return "❌", "No API key configured"

        console.print(f"  Testing Anthropic ({model})...")
        client = anthropic.Anthropic(api_key=api_key, timeout=30.0)

        message = client.messages.create(
            model=model,
            max_tokens=100,  # Increased from 10 to 100
            messages=[
                {"role": "user", "content": "Say 'Hello' and nothing else."}
            ]
        )

        result = message.content[0].text.strip()
        console.print(f"  Response: {result}")
        return "✅", f"Working! Response: {result}"

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "authentication" in error_msg.lower():
            return "❌", "Invalid API key"
        elif "529" in error_msg or "overloaded" in error_msg.lower():
            return "⚠️", "API temporarily overloaded"
        elif "404" in error_msg or "not found" in error_msg.lower():
            return "❌", f"Model '{model}' not found"
        else:
            return "❌", f"Error: {error_msg[:80]}"


def test_google(config):
    """Test Google Gemini API"""
    try:
        import google.generativeai as genai
        from google.generativeai.types import HarmCategory, HarmBlockThreshold

        ai_config = config.get('ai_providers', {}).get('google', {})
        api_key = ai_config.get('api_key')
        model_name = ai_config.get('model', 'gemini-pro')

        if not api_key:
            return "❌", "No API key configured"

        console.print(f"  Testing Google Gemini ({model_name})...")
        genai.configure(api_key=api_key)

        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        model = genai.GenerativeModel(
            model_name,
            safety_settings=safety_settings
        )

        response = model.generate_content(
            "Say 'Hello' and nothing else.",
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=100,  # Increased from 20 to 100
            )
        )

        console.print(f"  [DEBUG] Response candidates: {len(response.candidates) if response.candidates else 0}")

        if hasattr(response, 'prompt_feedback'):
            console.print(f"  [DEBUG] Prompt feedback: {response.prompt_feedback}")

        if response.candidates:
            candidate = response.candidates[0]
            console.print(f"  [DEBUG] Finish reason: {candidate.finish_reason}")
            if hasattr(candidate.content, 'parts'):
                console.print(f"  [DEBUG] Parts: {len(candidate.content.parts) if candidate.content.parts else 0}")
                if candidate.content.parts:
                    for i, part in enumerate(candidate.content.parts):
                        console.print(f"  [DEBUG] Part {i}: {part}")

        # Try to get text
        try:
            result = response.text.strip()
        except:
            # If response.text fails, try to extract from parts manually
            if response.candidates and response.candidates[0].content.parts:
                result = ''.join([part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')])
            else:
                raise ValueError("No content in response - 0 parts returned")
        console.print(f"  Response: {result}")
        return "✅", f"Working! Response: {result}"

    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
            return "❌", "Invalid API key"
        elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            return "❌", f"Model '{model_name}' not found"
        else:
            return "❌", f"Error: {error_msg[:80]}"


def main():
    console.print("\n[bold cyan]Testing API Keys...[/bold cyan]\n")

    try:
        config = load_config()
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    results = []

    # Test OpenAI
    console.print("[yellow]1. OpenAI[/yellow]")
    status, message = test_openai(config)
    results.append(("OpenAI", status, message))
    console.print()

    # Test Anthropic
    console.print("[yellow]2. Anthropic (Claude)[/yellow]")
    status, message = test_anthropic(config)
    results.append(("Anthropic", status, message))
    console.print()

    # Test Google
    console.print("[yellow]3. Google (Gemini)[/yellow]")
    status, message = test_google(config)
    results.append(("Google", status, message))
    console.print()

    # Summary table
    table = Table(title="API Test Results")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    for provider, status, message in results:
        table.add_row(provider, status, message)

    console.print(table)
    console.print()

    # Recommendations
    working = [r[0] for r in results if r[1] == "✅"]
    if working:
        console.print(f"[green]✓ Working providers: {', '.join(working)}[/green]")
        console.print(f"[dim]You can use any of these with --provider flag[/dim]")
    else:
        console.print("[red]✗ No providers are working! Please check your API keys.[/red]")

    console.print()


if __name__ == '__main__':
    main()
