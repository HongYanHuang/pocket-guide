"""
Research Agent - Recursive multi-layer POI knowledge extraction

This module implements a recursive research system that extracts comprehensive
knowledge about Points of Interest (POIs) through multiple layers:
- Layer 0: Research the POI itself
- Layer 1: Research native entities (people, locations, events)
- Layer 2: Research dramatic secondary entities (relationships, conflicts)

The agent automatically discovers relationships and context to enable
rich, dramatic storytelling without manual input.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
import time


class ResearchAgent:
    """
    Recursive research agent for POI knowledge extraction

    Features:
    - Multi-layer recursive research (0 → 1 → 2)
    - Entity extraction and filtering
    - Smart depth control (avoid over-researching)
    - API budget management
    - Entity caching (reuse across POIs)
    """

    def __init__(self, config: Dict):
        """
        Initialize Research Agent

        Args:
            config: Full application config dictionary
        """
        self.config = config
        self.ai_config = config.get('ai_providers', {})
        self.research_config = config.get('research', {})

        # Depth control
        self.max_depth = self.research_config.get('max_depth', 2)
        self.max_entities_per_layer = self.research_config.get('max_entities_per_layer', 5)
        self.max_api_calls = self.research_config.get('max_api_calls', 10)

        # Layer triggers
        self.layer1_triggers = set(self.research_config.get('layer1_triggers', ['native', 'drama']))
        self.layer2_triggers = set(self.research_config.get('layer2_triggers',
                                                            ['drama', 'irony', 'shocking', 'critical-context']))
        self.layer2_relationships = set(self.research_config.get('layer2_relationships',
                                                                 ['conflict', 'rival', 'boss', 'enemy', 'key-ally']))

        # Tracking
        self.researched_entities = set()  # Avoid duplicates
        self.api_calls_made = 0

    def research_poi_recursive(
        self,
        poi_name: str,
        city: str,
        user_description: Optional[str] = None,
        provider: Optional[str] = None
    ) -> Dict:
        """
        Recursively research POI with multi-layer depth

        Args:
            poi_name: Name of point of interest
            city: City where POI is located
            user_description: Optional user-provided description
            provider: AI provider (openai, anthropic, google)

        Returns:
            Complete knowledge graph with all layers
        """
        print(f"\n  [RESEARCH] Starting recursive research for {poi_name}", flush=True)
        print(f"  [CONFIG] Max depth: {self.max_depth}, Max entities/layer: {self.max_entities_per_layer}", flush=True)

        # Reset tracking for this research session
        self.researched_entities = set()
        self.api_calls_made = 0

        # Layer 0: Research the POI itself
        print(f"\n  [LAYER 0] Researching POI: {poi_name}", flush=True)

        poi_data = self._research_entity(
            entity_type="POI",
            entity_name=poi_name,
            context={"city": city, "description": user_description},
            provider=provider
        )

        # Initialize knowledge graph
        knowledge_graph = {
            "poi": poi_data,
            "entities": {},
            "research_depth": 0,
            "api_calls": self.api_calls_made
        }

        # Extract entities for Layer 1
        to_research_layer1 = []
        for entity in self._extract_entities(poi_data):
            if self._should_research_layer1(entity):
                to_research_layer1.append(entity)

        print(f"\n  [LAYER 1] Found {len(to_research_layer1)} entities to research")
        if to_research_layer1:
            print(f"    Entities: {', '.join(e['name'] for e in to_research_layer1[:5])}")

        # Layer 1: Research native entities
        to_research_layer2 = []
        for entity in to_research_layer1[:self.max_entities_per_layer]:
            if self.api_calls_made >= self.max_api_calls:
                print(f"    ⚠️  API call limit reached ({self.max_api_calls}), stopping")
                break

            entity_id = f"{entity['type']}:{entity['name']}"

            if entity_id in self.researched_entities:
                print(f"    ↳ Skipping {entity['name']} (already researched)")
                continue

            print(f"    ↳ Researching {entity['type']}: {entity['name']}")

            entity_data = self._research_entity(
                entity_type=entity['type'],
                entity_name=entity['name'],
                context={"poi": poi_name, "city": city},
                provider=provider
            )

            knowledge_graph["entities"][entity_id] = entity_data
            self.researched_entities.add(entity_id)

            # Extract entities for Layer 2
            for secondary in self._extract_entities(entity_data):
                if self._should_research_layer2(secondary, entity_data):
                    secondary['related_to'] = entity['name']
                    to_research_layer2.append(secondary)

        print(f"\n  [LAYER 2] Found {len(to_research_layer2)} secondary entities")
        if to_research_layer2:
            print(f"    Entities: {', '.join(e['name'] for e in to_research_layer2[:5])}")

        # Layer 2: Research critical secondary entities
        for entity in to_research_layer2[:self.max_entities_per_layer]:
            if self.api_calls_made >= self.max_api_calls:
                print(f"    ⚠️  API call limit reached ({self.max_api_calls}), stopping")
                break

            entity_id = f"{entity['type']}:{entity['name']}"

            if entity_id in self.researched_entities:
                print(f"    ↳ Skipping {entity['name']} (already researched)")
                continue

            print(f"    ↳ Researching secondary {entity['type']}: {entity['name']}")

            entity_data = self._research_entity(
                entity_type=entity['type'],
                entity_name=entity['name'],
                context={
                    "poi": poi_name,
                    "related_to": entity.get('related_to'),
                    "relationship": entity.get('relationship_type')
                },
                provider=provider
            )

            knowledge_graph["entities"][entity_id] = entity_data
            self.researched_entities.add(entity_id)

        knowledge_graph["research_depth"] = min(2, self.max_depth)
        knowledge_graph["total_entities"] = len(self.researched_entities)
        knowledge_graph["api_calls"] = self.api_calls_made

        print(f"\n  [COMPLETE] Research finished:")
        print(f"    - Depth: {knowledge_graph['research_depth']} layers")
        print(f"    - Entities: {knowledge_graph['total_entities']}")
        print(f"    - API calls: {knowledge_graph['api_calls']}")

        return knowledge_graph

    def _should_research_layer1(self, entity: Dict) -> bool:
        """
        Decide if entity should be researched in Layer 1

        Args:
            entity: Entity dict with type, name, labels

        Returns:
            True if should research, False otherwise
        """
        labels = set(entity.get('labels', []))

        # Always research if has layer1 trigger label
        if labels & self.layer1_triggers:
            return True

        # Research if it's a person central to story
        if entity['type'] == 'Person' and 'drama' in labels:
            return True

        return False

    def _should_research_layer2(self, entity: Dict, parent_data: Dict) -> bool:
        """
        Decide if entity should be researched in Layer 2

        Args:
            entity: Entity dict with type, name, labels
            parent_data: Data from parent entity (Layer 1)

        Returns:
            True if should research, False otherwise
        """
        labels = set(entity.get('labels', []))

        # Research if has layer2 trigger label
        if labels & self.layer2_triggers:
            return True

        # Research if it's a person with critical relationship
        if entity['type'] == 'Person':
            relationship = entity.get('relationship_type', '').lower()
            if any(rel in relationship for rel in self.layer2_relationships):
                return True

        return False

    def _research_entity(
        self,
        entity_type: str,
        entity_name: str,
        context: Dict,
        provider: Optional[str]
    ) -> Dict:
        """
        Research a single entity with specialized prompt

        Args:
            entity_type: Type of entity (POI, Person, Event, Concept, Location)
            entity_name: Name of entity to research
            context: Context dictionary (poi, city, relationship, etc.)
            provider: AI provider to use

        Returns:
            Parsed research data dictionary
        """
        # Build specialized prompt based on entity type
        if entity_type == "POI":
            prompt = self._build_poi_research_prompt(entity_name, context)
        elif entity_type == "Person":
            prompt = self._build_person_research_prompt(entity_name, context)
        elif entity_type == "Event":
            prompt = self._build_event_research_prompt(entity_name, context)
        elif entity_type == "Concept":
            prompt = self._build_concept_research_prompt(entity_name, context)
        elif entity_type == "Location":
            prompt = self._build_location_research_prompt(entity_name, context)
        else:
            prompt = self._build_generic_research_prompt(entity_name, context)

        # Call AI
        raw_response = self._call_ai(prompt, provider)
        self.api_calls_made += 1

        # Parse response
        parsed_data = self._parse_research_response(raw_response, entity_type)

        return parsed_data

    def _extract_entities(self, data: Dict) -> List[Dict]:
        """
        Extract entities mentioned in research data

        Args:
            data: Research data dictionary

        Returns:
            List of entity dictionaries with type, name, labels
        """
        entities = []

        # Extract people
        for person in data.get('people', []):
            entities.append({
                'type': 'Person',
                'name': person['name'],
                'labels': person.get('labels', []),
                'relationship_type': person.get('relationship_type', '')
            })

        # Extract events
        for event in data.get('events', []):
            entities.append({
                'type': 'Event',
                'name': event['name'],
                'labels': event.get('labels', [])
            })

        # Extract concepts
        for concept in data.get('concepts', []):
            entities.append({
                'type': 'Concept',
                'name': concept['name'],
                'labels': concept.get('labels', [])
            })

        # Extract locations
        for location in data.get('locations', []):
            entities.append({
                'type': 'Location',
                'name': location['name'],
                'labels': location.get('labels', [])
            })

        return entities

    def _call_ai(self, prompt: str, provider: Optional[str]) -> str:
        """
        Call AI provider with prompt

        Args:
            prompt: Research prompt
            provider: AI provider name (openai, anthropic, google)

        Returns:
            Raw AI response text
        """
        # Import providers dynamically to avoid circular imports
        try:
            from .content_generator import ContentGenerator
        except ImportError:
            from content_generator import ContentGenerator

        # Create temporary generator to use existing AI calling logic
        generator = ContentGenerator(self.config)

        # Determine provider
        if not provider:
            provider = self.config.get('defaults', {}).get('ai_provider', 'google')

        # Call appropriate provider
        if provider == 'openai':
            return generator._generate_openai(prompt)
        elif provider == 'anthropic':
            return generator._generate_anthropic(prompt)
        elif provider == 'google':
            return generator._generate_google(prompt)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _parse_research_response(self, raw_response: str, entity_type: str) -> Dict:
        """
        Parse AI response into structured data

        Args:
            raw_response: Raw text response from AI
            entity_type: Type of entity researched

        Returns:
            Structured dictionary
        """
        # Strip markdown code fences if present
        content = raw_response.strip()

        # Remove ```yaml ... ``` or ```yml ... ``` fences
        if content.startswith('```'):
            lines = content.split('\n')
            # Remove first line (```yaml or ```yml)
            if lines[0].startswith('```'):
                lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            content = '\n'.join(lines)

        # Try to parse as YAML
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                # Add metadata
                data['_parsed'] = True
                data['_entity_type'] = entity_type
                return data
        except yaml.YAMLError as e:
            print(f"    [WARNING] YAML parse error: {e}")
            print(f"    [DEBUG] First 200 chars: {content[:200]}")
        except Exception as e:
            print(f"    [WARNING] Unexpected parse error: {e}")

        # Fallback: Return raw response wrapped in dict
        return {
            "raw_content": raw_response,
            "entity_type": entity_type,
            "parsed": False
        }

    # ===== Research Prompt Templates =====

    def _build_poi_research_prompt(self, poi_name: str, context: Dict) -> str:
        """Build research prompt for POI"""
        city = context.get('city', '')
        user_desc = context.get('description', '')

        prompt = f"""
