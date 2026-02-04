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

# Import verification and insertion agents
try:
    from .verification_agent import VerificationAgent
    from .insertion_agent import InsertionAgent
    from .diagnosis_agent import DiagnosisAgent
except ImportError:
    from verification_agent import VerificationAgent
    from insertion_agent import InsertionAgent
    from diagnosis_agent import DiagnosisAgent

# Import language utilities
try:
    from .utils import get_language_name
except ImportError:
    from utils import get_language_name


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

        # Initialize verification agent
        verification_config = config.get('verification', {})
        self.verification_enabled = verification_config.get('enabled', True)
        self.smart_mode = verification_config.get('smart_mode', True)  # Enable smart mode by default
        self.coverage_threshold = verification_config.get('coverage_threshold', 0.90)

        if self.verification_enabled:
            self.verification_agent = VerificationAgent(
                coverage_threshold=self.coverage_threshold,
                similarity_threshold=verification_config.get('similarity_threshold', 0.35)
            )
            self.insertion_agent = None  # Initialized lazily when needed
            self.diagnosis_agent = DiagnosisAgent(config) if self.smart_mode else None
        else:
            self.verification_agent = None
            self.insertion_agent = None
            self.diagnosis_agent = None

    def _detect_active_modules(self, research_data: Dict, interests: List[str] = None) -> List[str]:
        """
        Detect which prompt modules should be activated based on research content and user interests.

        Args:
            research_data: Research data dictionary
            interests: User-specified interests

        Returns:
            List of module names to activate (e.g., ['architecture', 'biography'])
        """
        active_modules = []
        interests = interests or []

        # Get module configurations
        content_config = self.config.get('content_generation', {})
        modules_config = content_config.get('prompt_modules', {})

        for module_name, module_cfg in modules_config.items():
            activated = False

            # Check if user explicitly requested this module via interests
            trigger_interests = module_cfg.get('trigger_interests', [])
            if any(interest.lower() in [t.lower() for t in trigger_interests] for interest in interests):
                activated = True

            # Check if research content triggers this module
            if not activated:
                trigger_keywords = module_cfg.get('trigger_keywords', [])
                research_str = str(research_data).lower()

                # Count keyword matches
                keyword_matches = sum(1 for keyword in trigger_keywords if keyword.lower() in research_str)

                # Activate if we have enough keyword matches (threshold: 2+ matches)
                if keyword_matches >= 2:
                    activated = True

            if activated:
                active_modules.append(module_name)

        return active_modules

    def _assemble_dynamic_prompt_modules(self, active_modules: List[str]) -> str:
        """
        Assemble the content from activated prompt modules.

        Args:
            active_modules: List of module names to include

        Returns:
            Concatenated module content
        """
        if not active_modules:
            return ""

        content_config = self.config.get('content_generation', {})
        modules_config = content_config.get('prompt_modules', {})

        module_contents = []
        for module_name in active_modules:
            if module_name in modules_config:
                module_content = modules_config[module_name].get('content', '')
                if module_content:
                    module_contents.append(module_content.strip())

        if module_contents:
            return "\n\n" + "\n\n".join(module_contents) + "\n"
        return ""

    def _extract_learning_objectives(self, core_features: List[str]) -> List[str]:
        """
        Extract 2-3 key learning objectives from core features.

        These become the educational goals that the transcript must achieve.
        Instead of treating core features as checkboxes, we frame them as
        learning outcomes that should naturally emerge from the narrative.

        Args:
            core_features: List of core feature strings from research

        Returns:
            List of 2-3 learning objective strings
        """
        if not core_features or len(core_features) == 0:
            return []

        # Group features by theme
        architectural = []
        historical = []
        cultural = []

        for feature in core_features:
            feature_lower = feature.lower()

            # Categorize
            if any(term in feature_lower for term in ['column', 'marble', 'diameter', 'tall', 'optical', 'curve', 'entasis', 'floor', 'clamp']):
                architectural.append(feature)
            elif any(term in feature_lower for term in ['war', 'bullet', 'damage', 'explosion', 'feet', 'worn']):
                historical.append(feature)
            else:
                cultural.append(feature)

        # Create learning objectives
        objectives = []

        # Architecture objective (if we have architectural features)
        if architectural:
            arch_details = []
            for feat in architectural:
                # Extract key details
                if 'column' in feat.lower() and 'meter' in feat.lower():
                    arch_details.append("precise column measurements")
                if 'optical' in feat.lower() or 'curve' in feat.lower():
                    arch_details.append("optical illusion techniques")
                if 'clamp' in feat.lower() or 'mortar' in feat.lower():
                    arch_details.append("ancient construction methods")

            if arch_details:
                details_str = ", ".join(arch_details[:2])  # Max 2 details
                objectives.append(f"The architectural genius behind the structure ({details_str})")

        # Historical/cultural objective
        if historical or cultural:
            combined = historical + cultural
            # Pick the most dramatic feature
            for feat in combined:
                if 'stolen' in feat.lower() or 'british' in feat.lower():
                    objectives.append("The cultural theft and survival across 2,500 years of conflict")
                    break
                elif 'war' in feat.lower() or 'damage' in feat.lower():
                    objectives.append("The visible scars of wars and occupations throughout history")
                    break
                elif 'female statue' in feat.lower() or 'caryatid' in feat.lower():
                    objectives.append("The famous sculptures and their dramatic fates")
                    break
            else:
                # Fallback if no dramatic element found
                if combined:
                    objectives.append("The historical layers and transformations of the site")

        # Ensure we have at least 1 objective
        if not objectives and core_features:
            # Fallback: create generic objective from first feature
            objectives.append(f"The essential physical features that define this place")

        # Limit to 2-3 objectives
        return objectives[:3]

    def generate(
        self,
        poi_name: str,
        provider: str = None,
        city: str = None,
        description: str = None,
        interests: list = None,
        custom_prompt: str = None,
        language: str = "en",
        skip_research: bool = False,
        force_research: bool = False
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        Generate tour guide content for a POI

        Args:
            poi_name: Name of the point of interest
            provider: AI provider to use (openai, anthropic, google)
            city: City name
            description: Basic description of the POI
            interests: List of interests/aspects to focus on
            custom_prompt: Custom prompt to use instead of default
            language: Target language code (ISO 639-1, e.g., 'en', 'zh-tw', 'pt-br')
            skip_research: Skip research phase even if enabled in config
            force_research: Force research even if cached data exists

        Returns:
            Tuple of (transcript, summary_points, generation_metadata)
            - transcript: The narration text
            - summary_points: List of key learning points
            - generation_metadata: Dict with research_data, filtering info, etc.
        """
        if provider is None:
            provider = self.config.get('defaults', {}).get('ai_provider', 'openai')

        # Research Phase (if enabled and not skipped)
        research_data = None
        filtered_research = None
        research_path = None
        use_research = self.research_enabled and not skip_research and self.research_agent

        if use_research:
            print(f"  [STEP 1/2] Research Phase", flush=True)
            research_path = self._get_research_path(city, poi_name)

            # Check if research already exists
            if research_path.exists() and not force_research:
                research_data = self._load_research(research_path)
            else:
                # Perform recursive research
                research_data = self.research_agent.research_poi_recursive(
                    poi_name=poi_name,
                    city=city or "Unknown",
                    user_description=description or "",
                    provider=provider
                )

                # Save research for future use
                self._save_research(research_path, research_data)

        # Build the prompt
        if custom_prompt:
            prompt = custom_prompt
        else:
            if use_research:
                print(f"  [STEP 2/2] Storytelling Phase", flush=True)
                # Filter research before building prompt
                filtered_research = self._filter_research(research_data, interests)
                prompt = self._build_prompt_with_research(
                    poi_name, city, research_data, interests, language
                )
            else:
                prompt = self._build_prompt(poi_name, city, description, interests, language)

        # Generate content based on provider
        if provider == 'openai':
            raw_content = self._generate_openai(prompt)
        elif provider == 'anthropic':
            raw_content = self._generate_anthropic(prompt)
        elif provider == 'google':
            raw_content = self._generate_google(prompt)
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")

        # Parse the response to extract transcript and summary points
        result = self._parse_response(raw_content)
        transcript = result[0]
        summary_points = result[1]

        # Verification and refinement loop (if enabled and we have research data)
        verification_metadata = {}
        if self.verification_enabled and use_research and research_data:
            # Core features are nested under 'poi'
            core_features = research_data.get('poi', {}).get('core_features', [])
            if core_features:
                print(f"  [VERIFICATION] Checking core features coverage...", flush=True)

                # Use smart verification if enabled, otherwise use legacy version
                if self.smart_mode:
                    transcript, verification_metadata = self._verify_and_refine_smart(
                        transcript=transcript,
                        core_features=core_features,
                        research_data=research_data,
                        poi_name=poi_name,
                        city=city,
                        provider=provider
                    )
                else:
                    transcript, verification_metadata = self._verify_and_refine(
                        transcript=transcript,
                        core_features=core_features,
                        poi_name=poi_name,
                        city=city,
                        provider=provider
                    )

        # Build generation metadata for audit trail
        generation_metadata = {
            'research_data': research_data if use_research else None,
            'research_path': str(research_path) if research_path else None,
            'filtered_research': filtered_research if use_research else None,
            'entities_before_filter': len(research_data.get('entities', {})) if research_data else 0,
            'entities_after_filter': len(filtered_research.get('entities', {})) if filtered_research else 0,
            'verification': verification_metadata
        }

        return (transcript, summary_points, generation_metadata)

    def _verify_and_refine(
        self,
        transcript: str,
        core_features: List[str],
        poi_name: str,
        city: str,
        provider: str,
        max_iterations: int = 2
    ) -> Tuple[str, Dict]:
        """
        Verify transcript coverage and refine with insertions if needed.

        Args:
            transcript: Initial transcript text
            core_features: List of core feature strings from research
            poi_name: POI name for context
            city: City name for context
            provider: AI provider to use for insertions
            max_iterations: Maximum refinement iterations (default: 2)

        Returns:
            Tuple of (refined_transcript, verification_metadata)
        """
        verification_config = self.config.get('verification', {})
        max_iterations = verification_config.get('max_iterations', max_iterations)

        current_transcript = transcript
        iteration = 0
        refinement_history = []

        while iteration < max_iterations:
            iteration += 1

            # Verify coverage
            verification_result = self.verification_agent.verify_coverage(
                current_transcript,
                core_features
            )

            # Print report
            report = self.verification_agent.format_report(verification_result)
            print(f"\n{report}\n", flush=True)

            # Store iteration results
            refinement_history.append({
                'iteration': iteration,
                'coverage': verification_result['coverage'],
                'found_features': verification_result['found_features'],
                'total_features': verification_result['total_features'],
                'passes_threshold': verification_result['passes_threshold']
            })

            # Check if we pass threshold
            if verification_result['passes_threshold']:
                print(f"  ✅ Coverage threshold met: {verification_result['coverage']*100:.1f}%", flush=True)
                break

            # If we don't pass and haven't exceeded max iterations, refine with insertions
            if iteration < max_iterations:
                print(f"  ⚠️  Coverage below threshold. Generating insertions (iteration {iteration}/{max_iterations})...", flush=True)

                # Initialize insertion agent if needed
                if self.insertion_agent is None:
                    self.insertion_agent = InsertionAgent(self.config, provider)

                # Plan insertions for missing features
                missing_features = verification_result['missing_features']

                # Also include partial features if they have low confidence
                for feature_status in verification_result['feature_status']:
                    if feature_status['found'] and feature_status['confidence'] < 0.5:
                        if feature_status['feature'] not in missing_features:
                            missing_features.append(feature_status['feature'])

                if not missing_features:
                    print(f"  ℹ️  No missing features identified, but coverage still low. Stopping.", flush=True)
                    break

                print(f"  📝 Planning insertions for {len(missing_features)} missing features...", flush=True)
                insertion_plans = self.insertion_agent.plan_insertions(
                    current_transcript,
                    missing_features
                )

                # Generate insertion text for each plan
                insertions = []
                for i, plan in enumerate(insertion_plans, 1):
                    print(f"     [{i}/{len(insertion_plans)}] Generating insertion for: {plan['feature'][:60]}...", flush=True)

                    try:
                        insertion_text = self.insertion_agent.generate_insertion(
                            plan,
                            poi_name=poi_name,
                            city=city or ""
                        )

                        insertions.append({
                            'line_number': plan['line_number'],
                            'text': insertion_text,
                            'feature': plan['feature']
                        })

                        print(f"     ✓ Generated: \"{insertion_text[:80]}...\"", flush=True)

                    except Exception as e:
                        print(f"     ✗ Failed to generate insertion: {e}", flush=True)
                        continue

                # Splice insertions into transcript
                if insertions:
                    print(f"  🔧 Splicing {len(insertions)} insertions into transcript...", flush=True)
                    current_transcript = self.insertion_agent.splice_transcript(
                        current_transcript,
                        insertions
                    )
                    print(f"  ✓ Transcript refined (iteration {iteration} complete)", flush=True)
                else:
                    print(f"  ✗ No insertions generated. Stopping refinement.", flush=True)
                    break

            else:
                print(f"  ⚠️  Maximum iterations reached. Final coverage: {verification_result['coverage']*100:.1f}%", flush=True)

        # Build verification metadata
        verification_metadata = {
            'enabled': True,
            'iterations': iteration,
            'final_coverage': verification_result['coverage'] if verification_result else 0,
            'refinement_history': refinement_history,
            'final_status': 'passed' if verification_result.get('passes_threshold', False) else 'failed'
        }

        return current_transcript, verification_metadata

    def _build_prompt(
        self,
        poi_name: str,
        city: str = None,
        description: str = None,
        interests: list = None,
        language: str = "en"
    ) -> str:
        """
        Build a prompt for content generation

        Args:
            poi_name: Name of the POI
            city: City name
            description: Basic description of the POI
            interests: List of interests/aspects to focus on
            language: Target language code (ISO 639-1, e.g., 'en', 'zh-tw')

        Returns:
            Complete prompt string
        """
        # Convert language code to full descriptive name
        language_name = get_language_name(language)

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
            "=" * 60,
            "CRITICAL INSTRUCTION - LANGUAGE",
            "=" * 60,
            "",
            f"Write the ENTIRE tour guide script in {language_name}.",
            f"Every sentence, every word must be in {language_name}.",
            "Do not use English (or any other language) except for:",
            "- Proper names of people and places",
            "- Historical terms that don't translate well",
            "",
            f"The audience speaks {language_name} as their primary language.",
            f"They expect to hear the narration in {language_name}.",
            "",
            "=" * 60,
            "",
            f"Create a tour guide script for: {poi_name}"
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

        # Note: core_features are kept inside 'poi' dict, not extracted to top level
        filtered = {
            'poi': research_data.get('poi', {}),  # This includes core_features
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
        core_features = research_data.get('poi', {}).get('core_features', [])
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
        language: str = "en"
    ) -> str:
        """
        Build storytelling prompt using research data

        Args:
            poi_name: Name of POI
            city: City name
            research_data: Research data from research agent
            interests: User interests for filtering
            language: Target language code (ISO 639-1, e.g., 'en', 'zh-tw')

        Returns:
            Complete prompt for storytelling phase
        """
        # Convert language code to full descriptive name
        language_name = get_language_name(language)

        # Get style guidelines and system prompt from config
        content_config = self.config.get('content_generation', {})
        system_prompt = content_config.get('system_prompt',
            "You are a master storyteller tour guide who makes history come alive.")
        style_guidelines = content_config.get('style_guidelines', [])

        # Filter research by interests
        filtered_research = self._filter_research(research_data, interests)

        # Serialize research into readable text
        research_context = self._serialize_research(filtered_research)

        # Detect and assemble dynamic prompt modules
        active_modules = self._detect_active_modules(research_data, interests)
        module_content = self._assemble_dynamic_prompt_modules(active_modules)

        # Extract learning objectives from core features (Option C)
        core_features = research_data.get('poi', {}).get('core_features', [])
        learning_objectives = self._extract_learning_objectives(core_features)

        # Build prompt
        prompt_parts = [
            system_prompt.strip(),
            "",
            "=" * 60,
            "CRITICAL INSTRUCTION - LANGUAGE",
            "=" * 60,
            "",
            f"Write the ENTIRE tour guide script in {language_name}.",
            f"Every sentence, every word must be in {language_name}.",
            "Do not use English (or any other language) except for:",
            "- Proper names of people and places",
            "- Historical terms that don't translate well",
            "",
            f"The audience speaks {language_name} as their primary language.",
            f"They expect to hear the narration in {language_name}.",
            "",
            "=" * 60,
            "",
            "LEARNING OBJECTIVES: Your transcript must teach visitors these key things:",
        ]

        # Add learning objectives
        if learning_objectives:
            for i, objective in enumerate(learning_objectives, 1):
                prompt_parts.append(f"  {i}. {objective}")
        else:
            prompt_parts.append("  (Build your narrative around the core features provided)")

        prompt_parts.extend([
            "",
            "These objectives should emerge naturally from your dramatic storytelling.",
            "Don't lecture - weave these insights into your narrative so visitors",
            "learn through engaging stories, not academic explanations.",
            "",
            "NOTE: You will receive CORE FEATURES - essential physical facts about what visitors",
            "can experience at this POI right now. These features are the EVIDENCE that supports",
            "your learning objectives. YOU MUST include ALL core features in your transcript.",
            "Use exact measurements and details - do NOT invent or approximate.",
            "Weave them naturally into your narrative to teach the learning objectives above.",
            "",
            "=" * 60,
            "TASK: Create Engaging Tour Guide Script",
            "=" * 60,
            "",
            f"POI: {poi_name}",
        ])

        if city:
            prompt_parts.append(f"City: {city}")

        if interests:
            interests_str = ", ".join(interests)
            prompt_parts.append(f"Focus Areas: {interests_str}")

        prompt_parts.extend([
            f"Target Language: {language_name}",
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

        # Add dynamic prompt modules if any were activated
        if module_content:
            prompt_parts.append(module_content)

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
        config = self.ai_config.get('anthropic', {})
        api_key = config.get('api_key')
        model = config.get('model', 'claude-3-5-sonnet-20241022')

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

    # ===== Smart Verification Loop Methods =====

    def _verify_and_refine_smart(
        self,
        transcript: str,
        core_features: List[str],
        research_data: Dict,
        poi_name: str,
        city: str,
        provider: str,
        max_iterations: int = 2
    ) -> Tuple[str, Dict]:
        """
        Smart verification loop with diagnosis and targeted fixes

        This is the NEW smart verification approach that:
        1. Skips features that already passed (>70% confidence)
        2. Diagnoses WHY features fail (research gap vs selection gap)
        3. Expands research when needed (research gaps)
        4. Generates targeted insertions with explicit facts (selection gaps)
        5. Uses natural integration (full transcript, AI chooses placement)

        Args:
            transcript: Initial transcript text
            core_features: List of core feature strings from research
            research_data: Full research data dictionary (may be expanded)
            poi_name: POI name for context
            city: City name for context
            provider: AI provider to use
            max_iterations: Maximum refinement iterations (default: 2)

        Returns:
            Tuple of (refined_transcript, verification_metadata)
        """
        verification_config = self.config.get('verification', {})
        max_iterations = verification_config.get('max_iterations', max_iterations)

        current_transcript = transcript
        passed_features = set()  # Track features that passed
        iteration = 0
        refinement_history = []

        print(f"  [SMART VERIFICATION] Using smart verification loop with diagnosis", flush=True)

        while iteration < max_iterations:
            iteration += 1
            print(f"\n  [ITERATION {iteration}/{max_iterations}]", flush=True)

            # STEP 1: Smart verification (skip already-passed features)
            verification = self.verification_agent.verify_coverage_smart(
                current_transcript,
                core_features,
                passed_features
            )

            # Print status
            passed_count = len(verification['passed'])
            partial_count = len(verification['partial'])
            missing_count = len(verification['missing'])
            print(f"  Coverage: {verification['coverage']*100:.1f}% | Passed: {passed_count}, Partial: {partial_count}, Missing: {missing_count}", flush=True)

            # STEP 2: Update passed features
            passed_features = verification['passed_features']

            # Store iteration results
            refinement_history.append({
                'iteration': iteration,
                'coverage': verification['coverage'],
                'passed_count': passed_count,
                'partial_count': partial_count,
                'missing_count': missing_count,
                'passes_threshold': verification['passes_threshold']
            })

            # STEP 3: Check if we're done
            if verification['passes_threshold']:
                print(f"  ✅ Coverage threshold met: {verification['coverage']*100:.1f}%", flush=True)
                break

            # STEP 4: Get failed features (partial + missing)
            failed_features = verification['partial'] + verification['missing']

            if not failed_features or iteration >= max_iterations:
                if not failed_features:
                    print(f"  ℹ️  No failed features to fix", flush=True)
                else:
                    print(f"  ⚠️  Max iterations reached. Final coverage: {verification['coverage']*100:.1f}%", flush=True)
                break

            print(f"  📋 Processing {len(failed_features)} failed features...", flush=True)

            # STEP 5: Diagnose failures
            diagnoses = self.diagnosis_agent.diagnose_feature_failures(
                failed_features,
                research_data,
                current_transcript,
                provider
            )

            # STEP 6: Initialize insertion agent if needed
            if self.insertion_agent is None:
                self.insertion_agent = InsertionAgent(self.config, provider)

            # STEP 7: Process each diagnosis
            for i, diagnosis in enumerate(diagnoses, 1):
                feature_short = diagnosis['feature'][:60] + "..." if len(diagnosis['feature']) > 60 else diagnosis['feature']
                print(f"\n  [{i}/{len(diagnoses)}] Processing: {feature_short}", flush=True)

                try:
                    if diagnosis['diagnosis_type'] == 'research_gap':
                        # Research gap: Expand research then integrate
                        print(f"    → Research gap detected. Expanding research...", flush=True)

                        new_research = self.research_agent.expand_research_for_feature(
                            feature=diagnosis['feature'],
                            poi_name=poi_name,
                            city=city,
                            existing_research=research_data,
                            provider=provider
                        )

                        # Merge new research into existing
                        research_data = self._merge_research(research_data, new_research)

                        # Integrate with expanded research
                        current_transcript = self.insertion_agent.integrate_feature_with_expansion(
                            feature=diagnosis['feature'],
                            new_research=new_research,
                            full_transcript=current_transcript,
                            poi_name=poi_name,
                            city=city,
                            provider=provider
                        )

                        print(f"    ✓ Integrated with expanded research", flush=True)

                    else:  # selection_gap
                        # Selection gap: Integrate with explicit facts
                        print(f"    → Selection gap detected. Integrating with {len(diagnosis['relevant_facts'])} facts...", flush=True)

                        current_transcript = self.insertion_agent.integrate_feature_with_facts(
                            feature=diagnosis['feature'],
                            relevant_facts=diagnosis['relevant_facts'],
                            full_transcript=current_transcript,
                            poi_name=poi_name,
                            city=city,
                            provider=provider
                        )

                        print(f"    ✓ Integrated with explicit facts", flush=True)

                except Exception as e:
                    print(f"    ❌ Failed: {str(e)}", flush=True)
                    continue

        # Build metadata
        metadata = {
            'smart_mode': True,
            'iterations': iteration,
            'final_coverage': verification['coverage'],
            'passed_features': len(passed_features),
            'total_features': len(core_features),
            'refinement_history': refinement_history,
            'final_verification': {
                'passed': len(verification['passed']),
                'partial': len(verification['partial']),
                'missing': len(verification['missing'])
            }
        }

        return current_transcript, metadata

    def _merge_research(self, existing: Dict, new_research: Dict) -> Dict:
        """
        Merge new research into existing research data

        Strategy:
        - Append to core_features list
        - Extend people, events, locations, concepts lists
        - Merge entities dict (avoiding duplicates)
        - Preserve existing structure

        Args:
            existing: Existing research data
            new_research: New research data to merge

        Returns:
            Merged research data dictionary
        """
        merged = existing.copy()

        # Merge into 'poi' section
        if 'poi' in merged:
            poi = merged['poi']

            # Merge core_features
            if 'core_features' in new_research:
                if 'core_features' not in poi:
                    poi['core_features'] = []
                poi['core_features'].extend(new_research['core_features'])

        # Merge top-level arrays
        for section in ['people', 'events', 'locations', 'concepts']:
            if section in new_research:
                if section not in merged:
                    merged[section] = []
                merged[section].extend(new_research[section])

        # Merge entities (avoid duplicates by name)
        if 'entities' in new_research:
            if 'entities' not in merged:
                merged['entities'] = {}

            for entity_name, entity_data in new_research['entities'].items():
                if entity_name not in merged['entities']:
                    merged['entities'][entity_name] = entity_data

        return merged
