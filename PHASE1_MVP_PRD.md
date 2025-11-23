# Phase 1 MVP: Research-Driven Content Generation

## Product Requirements Document

**Version**: 1.0
**Date**: 2025-11-20
**Duration**: Week 1-2 (10-14 days)
**Status**: Planning

---

## 🎯 Executive Summary

**Goal**: Implement a two-step AI process (Research → Write) that automatically extracts comprehensive knowledge about POIs, stores it in structured YAML format, and uses it to generate high-quality dramatic narratives without requiring manual descriptions.

**Why This Matters**: Currently, generating quality transcripts requires manually providing detailed descriptions with dramatic elements. This MVP automates that research phase, making the system usable with just a POI name.

**Success Metric**: Generate transcript quality equal to manual description input, using only POI name + city.

---

## 📋 Objectives & Key Results (OKRs)

### Objective 1: Automated Knowledge Extraction
**Key Results**:
- [ ] Research agent extracts 8+ dimensions per POI
- [ ] 80%+ of extracted facts are relevant and accurate
- [ ] Captures "dramatic elements" (humiliations, ironies, twists)
- [ ] Identifies 2+ modern analogies per POI

### Objective 2: Structured Knowledge Storage
**Key Results**:
- [ ] YAML schema covers all content dimensions
- [ ] 100% of research data successfully stored
- [ ] Files are human-readable and editable
- [ ] Schema supports future graph migration

### Objective 3: Quality Generation from Research
**Key Results**:
- [ ] Generated transcripts score 9+/12 on quality checklist
- [ ] Quality comparable to manual description input (90%+)
- [ ] Storytelling structure maintained (cheat sheet, questions, parts)
- [ ] Modern analogies naturally incorporated

---

## 🏗️ System Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│  USER INPUT                                                 │
│  ./pocket-guide generate --city "Rome" --poi "Colosseum"   │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: RESEARCH PHASE                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Research Agent                                       │  │
│  │ - Queries AI with research prompt                    │  │
│  │ - Extracts: people, events, locations, concepts     │  │
│  │ - Finds: drama, irony, modern analogies             │  │
│  │ - Labels each element by dimension                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↓                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Output: poi_research/{city}/{poi}.yaml              │  │
│  │ - Structured data with all dimensions                │  │
│  │ - Labels: [native], [drama], [history], etc.        │  │
│  │ - Human-readable and editable                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: STORYTELLING PHASE                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Load Research Data                                   │  │
│  │ - Read YAML file                                     │  │
│  │ - Filter by user preferences (interests)            │  │
│  │ - Prioritize [native] labeled elements              │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↓                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Storytelling Agent                                   │  │
│  │ - Uses filtered research data as context            │  │
│  │ - Applies storytelling prompt (cheat sheet, etc.)   │  │
│  │ - Generates unified narrative                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↓                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Output: transcript.txt                               │  │
│  │ - High-quality dramatic narrative                    │  │
│  │ - Natural flow, no stitching artifacts              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Recursive Research Architecture

**Key Innovation**: Research happens in **multiple layers** to capture complete knowledge with context.

#### Why Recursive Research?

**Problem with Single-Layer**:
```
Research "Arch of Galerius"
  ↓
Extract: Galerius (person)
Done. ❌ Missing: Who is Diocletian? What's the Rule of Four?
```

**Solution with 2-Layer Recursive**:
```
Layer 0: Research "Arch of Galerius"
  ↓ Identifies: Galerius [native], Via Egnatia [native]

Layer 1: Research each [native] entity
  Research "Galerius"
    ↓ Identifies: Diocletian [secondary], Persian War [event]
  Research "Via Egnatia"
    ↓ Identifies: Roman road system [concept]

Layer 2: Research dramatic secondary entities
  Research "Diocletian"
    ↓ Extract: Why he humiliated Galerius (the drama!)
  Research "Rule of Four"
    ↓ Extract: Corporate management analogy
```

**Result**: Complete story with context, relationships, and drama!

#### Depth Control Strategy

| Layer | Research Target | Trigger Conditions | Max Entities |
|-------|----------------|-------------------|--------------|
| **Layer 0** | The POI itself | Always | 1 |
| **Layer 1** | Entities with `[native]` label | Always | 3-5 |
| **Layer 2** | Secondary entities with `[drama]`, `[irony]`, or critical relationships | Conditional | 2-3 |
| **Layer 3+** | N/A | Never (stop at Layer 2) | 0 |

#### Layer 2 Decision Criteria

