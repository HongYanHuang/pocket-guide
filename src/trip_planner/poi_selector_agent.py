"""
POI Selector Agent - AI-powered POI selection for trip planning.

This agent uses LLMs to intelligently select Starting POIs and Back-up POIs
based on user preferences, interests, and constraints.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
import anthropic
import openai
from google import generativeai as genai


class POISelectorAgent:
    """
    AI-powered agent for selecting POIs for trip itineraries.

    Uses LLMs to select:
    1. Starting POIs - Initial itinerary recommendations
    2. Back-up POIs - Alternative options for swapping
    """

    def __init__(self, config: Dict[str, Any], provider: str = 'anthropic'):
        """
        Initialize POI Selector Agent.

        Args:
            config: Application configuration dictionary
            provider: AI provider ('anthropic', 'openai', 'google')
        """
        self.config = config
        self.provider = provider
        self.ai_config = config.get('ai_providers', {})

    def select_pois(
        self,
        city: str,
        duration_days: int,
        interests: List[str] = None,
        preferences: Dict[str, Any] = None,
        must_see: List[str] = None,
        avoid: List[str] = None
    ) -> Dict[str, Any]:
        """
        Select Starting POIs and Back-up POIs using AI.

        Args:
            city: City name (e.g., "Athens")
            duration_days: Trip duration in days
            interests: List of interests (e.g., ['architecture', 'history'])
            preferences: User preferences dict:
                - walking_tolerance: 'low', 'moderate', 'high'
                - indoor_outdoor: 'indoor', 'outdoor', 'balanced'
                - pace: 'relaxed', 'normal', 'packed'
            must_see: POIs that must be included
            avoid: Constraints to avoid (e.g., ['crowded_places'])

        Returns:
            Dictionary with:
            {
                'starting_pois': [...],
                'backup_pois': {...},
                'metadata': {...}
            }
        """
        # Set defaults
        interests = interests or []
        preferences = preferences or {}
        must_see = must_see or []
        avoid = avoid or []

        # Load available POIs for this city
        print(f"  [POI SELECTOR] Loading POIs for {city}...", flush=True)
        available_pois = self._load_city_pois(city)

        if not available_pois:
            raise ValueError(f"No POIs found for city: {city}")

        print(f"  [POI SELECTOR] Found {len(available_pois)} POIs", flush=True)

        # Build selection prompt
        prompt = self._build_selection_prompt(
            city=city,
            duration_days=duration_days,
            interests=interests,
            preferences=preferences,
            must_see=must_see,
            avoid=avoid,
            available_pois=available_pois
        )

        # Calculate dynamic max_tokens based on POI count
        # Formula: poi_count * tokens_per_poi + base_tokens
        # - Each POI needs tokens for: starting selection (~150), backups (~250), or rejection (~30)
        # - Average per POI: ~150 tokens
        # - Base tokens: 1000 (for structure, reasoning_summary, metadata)
        tokens_per_poi = 150
        base_tokens = 1000
        max_tokens = len(available_pois) * tokens_per_poi + base_tokens

        print(f"  [POI SELECTOR] Calculated max_tokens: {max_tokens} (for {len(available_pois)} POIs)", flush=True)

        # Call AI based on provider
        print(f"  [POI SELECTOR] Calling {self.provider} API for selection...", flush=True)

        if self.provider == 'anthropic':
            response = self._call_anthropic(prompt, max_tokens)
        elif self.provider == 'openai':
            response = self._call_openai(prompt, max_tokens)
        elif self.provider == 'google':
            response = self._call_google(prompt, max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        # Parse and validate response
        print(f"  [POI SELECTOR] Parsing AI response...", flush=True)
        selection = self._parse_and_validate(response, available_pois)

        # Add metadata
        selection['metadata'] = {
            'city': city,
            'duration_days': duration_days,
            'interests': interests,
            'preferences': preferences,
            'provider': self.provider,
            'total_pois_available': len(available_pois),
            'total_starting_pois': len(selection['starting_pois']),
            'total_backup_pois': sum(len(backups) for backups in selection['backup_pois'].values()),
            'total_rejected_pois': len(selection['rejected_pois'])
        }

        print(f"  ✓ Selected {len(selection['starting_pois'])} Starting POIs", flush=True)
        print(f"  ✓ Generated {selection['metadata']['total_backup_pois']} Back-up POIs", flush=True)
        print(f"  ✓ Rejected {selection['metadata']['total_rejected_pois']} POIs", flush=True)

        return selection

    def _load_city_pois(self, city: str) -> List[Dict[str, Any]]:
        """
        Load all POIs for a city from poi_research directory.

        Args:
            city: City name

        Returns:
            List of POI dictionaries with metadata
        """
        # Get absolute path to poi_research directory (relative to project root)
        # This file is in src/trip_planner/, so go up 2 levels to reach project root
        project_root = Path(__file__).parent.parent.parent
        poi_research_dir = project_root / "poi_research" / city

        if not poi_research_dir.exists():
            return []

        pois = []

        # Load all YAML files in the city directory
        for yaml_file in poi_research_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    research_data = yaml.safe_load(f)

                # Extract POI metadata
                poi_data = research_data.get('poi', {})

                if not poi_data:
                    continue

                # Build POI summary
                poi_summary = {
                    'poi_id': poi_data.get('poi_id', yaml_file.stem),
                    'name': poi_data.get('name', yaml_file.stem),
                    'description': poi_data.get('basic_info', {}).get('description', ''),
                    'period': poi_data.get('basic_info', {}).get('period', ''),
                    'date_built': poi_data.get('basic_info', {}).get('date_built', ''),
                    'current_state': poi_data.get('basic_info', {}).get('current_state', ''),
                    'core_features': poi_data.get('core_features', []),
                    'people': [p.get('name') for p in poi_data.get('people', [])],
                    'events': [e.get('name') for e in poi_data.get('events', [])],
                    'concepts': [c.get('name') for c in poi_data.get('concepts', [])],
                    'labels': poi_data.get('basic_info', {}).get('labels', [])
                }

                pois.append(poi_summary)

            except Exception as e:
                print(f"  Warning: Failed to load {yaml_file}: {e}", flush=True)
                continue

        return pois

    def _build_selection_prompt(
        self,
        city: str,
        duration_days: int,
        interests: List[str],
        preferences: Dict[str, Any],
        must_see: List[str],
        avoid: List[str],
        available_pois: List[Dict[str, Any]]
    ) -> str:
        """
        Build the AI prompt for POI selection.

        Returns:
            Formatted prompt string
        """
        # Format available POIs for the prompt
        poi_list = []
        for i, poi in enumerate(available_pois, 1):
            poi_str = f"{i}. {poi['name']}"
            if poi.get('description'):
                poi_str += f"\n   Description: {poi['description'][:150]}..."
            if poi.get('period'):
                poi_str += f"\n   Period: {poi['period']}"
            if poi.get('core_features'):
                poi_str += f"\n   Features: {len(poi['core_features'])} key features"
            poi_list.append(poi_str)

        pois_formatted = "\n\n".join(poi_list)

        # Build preferences section
        prefs_list = []
        if preferences.get('walking_tolerance'):
            prefs_list.append(f"- Walking tolerance: {preferences['walking_tolerance']}")
        if preferences.get('indoor_outdoor'):
            prefs_list.append(f"- Indoor/Outdoor preference: {preferences['indoor_outdoor']}")
        if preferences.get('pace'):
            prefs_list.append(f"- Trip pace: {preferences['pace']}")

        prefs_str = "\n".join(prefs_list) if prefs_list else "- No specific preferences"

        # Build constraints
        constraints = []
        if must_see:
            constraints.append(f"MUST INCLUDE: {', '.join(must_see)}")
        if avoid:
            constraints.append(f"AVOID: {', '.join(avoid)}")

        constraints_str = "\n".join(constraints) if constraints else "No specific constraints"

        prompt = f"""You are an expert travel planner for {city}.

