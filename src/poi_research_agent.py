"""
POI Research Agent - AI-powered POI discovery and redundancy detection

This agent helps discover new tourist-worthy POIs for a city and detect
semantic duplicates against existing POI content.
"""

import json
import yaml
import re
import time
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import anthropic
import openai
from google import generativeai as genai


class TimeoutError(Exception):
    """Custom timeout exception"""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutError("API call timed out")


class POIResearchAgent:
    """
    AI-powered agent for researching tourist-relevant POIs and detecting redundancy.

    Features:
    - Research top N POIs for a city using AI
    - Semantic duplicate detection against existing POIs
    - Tourist-relevance scoring
    - Category classification
    """

    def __init__(self, config: Dict[str, Any], provider: str = 'anthropic'):
        """
        Initialize POI Research Agent.

        Args:
            config: Full application config
            provider: AI provider (openai/anthropic/google)
        """
        self.config = config
        self.ai_config = config.get('ai_providers', {})
        self.provider = provider

    def research_city_pois(
        self,
        city: str,
        count: int = 10,
        provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Research top N POIs for a city using AI.

        Args:
            city: City name (e.g., "Athens")
            count: Number of POIs to research
            provider: Override default provider

        Returns:
            List of POI dictionaries with standardized fields
        """
        print(f"[TRACE] research_city_pois() started: city={city}, count={count}, provider={provider}", flush=True)

        if provider:
            self.provider = provider

        # Build research prompt
        print(f"[TRACE] Building research prompt...", flush=True)
        prompt = self._build_research_prompt(city, count)
        print(f"[TRACE] Prompt built successfully. Length: {len(prompt)} characters", flush=True)

        # Call AI with count parameter for dynamic token calculation
        print(f"[TRACE] Calling AI with provider: {self.provider}", flush=True)
        response = self._call_ai(prompt, self.provider, count=count)
        print(f"[TRACE] AI response received. Length: {len(response)} characters", flush=True)

        # Parse response
        print(f"[TRACE] Parsing AI response...", flush=True)
        candidates = self._parse_research_response(response)
        print(f"[TRACE] Parsing complete. Found {len(candidates)} POIs", flush=True)

        return candidates

    def fulfill_city_pois(
        self,
        city: str,
        count: int = 10,
        provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Research additional POIs for a city that were missed in the first stage.

        Loads existing POIs (from content/ and poi_research/) and asks the AI
        to suggest new ones not already covered.

        Args:
            city: City name (e.g., "Athens")
            count: Number of additional POIs to discover
            provider: Override default provider

        Returns:
            List of new POI candidate dictionaries
        """
        if provider:
            self.provider = provider

        # Load existing POIs from content directory
        existing_content_pois = self._load_content_pois(city)

        # Load existing research candidates (if any)
        try:
            existing_research_pois = self._load_research_candidates(city)
        except FileNotFoundError:
            existing_research_pois = []

        # Merge all known POIs into one list
        all_existing = {}
        for poi in existing_content_pois:
            all_existing[poi['poi_id']] = poi
        for poi in existing_research_pois:
            all_existing[poi['poi_id']] = poi

        if not all_existing:
            print(f"[INFO] No existing POIs found for {city}. Running full research instead.", flush=True)
            return self.research_city_pois(city, count, self.provider)

        print(f"[INFO] Found {len(all_existing)} existing POIs for {city}. Researching {count} additional ones.", flush=True)

        # Build fulfill prompt with existing POIs context
        prompt = self._build_fulfill_prompt(city, count, list(all_existing.values()))

        # Call AI
        response = self._call_ai(prompt, self.provider, count=count)

        # Parse response
        candidates = self._parse_research_response(response)

        # Filter out any that match existing POIs by ID
        new_candidates = [
            c for c in candidates
            if c['poi_id'] not in all_existing
        ]

        if len(new_candidates) < len(candidates):
            skipped = len(candidates) - len(new_candidates)
            print(f"[INFO] Filtered out {skipped} POI(s) already in existing set.", flush=True)

        # Save new candidates (append to existing research_candidates.json)
        self._save_fulfill_candidates(city, new_candidates, all_existing)

        return new_candidates

    def check_redundancy(
        self,
        city: str,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check research candidates for duplicates against existing POIs.

        Uses batch processing - ONE API call to check all candidates at once.

        Args:
            city: City name
            provider: Override default provider

        Returns:
            Summary dict with duplicate detection results
        """
        if provider:
            self.provider = provider

        # Load research candidates
        candidates = self._load_research_candidates(city)

        # Load existing POIs
        existing_pois = self._load_existing_pois(city)

        # Filter candidates that need checking (not already marked as skip)
        candidates_to_check = [c for c in candidates if not c.get('skip')]
        already_skipped = [c for c in candidates if c.get('skip')]

        print(f"[INFO] Checking {len(candidates_to_check)} candidates against {len(existing_pois)} existing POIs...", flush=True)

        duplicates_found = []
        updated_candidates = []

        # If no existing POIs or no candidates to check, mark all as unique
        if not existing_pois or not candidates_to_check:
            for candidate in candidates_to_check:
                candidate['skip'] = False
                candidate['redundancy_note'] = None

            # Combine with already skipped
            updated_candidates = already_skipped + candidates_to_check

            # Update research_candidates.json
            self._update_research_candidates(city, updated_candidates)

            return {
                'total_candidates': len(updated_candidates),
                'duplicates_found': 0,
                'unique_pois': len(candidates_to_check),
                'duplicates': []
            }

        # BATCH CHECK: Single API call for all candidates
        print(f"[INFO] Making single API call to check all {len(candidates_to_check)} candidates...", flush=True)
        prompt = self._build_batch_redundancy_prompt(candidates_to_check, existing_pois)
        response = self._call_ai(prompt, self.provider, count=len(candidates_to_check))
        batch_results = self._parse_batch_redundancy_response(response, candidates_to_check)

        # Apply results to candidates
        for candidate in candidates_to_check:
            poi_id = candidate['poi_id']
            result = batch_results.get(poi_id)

            if result and result['is_duplicate']:
                candidate['skip'] = True
                candidate['redundancy_note'] = result['reason']
                duplicates_found.append({
                    'candidate_name': candidate['name'],
                    'duplicate_of': result['duplicate_of'],
                    'confidence': result['confidence'],
                    'reason': result['reason']
                })
            else:
                candidate['skip'] = False
                candidate['redundancy_note'] = None

            updated_candidates.append(candidate)

        # Add back the already-skipped candidates
        updated_candidates.extend(already_skipped)

        # Update research_candidates.json
        self._update_research_candidates(city, updated_candidates)

        # Return summary
        return {
            'total_candidates': len(updated_candidates),
            'duplicates_found': len(duplicates_found),
            'unique_pois': len([c for c in updated_candidates if not c.get('skip')]),
            'duplicates': duplicates_found
        }

    # ===== AI Provider Methods =====

    def _call_ai(self, prompt: str, provider: str, count: int = 10) -> str:
        """Route to appropriate AI provider.

        Args:
            prompt: The prompt to send
            provider: AI provider name
            count: Number of POIs being requested (for dynamic token calculation)
        """
        print(f"[TRACE] _call_ai() routing to provider: {provider}, count={count}", flush=True)
        if provider == 'openai':
            print(f"[TRACE] Calling OpenAI...", flush=True)
            return self._call_openai(prompt, count)
        elif provider == 'anthropic':
            print(f"[TRACE] Calling Anthropic...", flush=True)
            return self._call_anthropic(prompt, count)
        elif provider == 'google':
            print(f"[TRACE] Calling Google...", flush=True)
            return self._call_google(prompt, count)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _call_openai(self, prompt: str, count: int = 10) -> str:
        """Call OpenAI API.

        Args:
            prompt: The prompt to send
            count: Number of POIs being requested (for dynamic token calculation)
        """
        config = self.ai_config.get('openai', {})
        api_key = config.get('api_key')
        model = config.get('model', 'gpt-4-turbo-preview')

        if not api_key:
            raise ValueError("OpenAI API key not configured")

        # Calculate dynamic max_tokens
        max_tokens = min(count * 250 + 500, 16000)
        print(f"  [DEBUG] Using {max_tokens} max_tokens for {count} POIs", flush=True)

        client = openai.OpenAI(api_key=api_key, timeout=60.0)

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=max_tokens  # Use dynamic max_tokens
        )

        return response.choices[0].message.content

    def _call_anthropic(self, prompt: str, count: int = 10) -> str:
        """Call Anthropic Claude API with streaming to avoid read timeouts.

        Args:
            prompt: The prompt to send
            count: Number of POIs being requested (for dynamic token calculation)

        Returns:
            AI response text
        """
        print(f"[TRACE] _call_anthropic() started with count={count}", flush=True)

        config = self.ai_config.get('anthropic', {})
        api_key = config.get('api_key')
        model = config.get('model', 'claude-sonnet-4-5-20250929')

        print(f"[TRACE] API config loaded: model={model}, api_key={'***' if api_key else 'MISSING'}", flush=True)

        if not api_key:
            raise ValueError("Anthropic API key not configured")

        # Calculate dynamic max_tokens based on count
        # Formula: count × 250 tokens per POI + 500 buffer
        # Cap at 16000 (API limit for this model)
        max_tokens = min(count * 250 + 500, 16000)
        print(f"[TRACE] Dynamic max_tokens calculated: {max_tokens} (count={count} × 250 + 500)", flush=True)
        print(f"  [DEBUG] Using {max_tokens} max_tokens for {count} POIs", flush=True)

        print(f"[TRACE] Creating Anthropic client with 120s timeout...", flush=True)
        print(f"  [DEBUG] Preparing Anthropic API call (model: {model})...")
        client = anthropic.Anthropic(api_key=api_key, timeout=120.0)
        print(f"[TRACE] Client created successfully", flush=True)

        # Retry logic with exponential backoff
        max_retries = 5
        base_delay = 1.0  # Start with 1 second

        print(f"[TRACE] Starting retry loop (max_retries={max_retries})", flush=True)

        for attempt in range(max_retries):
            print(f"[TRACE] Attempt {attempt + 1}/{max_retries} starting...", flush=True)
            try:
                if attempt > 0:
                    # Exponential backoff: 1s, 2s, 4s, 8s, 16s
                    wait_time = base_delay * (2 ** (attempt - 1))
                    print(f"[TRACE] Retry attempt - sleeping {wait_time}s before retry...", flush=True)
                    print(f"  [DEBUG] Retry {attempt}/{max_retries} - waiting {wait_time}s...")
                    time.sleep(wait_time)
                    print(f"[TRACE] Sleep complete, retrying now...", flush=True)

                # Small delay between all API calls to prevent rate limiting
                if attempt == 0:
                    print(f"[TRACE] First attempt - applying 500ms rate limit delay...", flush=True)
                    time.sleep(0.5)  # 500ms delay between normal calls
                    print(f"[TRACE] Rate limit delay complete", flush=True)

                import sys
                print(f"[TRACE] Using STREAMING to avoid read timeout...", flush=True)
                print(f"  [DEBUG] Sending STREAMING request to Anthropic API...", flush=True)
                sys.stdout.flush()

                try:
                    # Use streaming to avoid read timeout
                    # Tokens arrive continuously → resets read timeout every 1-2 seconds
                    print(f"[TRACE] Creating streaming message...", flush=True)
                    response_text = ""

                    with client.messages.stream(
                        model=model,
                        max_tokens=max_tokens,  # Dynamic based on count
                        temperature=0.7,
                        messages=[{"role": "user", "content": prompt}]
                    ) as stream:
                        print(f"[TRACE] Stream opened, receiving tokens...", flush=True)

                        # Receive streamed tokens
                        for text in stream.text_stream:
                            response_text += text
                            # Data flows continuously, preventing read timeout

                        print(f"[TRACE] Stream completed successfully!", flush=True)

                        # Get final message to check stop reason
                        final_message = stream.get_final_message()
                        stop_reason = final_message.stop_reason
                        print(f"  [DEBUG] Stop reason: {stop_reason}", flush=True)

                        # Warn if response was truncated
                        if stop_reason == "max_tokens":
                            print(f"  [WARNING] Response truncated! Increase max_tokens or reduce --count", flush=True)
                            print(f"  [WARNING] Current max_tokens: {max_tokens}, consider using count × 300 instead", flush=True)

                except Exception as e:
                    print(f"[TRACE] Caught exception in streaming: {type(e).__name__}", flush=True)
                    print(f"  [ERROR] API call failed: {type(e).__name__}: {str(e)}", flush=True)
                    raise

                print(f"[TRACE] Response complete. Length: {len(response_text)} characters", flush=True)
                print(f"  [DEBUG] Response received! Length: {len(response_text)} characters", flush=True)

                print(f"[TRACE] Returning response text from _call_anthropic()", flush=True)
                return response_text

            except anthropic.APIStatusError as e:
                print(f"[TRACE] Caught APIStatusError: status_code={e.status_code}", flush=True)
                error_str = str(e)
                # Handle rate limit (429) and overload (529) errors
                if e.status_code in [429, 529]:
                    if attempt < max_retries - 1:
                        error_type = "rate limit" if e.status_code == 429 else "overloaded"
                        print(f"[TRACE] Retryable error {e.status_code}, will retry...", flush=True)
                        print(f"  [WARNING] Anthropic API {error_type}, retrying...")
                        continue
                    else:
                        print(f"[TRACE] Max retries exhausted for status {e.status_code}", flush=True)
                        print(f"  [ERROR] Anthropic API error after {max_retries} attempts")
                        raise Exception(
                            f"Anthropic API error (status {e.status_code}). "
                            f"Please try again later or use a different provider: "
                            f"--provider openai or --provider google"
                        ) from e
                else:
                    # Other API errors, raise immediately
                    print(f"[TRACE] Non-retryable APIStatusError {e.status_code}, raising...", flush=True)
                    raise

            except (anthropic.APIConnectionError, anthropic.APITimeoutError,
                    ConnectionError, TimeoutError) as e:
                print(f"[TRACE] Caught connection/timeout error: {type(e).__name__}", flush=True)
                # Handle connection/network errors
                if attempt < max_retries - 1:
                    print(f"[TRACE] Will retry connection error...", flush=True)
                    print(f"  [WARNING] Connection error, retrying...")
                    continue
                else:
                    print(f"[TRACE] Max retries exhausted for connection error", flush=True)
                    print(f"  [ERROR] Connection failed after {max_retries} attempts")
                    raise Exception(
                        f"Connection error after {max_retries} attempts. "
                        f"Please check your network connection and try again."
                    ) from e

            except Exception as e:
                # Unexpected errors, raise immediately
                print(f"[TRACE] Caught unexpected exception: {type(e).__name__}: {str(e)[:100]}", flush=True)
                raise

    def _call_google(self, prompt: str, count: int = 10) -> str:
        """Call Google Gemini API.

        Args:
            prompt: The prompt to send
            count: Number of POIs being requested (for dynamic token calculation)
        """
        config = self.ai_config.get('google', {})
        api_key = config.get('api_key')
        model_name = config.get('model', 'gemini-pro')

        if not api_key:
            raise ValueError("Google API key not configured")

        # Calculate dynamic max_tokens
        max_tokens = min(count * 250 + 500, 16000)
        print(f"  [DEBUG] Using {max_tokens} max_output_tokens for {count} POIs", flush=True)

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,  # Use dynamic max_tokens
                temperature=0.7
            )
        )

        return response.text

    # ===== Prompt Building Methods =====

    def _build_research_prompt(self, city: str, count: int) -> str:
        """Build prompt for POI research."""
        return f"""You are an expert travel guide researching the most tourist-worthy points of interest in {city}.

Your task: Identify the top {count} must-visit POIs that tourists should experience.

SELECTION CRITERIA:
- Historical significance (ancient ruins, monuments, battlefields)
- Architectural marvels (temples, palaces, bridges, fortresses)
- Cultural importance (museums, theaters, art galleries)
- Tourist appeal (famous landmarks, Instagram-worthy locations)
- Storytelling potential (dramatic history, interesting anecdotes)

AVOID:
- Generic restaurants, cafes, or shops (unless historically significant)
- Modern shopping malls
- Generic parks without historical significance
- Hotels or accommodations
- Generic streets or neighborhoods (unless major historical importance)

For each POI, provide:
- poi_id: lowercase slug with hyphens (e.g., "acropolis", "hagia-sophia", "temple-of-zeus")
- name: Official name as tourists would recognize it
- description: 2-3 sentence description of what it is and why it matters
- category: ONE of [monument, museum, temple, palace, archaeological_site, landmark, square, bridge, gate, fortress, theater, stadium]
- historical_period: Primary historical era (e.g., "Classical Greece (5th century BC)", "Ottoman Empire (15th-19th century)")
- why_significant: 1-2 sentences explaining tourist appeal and dramatic history

Output ONLY valid JSON with no markdown formatting:
{{
  "pois": [
    {{
      "poi_id": "...",
      "name": "...",
      "description": "...",
      "category": "...",
      "historical_period": "...",
      "why_significant": "..."
    }}
  ]
}}"""

    def _build_fulfill_prompt(self, city: str, count: int, existing_pois: List[Dict[str, Any]]) -> str:
        """Build prompt for fulfilling missing POIs, given the existing set."""
        existing_list = "\n".join([
            f"- {p['name']} (ID: {p['poi_id']}, Category: {p.get('category', 'unknown')}): {p.get('description', 'N/A')[:120]}"
            for p in existing_pois
        ])

        return f"""You are an expert travel guide researching additional points of interest in {city}.

A previous research stage already identified these POIs for {city}:

EXISTING POIs (DO NOT suggest these or similar):
{existing_list}

Your task: Identify {count} ADDITIONAL must-visit POIs that are NOT already in the list above.
These should be POIs that were missed or overlooked in the first stage.

SELECTION CRITERIA:
- Historical significance (ancient ruins, monuments, battlefields)
- Architectural marvels (temples, palaces, bridges, fortresses)
- Cultural importance (museums, theaters, art galleries)
- Tourist appeal (famous landmarks, Instagram-worthy locations)
- Storytelling potential (dramatic history, interesting anecdotes)
- Lesser-known gems that deserve more attention

AVOID:
- Any POI already listed above (or a renamed/alternate version of it)
- Generic restaurants, cafes, or shops (unless historically significant)
- Modern shopping malls
- Generic parks without historical significance
- Hotels or accommodations
- Generic streets or neighborhoods (unless major historical importance)

For each POI, provide:
- poi_id: lowercase slug with hyphens (e.g., "acropolis", "hagia-sophia", "temple-of-zeus")
- name: Official name as tourists would recognize it
- description: 2-3 sentence description of what it is and why it matters
- category: ONE of [monument, museum, temple, palace, archaeological_site, landmark, square, bridge, gate, fortress, theater, stadium]
- historical_period: Primary historical era (e.g., "Classical Greece (5th century BC)", "Ottoman Empire (15th-19th century)")
- why_significant: 1-2 sentences explaining tourist appeal and dramatic history

Output ONLY valid JSON with no markdown formatting:
{{
  "pois": [
    {{
      "poi_id": "...",
      "name": "...",
      "description": "...",
      "category": "...",
      "historical_period": "...",
      "why_significant": "..."
    }}
  ]
}}"""

    def _build_redundancy_prompt(
        self,
        candidate: Dict[str, Any],
        existing_pois: List[Dict[str, Any]]
    ) -> str:
        """
        Build prompt for semantic duplicate detection (single candidate).

        DEPRECATED: Use _build_batch_redundancy_prompt() instead for better performance.
        """
        existing_list = "\n".join([
            f"- {p['name']}: {p.get('description', 'N/A')[:150]}"
            for p in existing_pois
        ])

        return f"""You are analyzing whether a POI candidate is a duplicate of existing POIs.

CANDIDATE POI:
Name: {candidate['name']}
Description: {candidate['description']}
Category: {candidate.get('category', 'unknown')}

EXISTING POIs IN DATABASE:
{existing_list}

Task: Determine if the candidate is a TRUE DUPLICATE of any existing POI.

RULES FOR DUPLICATES:
- Same physical location (e.g., "Acropolis" vs "The Acropolis of Athens")
- Same monument with different names (e.g., "Hagia Sophia" vs "Ayasofya Mosque")
- Part of a larger complex already covered (e.g., "Parthenon" when "Acropolis" already exists and mentions the Parthenon)
- Subset of existing POI (e.g., "North Slope of Acropolis" when "Acropolis" exists)

NOT DUPLICATES (these are separate POIs):
- Different monuments in same area (e.g., "Arch of Hadrian" vs "Temple of Zeus" - both near Acropolis but different structures)
- Different sections of large site that deserve separate entries (e.g., "Acropolis Museum" vs "Acropolis" itself)
- Adjacent but distinct structures (e.g., "Roman Agora" vs "Ancient Agora")

Output ONLY valid JSON with no markdown formatting:
{{
  "is_duplicate": true or false,
  "duplicate_of": "existing poi name or null",
  "confidence": "high" or "medium" or "low",
  "reason": "1-2 sentence explanation"
}}"""

    def _build_batch_redundancy_prompt(
        self,
        candidates: List[Dict[str, Any]],
        existing_pois: List[Dict[str, Any]]
    ) -> str:
        """
        Build prompt for batch semantic duplicate detection.

        Checks ALL candidates in a single API call instead of one-by-one.
        """
        # Format existing POIs
        existing_list = "\n".join([
            f"- {p['name']}: {p.get('description', 'N/A')[:150]}"
            for p in existing_pois
        ])

        # Format candidate POIs
        candidates_list = "\n".join([
            f"{i+1}. ID: {c['poi_id']}\n   Name: {c['name']}\n   Description: {c.get('description', 'N/A')[:200]}\n   Category: {c.get('category', 'unknown')}"
            for i, c in enumerate(candidates)
        ])

        return f"""You are analyzing whether POI candidates are duplicates of existing POIs.

EXISTING POIs IN DATABASE:
{existing_list}

CANDIDATE POIs TO CHECK ({len(candidates)} total):
{candidates_list}

Task: For EACH candidate, determine if it is a TRUE DUPLICATE of any existing POI.

RULES FOR DUPLICATES:
- Same physical location (e.g., "Acropolis" vs "The Acropolis of Athens")
- Same monument with different names (e.g., "Hagia Sophia" vs "Ayasofya Mosque")
- Part of a larger complex already covered (e.g., "Parthenon" when "Acropolis" already exists and mentions the Parthenon)
- Subset of existing POI (e.g., "North Slope of Acropolis" when "Acropolis" exists)

NOT DUPLICATES (these are separate POIs):
- Different monuments in same area (e.g., "Arch of Hadrian" vs "Temple of Zeus" - both near Acropolis but different structures)
- Different sections of large site that deserve separate entries (e.g., "Acropolis Museum" vs "Acropolis" itself)
- Adjacent but distinct structures (e.g., "Roman Agora" vs "Ancient Agora")

Output ONLY valid JSON with no markdown formatting.
For EACH candidate, use its poi_id as the key:

{{
  "results": {{
    "candidate-poi-id-1": {{
      "is_duplicate": true or false,
      "duplicate_of": "existing poi name or null",
      "confidence": "high" or "medium" or "low",
      "reason": "Brief explanation (1 sentence)"
    }},
    "candidate-poi-id-2": {{
      "is_duplicate": false,
      "duplicate_of": null,
      "confidence": "high",
      "reason": "Unique POI"
    }}
  }}
}}

IMPORTANT: Include ALL {len(candidates)} candidates in your results using their exact poi_id values."""

    # ===== Response Parsing Methods =====

    def _parse_research_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse AI research response into POI list."""
        print(f"[TRACE] _parse_research_response() started, response length: {len(response)}", flush=True)

        # Extract JSON from response (handle markdown code blocks)
        print(f"[TRACE] Stripping response...", flush=True)
        json_str = response.strip()
        print(f"[TRACE] Stripped length: {len(json_str)}", flush=True)

        # Remove markdown code blocks if present
        print(f"[TRACE] Checking for markdown code blocks...", flush=True)
        if json_str.startswith('```'):
            print(f"[TRACE] Found markdown code blocks, removing...", flush=True)
            lines = json_str.split('\n')
            json_str = '\n'.join(lines[1:-1])
            print(f"[TRACE] After removing markdown: length={len(json_str)}", flush=True)

        # Remove language identifier
        if json_str.startswith('json'):
            print(f"[TRACE] Removing 'json' identifier...", flush=True)
            json_str = json_str[4:].strip()

        # Try extracting JSON from markdown
        print(f"[TRACE] Trying regex extraction...", flush=True)
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            print(f"[TRACE] Regex match found!", flush=True)
            json_str = json_match.group(1)

        # Parse JSON
        print(f"[TRACE] About to parse JSON (length: {len(json_str)})...", flush=True)
        print(f"[TRACE] First 100 chars: {json_str[:100]}", flush=True)
        print(f"[TRACE] Last 100 chars: {json_str[-100:]}", flush=True)

        try:
            print(f"[TRACE] Calling json.loads()...", flush=True)
            data = json.loads(json_str)
            print(f"[TRACE] JSON parsed successfully! Type: {type(data)}", flush=True)
        except json.JSONDecodeError as e:
            print(f"[TRACE] JSON parsing failed! Error: {e}", flush=True)
            # Show more context for debugging
            error_pos = getattr(e, 'pos', 0)
            context_start = max(0, error_pos - 100)
            context_end = min(len(json_str), error_pos + 100)
            context = json_str[context_start:context_end]

            print(f"[TRACE] Error position: {error_pos}, context: {context}", flush=True)

            raise ValueError(
                f"Failed to parse AI response as JSON: {e}\n"
                f"Response length: {len(json_str)} characters\n"
                f"Context around error:\n{context}\n"
                f"Hint: If response is very long, the API may have truncated it. Try reducing --count."
            )

        # Extract POIs list
        print(f"[TRACE] Extracting 'pois' key from data...", flush=True)
        pois = data.get('pois', [])
        print(f"[TRACE] Found {len(pois)} POIs in response", flush=True)

        # Validate and normalize each POI
        validated_pois = []
        for poi in pois:
            # Check required fields
            required = ['poi_id', 'name', 'description', 'category', 'historical_period']
            missing = [f for f in required if f not in poi]
            if missing:
                print(f"Warning: POI '{poi.get('name', 'unknown')}' missing fields: {missing}, skipping")
                continue

            # Add default fields
            poi['skip'] = False
            poi['redundancy_note'] = None

            validated_pois.append(poi)

        return validated_pois

    def _parse_redundancy_response(self, response: str) -> Dict[str, Any]:
        """Parse AI redundancy check response."""
        # Extract JSON from response
        json_str = response.strip()

        # Remove markdown code blocks if present
        if json_str.startswith('```'):
            lines = json_str.split('\n')
            json_str = '\n'.join(lines[1:-1])

        # Remove language identifier
        if json_str.startswith('json'):
            json_str = json_str[4:].strip()

        # Try extracting JSON from markdown
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)

        # Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse redundancy response as JSON: {e}\nResponse: {json_str[:500]}")

        # Validate required fields
        required = ['is_duplicate', 'confidence', 'reason']
        missing = [f for f in required if f not in data]
        if missing:
            raise ValueError(f"Redundancy response missing fields: {missing}")

        # Default duplicate_of to None if not duplicate
        if not data['is_duplicate']:
            data['duplicate_of'] = None

        return data

    def _parse_batch_redundancy_response(
        self,
        response: str,
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Parse AI batch redundancy check response.

        Args:
            response: AI response string
            candidates: List of candidate POIs that were checked

        Returns:
            Dict keyed by poi_id with duplicate detection results
        """
        # Extract JSON from response
        json_str = response.strip()

        # Remove markdown code blocks if present
        if json_str.startswith('```'):
            lines = json_str.split('\n')
            json_str = '\n'.join(lines[1:-1])

        # Remove language identifier
        if json_str.startswith('json'):
            json_str = json_str[4:].strip()

        # Try extracting JSON from markdown
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)

        # Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse batch redundancy response as JSON: {e}\nResponse: {json_str[:500]}")

        # Validate structure
        if 'results' not in data:
            raise ValueError("Batch redundancy response missing 'results' field")

        results = data['results']

        # Validate each result has required fields
        for poi_id, result in results.items():
            required = ['is_duplicate', 'confidence', 'reason']
            missing = [f for f in required if f not in result]
            if missing:
                print(f"  Warning: Result for '{poi_id}' missing fields {missing}, marking as unique", flush=True)
                # Default to not duplicate if fields missing
                results[poi_id] = {
                    'is_duplicate': False,
                    'duplicate_of': None,
                    'confidence': 'low',
                    'reason': 'Incomplete analysis'
                }

            # Default duplicate_of to None if not duplicate
            if not result.get('is_duplicate'):
                result['duplicate_of'] = None

        # Check if we got results for all candidates
        candidate_ids = {c['poi_id'] for c in candidates}
        result_ids = set(results.keys())
        missing_ids = candidate_ids - result_ids

        if missing_ids:
            print(f"  Warning: AI didn't return results for {len(missing_ids)} candidates, marking as unique", flush=True)
            for poi_id in missing_ids:
                results[poi_id] = {
                    'is_duplicate': False,
                    'duplicate_of': None,
                    'confidence': 'low',
                    'reason': 'Not analyzed by AI'
                }

        return results

    # ===== POI Loading/Saving Methods =====

    def _load_existing_pois(self, city: str) -> List[Dict[str, Any]]:
        """
        Load all existing POI YAML files from poi_research/{city}/.

        Returns:
            List of POI dictionaries with basic info
        """
        # Get absolute path to poi_research directory
        project_root = Path(__file__).parent.parent
        city_dir = project_root / "poi_research" / city

        if not city_dir.exists():
            return []

        pois = []

        for yaml_file in city_dir.glob("*.yaml"):
            # Skip backup files and research_candidates
            if 'backup' in yaml_file.name or 'research_candidates' in yaml_file.name:
                continue

            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                # Extract POI info
                poi_data = data.get('poi', {})
                if not poi_data:
                    continue

                basic_info = poi_data.get('basic_info', {})

                pois.append({
                    'poi_id': poi_data.get('poi_id', yaml_file.stem),
                    'name': poi_data.get('name', yaml_file.stem),
                    'description': basic_info.get('description', ''),
                    'period': basic_info.get('period', ''),
                    'category': poi_data.get('category', 'unknown')
                })

            except Exception as e:
                print(f"Warning: Failed to load {yaml_file}: {e}")
                continue

        return pois

    def _save_research_candidates(
        self,
        city: str,
        candidates: List[Dict[str, Any]]
    ) -> Path:
        """
        Save research candidates to JSON file.

        Returns:
            Path to saved file
        """
        # Get absolute path
        project_root = Path(__file__).parent.parent
        city_dir = project_root / "poi_research" / city

        # Create directory if needed
        city_dir.mkdir(parents=True, exist_ok=True)

        output_path = city_dir / "research_candidates.json"

        # Build output data
        output_data = {
            "city": city,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "provider": self.provider,
            "count": len(candidates),
            "pois": candidates
        }

        # Save JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        return output_path

    def _load_research_candidates(self, city: str) -> List[Dict[str, Any]]:
        """Load research candidates from JSON file."""
        project_root = Path(__file__).parent.parent
        candidates_path = project_root / "poi_research" / city / "research_candidates.json"

        if not candidates_path.exists():
            raise FileNotFoundError(f"No research_candidates.json found for {city}")

        with open(candidates_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data.get('pois', [])

    def _update_research_candidates(
        self,
        city: str,
        updated_candidates: List[Dict[str, Any]]
    ):
        """Update research_candidates.json with redundancy info."""
        project_root = Path(__file__).parent.parent
        candidates_path = project_root / "poi_research" / city / "research_candidates.json"

        # Load existing data
        with open(candidates_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Update POIs
        data['pois'] = updated_candidates

        # Save
        with open(candidates_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_content_pois(self, city: str) -> List[Dict[str, Any]]:
        """
        Load existing POIs from the content directory for a city.

        Returns:
            List of POI dicts with poi_id, name, and description fields
        """
        project_root = Path(__file__).parent.parent
        city_slug = city.lower().replace(' ', '-')
        city_dir = project_root / "content" / city_slug

        if not city_dir.exists():
            return []

        pois = []
        for poi_dir in city_dir.iterdir():
            if not poi_dir.is_dir():
                continue

            metadata_file = poi_dir / "metadata.json"
            poi_name = poi_dir.name.replace('-', ' ').title()
            poi_id = poi_dir.name

            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    poi_name = metadata.get('poi', poi_name)
                    description = metadata.get('description', '')
                except (json.JSONDecodeError, OSError):
                    description = ''
            else:
                description = ''

            pois.append({
                'poi_id': poi_id,
                'name': poi_name,
                'description': description,
                'category': 'unknown',
                'source': 'content'
            })

        return pois

    def _save_fulfill_candidates(
        self,
        city: str,
        new_candidates: List[Dict[str, Any]],
        existing_pois: Dict[str, Dict[str, Any]]
    ) -> Path:
        """
        Save fulfill candidates, merging with any existing research_candidates.json.

        New candidates are appended with a 'fulfill_stage' marker so they can
        be distinguished from the original research batch.

        Returns:
            Path to the updated research_candidates.json
        """
        project_root = Path(__file__).parent.parent
        city_dir = project_root / "poi_research" / city
        city_dir.mkdir(parents=True, exist_ok=True)

        candidates_path = city_dir / "research_candidates.json"

        # Load existing candidates if present
        existing_candidates = []
        if candidates_path.exists():
            with open(candidates_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            existing_candidates = data.get('pois', [])

        # Mark new candidates with fulfill metadata
        for candidate in new_candidates:
            candidate['fulfill_stage'] = True
            candidate['skip'] = False
            candidate['redundancy_note'] = None

        # Merge: keep existing candidates, append new ones
        merged = existing_candidates + new_candidates

        # Save
        output_data = {
            "city": city,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "provider": self.provider,
            "count": len(merged),
            "original_count": len(existing_candidates),
            "fulfill_count": len(new_candidates),
            "pois": merged
        }

        with open(candidates_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        return candidates_path