Research secondary entity if **any** of these are true:
- ✅ Labeled `[drama]`, `[irony]`, or `[shocking]`
- ✅ Person with relationship type: `conflict`, `rival`, `boss`, `enemy`
- ✅ Labeled `[critical-context]`
- ✅ Directly involved in core dramatic event

#### Example: Arch of Galerius Research Flow

```
Layer 0: Arch of Galerius
  ↓ Entities found:
  - Galerius [native, person]
  - Via Egnatia [native, location]
  - Rotunda [native, connected POI]
  - Persian War [event]

Layer 1: Research native entities
  ├─ Galerius
  │   ↓ Secondary entities found:
  │   - Diocletian [person, boss, conflict] ← Research in Layer 2!
  │   - Chariot Humiliation [event, drama] ← Keep as event
  │   - Rule of Four [concept, critical-context] ← Research in Layer 2!
  │
  └─ Via Egnatia
      ↓ Secondary entities found:
      - Roman road system [concept] ← Skip (not dramatic)
      - Times Square analogy [modern] ← Keep as analogy

Layer 2: Research critical secondaries
  ├─ Diocletian
  │   ↓ Extract: Created Rule of Four, tough manager, etc.
  │
  └─ Rule of Four
      ↓ Extract: 2 senior + 2 junior emperors, like corporate structure

Total API Calls: 6 (1 POI + 2 Layer 1 + 2 Layer 2 + 1 storytelling)
Result: Complete dramatic narrative with full context!
```

#### API Cost Analysis

| Approach | Calls | Tokens | Cost (GPT-4) | Quality | Time |
|----------|-------|--------|--------------|---------|------|
| No Research | 1 | 4K | $0.04 | 6/10 | 15s |
| Single Layer | 2 | 8K | $0.08 | 7/10 | 30s |
| **2-Layer Recursive** | **4-6** | **16K-24K** | **$0.16-$0.24** | **9-10/10** | **60-90s** |

**ROI**: Extra $0.16 for 3-4x quality improvement ✅ **Worth it!**

### Directory Structure

```
project/
├── poi_research/                    # NEW: Research data storage
│   ├── rome/
│   │   ├── colosseum.yaml
│   │   ├── roman-forum.yaml
│   │   └── pantheon.yaml
│   └── thessaloniki/
│       ├── arch-of-galerius.yaml
│       └── rotunda.yaml
│
├── content/                         # EXISTING: Generated transcripts
│   ├── rome/
│   │   └── colosseum/
│   │       ├── transcript.txt
│   │       ├── metadata.json
│   │       └── audio.mp3
│   └── ...
│
├── src/
│   ├── content_generator.py        # MODIFIED: Add research phase
│   ├── research_agent.py           # NEW: Research extraction
│   └── ...
│
├── config.yaml                      # MODIFIED: Add research config
└── ...
```

---

## 📝 Detailed Requirements

### Feature 1: Research Agent

#### 1.1 Research Prompt Design

**Requirement**: Create comprehensive research prompt that extracts all necessary dimensions.

**Prompt Structure**:
```python
RESEARCH_PROMPT = """
You are a historical researcher extracting information for dramatic tour guide narratives.

POI: {poi_name}
City: {city}
User Description (if provided): {user_description}

Your task is to research and extract information in the following categories:

1. BASIC INFORMATION
   - Name (including local names)
   - Historical period
   - Date built (absolute and relative: "1,700 years ago")
   - Current state
   - Brief description (1-2 sentences)

2. KEY PEOPLE
   For each person:
   - Name and role
   - Personality traits (2-3 adjectives or phrases)
   - Origin story (e.g., "started as shepherd")
   - Dramatic events in their life
   - Ironic ending or fate

3. DRAMATIC EVENTS
   For each event:
   - Name of event
   - Date (absolute and relative)
   - Emotional tone (humiliation, triumph, tragedy, irony)
   - Specific details (exact numbers, distances, actions)
   - Who was involved
   - What led to it
   - What resulted from it

4. LOCATIONS & GEOGRAPHY
   - Where exactly is it
   - What street/area (significance)
   - Connected locations
   - Spatial relationships

5. HISTORICAL CONTEXT
   - Political situation
   - Cultural context
   - Why it was built
   - What problem it solved
   - Larger historical movements

6. ARCHITECTURE & DESIGN
   - Structural features
   - Materials used
   - Artistic elements
   - Engineering innovations
   - What remains vs. original

7. PROPAGANDA & MESSAGING
   - What message did builders want to send
   - What were they hiding or exaggerating
   - Visual propaganda techniques
   - Location strategy (why here)

8. IRONIC ENDINGS & TWISTS
   - What unexpected thing happened later
   - How did original purpose change
   - Ironic fate of people involved
   - Contrasts between intention and outcome

9. MODERN ANALOGIES
   For each major concept, provide:
   - Ancient concept
   - Modern equivalent (be specific: "Times Square" not just "busy place")
   - Brief explanation of similarity

10. CULTURAL SIGNIFICANCE
    - What it represents
    - Tourist experience (what to look for)
    - Connected attractions
    - Practical tips

For each piece of information, add labels:
- [native] = Core to POI story, must always include
- [drama] = Dramatic/emotional element
- [history] = Historical fact
- [architecture] = Architectural detail
- [irony] = Ironic twist
- [propaganda] = Messaging/propaganda element
- [modern] = Modern analogy
- [specific-detail] = Has exact numbers/measurements
- [vivid] = Can paint vivid scene
- [memorable] = Highly memorable
- [shocking] = Surprising or shocking

OUTPUT FORMAT: Structured YAML (see schema below)

IMPORTANT:
- Focus on SPECIFIC DETAILS (exact distances, numbers, quotes)
- Find the EMBARRASSING moments (defeats, failures, humiliations)
- Identify IRONIES (what's the twist?)
- Create MODERN PARALLELS (Instagram, Amazon, Times Square, etc.)
- Extract EMOTIONAL ELEMENTS (shame, pride, revenge, fear)
"""
```

