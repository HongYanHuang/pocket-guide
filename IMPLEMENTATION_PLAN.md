# Implementation Plan: Research-Then-Write & Refine Features

## Overview

This document outlines the implementation plan for two major features that will significantly improve transcript quality without requiring manual descriptions for each POI.

### Problem Statement
Currently, generating high-quality dramatic narratives requires:
1. Manually providing detailed descriptions with dramatic elements
2. Understanding the historical context beforehand
3. Trial and error to get the right tone

### Solution
1. **Medium Solution**: Two-step AI process (Research → Write)
2. **Advanced Solution**: Iterative refinement with self-critique

---

## Phase 1: Research-Then-Write Two-Step Process

### Goal
Automatically research POIs to find dramatic details, then use those details for storytelling.

### Architecture

```
User Input (POI name only)
    ↓
Step 1: RESEARCH PHASE
    ↓
AI researches POI:
- Who were the key people?
- What embarrassing/dramatic events?
- What ironic endings?
- What propaganda elements?
- Modern parallels?
    ↓
Research Summary (structured data)
    ↓
Step 2: STORYTELLING PHASE
    ↓
AI uses research to craft narrative
    ↓
Final Transcript
```

### Implementation Details

#### 1. Create Research Prompt Template

**File**: `src/content_generator.py`

**New Method**: `_research_poi(poi_name, city, user_description)`

**Research Prompt Structure**:
```python
RESEARCH_PROMPT = """
You are a historical researcher finding dramatic stories for tour guides.

POI: {poi_name}
City: {city}
{user_description}

Research and extract:

1. KEY PEOPLE:
   - Who built/created this?
   - What was their personality/character?
   - What were they famous/infamous for?

2. DRAMATIC EVENTS:
   - What failures, defeats, or embarrassments happened?
   - What was the redemption story?
   - Any humiliating or shocking details?

3. IRONIC ENDINGS:
   - What unexpected twist occurred later?
   - How did the original purpose change?
   - Any ironic fate of the people involved?

4. PROPAGANDA ELEMENTS:
   - What were they lying about or exaggerating?
   - What were they hiding?
   - How is this similar to modern social media/advertising?

5. MODERN PARALLELS:
   - What's the modern equivalent? (Amazon? Instagram? Times Square?)
   - How would this concept work today?
   - What relatable analogy can we use?

6. SPECIFIC DETAILS:
   - Exact numbers (distances, amounts, years)
   - Specific actions (e.g., "ran for a mile", "waited 3 hours")
   - Concrete facts (not vague descriptions)

Output your findings in a structured format with bullet points.
"""
```

**Expected Output**:
```
KEY PEOPLE:
- Galerius: Started as shepherd, became emperor, had huge ego

DRAMATIC EVENTS:
- Lost battle to Persians badly
- Diocletian made him run alongside chariot in dust for 1 mile
- Came back and crushed Persians, captured king's family

IRONIC ENDINGS:
- Hated Christians but begged them to pray on deathbed
- Built Rotunda as tomb but Christians turned it into church
- Never buried there

PROPAGANDA ELEMENTS:
- Four emperors carved with same faces (like Instagram filters)
- Built arch on busiest street to force people to see it
- Showed him as victor, hid his earlier defeat

MODERN PARALLELS:
- Via Egnatia = Times Square of ancient world
- Arch = biggest billboard in city center
- Rule of Four = Corporate management structure (CEO + managers)

SPECIFIC DETAILS:
- Built around 300 AD (1,700 years ago)
- Made to run 1 full mile in royal robes
- Originally 8-pillared structure (quadripylon)
```

#### 2. Modify Generate Method

**Current Flow**:
```python
def generate(self, poi_name, ...):
    prompt = self._create_prompt(poi_name, ...)
    content = self._call_ai(prompt)
    return content
```

**New Flow**:
```python
def generate(self, poi_name, ...):
    # Step 1: Research
    print("  [STEP 1/2] Researching dramatic details...")
    research = self._research_poi(poi_name, city, description)

    # Step 2: Write using research
    print("  [STEP 2/2] Crafting narrative from research...")
    prompt = self._create_storytelling_prompt(poi_name, research)
    content = self._call_ai(prompt)
    return content
```

#### 3. Update Storytelling Prompt

