# Knowledge Graph Architecture for Pocket Guide

## Executive Summary

This document outlines the architectural vision for Pocket Guide's content system, transitioning from isolated POI descriptions to a **connected knowledge graph** that enables personalized, multi-dimensional tour experiences.

**Key Innovation**: Instead of pre-generating multiple transcript versions, we create a rich, connected knowledge base where each fact is a node with labels, enabling dynamic generation tailored to any user preference.

---

## 🎯 The Problem

### Current Limitations
- Each POI is isolated (no connections between related attractions)
- Duplicate knowledge across POIs (e.g., "Galerius" bio repeated in 3 places)
- Cannot personalize for different audiences (kids, architecture students, history buffs)
- Cannot recommend related POIs based on user interests
- Manual effort required to maintain consistency

### Failed Approach: Pre-generation
Pre-generating transcripts for each dimension (history version, drama version, architecture version) and stitching them together creates:
- ❌ Poor narrative flow (repetitive introductions)
- ❌ No unified dramatic arc
- ❌ Storage explosion (100 POIs × 5 versions = 500 transcripts)
- ❌ Inflexible (can't handle novel combinations)

---

## 💡 The Solution: Knowledge Graph

### Core Concept

Instead of storing complete transcripts, store **knowledge as a connected graph**:

```
POI Node ← [connects to] → Person Node
                              ↓
                         [experienced]
                              ↓
                         Event Node ← [similar to] → Analogy Node
                              ↓
                         [labels: drama, history, irony]
```

**Each node has:**
- **Type**: Person, Event, Location, Concept, Analogy, Architecture
- **Labels**: drama, history, architecture, irony, native, modern, etc.
- **Properties**: Name, dates, specific details, emotional tone
- **Relationships**: How it connects to other nodes

**Generation Process:**
1. User specifies interests: "I want drama + history"
2. System queries graph: "Find all nodes with labels [drama] or [history]"
3. Filter includes nodes labeled [native] (always required)
4. Generate **single unified narrative** from filtered subgraph
5. Natural flow, no stitching required

---

## 🏗️ Architecture Overview

### Visual Example: Arch of Galerius

```
                    ┌─────────────────┐
                    │ Arch of Galerius│ [POI]
                    │   [NATIVE]      │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────┐      ┌──────────────┐      ┌──────────┐
   │Galerius │      │ Via Egnatia  │      │ Rotunda  │
   │ [NATIVE]│      │   [NATIVE]   │      │ [NATIVE] │
   │[PERSON] │      │  [LOCATION]  │      │   [POI]  │
   └────┬────┘      └──────┬───────┘      └────┬─────┘
        │                  │                    │
   ┌────┼──────┐          │              ┌─────┴────┐
   │    │      │          │              │          │
   ▼    ▼      ▼          ▼              ▼          ▼
┌──────┐┌─────┐┌─────┐ ┌─────┐    ┌──────┐  ┌────────┐
│Chariot││Persian│Rule │ │Times│    │Corpo-│  │Christian│
│Humil- ││War   │of   │ │Square│    │rate  │  │Church  │
│iation ││[HIST]│Four │ │[MOD]│    │Mgmt  │  │[IRONY] │
│[DRAMA]│└──────┘[POL]│ │[ANAL]│    │[ANAL]│  │[HIST]  │
│[HIST] │       └─────┘ └─────┘    └──────┘  └────────┘
└───────┘
```

### Node Types

| Type | Purpose | Examples |
|------|---------|----------|
| **POI** | Main attractions | Arch of Galerius, Rotunda, Colosseum |
| **Person** | Historical figures | Galerius, Diocletian, Julius Caesar |
| **Event** | Historical events | Chariot Humiliation, Persian War |
| **Location** | Places, streets | Via Egnatia, Roman Forum |
| **Concept** | Ideas, systems | Tetrarchy, Roman Republic |
| **Analogy** | Modern parallels | Times Square, Corporate Management |
| **Architecture** | Design elements | Quadripylon, Dome, Columns |

### Label System

| Category | Labels | Purpose |
|----------|--------|---------|
| **Core** | `native`, `required`, `optional` | Determines inclusion priority |
| **Thematic** | `drama`, `history`, `architecture`, `art`, `politics`, `military`, `propaganda`, `irony` | User filtering |
| **Audience** | `kids-friendly`, `adult`, `academic`, `general` | Content appropriateness |
| **Presentation** | `modern`, `analogy`, `visual`, `emotional`, `funny`, `shocking` | How to use in narrative |
| **Quality** | `specific-detail`, `vivid`, `relatable`, `memorable` | Narrative value |

### Relationship Types

| Relationship | Example | Purpose |
|--------------|---------|---------|
| `HAS_CORE_STORY` | Arch → Galerius | Core narrative elements |
| `EXPERIENCED` | Galerius → Chariot Humiliation | Person's life events |
| `LOCATED_ON` | Arch → Via Egnatia | Spatial relationships |
| `SIMILAR_TO` | Via Egnatia → Times Square | Modern analogies |
| `LED_TO` | Defeat → Humiliation → Victory | Causal narrative flow |
| `CONNECTED_TO` | Arch → Rotunda | Physical/thematic links |

---

## 🔄 Generation Flow

### Example: User Requests "Drama + History for Adults"

```
Step 1: Query Graph
──────────────────
MATCH (poi:POI {id: "arch-of-galerius"})
MATCH path = (poi)-[*1..3]-(node)
WHERE
  "native" IN node.labels OR
  "drama" IN node.labels OR
  "history" IN node.labels
RETURN node

Step 2: Filter Results
───────────────────────
Nodes Found:
✓ Arch of Galerius [native, poi]
✓ Galerius [native, person, drama, history]
✓ Chariot Humiliation [native, drama, history, specific-detail]
✓ Persian Defeat [drama, history]
✓ Persian Victory [drama, history]
✓ Via Egnatia [native, location]
✓ Times Square Analogy [modern, analogy]
✓ Deathbed Irony [irony, drama, history]
✓ Rotunda [native, poi]
✓ Christian Church Conversion [irony, history]

Step 3: Rank by Importance
───────────────────────────
Priority:
1. [native] nodes (weight: 10)
2. User preference matches (weight: 5)
3. Connected nodes (weight: 2)

Ranked Output:
1. Galerius [native + drama + history]
2. Chariot Humiliation [native + drama + history + specific-detail]
3. Via Egnatia [native]
4. Persian Defeat [drama + history]
5. Persian Victory [drama + history]
6. Deathbed Irony [drama + history + irony]
...

Step 4: Generate Narrative
──────────────────────────
System Prompt + Filtered Knowledge Context:

"Using these knowledge nodes, create a dramatic narrative:

CORE STORY (native nodes - must include):
- Galerius: Shepherd → Emperor, huge ego
- Chariot Humiliation: Ran in dust for 1 mile
- Via Egnatia: Busiest street (like Times Square)

DRAMATIC ELEMENTS (user preference):
- Persian Defeat → led to humiliation
- Redemption through victory
- Deathbed irony: Persecutor begged Christians

Generate 5-minute transcript with:
- Opening cheat sheet
- Two big questions
- Emotional arc: setup → conflict → climax → resolution
- Modern analogies
- Twist ending"

Step 5: Single Unified Transcript
──────────────────────────────────
Output: Natural narrative with smooth transitions,
        unified dramatic arc, no stitching artifacts
```

---

## 🎁 Key Benefits

### 1. **Cross-POI Knowledge Reuse**

**Before (Flat Structure):**
```yaml
# arch-of-galerius.yaml
people:
  galerius: [full bio, 500 words]

# rotunda.yaml
people:
  galerius: [DUPLICATE full bio, 500 words]

# palace.yaml
people:
  galerius: [DUPLICATE full bio, 500 words]
```

**After (Knowledge Graph):**
```cypher
// One Galerius node, connected to all three POIs
(arch)-[:HAS_CORE_STORY]->(galerius)<-[:BUILT]-(palace)
(galerius)-[:PLANNED_TOMB]->(rotunda)

// Update once → improves all POIs!
```

### 2. **Personalization Without Pre-generation**

```
Same POI + Different Preferences = Different Narratives

Arch of Galerius + "drama + history"
  → Focus: Humiliation, redemption, irony
  → 750 words about Galerius's emotional journey

Arch of Galerius + "architecture + art"
  → Focus: Quadripylon structure, relief carvings
  → 750 words about design and propaganda art

Arch of Galerius + "kids + modern analogies"
  → Focus: Underdog story, Times Square comparison
  → 500 words with simple language, more analogies

All generated dynamically from same knowledge graph!
```

### 3. **Itinerary Generation**

```cypher
// Find POIs that tell a connected story
MATCH path = (poi1:POI)-[*1..2]-(shared)-[*1..2]-(poi2:POI)
WHERE poi1.city = "Thessaloniki"
  AND "drama" IN shared.labels
RETURN poi1, poi2, shared
ORDER BY strength_of_connection DESC

Output:
Walking Tour: "Galerius's Story"
1. Arch of Galerius (his triumph)
   ↓ [connected by Galerius's life]
2. Palace of Galerius (his residence)
   ↓ [connected by planned tomb]
3. Rotunda (his unfulfilled tomb → church)

Natural narrative flow through connected knowledge!
```

### 4. **Semantic Discovery**

```cypher
// "If you liked X, you'll love Y"
MATCH (poi1:POI {id: "arch-of-galerius"})
MATCH (poi1)-[*1..2]-(shared)-[*1..2]-(poi2:POI)
WHERE "drama" IN shared.labels
  AND "irony" IN shared.labels
RETURN poi2, COUNT(shared) as similarity
ORDER BY similarity DESC

Output:
"Based on liking Arch of Galerius (drama + irony),
 you might also enjoy:"
- Pantheon, Rome (pagan temple → church)
- Hagia Sophia, Istanbul (church → mosque → museum)
- Colosseum, Rome (gladiator arena → tourist site)
```

### 5. **Quality Compounds Over Time**

```
Today: Add new analogy
"Tetrarchy = Modern Federal Government (states + federal)"

↓ Automatically enhances:
- Arch of Galerius transcript
- Rotunda transcript
- Palace of Galerius transcript
- Any other Tetrarchy POI

Tomorrow: Add new dramatic detail
"Galerius wore purple royal robes during humiliation"

↓ Automatically enriches all Galerius stories

No manual updates to transcripts needed!
Knowledge graph is single source of truth.
```

---

## 📊 Comparison: Flat vs Graph

| Aspect | Flat YAML | Knowledge Graph |
|--------|-----------|-----------------|
| **Storage** | Duplicate data across POIs | Shared nodes, zero duplication |
| **Personalization** | Pre-generate all versions | Dynamic generation |
| **Connections** | None | Rich semantic relationships |
| **Discovery** | Manual curation | Automatic recommendations |
| **Itineraries** | Manual planning | Graph-based path finding |
| **Updates** | Edit each POI manually | Update node once, improves all |
| **Scalability** | O(n) POIs × O(m) versions | O(n) POIs + O(k) shared nodes |
| **Quality** | Static | Compounds over time |

---

## 🚀 Migration Strategy: Flat → Graph

### Phase 1: MVP with Flat Structure (Week 1-2)
**Goal**: Validate concept, gather real data

**Output**: YAML files per POI
```yaml
# arch-of-galerius.yaml
people:
  - name: Galerius
    personality: "Tough, ambitious"
    events:
      - Chariot Humiliation
      - Persian Victory
    labels: [native, drama, history]
```

**Why start flat?**
- ✅ Faster to prototype
- ✅ Learn what dimensions matter
- ✅ Validate that research agent works
- ✅ Human-readable for debugging

### Phase 2: Design Graph Schema (Week 3)
**Goal**: Analyze Phase 1 data, design optimal schema

**Activities**:
1. Review all collected YAML files
2. Identify common patterns
3. Define node types (Person, Event, Location, etc.)
4. Define relationship types (HAS_CORE_STORY, EXPERIENCED, etc.)
5. Define label taxonomy (drama, history, irony, etc.)
6. Document schema in GRAPH_SCHEMA.md

**Output**: Clear schema definition

### Phase 3: Build Converter (Week 4)
**Goal**: Migrate existing data to graph

**Implementation**:
```python
class YAMLToGraphConverter:
    def convert_poi(self, yaml_file):
        """Convert POI YAML to graph nodes + relationships"""
        data = load_yaml(yaml_file)

        # Create POI node
        poi_node = self.create_poi_node(data)

        # Create person nodes
        for person in data['people']:
            person_node = self.create_person_node(person)
            self.add_relationship(poi_node, person_node, "HAS_CORE_STORY")

            # Create event nodes for this person
            for event in person['events']:
                event_node = self.create_event_node(event)
                self.add_relationship(person_node, event_node, "EXPERIENCED")

        # ... similar for other dimensions

        return graph
```

**Output**: `poi_knowledge_graph.json` or Neo4j database

### Phase 4: Implement Graph Queries (Week 5)
**Goal**: Generate from graph instead of flat files

**Implementation**:
```python
def generate_transcript(poi_id, user_preferences):
    # Query graph
    subgraph = knowledge_graph.query(
        poi_id=poi_id,
        labels=user_preferences['interests']
    )

    # Rank nodes
    ranked_nodes = rank_by_importance(subgraph)

    # Generate
    transcript = generate_from_nodes(ranked_nodes, user_preferences)
    return transcript
```

### Phase 5: Advanced Features (Week 6+)
- Recommendation engine
- Itinerary planner
- Cross-language support
- Vector embeddings for semantic search

---

## 🛠️ Technology Stack Options

### Option 1: NetworkX (Lightweight, Start Here)
**Pros**:
- Pure Python, no external database
- Easy to prototype
- Human-readable JSON export
- Good for < 1000 POIs

**Cons**:
- No concurrent access
- All in-memory
- Limited query optimization

**When to use**: Phase 1-4 (MVP → Initial Scale)

### Option 2: Neo4j (Production, Scale)
**Pros**:
- Purpose-built graph database
- Powerful Cypher query language
- Scales to millions of nodes
- Built-in visualization

**Cons**:
- Setup complexity
- Requires server
- Learning curve

**When to use**: Phase 5+ (> 100 POIs, production ready)

### Option 3: SQLite with Graph Extension (Middle Ground)
**Pros**:
- File-based (no server)
- SQL + graph queries
- Good performance

**Cons**:
- Less mature than Neo4j
- Limited graph-specific features

**When to use**: Phase 4-5 (If avoiding Neo4j complexity)

---

## 📈 Success Metrics

### Phase 1 (Flat Structure)
- [ ] Research agent extracts 80%+ relevant facts
- [ ] Generated transcripts score 8+/12 on quality checklist
- [ ] Collected data for 10+ POIs
- [ ] Identified common patterns for graph schema

### Phase 2 (Graph Schema)
- [ ] Schema covers 90%+ of extracted data types
- [ ] Label taxonomy validated against real use cases
- [ ] Relationship types capture all connections

### Phase 3 (Migration)
- [ ] 100% of flat data converted to graph
- [ ] Zero data loss in migration
- [ ] Graph queries return expected results

### Phase 4 (Graph Generation)
- [ ] Generated quality equals or exceeds flat version
- [ ] Personalization works (same POI, different outputs)
- [ ] Generation time < 30 seconds

### Phase 5 (Advanced Features)
- [ ] Recommendation accuracy > 70%
- [ ] Itinerary generation produces coherent tours
- [ ] Cross-POI knowledge reuse demonstrated

---

## 🎯 Long-term Vision

### Year 1: Foundation
- Knowledge graph for 100+ POIs
- Personalization engine
- Itinerary generator

### Year 2: Intelligence
- AI learns which connections work best
- Automatic quality improvement
- Predictive recommendations

### Year 3: Network Effects
- User contributions to knowledge graph
- Community-verified facts
- Multi-language knowledge sharing

### Ultimate Goal
**A living, growing knowledge network that makes every tourist's experience unique and meaningful, powered by connected facts rather than isolated descriptions.**

---

## 📚 Related Documents

- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Overall project roadmap
- [PHASE1_MVP_PRD.md](PHASE1_MVP_PRD.md) - Detailed Phase 1 requirements
- [PRD.md](PRD.md) - Original product vision
- [STORYTELLER_PROMPT_GUIDE.md](STORYTELLER_PROMPT_GUIDE.md) - Content quality guidelines

---

**Document Version**: 1.0
**Last Updated**: 2025-11-20
**Status**: Architectural Vision
**Next Step**: Review and approve before Phase 1 implementation