You are a historical researcher extracting information for dramatic tour guide narratives.

POI: {poi_name}
City: {city}
{f"Additional Context: {user_desc}" if user_desc else ""}

Research and extract information in YAML format:

```yaml
poi_id: {poi_name.lower().replace(' ', '-')}
name: "{poi_name}"
city: "{city}"

basic_info:
  period: # Historical period (e.g., "Roman Empire", "Medieval")
  date_built: # Absolute date (e.g., "298-303 AD")
  date_relative: # Relative date (e.g., "about 1,700 years ago")
  current_state: # Description of current condition
  description: # 1-2 sentence overview
  labels: [native, poi]

core_features:  # 2-5 essential physical facts visitors need (ALWAYS included, never filtered)
  - # What visitor can SEE/TOUCH/HEAR/SMELL/EXPERIENCE right now at this POI
  - # How to identify key visual elements (e.g., "Roman figures are larger, wear armor")
  - # Scale, size, materials, current condition (e.g., "10 meters tall, brick exposed")
  - # Spatial orientation (e.g., "Two pillars, north faces Rotunda")
  - # Current state details (e.g., "2 of 8 original pillars remain, marble lost")

people:
  - name: # Person's name
    role: # Their role (e.g., "Roman Emperor")
    personality: # 2-3 adjectives/phrases
    origin: # Where they came from
    relationship_type: # If mentioned in context
    labels: [native, drama]  # Use: native, drama, history

events:
  - name: # Event name
    date: # When it happened
    date_relative: # Relative timeframe
    emotional_tone: # humiliation, triumph, tragedy, irony
    specific_detail: # Exact numbers, actions, distances
    labels: [drama, history]  # Use: drama, irony, shocking

locations:
  - name: # Location name
    significance: # Why important
    labels: [native, geography]

concepts:
  - name: # Concept name (e.g., "Rule of Four")
    explanation: # Brief explanation
    labels: [history, politics]
```

