"""
POI Research Agent - AI-powered POI discovery and redundancy detection

This agent helps discover new tourist-worthy POIs for a city and detect
semantic duplicates against existing POI content.
"""

import json
import yaml
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import anthropic
import openai
from google import generativeai as genai


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
        if provider:
            self.provider = provider

        # Build research prompt
        prompt = self._build_research_prompt(city, count)

        # Call AI
        response = self._call_ai(prompt, self.provider)

        # Parse response
        candidates = self._parse_research_response(response)

        return candidates

    def check_redundancy(
        self,
        city: str,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check research candidates for duplicates against existing POIs.

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

        # Check each candidate for redundancy
        duplicates_found = []
        updated_candidates = []

        for candidate in candidates:
            # Skip if already marked as duplicate
            if candidate.get('skip'):
                updated_candidates.append(candidate)
                continue

            # Check against existing POIs
            if existing_pois:
                prompt = self._build_redundancy_prompt(candidate, existing_pois)
                response = self._call_ai(prompt, self.provider)
                result = self._parse_redundancy_response(response)

                if result['is_duplicate']:
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
            else:
                # No existing POIs, mark as unique
                candidate['skip'] = False
                candidate['redundancy_note'] = None

            updated_candidates.append(candidate)

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

    def _call_ai(self, prompt: str, provider: str) -> str:
        """Route to appropriate AI provider."""
        if provider == 'openai':
            return self._call_openai(prompt)
        elif provider == 'anthropic':
            return self._call_anthropic(prompt)
        elif provider == 'google':
            return self._call_google(prompt)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        config = self.ai_config.get('openai', {})
        api_key = config.get('api_key')
        model = config.get('model', 'gpt-4-turbo-preview')

        if not api_key:
            raise ValueError("OpenAI API key not configured")

        client = openai.OpenAI(api_key=api_key, timeout=60.0)

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4096
        )

        return response.choices[0].message.content

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API."""
        config = self.ai_config.get('anthropic', {})
        api_key = config.get('api_key')
        model = config.get('model', 'claude-sonnet-4-5-20250929')

        if not api_key:
            raise ValueError("Anthropic API key not configured")

        client = anthropic.Anthropic(api_key=api_key, timeout=60.0)

        try:
            message = client.messages.create(
                model=model,
                max_tokens=4096,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                # Overloaded, retry once after delay
                import time
                time.sleep(2)
                message = client.messages.create(
                    model=model,
                    max_tokens=4096,
                    temperature=0.7,
                    messages=[{"role": "user", "content": prompt}]
                )
                return message.content[0].text
            raise

    def _call_google(self, prompt: str) -> str:
        """Call Google Gemini API."""
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
                max_output_tokens=4000,
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

    def _build_redundancy_prompt(
        self,
        candidate: Dict[str, Any],
        existing_pois: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for semantic duplicate detection."""
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

    # ===== Response Parsing Methods =====

    def _parse_research_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse AI research response into POI list."""
        # Extract JSON from response (handle markdown code blocks)
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
            raise ValueError(f"Failed to parse AI response as JSON: {e}\nResponse: {json_str[:500]}")

        # Extract POIs list
        pois = data.get('pois', [])

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