**File**: `src/content_generator.py` → `_create_storytelling_prompt()`

```python
STORYTELLING_PROMPT = """
{system_prompt}

{style_guidelines}

RESEARCH FINDINGS:
{research_summary}

Now create an engaging 2-5 minute tour guide script for:
POI: {poi_name}
City: {city}

Use the research findings above to craft a dramatic narrative following all structure requirements.
"""
```

#### 4. Configuration Option

**File**: `config.yaml`

```yaml
content_generation:
  # Enable two-step research process (research → write)
  use_research_phase: true  # Set to false to skip research phase

  # Tokens allocated to each phase
  research_tokens: 2048
  storytelling_tokens: 4096
```

### Testing Plan

**Test Cases**:
1. Generate without description (research should fill in details)
2. Generate with minimal description (research should expand)
3. Compare output quality: single-step vs two-step
4. Test with different providers (OpenAI, Anthropic, Google)

**Success Metrics**:
- [ ] Can generate quality transcript with ONLY POI name
- [ ] Research finds 3+ dramatic details
- [ ] Research identifies ironic ending
- [ ] Research finds modern parallel
- [ ] Final transcript uses research findings
- [ ] Quality comparable to manual description input

---

## Phase 2: Iterative Refinement with --refine Flag

### Goal
Allow AI to self-critique and improve transcripts through multiple iterations.

### Architecture

```
Initial Generation
    ↓
    ↓───────────────────┐
    ↓                   ↓
Iteration 1         Self-Critique:
Generate        →   - Does it have cheat sheet?
Transcript          - Does it have big questions?
                    - Does it have personality?
                    - Does it have drama?
                    - Does it have modern analogies?
                    - Score: 7/10
    ↓                   ↓
    ↓←──────────────────┘
    ↓
Iteration 2 (with critique feedback)
Improve based on critique
    ↓
Iteration 3 (final polish)
    ↓
Best Version Selected
```

### Implementation Details

#### 1. Add --refine Flag

**File**: `src/cli.py`

```python
@cli.command()
@click.option('--refine', is_flag=True, default=False,
              help='Enable iterative refinement (2-3 iterations for better quality)')
def generate(..., refine):
    if refine:
        console.print("[yellow]Refinement mode enabled - will iterate 2-3 times[/yellow]")
```

#### 2. Create Self-Critique Prompt

**File**: `src/content_generator.py`

**New Method**: `_critique_transcript(transcript)`

```python
CRITIQUE_PROMPT = """
You are a quality reviewer for tour guide scripts.

Evaluate this transcript against our gold standard:

TRANSCRIPT TO REVIEW:
{transcript}

CHECKLIST - Rate each (Yes/No/Partial):
1. Opens with "cheat sheet" (2-3 learning objectives)
2. Frames with 1-2 big questions
3. Historical figure has personality/nickname
4. Contains specific dramatic detail (exact numbers/actions)
5. Includes 2+ modern analogies
6. Has clear sections (Part 1, Part 2, etc.)
7. Uses direct engagement ("Imagine...", "Close your eyes...")
8. Has emotional arc (setup → conflict → resolution)
9. Includes twist/ironic ending
10. Returns to opening questions (callbacks)
11. Zero empty adjectives ("magnificent", "impressive")
12. Conversational tone (not academic)

SCORE: X/12

SPECIFIC IMPROVEMENTS NEEDED:
- [List specific things to fix]

WHAT WORKS WELL:
- [List what should be kept]
"""
```

#### 3. Implement Refinement Loop

**File**: `src/content_generator.py`

**New Method**: `generate_with_refinement()`

```python
def generate_with_refinement(self, poi_name, max_iterations=3, ...):
    """Generate transcript with iterative refinement"""

    # Initial generation
    print(f"  [ITERATION 1/{max_iterations}] Initial generation...")
    transcript = self.generate(poi_name, ...)
    transcripts = [transcript]
    scores = []

    # Refinement iterations
    for i in range(1, max_iterations):
        print(f"  [ITERATION {i+1}/{max_iterations}] Critiquing and refining...")

        # Critique current version
        critique = self._critique_transcript(transcript)
        score = self._extract_score(critique)
        scores.append(score)

        print(f"    Score: {score}/12")

        # If score is perfect or good enough, stop
        if score >= 11:
            print(f"    ✓ Quality threshold reached!")
            break

        # Generate improved version
        improvement_prompt = f"""
        Previous attempt:
        {transcript}

        Critique:
        {critique}

        Create an improved version addressing the critique.
        Keep what works well, fix what doesn't.
        """

        transcript = self._call_ai(improvement_prompt)
        transcripts.append(transcript)

    # Return best version
    best_idx = scores.index(max(scores)) if scores else 0
    return transcripts[best_idx], scores
```