IMPORTANT:

For core_features (CRITICAL - these ground visitors in physical reality):
- List 2-5 essential physical facts about what visitors experience at the POI RIGHT NOW
- Include: What they see/hear/touch, how to identify key elements, scale/size, current condition
- Example: "Two massive brick pillars, 10m tall; relief carvings show Galerius on horseback;
  Roman figures larger with armor, Persian figures smaller with pointed hats"
- These are grounding facts, NOT historical stories
- Keep each feature concise (1-2 sentences max)

For people/events/locations/concepts (historical context):
- Mark core elements with [native] label
- Find DRAMATIC elements (failures, humiliations, conflicts) → [drama]
- Find IRONIES and twists → [irony]
- Include SPECIFIC DETAILS (exact numbers, distances, actions) → [specific-detail]
- Focus on EMOTIONAL STORY, not just facts

Output ONLY valid YAML, no markdown fences or extra text.
"""
        return prompt

    def _build_person_research_prompt(self, person_name: str, context: Dict) -> str:
        """Build research prompt for Person entity"""
        poi = context.get('poi', '')
        city = context.get('city', '')
        relationship = context.get('relationship', '')

        return f"""
Research historical figure: {person_name}

Context: Related to {poi} in {city}
{f"Relationship: {relationship}" if relationship else ""}