#### 1.2 Research Agent Implementation (Recursive)

**File**: `src/research_agent.py`

**Class**: `ResearchAgent`

**Key Feature**: Implements 2-layer recursive research to capture complete knowledge with context.

**Methods**:

```python
class ResearchAgent:
    def __init__(self, config):
        self.config = config
        self.ai_config = config.get('ai_providers', {})
        self.research_config = config.get('research', {})

        # Depth control
        self.max_depth = self.research_config.get('max_depth', 2)
        self.max_entities_per_layer = self.research_config.get('max_entities_per_layer', 5)
        self.max_api_calls = self.research_config.get('max_api_calls', 10)

        # Tracking
        self.researched_entities = set()  # Avoid duplicates
        self.api_calls_made = 0

    def research_poi_recursive(
        self,
        poi_name: str,
        city: str,
        user_description: str = None,
        provider: str = None
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

        print(f"\n  [RESEARCH] Starting recursive research for {poi_name}")
        print(f"  [CONFIG] Max depth: {self.max_depth}, Max entities/layer: {self.max_entities_per_layer}")

        # Layer 0: Research the POI itself
        print(f"\n  [LAYER 0] Researching POI: {poi_name}")
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

        knowledge_graph["research_depth"] = 2
        knowledge_graph["total_entities"] = len(self.researched_entities)
        knowledge_graph["api_calls"] = self.api_calls_made

        print(f"\n  [COMPLETE] Research finished:")
        print(f"    - Depth: {knowledge_graph['research_depth']} layers")
        print(f"    - Entities: {knowledge_graph['total_entities']}")
        print(f"    - API calls: {knowledge_graph['api_calls']}")

        return knowledge_graph

    def _should_research_layer1(self, entity: Dict) -> bool:
        """Decide if entity should be researched in Layer 1"""
        labels = entity.get('labels', [])

        # Always research [native] entities
        if 'native' in labels:
            return True

        # Research if it's a person central to story
        if entity['type'] == 'Person' and 'drama' in labels:
            return True

        return False

    def _should_research_layer2(self, entity: Dict, parent_data: Dict) -> bool:
        """Decide if entity should be researched in Layer 2"""
        labels = entity.get('labels', [])

        # Research if it has high narrative value
        if any(label in labels for label in ['drama', 'irony', 'shocking', 'critical-context']):
            return True

        # Research if it's a person in conflict/relationship
        if entity['type'] == 'Person':
            relationships = entity.get('relationship_type', '')
            if any(rel in relationships for rel in ['conflict', 'rival', 'boss', 'enemy', 'ally']):
                return True

        return False

    def _research_entity(
        self,
        entity_type: str,
        entity_name: str,
        context: Dict,
        provider: str
    ) -> Dict:
        """Research a single entity with specialized prompt"""

        # Build specialized prompt based on entity type
        if entity_type == "POI":
            prompt = self._build_poi_research_prompt(entity_name, context)
        elif entity_type == "Person":
            prompt = self._build_person_research_prompt(entity_name, context)
        elif entity_type == "Event":
            prompt = self._build_event_research_prompt(entity_name, context)
        elif entity_type == "Concept":
            prompt = self._build_concept_research_prompt(entity_name, context)
        else:
            prompt = self._build_generic_research_prompt(entity_name, context)

        # Call AI
        raw_response = self._call_ai(prompt, provider)
        self.api_calls_made += 1

        # Parse response
        parsed_data = self._parse_research_response(raw_response, entity_type)

        return parsed_data

    def _extract_entities(self, data: Dict) -> List[Dict]:
        """Extract entities mentioned in research data"""
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

        return entities

    def _build_person_research_prompt(self, person_name: str, context: Dict) -> str:
        """Build specialized prompt for researching a person"""
        return f"""
Research historical figure: {person_name}

Context: Related to {context.get('poi')} in {context.get('city')}
{f"Relationship: {context.get('relationship')}" if context.get('relationship') else ""}

Extract:
1. BIOGRAPHY
   - Full name and titles
   - Birth/death dates (absolute + relative like "1,700 years ago")
   - Origin story (where from, social class, background)
   - Personality traits (3-5 descriptive adjectives/phrases)
   Label: [native] if central to POI story

2. DRAMATIC LIFE EVENTS
   For each major event:
   - Name of event
   - Date (absolute + relative)
   - Specific details (exact actions, numbers, distances)
   - Emotional tone (humiliation, triumph, tragedy, etc.)
   - What led to it
   - What resulted from it
   Labels: [drama], [shocking], [irony]

3. KEY RELATIONSHIPS
   For each important person they interacted with:
   - Name
   - Relationship type (boss, rival, ally, enemy, mentor, etc.)
   - Nature of interaction (conflict, cooperation, betrayal)
   - Dramatic incidents between them
   Labels: [secondary, drama] if important to main story

4. IRONIC ENDING
   - How did they die or what was their fate?
   - What unexpected outcome?
   - Contrast between their intention and reality
   Labels: [irony], [shocking]

5. MODERN PARALLELS
   - What modern figure, situation, or story is similar?
   - Relatable comparisons for audience

Output structured YAML format.
"""

    def save_research(self, research_data: Dict, output_path: Path):
        """Save research data to YAML file"""
        with open(output_path, 'w') as f:
            yaml.dump(research_data, f, default_flow_style=False, sort_keys=False)

    def load_research(self, research_path: Path) -> Dict:
        """Load research data from YAML file"""
        with open(research_path, 'r') as f:
            return yaml.safe_load(f)
```

