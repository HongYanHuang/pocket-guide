"""
Verification Agent - Validates transcript coverage of core features.

This agent parses transcripts and checks whether all core features from research
are properly included. Uses fuzzy matching to detect features even when paraphrased.
"""

import re
from typing import List, Dict, Tuple
from difflib import SequenceMatcher


class VerificationAgent:
    """
    Agent responsible for verifying that transcripts include all core features.
    """

    def __init__(self, coverage_threshold: float = 0.90, similarity_threshold: float = 0.35):
        """
        Initialize verification agent.

        Args:
            coverage_threshold: Minimum % of features that must be present (default: 90%)
            similarity_threshold: How similar text must be to consider feature "found" (default: 0.35)
        """
        self.coverage_threshold = coverage_threshold
        self.similarity_threshold = similarity_threshold

    def verify_coverage(self, transcript: str, core_features: List[str]) -> Dict:
        """
        Verify that transcript includes all core features.

        Args:
            transcript: The generated transcript text
            core_features: List of core feature strings from research

        Returns:
            Dictionary with coverage analysis:
            {
                'coverage': 0.6,  # 60% coverage
                'total_features': 5,
                'found_features': 3,
                'feature_status': [
                    {
                        'feature': 'Plateau rises 150 meters...',
                        'found': True,
                        'confidence': 0.75,
                        'matched_text': 'limestone plateau that towers 150 meters',
                        'line_numbers': [8, 9]
                    },
                    ...
                ],
                'missing_features': [...],
                'partial_features': [...]
            }
        """
        if not core_features:
            return {
                'coverage': 1.0,
                'total_features': 0,
                'found_features': 0,
                'feature_status': [],
                'missing_features': [],
                'partial_features': []
            }

        # Split transcript into lines for reference
        transcript_lines = transcript.split('\n')
        transcript_lower = transcript.lower()

        feature_status = []
        found_count = 0
        partial_count = 0

        for feature in core_features:
            status = self._check_feature(feature, transcript_lower, transcript_lines)
            feature_status.append(status)

            if status['found']:
                if status['confidence'] >= 0.6:
                    found_count += 1
                else:
                    partial_count += 1

        # Calculate coverage (found + 0.5*partial)
        total_features = len(core_features)
        weighted_found = found_count + (0.5 * partial_count)
        coverage = weighted_found / total_features if total_features > 0 else 1.0

        # Categorize features
        missing_features = [
            f['feature'] for f in feature_status
            if not f['found'] or f['confidence'] < 0.3
        ]

        partial_features = [
            f for f in feature_status
            if f['found'] and 0.3 <= f['confidence'] < 0.6
        ]

        return {
            'coverage': coverage,
            'total_features': total_features,
            'found_features': found_count,
            'partial_features_count': partial_count,
            'feature_status': feature_status,
            'missing_features': missing_features,
            'partial_features': partial_features,
            'passes_threshold': coverage >= self.coverage_threshold
        }

    def _check_feature(self, feature: str, transcript_lower: str, transcript_lines: List[str]) -> Dict:
        """
        Check if a single feature is present in the transcript.

        Uses multiple detection strategies:
        1. Exact key numbers/measurements
        2. Key terms presence (fuzzy matching)
        3. Semantic similarity of phrases

        Args:
            feature: The core feature string to check
            transcript_lower: Lowercase transcript for matching
            transcript_lines: Original transcript split by lines

        Returns:
            Status dict with 'found', 'confidence', 'matched_text', 'line_numbers'
        """
        feature_lower = feature.lower()

        # Extract key elements from feature
        key_numbers = self._extract_numbers(feature)
        key_terms = self._extract_key_terms(feature)

        # Check for exact numbers (measurements are critical)
        number_matches = 0
        for number in key_numbers:
            if number in transcript_lower or self._fuzzy_number_match(number, transcript_lower):
                number_matches += 1

        number_score = number_matches / len(key_numbers) if key_numbers else 0

        # Check for key terms
        term_matches = 0
        for term in key_terms:
            if term in transcript_lower:
                term_matches += 1

        term_score = term_matches / len(key_terms) if key_terms else 0

        # Find best matching text segment
        best_match = self._find_best_match(feature_lower, transcript_lines)

        # Calculate overall confidence
        # Numbers are critical (weight: 0.5), terms important (weight: 0.3), similarity (weight: 0.2)
        confidence = (0.5 * number_score) + (0.3 * term_score) + (0.2 * best_match['similarity'])

        found = confidence >= self.similarity_threshold

        return {
            'feature': feature,
            'found': found,
            'confidence': confidence,
            'matched_text': best_match['text'] if found else None,
            'line_numbers': best_match['lines'] if found else [],
            'number_score': number_score,
            'term_score': term_score,
            'similarity_score': best_match['similarity']
        }

    def _extract_numbers(self, text: str) -> List[str]:
        """
        Extract numbers and measurements from text.

        Examples: "150 meters", "10.4 meters", "46 columns", "1.9 meters diameter"
        """
        # Match patterns like: "150 meters", "10.4m", "46 columns", "300 by 150"
        patterns = [
            r'\d+\.?\d*\s*(?:meters?|m|feet|ft|km|miles?)',  # Measurements
            r'\d+\.?\d*\s*(?:columns?|statues?|tons?|years?)',  # Quantities
            r'\d+\s*(?:by|×|x)\s*\d+',  # Dimensions
            r'\d+\.?\d*\s*(?:diameter|tall|high|wide|long)',  # Size descriptors
        ]

        numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            numbers.extend(matches)

        return numbers

    def _extract_key_terms(self, text: str) -> List[str]:
        """
        Extract key terms from feature text.

        Focus on: proper nouns, architectural terms, distinctive adjectives
        """
        # Common stopwords to exclude
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'has', 'have', 'had', 'each', 'one', 'now', 'above', 'side'
        }

        # Split and clean
        words = re.findall(r'\b[a-z]+\b', text.lower())

        # Filter: keep words that are meaningful
        key_terms = []
        for word in words:
            if len(word) >= 4 and word not in stopwords:
                key_terms.append(word)

        # Also extract capitalized proper nouns from original text
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        key_terms.extend([noun.lower() for noun in proper_nouns])

        return list(set(key_terms))  # Remove duplicates

    def _fuzzy_number_match(self, number_pattern: str, text: str) -> bool:
        """
        Check if a number/measurement appears in text with fuzzy matching.

        Examples:
        - "150 meters" matches "150m", "150 meter", "150-meter"
        - "10.4 meters" matches "10.4m", "10.4 meter"
        """
        # Extract the numeric part
        numeric_match = re.search(r'(\d+\.?\d*)', number_pattern)
        if not numeric_match:
            return False

        number = numeric_match.group(1)

        # Check if this number appears with similar context
        # Allow for variations: "150 meters", "150m", "150-meter"
        flexible_pattern = number + r'[\s\-]*(?:meters?|m|feet|ft|columns?|statues?)?'

        return bool(re.search(flexible_pattern, text))

    def _find_best_match(self, feature: str, transcript_lines: List[str]) -> Dict:
        """
        Find the text segment in transcript that best matches the feature.

        Args:
            feature: Feature text to find
            transcript_lines: Transcript split into lines

        Returns:
            {'text': matching_text, 'lines': [line_nums], 'similarity': score}
        """
        best_similarity = 0.0
        best_text = ""
        best_lines = []

        # Check each line
        for i, line in enumerate(transcript_lines):
            line_clean = line.lower().strip()
            if len(line_clean) < 10:  # Skip very short lines
                continue

            similarity = SequenceMatcher(None, feature, line_clean).ratio()

            if similarity > best_similarity:
                best_similarity = similarity
                best_text = line.strip()
                best_lines = [i + 1]  # 1-indexed line numbers

        # Also check 2-line windows for features that might span lines
        for i in range(len(transcript_lines) - 1):
            window = (transcript_lines[i] + " " + transcript_lines[i + 1]).lower().strip()
            similarity = SequenceMatcher(None, feature, window).ratio()

            if similarity > best_similarity:
                best_similarity = similarity
                best_text = transcript_lines[i].strip() + " " + transcript_lines[i + 1].strip()
                best_lines = [i + 1, i + 2]

        return {
            'text': best_text,
            'lines': best_lines,
            'similarity': best_similarity
        }

    def format_report(self, verification_result: Dict) -> str:
        """
        Format verification result as a human-readable report.

        Args:
            verification_result: Output from verify_coverage()

        Returns:
            Formatted string report
        """
        result = verification_result

        lines = []
        lines.append("=" * 60)
        lines.append("VERIFICATION REPORT")
        lines.append("=" * 60)
        lines.append(f"Coverage: {result['coverage']*100:.1f}%")
        lines.append(f"Features Found: {result['found_features']}/{result['total_features']}")

        if result['partial_features_count'] > 0:
            lines.append(f"Partially Found: {result['partial_features_count']}")

        lines.append(f"Status: {'✅ PASS' if result['passes_threshold'] else '❌ FAIL'}")
        lines.append("")

        # Detail each feature
        for status in result['feature_status']:
            feature_short = status['feature'][:60] + "..." if len(status['feature']) > 60 else status['feature']
            confidence_pct = status['confidence'] * 100

            if status['found'] and status['confidence'] >= 0.6:
                symbol = "✅"
            elif status['found'] and status['confidence'] >= 0.3:
                symbol = "⚠️ "
            else:
                symbol = "❌"

            lines.append(f"{symbol} [{confidence_pct:5.1f}%] {feature_short}")

            if status['matched_text']:
                matched_short = status['matched_text'][:80] + "..." if len(status['matched_text']) > 80 else status['matched_text']
                lines.append(f"          Found: \"{matched_short}\" (lines {status['line_numbers']})")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