Extract in YAML format:

```yaml
name: "{person_name}"
type: "Person"

biography:
  full_name: # Full name with titles
  birth_death: # Dates
  birth_death_relative: # "about 1,700 years ago"
  origin: # Where from, social class
  personality: # 3-5 descriptive traits
  labels: [native, person]

events:
  - name: # Event name
    date: # When
    date_relative: # Relative
    emotional_tone: # humiliation, triumph, etc.
    specific_detail: # EXACT details with numbers!
    what_led_to_it: # Cause
    what_resulted: # Effect
    labels: [drama, shocking]

relationships:
  - name: # Other person's name
    relationship_type: # boss, rival, ally, enemy
    nature: # conflict, cooperation, betrayal
    dramatic_incidents: # What happened between them
    labels: [secondary, drama, conflict]  # Label with relationship type!

ironic_ending:
  how_died: # Death or fate
  unexpected_outcome: # The twist
  contrast: # Intention vs reality
  labels: [irony, shocking]
```

Focus on:
- DRAMATIC EVENTS with exact details
- KEY RELATIONSHIPS (especially conflicts, bosses, rivals)
- IRONIC ENDING or fate
- Label relationships: [boss], [rival], [enemy] for Layer 2 research

Output ONLY valid YAML.
"""

    def _build_event_research_prompt(self, event_name: str, context: Dict) -> str:
        """Build research prompt for Event entity"""
        poi = context.get('poi', '')

        return f"""
Research historical event: {event_name}