#### 1.3 YAML Schema

**File**: `docs/RESEARCH_SCHEMA.yaml`

```yaml
# POI Research Data Schema

poi_id: string                    # Unique identifier (slug)
name: string                      # Full name
city: string                      # City name
country: string                   # Country name

basic_info:
  period: string                  # Historical period
  date_built: string              # "298-303 AD"
  date_relative: string           # "about 1,700 years ago"
  current_state: string           # Description of current condition
  description: string             # 1-2 sentence overview
  labels: [list]                  # [native, poi]

people:
  - id: string
    name: string
    role: string
    personality: string           # "Ambitious, tough, huge ego"
    origin: string                # "Started as shepherd"
    labels: [list]                # [native, drama, history]

    events:
      - id: string
        name: string
        date: string
        date_relative: string
        emotional_tone: string    # "humiliation", "triumph"
        specific_detail: string   # The juicy details!
        labels: [list]            # [drama, history, specific-detail, vivid]

    ironic_ending:
      detail: string
      twist: string
      labels: [list]              # [irony, shocking]

events:
  - id: string
    name: string
    date: string
    date_relative: string
    emotional_tone: string
    specific_detail: string
    involved_people: [list]       # Person IDs
    led_to: [list]                # Event IDs
    labels: [list]

locations:
  - id: string
    name: string
    significance: string
    description: string
    labels: [list]                # [native, geography]

historical_context:
  - type: string                  # "political", "military", "cultural"
    name: string
    description: string
    relevance: string
    labels: [list]

architecture:
  - id: string
    feature: string
    description: string
    materials: [list]
    current_state: string
    labels: [list]                # [architecture, visual]

propaganda:
  location_strategy:
    why_here: string
    significance: string
    modern_parallel: string
    labels: [list]                # [propaganda, strategic]

  visual_elements:
    - technique: string
      reality: string             # What was reality
      message: string             # What they wanted you to believe
      modern_equivalent: string
      labels: [list]              # [propaganda, visual, irony]

modern_analogies:
  - id: string
    ancient_concept: string
    modern_equivalent: string
    explanation: string
    labels: [list]                # [modern, analogy, relatable]

cultural_significance:
  symbolism: [list]
  tourist_experience:
    what_to_look_for: [list]
    connections: [list]           # Related POIs
    practical_tips: [list]
  labels: [list]

dramatic_elements:
  opening_hooks: [list]           # For cheat sheet
  central_questions: [list]       # Big questions to answer
  conflict: string                # Setup → conflict
  climax: string                  # Resolution
  twist: string                   # Unexpected ending
  emotional_arc: [list]           # Journey through emotions

metadata:
  research_date: string
  research_provider: string
  research_quality: string        # "high", "medium", "low"
  completeness: number            # 0-1 score
```

