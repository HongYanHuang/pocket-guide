"""
AI Content Generation for tour guide transcripts
Supports: OpenAI, Anthropic (Claude), Google (Gemini)
"""
from typing import Dict, Any, Optional, Tuple, List
import openai
import anthropic
import google.generativeai as genai
import re
import time
import os
import yaml
from pathlib import Path

# Import research agent
try:
    from .research_agent import ResearchAgent
except ImportError:
    from research_agent import ResearchAgent


class ContentGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ai_config = config.get('ai_providers', {})

        # Initialize research agent if research is enabled
        self.research_enabled = config.get('research', {}).get('enabled', True)
        if self.research_enabled:
            self.research_agent = ResearchAgent(config)
        else:
            self.research_agent = None

    def generate(
        self,
        poi_name: str,
        provider: str = None,
        city: str = None,
        description: str = None,
        interests: list = None,
        custom_prompt: str = None,
        language: str = "English",
        skip_research: bool = False,
        force_research: bool = False
    ) -> Tuple[str, List[str]]:
        """
        Generate tour guide content for a POI

        Args:
            poi_name: Name of the point of interest
            provider: AI provider to use (openai, anthropic, google)
            city: City name
            description: Basic description of the POI
            interests: List of interests/aspects to focus on
            custom_prompt: Custom prompt to use instead of default
            language: Target language for content
            skip_research: Skip research phase even if enabled in config
            force_research: Force research even if cached data exists

        Returns:
            Tuple of (transcript, summary_points)
            - transcript: The narration text
            - summary_points: List of key learning points
        """
        if provider is None:
            provider = self.config.get('defaults', {}).get('ai_provider', 'openai')

        print(f"  [DEBUG] Using provider: {provider}")

        # Research Phase (if enabled and not skipped)
        research_data = None
        use_research = self.research_enabled and not skip_research and self.research_agent

        if use_research:
            print(f"  [STEP 1/2] Research Phase")
            research_path = self._get_research_path(city, poi_name)

            # Check if research already exists
            if research_path.exists() and not force_research:
                print(f"  [DEBUG] Loading existing research from {research_path}")
                research_data = self._load_research(research_path)
            else:
                if force_research:
                    print(f"  [DEBUG] Force research enabled, researching...")
                else:
                    print(f"  [DEBUG] No existing research found, researching...")

                # Perform recursive research
                research_data = self.research_agent.research_poi_recursive(
                    poi_name=poi_name,
                    city=city or "Unknown",
                    user_description=description or "",
                    provider=provider
                )

                # Save research for future use
                self._save_research(research_path, research_data)
                print(f"  [DEBUG] Research saved to {research_path}")

        # Build the prompt
        if custom_prompt:
            prompt = custom_prompt
            print(f"  [DEBUG] Using custom prompt ({len(prompt)} chars)")
        else:
            if use_research:
                print(f"  [STEP 2/2] Storytelling Phase")
                print(f"  [DEBUG] Building prompt with research data...")
                prompt = self._build_prompt_with_research(
                    poi_name, city, research_data, interests, language
                )
            else:
                print(f"  [DEBUG] Building prompt for {poi_name}...")
                prompt = self._build_prompt(poi_name, city, description, interests, language)
            print(f"  [DEBUG] Prompt built ({len(prompt)} chars)")

        # Generate content based on provider
        print(f"  [DEBUG] Calling {provider} API...")
        if provider == 'openai':
            raw_content = self._generate_openai(prompt)
        elif provider == 'anthropic':
            raw_content = self._generate_anthropic(prompt)
        elif provider == 'google':
            raw_content = self._generate_google(prompt)
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")

        print(f"  [DEBUG] Parsing response...")
        # Parse the response to extract transcript and summary points
        result = self._parse_response(raw_content)
        print(f"  [DEBUG] Parsing complete")
        return result

    def _build_prompt(
        self,
        poi_name: str,
        city: str = None,
        description: str = None,
        interests: list = None,
        language: str = "English"
    ) -> str:
        """Build a prompt for content generation"""
        # Get style guidelines from config
        content_config = self.config.get('content_generation', {})
        style_guidelines = content_config.get('style_guidelines', [
            "Write in a conversational, engaging tone suitable for audio",
            "Length: 300-750 words (about 2-5 minutes when spoken)",
            "Include interesting facts, historical context, and practical tips",
            "Use natural speech patterns with appropriate pauses",
            "Avoid overly formal or academic language",
            "Make dates and numbers relatable - say '1700 years ago' instead of '300 AD'",
            "Use relative timeframes that connect to the listener's experience",
            "DO NOT include any stage directions, sound effects, or meta-commentary",
            "Write ONLY the spoken narration"
        ])

        prompt_parts = [
            f"Create a {language} tour guide script for: {poi_name}"
        ]

        if city:
            prompt_parts.append(f"Located in: {city}")

        if description:
            prompt_parts.append(f"\nBackground information: {description}")

        if interests:
            interests_str = ", ".join(interests)
            prompt_parts.append(f"\nFocus on these aspects: {interests_str}")

        # Add style guidelines
        prompt_parts.append(f"\nRequirements:")
        for guideline in style_guidelines:
            prompt_parts.append(f"- {guideline}")

        # Request both transcript and summary points
        prompt_parts.extend([
            f"\nYour response should include TWO sections:",
            f"1. TRANSCRIPT: The spoken tour guide narration",
            f"2. SUMMARY POINTS: 3-5 bullet points of key things the audience will learn",
            f"\nFormat your response EXACTLY like this:",
            f"TRANSCRIPT:",
            f"[Your narration here]",
            f"\nSUMMARY POINTS:",
            f"- Point 1",
            f"- Point 2",
            f"- Point 3"
        ])

        return "\n".join(prompt_parts)

    def _get_research_path(self, city: str, poi_name: str) -> Path:
        """Get path to research YAML file"""
        # Create poi_research directory if it doesn't exist
        research_dir = Path("poi_research")
        if city:
            research_dir = research_dir / city
        research_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize POI name for filename
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in poi_name)
        safe_name = safe_name.replace(' ', '_').lower()

        return research_dir / f"{safe_name}.yaml"

    def _load_research(self, research_path: Path) -> Dict:
        """Load research from YAML file"""
        with open(research_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _save_research(self, research_path: Path, research_data: Dict):
        """Save research to YAML file"""
        research_path.parent.mkdir(parents=True, exist_ok=True)
        with open(research_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(research_data, f, allow_unicode=True, sort_keys=False)

    def _filter_research(self, research_data: Dict, interests: List[str] = None) -> Dict:
        """
        Filter research data by user interests

        Args:
            research_data: Full research data from research agent
            interests: List of interest labels (e.g., ['drama', 'history'])

        Returns:
            Filtered research data containing only relevant nodes
        """
        if not interests:
            return research_data

        # Convert interests to lowercase for comparison
        interests_set = set(i.lower() for i in interests)

        # Always include nodes with 'native' label
        interests_set.add('native')

        filtered = {
            'poi': research_data.get('poi', {}),
            'core_features': research_data.get('core_features', []),  # Always included, never filtered
            'entities': {}
        }

        # Filter entities by label
        # entities is a dict with keys like "Person:Name" and values as entity data
        for entity_id, entity_data in research_data.get('entities', {}).items():
            # Get labels from entity data (may be nested in different structures)
            entity_labels = set()

            # Try to find labels in the entity data
            if isinstance(entity_data, dict):
                # Check top-level labels
                if 'labels' in entity_data:
                    entity_labels.update(l.lower() for l in entity_data.get('labels', []))

                # Check nested structures (biography, events, etc.)
                for key, value in entity_data.items():
                    if isinstance(value, dict) and 'labels' in value:
                        entity_labels.update(l.lower() for l in value.get('labels', []))

            # Include if any label matches user interests or has 'native'
            if entity_labels & interests_set:
                filtered['entities'][entity_id] = entity_data

        return filtered

    def _serialize_research(self, research_data: Dict) -> str:
        """
        Convert research data to readable text for AI prompt

        Args:
            research_data: Research data dictionary

        Returns:
            Human-readable text summary of research
        """
        lines = []

        # POI section
        poi = research_data.get('poi', {})
        if poi:
            lines.append("=== POI INFORMATION ===")
            lines.append(f"Name: {poi.get('name', 'Unknown')}")
            if poi.get('basic_info'):
                basic_info = poi['basic_info']
                if basic_info.get('period'):
                    lines.append(f"Period: {basic_info['period']}")
                if basic_info.get('date_built'):
                    lines.append(f"Built: {basic_info['date_built']}")
            lines.append("")

        # Core Features section (ALWAYS included - grounds visitor in physical reality)
        core_features = research_data.get('core_features', [])
        if core_features:
            lines.append("=== CORE FEATURES (What visitor experiences) ===")
            lines.append("These are essential physical facts that ground your story in reality.")
            lines.append("Weave them naturally into your narrative:\n")
            for i, feature in enumerate(core_features, 1):
                lines.append(f"{i}. {feature}")
            lines.append("")

        # Entities section
        entities = research_data.get('entities', {})
        if entities:
            lines.append("=== KNOWLEDGE NODES ===")
            lines.append("(Use these facts to craft your narrative)\n")

            # Group entities by type
            by_type = {}
            for entity_id, entity_data in entities.items():
                # Extract type from entity_id (format: "Type:Name")
                if ':' in entity_id:
                    entity_type = entity_id.split(':', 1)[0]
                else:
                    entity_type = entity_data.get('type', 'Other')

                if entity_type not in by_type:
                    by_type[entity_type] = []
                by_type[entity_type].append((entity_id, entity_data))

            # Output each type group
            for entity_type, entity_list in by_type.items():
                lines.append(f"--- {entity_type.upper()}S ---")

                for entity_id, entity_data in entity_list:
                    name = entity_data.get('name', entity_id)

                    # Serialize the full entity data as YAML for the AI
                    import yaml
                    entity_yaml = yaml.safe_dump(entity_data, default_flow_style=False, allow_unicode=True)
                    lines.append(f"\n{name}:")
                    lines.append(entity_yaml)

                lines.append("")

        return "\n".join(lines)

    def _build_prompt_with_research(
        self,
        poi_name: str,
        city: str = None,
        research_data: Dict = None,
        interests: list = None,
        language: str = "English"
    ) -> str:
        """
        Build storytelling prompt using research data

        Args:
            poi_name: Name of POI
            city: City name
            research_data: Research data from research agent
            interests: User interests for filtering
            language: Target language

        Returns:
            Complete prompt for storytelling phase
        """
        # Get style guidelines and system prompt from config
        content_config = self.config.get('content_generation', {})
        system_prompt = content_config.get('system_prompt',
            "You are a master storyteller tour guide who makes history come alive.")
        style_guidelines = content_config.get('style_guidelines', [])

        # Filter research by interests
        filtered_research = self._filter_research(research_data, interests)

        # Serialize research into readable text
        research_context = self._serialize_research(filtered_research)

        # Build prompt
        prompt_parts = [
            system_prompt.strip(),
            "",
            "NOTE: You will receive CORE FEATURES - essential physical facts about what visitors",
            "can experience at this POI right now. Weave these naturally into your narrative to",
            "keep listeners grounded in reality. Don't list them mechanically - integrate them",
            "when they enhance the story.",
            "",
            "=" * 60,
            "TASK: Create Engaging Tour Guide Script",
            "=" * 60,
            "",
            f"POI: {poi_name}",
        ]

        if city:
            prompt_parts.append(f"City: {city}")

        if interests:
            interests_str = ", ".join(interests)
            prompt_parts.append(f"Focus Areas: {interests_str}")

        prompt_parts.extend([
            f"Language: {language}",
            "",
            "=" * 60,
            "RESEARCH FINDINGS",
            "=" * 60,
            "",
            research_context,
            "",
            "=" * 60,
            "REQUIREMENTS",
            "=" * 60,
            ""
        ])

        # Add style guidelines
        if style_guidelines:
            for guideline in style_guidelines:
                prompt_parts.append(f"- {guideline}")
            prompt_parts.append("")

        # Request both transcript and summary points
        prompt_parts.extend([
            "=" * 60,
            "OUTPUT FORMAT",
            "=" * 60,
            "",
            "Your response MUST include TWO sections:",
            "",
            "TRANSCRIPT:",
            "[Your engaging narration here - use the research findings above]",
            "",
            "SUMMARY POINTS:",
            "- Key learning point 1",
            "- Key learning point 2",
            "- Key learning point 3",
            "",
            "Now create the tour guide script using the research findings above."
        ])

        return "\n".join(prompt_parts)

    def _parse_response(self, raw_content: str) -> Tuple[str, List[str]]:
        """
        Parse AI response to extract transcript and summary points

        Args:
            raw_content: Raw response from AI

        Returns:
            Tuple of (transcript, summary_points)
        """
        # Look for TRANSCRIPT and SUMMARY POINTS sections
        transcript_match = re.search(r'TRANSCRIPT:\s*(.*?)\s*(?=SUMMARY POINTS:|$)',
                                     raw_content, re.DOTALL | re.IGNORECASE)
        summary_match = re.search(r'SUMMARY POINTS?:\s*(.*)',
                                  raw_content, re.DOTALL | re.IGNORECASE)

        # Extract transcript
        if transcript_match:
            transcript = transcript_match.group(1).strip()
        else:
            # Fallback: use everything before "SUMMARY POINTS" or entire content
            if 'SUMMARY POINTS' in raw_content.upper():
                transcript = raw_content.split('SUMMARY POINTS')[0].strip()
            else:
                transcript = raw_content.strip()

        # Extract summary points
        summary_points = []
        if summary_match:
            summary_text = summary_match.group(1).strip()
            # Extract bullet points
            lines = summary_text.split('\n')
            for line in lines:
                line = line.strip()
                # Match lines starting with -, *, •, or numbers
                if re.match(r'^[-*•]\s+', line):
                    point = re.sub(r'^[-*•]\s+', '', line).strip()
                    if point:
                        summary_points.append(point)
                elif re.match(r'^\d+[\.)]\s+', line):
                    point = re.sub(r'^\d+[\.)]\s+', '', line).strip()
                    if point:
                        summary_points.append(point)
                elif line and not line.startswith('TRANSCRIPT'):
                    # Include non-empty lines that aren't section headers
                    summary_points.append(line)

        # If no summary points found, create default ones
        if not summary_points:
            summary_points = [
                "Historical and cultural context of the location",
                "Interesting facts and stories",
                "Practical visitor information"
            ]

        return transcript, summary_points

    def _generate_openai(self, prompt: str) -> str:
        """Generate content using OpenAI"""
        print(f"  [DEBUG] Configuring OpenAI...")
        config = self.ai_config.get('openai', {})
        api_key = config.get('api_key')
        model = config.get('model', 'gpt-4-turbo-preview')

        print(f"  [DEBUG] Model: {model}")
        print(f"  [DEBUG] API key present: {bool(api_key)}")

        if not api_key:
            raise ValueError("OpenAI API key not configured")

        # Get system prompt from config
        content_config = self.config.get('content_generation', {})
        system_prompt = content_config.get('system_prompt',
            "You are an expert tour guide creating engaging audio scripts for tourists.")

        print(f"  [DEBUG] Prompt length: {len(prompt)} chars, System prompt: {len(system_prompt)} chars")
        print(f"  [DEBUG] Creating OpenAI client and sending request...")

        client = openai.OpenAI(api_key=api_key, timeout=60.0)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4096  # Increased for 5-min transcripts (~750 words + buffer)
        )

        print(f"  [DEBUG] Response received! Length: {len(response.choices[0].message.content)} chars")
        return response.choices[0].message.content.strip()

    def _generate_anthropic(self, prompt: str) -> str:
        """Generate content using Anthropic Claude with retry on overload"""
        print(f"  [DEBUG] Configuring Anthropic...")
        config = self.ai_config.get('anthropic', {})
        api_key = config.get('api_key')
        model = config.get('model', 'claude-3-5-sonnet-20241022')

        print(f"  [DEBUG] Model: {model}")
        print(f"  [DEBUG] API key present: {bool(api_key)}")

        if not api_key:
            raise ValueError("Anthropic API key not configured")

        # Get system prompt from config
        content_config = self.config.get('content_generation', {})
        system_prompt = content_config.get('system_prompt',
            "You are an expert tour guide creating engaging audio scripts for tourists.")

        print(f"  [DEBUG] Creating Anthropic client and sending request...")
        client = anthropic.Anthropic(api_key=api_key, timeout=60.0)

        # Retry logic for overloaded errors
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                    print(f"  [DEBUG] Retry {attempt}/{max_retries} - waiting {wait_time}s...")
                    time.sleep(wait_time)

                message = client.messages.create(
                    model=model,
                    max_tokens=4096,  # Increased for 5-min transcripts (~750 words + buffer)
                    temperature=0.7,
                    system=system_prompt.strip(),
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                print(f"  [DEBUG] Response received! Length: {len(message.content[0].text)} chars")
                return message.content[0].text.strip()

            except Exception as e:
                # Check if it's an overload error (529)
                error_str = str(e)
                if "529" in error_str or "overloaded" in error_str.lower():
                    if attempt < max_retries - 1:
                        print(f"  [WARNING] Anthropic API overloaded, retrying...")
                    else:
                        print(f"  [ERROR] Anthropic API still overloaded after {max_retries} attempts")
                        raise Exception(
                            f"Anthropic API is overloaded. Please try again in a minute, "
                            f"or use a different provider: --provider openai or --provider google"
                        ) from e
                else:
                    # Different error, raise immediately
                    raise

    def _generate_google(self, prompt: str) -> str:
        """Generate content using Google Gemini"""
        print(f"  [DEBUG] Configuring Google Gemini...")
        config = self.ai_config.get('google', {})
        api_key = config.get('api_key')
        model_name = config.get('model', 'gemini-pro')

        print(f"  [DEBUG] Model: {model_name}")
        print(f"  [DEBUG] API key present: {bool(api_key)}")

        if not api_key:
            raise ValueError("Google API key not configured")

        # Get system prompt from config
        content_config = self.config.get('content_generation', {})
        system_prompt = content_config.get('system_prompt',
            "You are an expert tour guide creating engaging audio scripts for tourists.")

        # For Gemini, prepend system prompt to user prompt
        full_prompt = f"{system_prompt.strip()}\n\n{prompt}"

        print(f"  [DEBUG] Creating Gemini client and sending request...")
        genai.configure(api_key=api_key)

        # Configure safety settings to be less restrictive for historical content
        from google.generativeai.types import HarmCategory, HarmBlockThreshold

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

        print(f"  [DEBUG] Full prompt length: {len(full_prompt)} chars")

        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=8192,  # Increased to max
            )
        )

        # Debug: Print the full response structure
        print(f"  [DEBUG] Response object type: {type(response)}")
        print(f"  [DEBUG] Has candidates: {hasattr(response, 'candidates')}")
        if hasattr(response, 'candidates'):
            print(f"  [DEBUG] Number of candidates: {len(response.candidates) if response.candidates else 0}")

        if hasattr(response, 'prompt_feedback'):
            print(f"  [DEBUG] Prompt feedback: {response.prompt_feedback}")

        # Check if response was blocked
        if not response.candidates:
            print(f"  [ERROR] No candidates returned")
            if hasattr(response, 'prompt_feedback'):
                print(f"  [ERROR] Prompt feedback details: {response.prompt_feedback}")
            raise ValueError("Google Gemini returned no candidates. Check prompt_feedback above.")

        candidate = response.candidates[0]
        print(f"  [DEBUG] Candidate object: {candidate}")

        # Check safety ratings
        if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
            print(f"  [DEBUG] Safety ratings:")
            for rating in candidate.safety_ratings:
                print(f"    - {rating.category}: {rating.probability}")

        # Check finish reason
        if hasattr(candidate, 'finish_reason'):
            finish_reason_names = {
                0: "FINISH_REASON_UNSPECIFIED",
                1: "STOP (normal)",
                2: "MAX_TOKENS",
                3: "SAFETY",
                4: "RECITATION",
                5: "OTHER"
            }
            finish_reason_name = finish_reason_names.get(candidate.finish_reason, f"Unknown ({candidate.finish_reason})")
            print(f"  [DEBUG] Finish reason: {candidate.finish_reason} = {finish_reason_name}")

            if candidate.finish_reason == 3:  # SAFETY
                raise ValueError(
                    "Google Gemini blocked the response due to safety filters. "
                    "Try using --provider openai or --provider anthropic instead."
                )
            elif candidate.finish_reason == 2:  # MAX_TOKENS
                print(f"  [WARNING] Response was truncated (MAX_TOKENS). Continuing anyway...")

        # Check if content exists
        if hasattr(candidate, 'content'):
            print(f"  [DEBUG] Candidate has content: {candidate.content}")
            if hasattr(candidate.content, 'parts'):
                print(f"  [DEBUG] Number of parts: {len(candidate.content.parts) if candidate.content.parts else 0}")

        try:
            text = response.text.strip()
            print(f"  [DEBUG] Response received! Length: {len(text)} chars")
            return text
        except ValueError as e:
            print(f"  [ERROR] Could not extract text from response")
            if hasattr(response, 'prompt_feedback'):
                print(f"  [DEBUG] Prompt feedback: {response.prompt_feedback}")
            raise ValueError(
                "Google Gemini could not generate content. "
                "The prompt may have triggered safety filters. "
                "Try using --provider openai or --provider anthropic instead."
            ) from e