#### 4. Progress Display

**File**: `src/cli.py`

```python
if refine:
    with console.status("[bold green]Refining transcript...") as status:
        transcript, scores = generator.generate_with_refinement(...)

    # Show refinement results
    console.print("\n[cyan]Refinement Progress:[/cyan]")
    for i, score in enumerate(scores, 1):
        bar = "█" * score + "░" * (12 - score)
        console.print(f"  Iteration {i}: {bar} {score}/12")
```

#### 5. Configuration

**File**: `config.yaml`

```yaml
content_generation:
  # Refinement settings
  refinement:
    enabled_by_default: false
    max_iterations: 3
    quality_threshold: 11  # Stop if score >= 11/12
    save_all_iterations: false  # Save intermediate versions?
```

### Testing Plan

**Test Cases**:
1. Generate with `--refine` flag, verify 2-3 iterations run
2. Verify each iteration improves score
3. Verify it stops early if threshold reached
4. Compare final quality: with vs without refinement
5. Test with low-quality initial generation

**Success Metrics**:
- [ ] Refinement runs 2-3 iterations
- [ ] Score improves each iteration
- [ ] Final score >= 10/12
- [ ] Quality noticeably better than single-pass
- [ ] Takes acceptable time (< 2 minutes total)

---

## Implementation Order

### Week 1: Research Phase
- [ ] Day 1-2: Implement research prompt and method
- [ ] Day 3: Integrate into generate() flow
- [ ] Day 4-5: Test and refine research quality

### Week 2: Refinement Feature
- [ ] Day 1-2: Implement critique prompt and scoring
- [ ] Day 3: Implement refinement loop
- [ ] Day 4: Add CLI flag and progress display
- [ ] Day 5: Test and refine

### Week 3: Polish & Documentation
- [ ] Day 1-2: Compare quality across all features
- [ ] Day 3: Update documentation
- [ ] Day 4-5: Create examples and tutorials

---

## Risk Mitigation

### Risks:
1. **API costs**: Two-step + refinement = 3-5x API calls
   - Mitigation: Make refinement opt-in, cache research results

2. **Time**: Multiple iterations take longer
   - Mitigation: Show progress, allow early stopping

3. **Quality regression**: Refinement might make it worse
   - Mitigation: Always keep original, return best scored version

4. **Token limits**: Research + storytelling might exceed limits
   - Mitigation: Allocate tokens carefully, summarize research

---

## Success Criteria

### Phase 1 Success:
- ✅ Can generate quality transcript with ONLY POI name
- ✅ Research finds dramatic elements automatically
- ✅ 80%+ quality compared to manual description

### Phase 2 Success:
- ✅ --refine flag improves transcript score
- ✅ Final quality matches manual refinement
- ✅ Completes in < 2 minutes

### Overall Success:
- ✅ User can generate great transcripts with zero manual input
- ✅ Quality comparable to manual Gemini GUI refinement
- ✅ Reproducible and automated process

---

## Future Enhancements

1. **RAG Integration**: Use vector DB for historical research
2. **Template Library**: Pre-researched dramatic elements by location
3. **A/B Testing**: Generate multiple versions, let user choose
4. **Quality Prediction**: Predict final quality before generation
5. **Cost Optimization**: Cache research results, reuse across POIs

---

## Rollout Plan

### Phase 1: Internal Testing (Week 1-2)
- Implement and test with 5-10 POIs
- Compare quality metrics
- Gather feedback

### Phase 2: Beta Release (Week 3)
- Add `--experimental-research` flag
- Document in ADVANCED.md
- Collect user feedback

### Phase 3: General Availability (Week 4)
- Make research default behavior
- Update QUICKSTART.md
- Create video tutorial

---

**Document Version**: 1.0
**Last Updated**: 2025-11-20
**Status**: Planning Phase
**Next Action**: Begin Phase 1 Implementation