### Feature 2: Modified Content Generator

#### 2.1 Integration with Research

**File**: `src/content_generator.py`

**Modified Method**: `generate()`

```python
def generate(
    self,
    poi_name: str,
    city: str = None,
    provider: str = None,
    description: str = None,
    interests: list = None,
    use_research: bool = True,      # NEW parameter
    force_research: bool = False,    # NEW parameter
    **kwargs
) -> Tuple[str, List[str]]:
    """
    Generate tour guide content for a POI

    Args:
        use_research: Use research phase (default: True)
        force_research: Re-research even if data exists (default: False)

    Returns:
        Tuple of (transcript, summary_points)
    """

    # NEW: Check if research exists
    research_path = self._get_research_path(city, poi_name)

    if use_research:
        # NEW: Research phase
        if force_research or not research_path.exists():
            print("  [STEP 1/2] Researching POI...")
            research_agent = ResearchAgent(self.config)
            research_data = research_agent.research_poi(
                poi_name=poi_name,
                city=city,
                user_description=description,
                provider=provider
            )

            # Save research
            research_path.parent.mkdir(parents=True, exist_ok=True)
            research_agent.save_research(research_data, research_path)
            print(f"  ✓ Research saved: {research_path}")
        else:
            print("  [STEP 1/2] Loading existing research...")
            research_agent = ResearchAgent(self.config)
            research_data = research_agent.load_research(research_path)
            print(f"  ✓ Research loaded: {research_path}")

        # NEW: Filter research by interests
        filtered_research = self._filter_research(research_data, interests)

        # NEW: Build storytelling prompt with research
        print("  [STEP 2/2] Generating narrative from research...")
        prompt = self._create_storytelling_prompt(
            poi_name=poi_name,
            city=city,
            research_data=filtered_research,
            interests=interests,
            **kwargs
        )
    else:
        # OLD: Direct generation (backward compatibility)
        print("  [GENERATING] Creating content...")
        prompt = self._create_prompt(
            poi_name=poi_name,
            city=city,
            description=description,
            interests=interests,
            **kwargs
        )

    # Call AI to generate
    raw_content = self._call_provider(prompt, provider)

    # Parse response
    transcript, summary_points = self._parse_response(raw_content)

    return transcript, summary_points
```

#### 2.2 New Helper Methods