Context: Related to {poi}

Extract in YAML format:

```yaml
name: "{event_name}"
type: "Event"

basic_info:
  date: # Exact date
  date_relative: # "1,700 years ago"
  location: # Where
  involved_people: # Who was there

dramatic_details:
  what_led_up: # Causes
  exact_actions: # Specific numbers, distances, durations
  emotional_tone: # humiliation, triumph, tragedy
  immediate_consequences: # What happened right after
  labels: [drama, shocking]

context:
  significance: # Why important
  larger_conflict: # What story is this part of
  aftermath: # Long-term effects
  labels: [critical-context]
```

Focus on SPECIFIC DETAILS and EMOTIONAL ELEMENTS.

Output ONLY valid YAML.
"""

    def _build_concept_research_prompt(self, concept_name: str, context: Dict) -> str:
        """Build research prompt for Concept entity"""
        poi = context.get('poi', '')

        return f"""
Research historical concept: {concept_name}

Context: Related to {poi}

Extract in YAML format:

```yaml
name: "{concept_name}"
type: "Concept"

explanation:
  what_it_is: # Brief explanation
  why_created: # Purpose
  how_it_worked: # Structure or mechanism
  relevance_to_poi: # How it relates to {poi}
  labels: [history, politics]
```

Output ONLY valid YAML.
"""

    def _build_location_research_prompt(self, location_name: str, context: Dict) -> str:
        """Build research prompt for Location entity"""
        poi = context.get('poi', '')
        city = context.get('city', '')

        return f"""
Research location: {location_name}

Context: Related to {poi} in {city}

Extract in YAML format:

```yaml
name: "{location_name}"
type: "Location"

geography:
  where: # Exact location
  significance: # Why important historically
  what_happened_there: # Events at this location
  labels: [native, geography]
```

Find what makes this location STRATEGICALLY important!

Output ONLY valid YAML.
"""

    def _build_generic_research_prompt(self, entity_name: str, context: Dict) -> str:
        """Generic fallback research prompt"""
        return f"""
Research: {entity_name}

Context: {context}

Provide structured information about this entity including:
- Basic facts
- Historical significance
- Dramatic or interesting details

