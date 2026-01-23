"""
Insertion Agent - Generates and splices missing feature text into transcripts.

This agent takes verification results and creates targeted insertions to fill gaps
in feature coverage. Uses AI to generate contextually appropriate paragraphs.
"""

import re
import time
from typing import List, Dict, Tuple
import anthropic
import openai
from google import generativeai as genai


class InsertionAgent:
    """
    Agent responsible for generating and inserting missing features into transcripts.
    """

    def __init__(self, config: Dict, provider: str = 'anthropic'):
        """
        Initialize insertion agent.

        Args:
            config: Full application config dictionary
            provider: AI provider to use ('anthropic', 'openai', 'google')
        """
        self.config = config
        self.provider = provider
        self.ai_config = config.get('ai_providers', {})

    def plan_insertions(self, transcript: str, missing_features: List[str]) -> List[Dict]:
        """
        Analyze transcript structure and plan where to insert each missing feature.

        Args:
            transcript: The original transcript text
            missing_features: List of feature strings that are missing

        Returns:
            List of insertion plans with context for each feature:
            [
                {
                    'feature': 'Limestone plateau rises 150 meters...',
                    'insert_location': 'after_line',
                    'line_number': 5,
                    'context_before': '...Close your eyes and imagine...',
                    'context_after': 'Then one day, this guy Pericles...',
                    'section': 'Part 1: The Heist',
                    'suggested_tone': 'dramatic scene-setting'
                },
                ...
            ]
        """
        lines = transcript.split('\n')

        # Identify transcript structure (Parts, sections)
        structure = self._analyze_structure(lines)

        insertion_plans = []

        for feature in missing_features:
            # Determine best insertion point based on feature content
            plan = self._find_best_insertion_point(feature, lines, structure)
            insertion_plans.append(plan)

        return insertion_plans

    def _analyze_structure(self, lines: List[str]) -> Dict:
        """
        Analyze transcript structure to identify parts, sections, themes.

        Returns:
            {
                'parts': [
                    {'title': 'Part 1: The Heist', 'start_line': 5, 'end_line': 15},
                    ...
                ],
                'intro_end': 4,
                'conclusion_start': 29
            }
        """
        structure = {
            'parts': [],
            'intro_end': 0,
            'conclusion_start': len(lines)
        }

        # Find Part markers
        for i, line in enumerate(lines):
            if re.match(r'\*\*Part \d+:', line):
                # Find end of this part (next Part or end of transcript)
                end_line = len(lines)
                for j in range(i + 1, len(lines)):
                    if re.match(r'\*\*Part \d+:', lines[j]):
                        end_line = j
                        break

                structure['parts'].append({
                    'title': line.strip(),
                    'start_line': i,
                    'end_line': end_line
                })

        # Find intro end (usually first Part or question mark)
        for i, line in enumerate(lines):
            if '**Part ' in line or 'Here\'s our big question:' in line:
                structure['intro_end'] = i
                break

        # Find conclusion (usually mentioned "Remember our opening question" or final twist)
        for i in range(len(lines) - 1, -1, -1):
            if 'Remember our' in lines[i] or 'back to our question' in lines[i] or '**Part 3' in lines[i]:
                structure['conclusion_start'] = i
                break

        return structure

    def _find_best_insertion_point(self, feature: str, lines: List[str], structure: Dict) -> Dict:
        """
        Determine best place to insert a feature based on its content and narrative flow.

        Strategy:
        - Plateau/location features → intro or Part 1 (scene-setting)
        - Architecture details → Part 1 or 2 (description)
        - People/statues → Part 2 (human stories)
        - War damage/history → Part 3 (irony/conclusion)
        """
        feature_lower = feature.lower()

        # Default insertion point (after intro, before Part 1)
        default_insert = structure.get('intro_end', 5)

        # Categorize feature
        if any(term in feature_lower for term in ['plateau', 'meters above', 'accessible', 'rises', 'flat top']):
            # Location/geography → intro or early Part 1
            suggested_tone = 'dramatic scene-setting, help visitor visualize the location'
            insert_line = default_insert
            section = 'Introduction'

        elif any(term in feature_lower for term in ['columns', 'marble', 'diameter', 'tall', 'clamps', 'mortar']):
            # Architecture details → Part 1 or early Part 2
            if structure['parts']:
                part1 = structure['parts'][0] if len(structure['parts']) > 0 else {'start_line': default_insert}
                insert_line = part1['start_line'] + 3  # A few lines into Part 1
            else:
                insert_line = default_insert + 5
            suggested_tone = 'technical appreciation mixed with awe, explain why it\'s impressive'
            section = 'Part 1 (Architecture)'

        elif any(term in feature_lower for term in ['caryatids', 'statues', 'erechtheion', 'temple', 'female', 'stolen']):
            # Sculptures/art → Part 2 (human drama)
            if len(structure['parts']) > 1:
                part2 = structure['parts'][1]
                insert_line = part2['end_line'] - 2  # Near end of Part 2
            else:
                insert_line = (default_insert + structure['conclusion_start']) // 2
            suggested_tone = 'tragic loss, cultural theft, connect to human stories'
            section = 'Part 2 (Art & Tragedy)'

        elif any(term in feature_lower for term in ['propylaea', 'gateway', 'bullet', 'war', 'damage', 'explosion']):
            # War/damage → Part 3 (irony/survival)
            insert_line = structure['conclusion_start'] + 2
            suggested_tone = 'ironic survival, layers of history, visible scars'
            section = 'Part 3 (Conclusion)'

        else:
            # Unknown feature type → safe default
            insert_line = default_insert
            suggested_tone = 'match the conversational storytelling tone'
            section = 'General'

        # Get EXPANDED context around insertion point (Option D improvement)
        # Give AI 10 lines before/after instead of 2 for better integration
        context_before = ""
        context_after = ""
        surrounding_context = ""

        if insert_line > 0:
            # Get 10 lines before for context
            start = max(0, insert_line - 10)
            context_before = "\n".join(lines[start:insert_line]).strip()

        if insert_line < len(lines):
            # Get 10 lines after for context
            end = min(len(lines), insert_line + 10)
            context_after = "\n".join(lines[insert_line:end]).strip()

        # Also get surrounding 20-line window for rewriting
        surround_start = max(0, insert_line - 10)
        surround_end = min(len(lines), insert_line + 10)
        surrounding_context = "\n".join(lines[surround_start:surround_end]).strip()

        return {
            'feature': feature,
            'insert_location': 'after_line',
            'line_number': insert_line,
            'context_before': context_before,
            'context_after': context_after,
            'surrounding_context': surrounding_context,  # Full 20-line window
            'section': section,
            'suggested_tone': suggested_tone
        }

    def generate_insertion(self, plan: Dict, poi_name: str = "", city: str = "") -> str:
        """
        Generate insertion text for a missing feature using AI.

        Option D Enhancement: Uses full context and asks AI to rewrite
        surrounding text for seamless integration.

        Args:
            plan: Insertion plan from plan_insertions()
            poi_name: Name of POI for context
            city: City name for context

        Returns:
            Generated insertion text that rewrites/enhances surrounding content
        """
        feature = plan['feature']
        surrounding_context = plan.get('surrounding_context', plan['context_before'])
        section = plan['section']
        suggested_tone = plan['suggested_tone']

        prompt = f"""You are refining a tour guide transcript for {poi_name} in {city}.

A core feature is missing from {section} and needs to be woven in naturally.

MISSING FEATURE (must include ALL these details exactly):
\"\"\"{feature}\"\"\"

SURROUNDING TEXT (20-line context window):
\"\"\"
{surrounding_context}
\"\"\"

TASK: Generate a 100-150 word paragraph that:
1. Naturally integrates the missing feature into this section
2. Uses EXACT measurements and details (do NOT approximate or change numbers)
3. Connects to the surrounding narrative - reference what comes before/after
4. Matches the dramatic storytelling tone ({suggested_tone})
5. Makes the feature feel like it was always part of the story

INTEGRATION STRATEGIES:
- If surrounding text mentions a person, connect the feature to their story
- If surrounding text builds tension, use the feature to heighten it
- If surrounding text reveals irony, show how the feature adds to that irony
- Use transitions like "But here's the thing...", "Now look closer...", "Here's what they don't tell you..."

CRITICAL REQUIREMENTS:
- Use EXACT measurements from feature (e.g., "10.4 meters" not "about 10 meters")
- Match conversational tone with modern analogies
- 100-150 words (one substantial paragraph)
- NO stage directions, NO meta-commentary
- Make it sound like the original narrator wrote it

Generate the paragraph:"""

        # Call AI based on provider
        if self.provider == 'anthropic':
            insertion_text = self._generate_anthropic(prompt)
        elif self.provider == 'openai':
            insertion_text = self._generate_openai(prompt)
        elif self.provider == 'google':
            insertion_text = self._generate_google(prompt)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        return insertion_text.strip()

    def splice_transcript(self, original: str, insertions: List[Dict]) -> str:
        """
        Splice generated insertions into original transcript.

        Args:
            original: Original transcript text
            insertions: List of insertion dicts with 'line_number' and 'text' keys

        Returns:
            Modified transcript with insertions
        """
        lines = original.split('\n')

        # Sort insertions by line number (descending) to avoid index shifting
        sorted_insertions = sorted(insertions, key=lambda x: x['line_number'], reverse=True)

        for insertion in sorted_insertions:
            line_num = insertion['line_number']
            text = insertion['text']

            # Insert after specified line
            if 0 <= line_num <= len(lines):
                # Add blank line, insertion, blank line for spacing
                lines.insert(line_num, "")
                lines.insert(line_num + 1, text)
                lines.insert(line_num + 2, "")

        return '\n'.join(lines)

    # AI Provider Methods

    def _generate_anthropic(self, prompt: str) -> str:
        """Generate insertion using Anthropic Claude with retry logic"""
        config = self.ai_config.get('anthropic', {})
        api_key = config.get('api_key')
        model = config.get('model', 'claude-3-5-sonnet-20241022')

        if not api_key:
            raise ValueError("Anthropic API key not configured")

        client = anthropic.Anthropic(api_key=api_key, timeout=60.0)

        system_prompt = "You are a master storyteller helping refine a tour guide transcript. Your insertions should blend seamlessly with the existing narrative, matching the dramatic storytelling tone perfectly while including all required factual details."

        # Retry logic with exponential backoff
        max_retries = 5
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = base_delay * (2 ** (attempt - 1))
                    print(f"  [DEBUG] Retry {attempt}/{max_retries} - waiting {wait_time}s...")
                    time.sleep(wait_time)

                # Small delay between API calls to prevent rate limiting
                if attempt == 0:
                    time.sleep(0.5)

                response = client.messages.create(
                    model=model,
                    max_tokens=800,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                )

                return response.content[0].text

            except anthropic.APIStatusError as e:
                if e.status_code in [429, 529]:
                    if attempt < max_retries - 1:
                        error_type = "rate limit" if e.status_code == 429 else "overloaded"
                        print(f"  [WARNING] Anthropic API {error_type}, retrying...")
                        continue
                    else:
                        print(f"  [ERROR] Anthropic API error after {max_retries} attempts")
                        raise Exception(f"Anthropic API error (status {e.status_code})") from e
                else:
                    raise

            except (anthropic.APIConnectionError, anthropic.APITimeoutError,
                    ConnectionError, TimeoutError) as e:
                if attempt < max_retries - 1:
                    print(f"  [WARNING] Connection error, retrying...")
                    continue
                else:
                    print(f"  [ERROR] Connection failed after {max_retries} attempts")
                    raise Exception(f"Connection error after {max_retries} attempts") from e

            except Exception as e:
                raise

    def _generate_openai(self, prompt: str) -> str:
        """Generate insertion using OpenAI"""
        config = self.ai_config.get('openai', {})
        api_key = config.get('api_key')
        model = config.get('model', 'gpt-4-turbo-preview')

        if not api_key:
            raise ValueError("OpenAI API key not configured")

        client = openai.OpenAI(api_key=api_key)

        system_prompt = "You are a master storyteller helping refine a tour guide transcript. Your insertions should blend seamlessly with the existing narrative, matching the dramatic storytelling tone perfectly while including all required factual details."

        response = client.chat.completions.create(
            model=model,
            max_tokens=800,  # Longer for Option D
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content

    def _generate_google(self, prompt: str) -> str:
        """Generate insertion using Google Gemini"""
        config = self.ai_config.get('google', {})
        api_key = config.get('api_key')
        model_name = config.get('model', 'gemini-pro')

        if not api_key:
            raise ValueError("Google API key not configured")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        full_prompt = f"""You are a master storyteller helping refine a tour guide transcript. Your insertions should blend seamlessly with the existing narrative, matching the dramatic storytelling tone perfectly while including all required factual details.

{prompt}"""

        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=800,  # Longer for Option D
                temperature=0.7
            )
        )

        return response.text

    # ===== Natural Integration Methods (Smart Verification Loop) =====

    def integrate_feature_with_facts(
        self,
        feature: str,
        relevant_facts: List[str],
        full_transcript: str,
        poi_name: str,
        city: str,
        provider: str
    ) -> str:
        """
        Integrate missing feature naturally into full transcript using explicit facts

        This is the NEW approach for smart verification:
        - Takes FULL transcript (not just surrounding context)
        - AI decides where and how to integrate (sentence, expand paragraph, or new paragraph)
        - Requires using specific facts from research
        - No forced paragraph length - natural integration

        Args:
            feature: Missing feature description
            relevant_facts: List of relevant facts extracted from research
            full_transcript: Complete current transcript
            poi_name: POI name
            city: City name
            provider: AI provider to use

        Returns:
            Complete updated transcript with feature integrated
        """
        print(f"  [INTEGRATE] Integrating feature with {len(relevant_facts)} facts...")

        # Build prompt for natural integration
        facts_formatted = '\n'.join([f"  - {fact}" for fact in relevant_facts])

        prompt = f"""
POI: {poi_name}, {city}

TASK: Integrate the following missing feature into the transcript naturally.

MISSING FEATURE:
{feature}

RESEARCH FACTS YOU MUST USE (use at least 2):
{facts_formatted}

CURRENT TRANSCRIPT:
{full_transcript}

INSTRUCTIONS:
1. Read the full transcript to understand the narrative flow and tone
2. Find the BEST place(s) to integrate this missing feature
3. You can choose to:
   - Add a sentence to an existing paragraph
   - Expand an existing paragraph with 2-3 sentences
   - Insert a new paragraph if truly needed (but avoid if possible)
4. MUST use at least 2 specific facts from the research facts list above
5. Match the existing tone and style
6. Use exact measurements and details (no approximations)
7. Ensure smooth narrative flow

OUTPUT: Return the COMPLETE updated transcript with the feature integrated.
Do NOT explain your changes or add comments. Just return the full updated transcript.
"""

        # Call AI provider
        updated_transcript = self._call_provider(prompt, provider)

        return updated_transcript.strip()

    def integrate_feature_with_expansion(
        self,
        feature: str,
        new_research: Dict,
        full_transcript: str,
        poi_name: str,
        city: str,
        provider: str
    ) -> str:
        """
        Integrate missing feature using newly expanded research

        Used when research was expanded to cover a gap.
        Gives AI full transcript to integrate new information naturally.

        Args:
            feature: Missing feature description
            new_research: Newly discovered research data
            full_transcript: Complete current transcript
            poi_name: POI name
            city: City name
            provider: AI provider to use

        Returns:
            Complete updated transcript with new information integrated
        """
        print(f"  [INTEGRATE] Integrating feature with expanded research...")

        # Format new research for prompt
        research_formatted = self._format_research_data(new_research)

        prompt = f"""
POI: {poi_name}, {city}

TASK: Integrate newly discovered information into the transcript.

MISSING FEATURE:
{feature}

NEW RESEARCH DISCOVERED:
{research_formatted}

CURRENT TRANSCRIPT:
{full_transcript}

INSTRUCTIONS:
1. This research was just discovered to fill a knowledge gap
2. Find the BEST place(s) in the transcript to integrate this information
3. You can choose to:
   - Add a sentence to an existing paragraph
   - Expand an existing paragraph with 2-3 sentences
   - Insert a new paragraph if the information is substantial
4. Highlight the new details naturally
5. Match the existing tone and style
6. Ensure smooth narrative flow

OUTPUT: Return the COMPLETE updated transcript with the new information integrated.
Do NOT explain your changes or add comments. Just return the full updated transcript.
"""

        # Call AI provider
        updated_transcript = self._call_provider(prompt, provider)

        return updated_transcript.strip()

    def _format_research_data(self, research_data: Dict) -> str:
        """Format research data for prompt"""
        lines = []

        # Core features
        if 'core_features' in research_data:
            lines.append("Core Features:")
            for feature in research_data['core_features']:
                lines.append(f"  - {feature}")

        # People
        if 'people' in research_data:
            lines.append("\nPeople:")
            for person in research_data['people']:
                name = person.get('name', 'Unknown')
                role = person.get('role', '')
                info = f"  - {name}"
                if role:
                    info += f" ({role})"
                if person.get('personality'):
                    info += f": {person['personality']}"
                lines.append(info)

        # Events
        if 'events' in research_data:
            lines.append("\nEvents:")
            for event in research_data['events']:
                name = event.get('name', 'Unknown')
                date = event.get('date', '')
                info = f"  - {name}"
                if date:
                    info += f" ({date})"
                if event.get('significance'):
                    info += f": {event['significance']}"
                lines.append(info)

        # Locations
        if 'locations' in research_data:
            lines.append("\nLocations:")
            for location in research_data['locations']:
                name = location.get('name', 'Unknown')
                desc = location.get('description', '')
                info = f"  - {name}"
                if desc:
                    info += f": {desc}"
                lines.append(info)

        # Concepts
        if 'concepts' in research_data:
            lines.append("\nConcepts:")
            for concept in research_data['concepts']:
                name = concept.get('name', 'Unknown')
                explanation = concept.get('explanation', '')
                info = f"  - {name}"
                if explanation:
                    info += f": {explanation}"
                lines.append(info)

        return '\n'.join(lines)

    def _call_provider(self, prompt: str, provider: str, max_tokens: int = 4000) -> str:
        """
        Call appropriate AI provider with custom max_tokens

        Args:
            prompt: Prompt string
            provider: AI provider name
            max_tokens: Maximum tokens for response (default 4000 for full transcripts)

        Returns:
            AI response text
        """
        if provider == 'anthropic':
            return self._generate_anthropic_custom(prompt, max_tokens)
        elif provider == 'openai':
            return self._generate_openai_custom(prompt, max_tokens)
        elif provider == 'google':
            return self._generate_google_custom(prompt, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _generate_anthropic_custom(self, prompt: str, max_tokens: int = 4000) -> str:
        """Generate using Anthropic with custom max_tokens and retry logic"""
        config = self.ai_config.get('anthropic', {})
        api_key = config.get('api_key')
        model = config.get('model', 'claude-sonnet-4-5-20250929')

        if not api_key:
            raise ValueError("Anthropic API key not configured")

        client = anthropic.Anthropic(api_key=api_key, timeout=60.0)

        # Retry logic with exponential backoff
        max_retries = 5
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = base_delay * (2 ** (attempt - 1))
                    print(f"  [DEBUG] Retry {attempt}/{max_retries} - waiting {wait_time}s...")
                    time.sleep(wait_time)

                # Small delay between API calls to prevent rate limiting
                if attempt == 0:
                    time.sleep(0.5)

                message = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system="You are a master storyteller helping refine a tour guide transcript. Your insertions should blend seamlessly with the existing narrative, matching the dramatic storytelling tone perfectly while including all required factual details.",
                    messages=[{"role": "user", "content": prompt}]
                )

                return message.content[0].text

            except anthropic.APIStatusError as e:
                if e.status_code in [429, 529]:
                    if attempt < max_retries - 1:
                        error_type = "rate limit" if e.status_code == 429 else "overloaded"
                        print(f"  [WARNING] Anthropic API {error_type}, retrying...")
                        continue
                    else:
                        print(f"  [ERROR] Anthropic API error after {max_retries} attempts")
                        raise Exception(f"Anthropic API error (status {e.status_code})") from e
                else:
                    raise

            except (anthropic.APIConnectionError, anthropic.APITimeoutError,
                    ConnectionError, TimeoutError) as e:
                if attempt < max_retries - 1:
                    print(f"  [WARNING] Connection error, retrying...")
                    continue
                else:
                    print(f"  [ERROR] Connection failed after {max_retries} attempts")
                    raise Exception(f"Connection error after {max_retries} attempts") from e

            except Exception as e:
                raise

    def _generate_openai_custom(self, prompt: str, max_tokens: int = 4000) -> str:
        """Generate using OpenAI with custom max_tokens"""
        config = self.ai_config.get('openai', {})
        api_key = config.get('api_key')
        model = config.get('model', 'gpt-4')

        if not api_key:
            raise ValueError("OpenAI API key not configured")

        client = openai.OpenAI(api_key=api_key)

        system_prompt = "You are a master storyteller helping refine a tour guide transcript. Your insertions should blend seamlessly with the existing narrative, matching the dramatic storytelling tone perfectly while including all required factual details."

        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content

    def _generate_google_custom(self, prompt: str, max_tokens: int = 4000) -> str:
        """Generate using Google Gemini with custom max_tokens"""
        config = self.ai_config.get('google', {})
        api_key = config.get('api_key')
        model_name = config.get('model', 'gemini-pro')

        if not api_key:
            raise ValueError("Google API key not configured")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        full_prompt = f"""You are a master storyteller helping refine a tour guide transcript. Your insertions should blend seamlessly with the existing narrative, matching the dramatic storytelling tone perfectly while including all required factual details.

{prompt}"""

        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.7
            )
        )

        return response.text