```python
def _get_research_path(self, city: str, poi_name: str) -> Path:
    """Get path to research file"""
    from src.utils import slugify
    city_slug = slugify(city)
    poi_slug = slugify(poi_name)
    return Path("poi_research") / city_slug / f"{poi_slug}.yaml"

def _filter_research(
    self,
    research_data: Dict,
    interests: List[str]
) -> Dict:
    """
    Filter research data based on user interests

    Priority:
    1. Always include [native] labeled elements
    2. Include elements matching user interests
    3. Include highly-rated elements ([memorable], [shocking])

    Returns:
        Filtered copy of research_data
    """
    if not interests:
        return research_data

    filtered = copy.deepcopy(research_data)

    # Implementation: Filter each dimension based on labels
    # Keep all [native] items
    # Keep items with labels matching interests

    return filtered

def _create_storytelling_prompt(
    self,
    poi_name: str,
    city: str,
    research_data: Dict,
    interests: List[str],
    **kwargs
) -> str:
    """
    Create prompt using research data as context

    Returns:
        Complete prompt for AI
    """
    # Get system prompt
    system_prompt = self.config.get('content_generation', {}).get('system_prompt', '')

    # Serialize research data for prompt
    research_context = self._serialize_research(research_data)

    # Build prompt
    prompt = f"""
{system_prompt}

RESEARCH FINDINGS FOR: {poi_name}, {city}
{research_context}

USER PREFERENCES:
- Interests: {', '.join(interests) if interests else 'General audience'}

TASK:
Create a dramatic 5-minute tour guide narrative using the research above.
- Prioritize elements marked [NATIVE]
- Emphasize elements matching user interests
- Follow storytelling structure: cheat sheet, big questions, parts, callbacks, twist
- Use modern analogies provided in research
- Include specific details (numbers, distances, quotes)

Generate transcript with natural flow and unified dramatic arc.
"""

    return prompt

def _serialize_research(self, research_data: Dict) -> str:
    """
    Convert research data to readable text for AI prompt

    Returns:
        Formatted text summary of research
    """
    lines = []

    # Basic info
    lines.append("BASIC INFORMATION:")
    basic = research_data.get('basic_info', {})
    lines.append(f"- Period: {basic.get('period')}")
    lines.append(f"- Built: {basic.get('date_relative', basic.get('date_built'))}")
    lines.append(f"- Description: {basic.get('description')}")
    lines.append("")

    # People
    if research_data.get('people'):
        lines.append("KEY PEOPLE:")
        for person in research_data['people']:
            native = "[NATIVE]" if 'native' in person.get('labels', []) else ""
            lines.append(f"- {person['name']} {native}")
            lines.append(f"  Role: {person.get('role')}")
            lines.append(f"  Personality: {person.get('personality')}")

            if person.get('events'):
                lines.append("  Events:")
                for event in person['events']:
                    labels_str = ', '.join(event.get('labels', []))
                    lines.append(f"    • {event['name']} [{labels_str}]")
                    lines.append(f"      {event.get('specific_detail')}")

            if person.get('ironic_ending'):
                lines.append(f"  Ironic Ending: {person['ironic_ending']['detail']}")
            lines.append("")

    # Dramatic events
    if research_data.get('events'):
        lines.append("DRAMATIC EVENTS:")
        for event in research_data['events']:
            labels_str = ', '.join(event.get('labels', []))
            lines.append(f"- {event['name']} [{labels_str}]")
            lines.append(f"  {event.get('specific_detail')}")
            lines.append("")

    # Modern analogies
    if research_data.get('modern_analogies'):
        lines.append("MODERN ANALOGIES:")
        for analogy in research_data['modern_analogies']:
            lines.append(f"- {analogy['ancient_concept']} = {analogy['modern_equivalent']}")
            lines.append(f"  {analogy.get('explanation')}")
            lines.append("")

    # Dramatic elements
    if research_data.get('dramatic_elements'):
        drama = research_data['dramatic_elements']
        lines.append("STORYTELLING GUIDANCE:")
        if drama.get('opening_hooks'):
            lines.append("Opening Hooks:")
            for hook in drama['opening_hooks']:
                lines.append(f"  - {hook}")
        if drama.get('central_questions'):
            lines.append("Central Questions:")
            for q in drama['central_questions']:
                lines.append(f"  - {q}")
        if drama.get('conflict'):
            lines.append(f"Conflict: {drama['conflict']}")
        if drama.get('climax'):
            lines.append(f"Climax: {drama['climax']}")
        if drama.get('twist'):
            lines.append(f"Twist: {drama['twist']}")
        lines.append("")

    return "\n".join(lines)
```

### Feature 3: CLI Updates

#### 3.1 New CLI Options

**File**: `src/cli.py`

**Modified Command**: `generate`

```python
@cli.command()
@click.option('--city', prompt=True, help='City name')
@click.option('--poi', prompt=True, help='Point of interest name')
@click.option('--provider', help='AI provider (openai, anthropic, google)')
@click.option('--description', help='Optional POI description')
@click.option('--interests', help='Comma-separated interests (e.g., history,drama)')
@click.option('--skip-research', is_flag=True, default=False,
              help='Skip research phase, use description only (old behavior)')
@click.option('--force-research', is_flag=True, default=False,
              help='Re-research even if research data exists')
@click.pass_context
def generate(ctx, city, poi, provider, description, interests, skip_research, force_research):
    """Generate tour guide content for a POI"""

    # Parse interests
    interests_list = [i.strip() for i in interests.split(',')] if interests else None

    # Show research status
    if skip_research:
        console.print("[yellow]Research phase skipped[/yellow]")
    elif force_research:
        console.print("[yellow]Forcing new research (ignoring cached data)[/yellow]")
    else:
        console.print("[cyan]Research phase enabled[/cyan]")

    # Generate
    generator = ContentGenerator(config)

    transcript, summary_points = generator.generate(
        poi_name=poi,
        city=city,
        provider=provider or default_provider,
        description=description,
        interests=interests_list,
        use_research=not skip_research,
        force_research=force_research
    )

    # ... rest of existing code
```

### Feature 4: Configuration