Output in YAML format.
"""

    # ===== Save/Load Methods =====

    def save_research(self, research_data: Dict, output_path: Path):
        """
        Save research data to YAML file

        Args:
            research_data: Research dictionary
            output_path: Path to save file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(research_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def load_research(self, research_path: Path) -> Dict:
        """
        Load research data from YAML file

        Args:
            research_path: Path to research file

        Returns:
            Research dictionary
        """
        with open(research_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    # ===== Research Expansion Methods =====

    def expand_research_for_feature(
        self,
        feature: str,
        poi_name: str,
        city: str,
        existing_research: Dict,
        provider: str
    ) -> Dict:
        """
        Expand research to cover a missing feature

        This is called when diagnosis identifies a research gap - the research
        data doesn't contain enough information about a specific feature.

        Strategy:
        1. Extract aspect from feature (e.g., "towers" from "Two massive stone towers")
        2. Build focused research prompt targeting that aspect
        3. Call AI to research that specific aspect
        4. Parse and return new research data (to be merged with existing)

        Args:
            feature: Feature description that's missing from research
            poi_name: Name of POI
            city: City name
            existing_research: Current research data
            provider: AI provider to use

        Returns:
            New research data dictionary to merge with existing
        """
        print(f"\n  [RESEARCH EXPANSION] Expanding research for feature: {feature[:60]}...")

        # Extract main aspect from feature
        aspect = self._extract_aspect(feature)
        print(f"  [ASPECT] Identified aspect: {aspect}")

        # Build focused research prompt
        prompt = self._build_aspect_research_prompt(
            poi_name=poi_name,
            city=city,
            aspect=aspect,
            feature_context=feature,
            existing_research=existing_research
        )

        # Call AI to research this specific aspect
        raw_response = self._call_ai(prompt, provider)
        self.api_calls_made += 1

        # Parse response
        new_research = self._parse_research_response(raw_response, "aspect_expansion")

        print(f"  [EXPANSION] Successfully expanded research for: {aspect}")

        return new_research

    def _extract_aspect(self, feature: str) -> str:
        """
        Extract the main aspect/focus from a feature description

        Examples:
        - "Two massive stone towers flank the gate" → "tower structures"
        - "Relief carvings show Galerius defeating Persians" → "relief carvings"
        - "Built during the reign of Emperor Diocletian" → "construction period"

        Args:
            feature: Feature description

        Returns:
            Extracted aspect string
        """
        feature_lower = feature.lower()

        # Common architectural elements
        architectural_terms = {
            'tower': 'tower structures',
            'column': 'column structures',
            'pillar': 'pillar structures',
            'arch': 'arched structures',
            'dome': 'dome structures',
            'wall': 'wall structures',
            'gate': 'gateway architecture',
            'relief': 'relief carvings',
            'carving': 'sculptural carvings',
            'sculpture': 'sculptural elements',
            'mosaic': 'mosaic artwork',
            'fresco': 'fresco paintings',
            'inscription': 'inscriptions and text'
        }

        for term, aspect in architectural_terms.items():
            if term in feature_lower:
                return aspect

        # Historical/temporal references
        temporal_terms = {
            'built': 'construction history',
            'reign': 'historical period',
            'century': 'historical period',
            'emperor': 'imperial context',
            'king': 'royal context',
            'battle': 'military history',
            'war': 'military history',
            'conquest': 'military conquest'
        }

        for term, aspect in temporal_terms.items():
            if term in feature_lower:
                return aspect

        # Fallback: extract key nouns (capitalized words or long words)
        import re
        capitalized = re.findall(r'\b[A-Z][a-z]+\b', feature)
        if capitalized:
            return f"{capitalized[0].lower()} context"

        long_words = re.findall(r'\b[a-z]{6,}\b', feature_lower)
        if long_words:
            return f"{long_words[0]} details"

        # Ultimate fallback
        return "additional details"

    def _build_aspect_research_prompt(
        self,
        poi_name: str,
        city: str,
        aspect: str,
        feature_context: str,
        existing_research: Dict
    ) -> str:
        """
        Build focused research prompt for specific aspect

        Args:
            poi_name: POI name
            city: City name
            aspect: Extracted aspect (e.g., "tower structures")
            feature_context: Original feature description
            existing_research: Existing research data (for context)

        Returns:
            Research prompt string
        """
        # Build summary of existing research
        existing_summary = ""
        if 'poi' in existing_research and 'description' in existing_research['poi']:
            existing_summary = f"Known: {existing_research['poi']['description']}"

        prompt = f"""
You are a historical researcher conducting FOCUSED research to fill a specific gap.

POI: {poi_name}
City: {city}
EXISTING RESEARCH: {existing_summary}

MISSING INFORMATION:
We need detailed information about: {aspect}

CONTEXT: The tour guide needs to cover this feature:
"{feature_context}"

But our current research lacks specific details about {aspect}.

TASK: Research {poi_name} specifically focusing on {aspect}.

Extract information in YAML format:

```yaml
aspect: "{aspect}"
poi_name: "{poi_name}"

core_features:  # Physical details about {aspect} that visitors can see/experience
  - # Specific measurements, materials, visual characteristics
  - # How to identify or recognize this aspect
  - # Current condition and state

people:  # People associated with {aspect} (if applicable)
  - name:
    role:
    relationship_to_aspect:  # How they relate to {aspect}

events:  # Events related to {aspect} (if applicable)
  - name:
    date:
    significance:  # How this event relates to {aspect}

locations:  # Sub-locations or parts related to {aspect} (if applicable)
  - name:
    description:

concepts:  # Historical/cultural concepts related to {aspect} (if applicable)
  - name:
    explanation:
```

IMPORTANT:
- Focus ONLY on {aspect} - don't repeat general information
- Include SPECIFIC DETAILS: exact measurements, materials, numbers, dates
- Prioritize information that helps a tour guide explain {aspect} to visitors
- If {aspect} doesn't exist or you find no information, return minimal structure

Output ONLY valid YAML, no markdown fences or extra text.
"""
        return prompt