AVAILABLE POIs IN {city.upper()}:
{pois_formatted}

USER PROFILE:
- Trip duration: {duration_days} days
- Interests: {', '.join(interests) if interests else 'General sightseeing'}
- Preferences:
{prefs_str}

CONSTRAINTS:
{constraints_str}

TASK:
1. Select 8-12 "Starting POIs" that best match the user's profile for a {duration_days}-day trip
2. For each Starting POI, suggest 2-3 "Back-up POIs" that are similar and could serve as replacements
3. Explain your reasoning for selections and similarity

SELECTION CRITERIA:
- Respect time budget ({duration_days} days = approximately {duration_days * 8} hours of activities)
- Match user interests: {', '.join(interests) if interests else 'varied experiences'}
- Consider geographic diversity (don't cluster everything in one area)
- Balance famous must-sees with hidden gems
- Ensure Back-ups can actually replace their Starting POI (similar theme/duration/location)

BACKUP SELECTION RULES:
- Each backup must be similar enough to substitute for the Starting POI
- Rate similarity on 0.0-1.0 scale (0.8+ = very similar, 0.6-0.8 = moderately similar)
- Include at least one "theme match" (same type/period) and one "location match" (nearby)
- Explain WHY each backup is a good substitute

OUTPUT FORMAT (JSON):
{{
  "starting_pois": [
    {{
      "poi": "Acropolis",
      "reason": "Must-see ancient monument, matches history & architecture interests",
      "suggested_day": 1,
      "estimated_hours": 2.5,
      "priority": "high"
    }}
  ],
  "backup_pois": {{
    "Acropolis": [
      {{
        "poi": "Temple of Olympian Zeus",
        "similarity_score": 0.85,
        "reason": "Same Classical period, similar architectural significance, nearby location",
        "substitute_scenario": "If Acropolis is too crowded or closed"
      }}
    ]
  }},
  "rejected_pois": [
    {{
      "poi": "Modern Shopping Mall",
      "reason": "Not historical/architectural focus"
    }}
  ],
  "total_estimated_hours": 24.0,
  "reasoning_summary": "Brief explanation of overall selection strategy"
}}

IMPORTANT:
- Output ONLY valid JSON, no markdown formatting
- POI names must EXACTLY match the available POIs list above
- Each Starting POI must have 2-3 backups
- Similarity scores must be realistic (0.6-1.0 range)
- Include ALL POIs not selected in "rejected_pois" with very brief reason (5-8 words max)

Generate the POI selection now:"""

        return prompt

    def _parse_and_validate(
        self,
        response: str,
        available_pois: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Parse AI response and validate POI names.

        Args:
            response: Raw AI response string
            available_pois: List of available POIs for validation

        Returns:
            Validated selection dictionary
        """
        # Extract JSON from response (handle markdown code blocks)
        json_str = response.strip()

        # Remove markdown code blocks if present
        if json_str.startswith('```'):
            lines = json_str.split('\n')
            json_str = '\n'.join(lines[1:-1])  # Remove first and last lines

        # Remove any "json" language identifier
        if json_str.startswith('json'):
            json_str = json_str[4:].strip()

        # Parse JSON
        try:
            selection = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI response as JSON: {e}\nResponse: {json_str[:500]}")

        # Validate structure
        if 'starting_pois' not in selection:
            raise ValueError("AI response missing 'starting_pois' field")
        if 'backup_pois' not in selection:
            raise ValueError("AI response missing 'backup_pois' field")
        if 'rejected_pois' not in selection:
            print("  Warning: AI response missing 'rejected_pois' field, using empty list", flush=True)
            selection['rejected_pois'] = []

        # Build POI name lookup
        available_names = {poi['name'].lower(): poi['name'] for poi in available_pois}

        # Validate and normalize Starting POI names
        validated_starting = []
        for poi_entry in selection['starting_pois']:
            poi_name = poi_entry.get('poi', '')
            normalized_name = available_names.get(poi_name.lower())

            if not normalized_name:
                print(f"  Warning: POI '{poi_name}' not found in available POIs, skipping", flush=True)
                continue

            poi_entry['poi'] = normalized_name
            validated_starting.append(poi_entry)

        # Validate and normalize Back-up POI names
        validated_backups = {}
        for starting_poi, backups in selection['backup_pois'].items():
            # Normalize starting POI name
            normalized_starting = available_names.get(starting_poi.lower(), starting_poi)

            validated_backup_list = []
            for backup_entry in backups:
                backup_name = backup_entry.get('poi', '')
                normalized_backup = available_names.get(backup_name.lower())

                if not normalized_backup:
                    print(f"  Warning: Backup POI '{backup_name}' not found, skipping", flush=True)
                    continue

                backup_entry['poi'] = normalized_backup
                validated_backup_list.append(backup_entry)

            if validated_backup_list:
                validated_backups[normalized_starting] = validated_backup_list

        # Validate and normalize Rejected POI names
        validated_rejected = []
        for rejected_entry in selection.get('rejected_pois', []):
            rejected_name = rejected_entry.get('poi', '')
            normalized_rejected = available_names.get(rejected_name.lower())

            if not normalized_rejected:
                print(f"  Warning: Rejected POI '{rejected_name}' not found, skipping", flush=True)
                continue

            rejected_entry['poi'] = normalized_rejected
            validated_rejected.append(rejected_entry)

        return {
            'starting_pois': validated_starting,
            'backup_pois': validated_backups,
            'rejected_pois': validated_rejected,
            'total_estimated_hours': selection.get('total_estimated_hours', 0),
            'reasoning_summary': selection.get('reasoning_summary', '')
        }

    # AI Provider Methods

    def _call_anthropic(self, prompt: str, max_tokens: int) -> str:
        """Call Anthropic Claude API"""
        config = self.ai_config.get('anthropic', {})
        api_key = config.get('api_key')
        model = config.get('model', 'claude-3-5-sonnet-20241022')

        if not api_key:
            raise ValueError("Anthropic API key not configured")

        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0.3,  # Lower temperature for more consistent selections
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def _call_openai(self, prompt: str, max_tokens: int) -> str:
        """Call OpenAI API"""
        config = self.ai_config.get('openai', {})
        api_key = config.get('api_key')
        model = config.get('model', 'gpt-4-turbo-preview')

        if not api_key:
            raise ValueError("OpenAI API key not configured")

        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0.3,
            messages=[
                {"role": "system", "content": "You are an expert travel planner. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}  # Force JSON output
        )

        return response.choices[0].message.content

    def _call_google(self, prompt: str, max_tokens: int) -> str:
        """Call Google Gemini API"""
        config = self.ai_config.get('google', {})
        api_key = config.get('api_key')
        model_name = config.get('model', 'gemini-pro')

        if not api_key:
            raise ValueError("Google API key not configured")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.3
            )
        )

        return response.text