#### 4.1 New Config Section

**File**: `config.yaml`

```yaml
# Research Configuration
research:
  # Enable research phase by default
  enabled: true

  # Research data storage
  storage_dir: "poi_research"

  # Recursive research depth control
  max_depth: 2                     # Layer 0 → Layer 1 → Layer 2
  max_entities_per_layer: 5        # Don't research more than 5 per layer
  max_api_calls: 10                # Stop if exceeding budget

  # Layer 1: Always research entities with these labels
  layer1_triggers:
    - native
    - drama

  # Layer 2: Research if entity has these labels
  layer2_triggers:
    - drama
    - irony
    - shocking
    - critical-context

  # Layer 2: Research if relationship type matches
  layer2_relationships:
    - conflict
    - rival
    - boss
    - enemy
    - key-ally

  # Tokens allocated to each research call
  max_tokens_per_call: 4096

  # Cache research results
  cache_enabled: true
  cache_ttl_days: 30               # Re-research POIs after 30 days
  cache_entities: true             # Cache entities globally (reuse across POIs)
  entity_cache_ttl_days: 90        # Entities don't change often

  # Quality thresholds
  min_people: 1                    # Require at least 1 person
  min_events: 2                    # Require at least 2 events
  min_analogies: 1                 # Require at least 1 modern analogy

  # Label weights (for filtering during generation)
  label_weights:
    native: 10                     # Always include
    drama: 5
    history: 4
    irony: 4
    shocking: 3
    memorable: 3
    specific-detail: 2
```

---

## ✅ Acceptance Criteria

### Research Phase
- [ ] Research agent extracts all 10 dimensions
- [ ] YAML output validates against schema
- [ ] Research saved to correct path
- [ ] Cached research loaded when available
- [ ] Force research flag bypasses cache

### Content Generation
- [ ] Generated transcript uses research data
- [ ] Quality score 9+/12 on checklist
- [ ] Native elements always included
- [ ] Modern analogies incorporated naturally
- [ ] Specific details present (numbers, distances)

### CLI
- [ ] `--skip-research` flag works (backward compatibility)
- [ ] `--force-research` flag re-researches
- [ ] Progress messages show research status
- [ ] Works with minimal input (just city + POI)

### Documentation
- [ ] RESEARCH_SCHEMA.yaml documented
- [ ] README updated with research features
- [ ] QUICKSTART includes research examples
- [ ] Example research YAML files provided

---

## 🧪 Testing Plan

### Unit Tests

```python
# tests/test_research_agent.py

def test_research_poi_basic():
    """Test basic research extraction"""
    agent = ResearchAgent(config)
    research = agent.research_poi("Colosseum", "Rome")

    assert research['poi_id'] == "colosseum"
    assert research['city'] == "Rome"
    assert len(research['people']) >= 1
    assert len(research['events']) >= 2

def test_research_saves_correctly():
    """Test YAML save/load"""
    agent = ResearchAgent(config)
    research = {...}
    path = Path("test_output/research.yaml")

    agent.save_research(research, path)
    loaded = agent.load_research(path)

    assert loaded == research

def test_filter_research_by_interests():
    """Test research filtering"""
    generator = ContentGenerator(config)
    research = load_test_research()

    filtered = generator._filter_research(research, interests=["drama"])

    # Should include all [native] + [drama] labeled items
    assert all('native' in item['labels'] or 'drama' in item['labels']
               for item in filtered['people'])
```

### Integration Tests

```python
# tests/test_integration.py

def test_end_to_end_with_research():
    """Test complete flow: research → generate"""

    # Generate with research
    generator = ContentGenerator(config)
    transcript, summary = generator.generate(
        poi_name="Test POI",
        city="Test City",
        use_research=True
    )

    # Verify research was created
    research_path = Path("poi_research/test-city/test-poi.yaml")
    assert research_path.exists()

    # Verify transcript quality
    assert len(transcript) > 500
    assert "Part 1:" in transcript or "First:" in transcript
    assert len(summary) >= 3

def test_cached_research_reuse():
    """Test that cached research is reused"""
    generator = ContentGenerator(config)

    # First generation
    transcript1, _ = generator.generate("POI", "City", use_research=True)

    # Second generation (should use cache)
    transcript2, _ = generator.generate("POI", "City", use_research=True)

    # Should be fast (no API call for research)
    # Transcripts may differ but should use same research data
```

### Manual Testing Checklist

