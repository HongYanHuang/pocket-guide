"""
Diagnosis Agent - Root cause analysis for feature verification failures

This module diagnoses WHY features are missing from transcripts:
- Research Gap: Research data doesn't contain information about the feature
- Selection Gap: Research has info but transcript didn't use it

The diagnosis enables targeted fixes:
- Research gaps → Expand research with focused queries
- Selection gaps → Generate insertions with explicit facts
"""

from typing import Dict, List, Any
import re
from difflib import SequenceMatcher


class DiagnosisAgent:
    """
    Diagnosis agent for feature verification failures

    Features:
    - Root cause analysis (research gap vs selection gap)
    - Research coverage checking with keyword extraction
    - Fact extraction from research data
    - Confidence scoring for diagnoses
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Diagnosis Agent

        Args:
            config: Full application config dictionary
        """
        self.config = config
        self.verification_config = config.get('verification', {})
        self.diagnosis_config = self.verification_config.get('diagnosis', {})

        # Thresholds
        self.research_gap_threshold = self.diagnosis_config.get('research_gap_threshold', 0.30)

    def diagnose_feature_failures(
        self,
        features: List[Dict],
        research_data: Dict,
        transcript: str,
        provider: str
    ) -> List[Dict]:
        """
        Diagnose each failed feature to identify root cause

        Args:
            features: List of failed feature dicts with 'feature' and 'score' keys
            research_data: Full research data dictionary
            transcript: Current transcript text
            provider: AI provider name (for potential AI-based diagnosis)

        Returns:
            List of diagnosis dictionaries:
            {
                'feature': str,
                'score': float,
                'diagnosis_type': 'research_gap' | 'selection_gap',
                'relevant_facts': List[str],  # if selection_gap
                'missing_info': str,  # if research_gap
                'confidence': float
            }
        """
        diagnoses = []

        for feature_dict in features:
            feature = feature_dict['feature']
            score = feature_dict.get('score', 0.0)

            # Check research coverage
            coverage_result = self._check_research_coverage(feature, research_data)

            # Determine diagnosis type based on coverage
            if coverage_result['coverage_score'] < self.research_gap_threshold:
                # Research gap: Research doesn't have enough info about this feature
                diagnosis = {
                    'feature': feature,
                    'score': score,
                    'diagnosis_type': 'research_gap',
                    'relevant_facts': [],
                    'missing_info': coverage_result.get('missing_keywords', ''),
                    'confidence': 1.0 - coverage_result['coverage_score']
                }
            else:
                # Selection gap: Research has info but transcript didn't use it
                relevant_facts = self._extract_relevant_facts(feature, research_data)
                diagnosis = {
                    'feature': feature,
                    'score': score,
                    'diagnosis_type': 'selection_gap',
                    'relevant_facts': relevant_facts,
                    'missing_info': '',
                    'confidence': coverage_result['coverage_score']
                }

            diagnoses.append(diagnosis)

            # Log diagnosis
            print(f"  [DIAGNOSIS] Feature: {feature[:60]}...")
            print(f"    Type: {diagnosis['diagnosis_type']}")
            print(f"    Confidence: {diagnosis['confidence']:.2f}")
            if diagnosis['diagnosis_type'] == 'research_gap':
                print(f"    Missing: {diagnosis['missing_info']}")
            else:
                print(f"    Found {len(diagnosis['relevant_facts'])} relevant facts")

        return diagnoses

    def _check_research_coverage(
        self,
        feature: str,
        research_data: Dict
    ) -> Dict:
        """
        Check if research data contains information about this feature

        Strategy:
        1. Extract keywords from feature description
        2. Search all sections of research_data for keyword mentions
        3. Use fuzzy matching for related terms
        4. Return coverage score and matched content

        Args:
            feature: Feature description string
            research_data: Full research data dictionary

        Returns:
            {
                'coverage_score': float (0.0-1.0),
                'matched_sections': List[str],
                'matched_keywords': List[str],
                'missing_keywords': str
            }
        """
        # Extract keywords from feature (nouns, adjectives, numbers)
        keywords = self._extract_keywords(feature)

        if not keywords:
            return {
                'coverage_score': 0.0,
                'matched_sections': [],
                'matched_keywords': [],
                'missing_keywords': feature
            }

        # Convert research_data to searchable text
        research_text = self._research_to_text(research_data)
        research_text_lower = research_text.lower()

        # Check each keyword
        matched_keywords = []
        for keyword in keywords:
            keyword_lower = keyword.lower()

            # Exact match
            if keyword_lower in research_text_lower:
                matched_keywords.append(keyword)
                continue

            # Fuzzy match (check for similar words)
            if self._fuzzy_search(keyword_lower, research_text_lower):
                matched_keywords.append(keyword)

        # Calculate coverage score
        coverage_score = len(matched_keywords) / len(keywords) if keywords else 0.0

        # Identify missing keywords
        missing_keywords = [k for k in keywords if k not in matched_keywords]
        missing_info = ', '.join(missing_keywords) if missing_keywords else ''

        return {
            'coverage_score': coverage_score,
            'matched_sections': [],  # Could be enhanced to track which sections matched
            'matched_keywords': matched_keywords,
            'missing_keywords': missing_info
        }

    def _extract_relevant_facts(
        self,
        feature: str,
        research_data: Dict
    ) -> List[str]:
        """
        Extract specific facts from research related to the feature

        Args:
            feature: Feature description string
            research_data: Full research data dictionary

        Returns:
            List of atomic facts (strings) relevant to the feature
        """
        keywords = self._extract_keywords(feature)
        facts = []

        # Extract from core_features
        if 'core_features' in research_data:
            for core_feature in research_data['core_features']:
                if isinstance(core_feature, str):
                    if self._matches_keywords(core_feature, keywords):
                        facts.append(f"Core feature: {core_feature}")

        # Extract from people
        if 'people' in research_data:
            for person in research_data['people']:
                person_text = f"{person.get('name', '')} {person.get('role', '')} {person.get('personality', '')}"
                if self._matches_keywords(person_text, keywords):
                    fact = f"{person.get('name', 'Person')}"
                    if person.get('role'):
                        fact += f" ({person['role']})"
                    if person.get('personality'):
                        fact += f": {person['personality']}"
                    facts.append(fact)

        # Extract from events
        if 'events' in research_data:
            for event in research_data['events']:
                event_text = f"{event.get('name', '')} {event.get('date', '')} {event.get('significance', '')}"
                if self._matches_keywords(event_text, keywords):
                    fact = f"{event.get('name', 'Event')}"
                    if event.get('date'):
                        fact += f" ({event['date']})"
                    if event.get('significance'):
                        fact += f": {event['significance']}"
                    facts.append(fact)

        # Extract from locations
        if 'locations' in research_data:
            for location in research_data['locations']:
                location_text = f"{location.get('name', '')} {location.get('description', '')}"
                if self._matches_keywords(location_text, keywords):
                    fact = f"{location.get('name', 'Location')}"
                    if location.get('description'):
                        fact += f": {location['description']}"
                    facts.append(fact)

        # Extract from concepts
        if 'concepts' in research_data:
            for concept in research_data['concepts']:
                concept_text = f"{concept.get('name', '')} {concept.get('explanation', '')}"
                if self._matches_keywords(concept_text, keywords):
                    fact = f"{concept.get('name', 'Concept')}"
                    if concept.get('explanation'):
                        fact += f": {concept['explanation']}"
                    facts.append(fact)

        # If no facts found but coverage score was high, extract from POI basic info
        if not facts and 'poi' in research_data:
            poi = research_data['poi']
            if 'description' in poi:
                if self._matches_keywords(poi['description'], keywords):
                    facts.append(f"POI description: {poi['description']}")

        return facts

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract important keywords from text (nouns, numbers, significant adjectives)

        Args:
            text: Input text

        Returns:
            List of keyword strings
        """
        # Extract numbers (often important: dates, measurements, counts)
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)

        # Extract capitalized words (likely proper nouns or important terms)
        capitalized = re.findall(r'\b[A-Z][a-z]+\b', text)

        # Extract significant words (length > 4, not common words)
        common_words = {'this', 'that', 'with', 'from', 'have', 'were', 'been', 'their', 'there', 'where', 'which', 'while', 'these', 'those'}
        words = re.findall(r'\b[a-z]{5,}\b', text.lower())
        significant_words = [w for w in words if w not in common_words]

        # Combine and deduplicate
        keywords = list(set(numbers + capitalized + significant_words))

        return keywords

    def _research_to_text(self, research_data: Dict) -> str:
        """
        Convert research data structure to searchable text

        Args:
            research_data: Full research data dictionary

        Returns:
            Concatenated text from all research sections
        """
        text_parts = []

        # POI section
        if 'poi' in research_data:
            poi = research_data['poi']
            if isinstance(poi, dict):
                for key, value in poi.items():
                    if isinstance(value, str):
                        text_parts.append(value)
                    elif isinstance(value, list):
                        text_parts.extend([str(v) for v in value])

        # Core features
        if 'core_features' in research_data:
            text_parts.extend([str(f) for f in research_data['core_features']])

        # People, events, locations, concepts
        for section in ['people', 'events', 'locations', 'concepts']:
            if section in research_data:
                for item in research_data[section]:
                    if isinstance(item, dict):
                        for key, value in item.items():
                            if isinstance(value, str):
                                text_parts.append(value)
                            elif isinstance(value, list):
                                text_parts.extend([str(v) for v in value])

        return ' '.join(text_parts)

    def _fuzzy_search(self, keyword: str, text: str, threshold: float = 0.75) -> bool:
        """
        Fuzzy search for keyword in text using sequence matching

        Args:
            keyword: Keyword to search for
            text: Text to search in
            threshold: Similarity threshold (0.0-1.0)

        Returns:
            True if similar word found, False otherwise
        """
        # Split text into words
        words = text.split()

        for word in words:
            # Check similarity
            similarity = SequenceMatcher(None, keyword, word).ratio()
            if similarity >= threshold:
                return True

        return False

    def _matches_keywords(self, text: str, keywords: List[str]) -> bool:
        """
        Check if text contains any of the keywords (case-insensitive)

        Args:
            text: Text to check
            keywords: List of keywords

        Returns:
            True if at least one keyword matches
        """
        text_lower = text.lower()

        for keyword in keywords:
            if keyword.lower() in text_lower:
                return True

        return False