- [ ] Test with POI name only (no description)
- [ ] Test with multiple interests
- [ ] Test with `--force-research` flag
- [ ] Test with `--skip-research` flag
- [ ] Verify YAML is human-readable
- [ ] Edit YAML manually, regenerate, verify changes
- [ ] Test with different AI providers
- [ ] Compare quality: with research vs. without

---

## 📊 Success Metrics

### Quantitative

| Metric | Target | Measurement |
|--------|--------|-------------|
| Research completeness | 80%+ | % of required fields populated |
| Generation quality score | 9/12+ | Quality checklist evaluation |
| Time to research | < 30s | Average API call time |
| Time to generate | < 30s | Average API call time |
| Total time | < 60s | End-to-end generation |
| Research reuse rate | 70%+ | % of generations using cached research |

### Qualitative

- [ ] Generated transcripts feel "dramatically improved"
- [ ] Modern analogies are natural and helpful
- [ ] Specific details make content vivid
- [ ] Ironic endings create memorable moments
- [ ] Users can generate quality content with zero manual input

---

## 🚀 Rollout Plan

### Day 1-2: Research Agent Implementation
- [ ] Create `src/research_agent.py`
- [ ] Implement research prompt
- [ ] Implement YAML save/load
- [ ] Unit tests pass

### Day 3-4: Content Generator Integration
- [ ] Modify `generate()` method
- [ ] Implement research filtering
- [ ] Implement storytelling prompt with research
- [ ] Integration tests pass

### Day 5-6: CLI & Configuration
- [ ] Add CLI flags
- [ ] Add config section
- [ ] Update help text
- [ ] Manual testing

### Day 7-8: Documentation & Examples
- [ ] Document RESEARCH_SCHEMA.yaml
- [ ] Update README.md
- [ ] Update QUICKSTART.md
- [ ] Create 3-5 example research files

### Day 9-10: Testing & Refinement
- [ ] Generate 10+ POIs
- [ ] Evaluate quality
- [ ] Iterate on prompt
- [ ] Fix bugs

### Day 11-12: Polish & Release
- [ ] Final testing
- [ ] Performance optimization
- [ ] Commit to GitHub
- [ ] Update project documentation

---

## 📚 Deliverables

### Code
- [ ] `src/research_agent.py` (new)
- [ ] `src/content_generator.py` (modified)
- [ ] `src/cli.py` (modified)
- [ ] `tests/test_research_agent.py` (new)
- [ ] `tests/test_integration.py` (modified)

### Documentation
- [ ] `docs/RESEARCH_SCHEMA.yaml` (new)
- [ ] `README.md` (updated)
- [ ] `QUICKSTART.md` (updated)
- [ ] `PHASE1_COMPLETION_REPORT.md` (new)

### Data
- [ ] `poi_research/` directory structure
- [ ] 5-10 example research YAML files
- [ ] Quality evaluation spreadsheet

### Config
- [ ] `config.yaml` (updated with research section)
- [ ] `config.example.yaml` (updated)

---

## 🎯 Definition of Done

Phase 1 MVP is complete when:

✅ **Functionality**
- [ ] Can generate transcript with only POI name + city
- [ ] Research phase extracts comprehensive data
- [ ] Research cached and reused correctly
- [ ] Generated quality equals manual description input

✅ **Quality**
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] 5+ POIs tested end-to-end
- [ ] Quality scores consistently 9+/12

✅ **Documentation**
- [ ] Schema documented
- [ ] README updated
- [ ] Examples provided
- [ ] Migration path to graph clear

✅ **User Experience**
- [ ] CLI intuitive and responsive
- [ ] Progress messages helpful
- [ ] Error messages clear
- [ ] Can manually edit research YAML

✅ **Technical**
- [ ] Code reviewed
- [ ] No critical bugs
- [ ] Performance acceptable (< 60s total)
- [ ] Committed to GitHub

---

## 🔗 Related Documents

- [KNOWLEDGE_GRAPH_ARCHITECTURE.md](KNOWLEDGE_GRAPH_ARCHITECTURE.md) - Long-term vision
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Full project roadmap
- [STORYTELLER_PROMPT_GUIDE.md](STORYTELLER_PROMPT_GUIDE.md) - Quality guidelines
- [QUICKSTART.md](QUICKSTART.md) - User guide

---

## 📞 Stakeholders & Sign-off

**Product Owner**: [User]
**Technical Lead**: [Claude Code]
**Status**: Awaiting approval

**Next Steps After Approval**:
1. Create detailed implementation tickets
2. Set up project board
3. Begin Day 1 development
4. Daily progress updates

---

**Document Status**: Ready for Review
**Last Updated**: 2025-11-20
**Version**: 1.0
