"""
Itinerary Optimizer Agent - Optimizes POI sequences for day-by-day trip planning.

This agent takes selected POIs and creates an optimized itinerary considering:
- Geographic proximity (minimize walking distance)
- Storytelling coherence (chronological/thematic flow)
- Opening hours and time constraints
- Visit durations and daily limits
"""

import math
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import yaml
from pathlib import Path
import sys

# Add parent directory to path for data module import
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.combo_ticket_loader import ComboTicketLoader


class ItineraryOptimizerAgent:
    """
    AI-assisted agent for optimizing POI sequences into day-by-day itineraries.

    Uses hybrid scoring:
    - Geographic distance (minimize walking)
    - Storytelling coherence (chronological/thematic flow)
    - Context-aware weighting (morning vs afternoon)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Itinerary Optimizer.

        Args:
            config: Application configuration dictionary
        """
        self.config = config
        self.walking_speed_kmh = 4.0  # Average walking speed in km/h
        self.ilp_optimizer = None  # Lazy load ILP optimizer
        # Note: max_hours_per_day is now calculated dynamically based on pace preference

    def optimize_itinerary(
        self,
        selected_pois: List[Dict[str, Any]],
        city: str,
        duration_days: int,
        start_time: str = "09:00",
        preferences: Dict[str, Any] = None,
        mode: str = 'simple',
        start_location: Optional[Dict] = None,
        end_location: Optional[Dict] = None,
        trip_start_date: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Optimize POI sequence into day-by-day itinerary.

        Args:
            selected_pois: List of POIs from POISelectorAgent (Starting POIs)
            city: City name
            duration_days: Number of days
            start_time: Daily start time (default "09:00")
            preferences: User preferences for optimization weights
            mode: Optimization mode - 'simple' (greedy+2-opt) or 'ilp' (OR-Tools)

        Returns:
            {
                'itinerary': [
                    {
                        'day': 1,
                        'pois': [...],
                        'total_hours': 7.5,
                        'total_walking_km': 3.2
                    }
                ],
                'optimization_scores': {
                    'distance_score': 0.85,
                    'coherence_score': 0.78,
                    'overall_score': 0.81
                },
                'constraints_violated': [],
                'solver_stats': {...}  # Only present if mode='ilp'
            }
        """
        preferences = preferences or {}

        # Calculate max hours per day based on pace (same logic as POI selector)
        pace_value = preferences.get('pace', 'normal')
        if pace_value == 'relaxed':
            max_hours_per_day = 6.0  # Relaxed: fewer POIs, more leisure time
        elif pace_value == 'packed':
            max_hours_per_day = 9.0  # Packed: maximize sightseeing
        else:  # normal
            max_hours_per_day = 7.5  # Normal: balanced

        print(f"  [OPTIMIZER] Pace: {pace_value} ({max_hours_per_day}h/day)", flush=True)
        print(f"  [OPTIMIZER] Loading metadata for {len(selected_pois)} POIs...", flush=True)

        # Load full POI metadata with coordinates and hours
        enriched_pois = self._enrich_pois_with_metadata(selected_pois, city)

        # Build distance matrix
        print(f"  [OPTIMIZER] Calculating distances...", flush=True)
        distance_matrix = self._build_distance_matrix(enriched_pois)

        # Calculate storytelling coherence scores
        print(f"  [OPTIMIZER] Analyzing storytelling coherence...", flush=True)
        coherence_scores = self._calculate_coherence_scores(enriched_pois)

        # Optimize sequence based on mode
        optimization_scores = {}
        solver_stats = None

        if mode == 'ilp' and self._is_ilp_available():
            # ILP mode - use OR-Tools CP-SAT solver
            print(f"  [OPTIMIZER] Using ILP optimization mode...", flush=True)

            if not self.ilp_optimizer:
                from .ilp_optimizer import ILPOptimizer
                self.ilp_optimizer = ILPOptimizer(self.config)

            ilp_result = self.ilp_optimizer.optimize_sequence(
                enriched_pois,
                distance_matrix,
                coherence_scores,
                duration_days,
                preferences,
                start_location=start_location,
                end_location=end_location,
                trip_start_date=trip_start_date
            )

            optimized_sequence = ilp_result['sequence']
            day_assignments = ilp_result['day_assignments']
            optimization_scores = ilp_result['scores']
            solver_stats = ilp_result.get('solver_stats', {})

            # Schedule into days using ILP day assignments
            print(f"  [OPTIMIZER] Scheduling into {duration_days} days...", flush=True)
            itinerary = self._schedule_days_with_assignments(
                optimized_sequence,
                day_assignments,
                duration_days,
                start_time,
                distance_matrix
            )

        else:
            # Simple mode - use greedy + 2-opt
            if mode == 'ilp':
                print(f"  [OPTIMIZER] Warning: ILP mode requested but not available, using simple mode", flush=True)
            else:
                print(f"  [OPTIMIZER] Using simple optimization mode...", flush=True)

            optimized_sequence = self._optimize_sequence(
                enriched_pois,
                distance_matrix,
                coherence_scores,
                preferences
            )

            # Schedule into days
            print(f"  [OPTIMIZER] Scheduling into {duration_days} days...", flush=True)
            itinerary = self._schedule_days(
                optimized_sequence,
                duration_days,
                start_time,
                distance_matrix,
                max_hours_per_day
            )

        # Enforce duration_days limit as safety net
        if len(itinerary) > duration_days:
            print(f"  [OPTIMIZER] Warning: Generated {len(itinerary)} days but only {duration_days} requested", flush=True)
            print(f"  [OPTIMIZER] Trimming to first {duration_days} days and re-optimizing...", flush=True)

            # Calculate how many POIs fit in duration_days
            pois_to_keep = sum(len(day['pois']) for day in itinerary[:duration_days])

            # Take the first pois_to_keep POIs from optimized_sequence
            # (they're already optimally ordered, so we keep the best sequence)
            trimmed_sequence = optimized_sequence[:pois_to_keep]

            # Re-schedule with correct number of POIs
            itinerary = self._schedule_days(
                trimmed_sequence,
                duration_days,
                start_time,
                distance_matrix,
                max_hours_per_day
            )

            print(f"  ✓ Re-optimized to {len(itinerary)} days with {pois_to_keep} POIs", flush=True)

        # Validate constraints
        violations = self._validate_constraints(itinerary, max_hours_per_day)

        # Calculate final scores (use ILP scores if available)
        if optimization_scores:
            scores = optimization_scores
        else:
            scores = self._calculate_scores(
                itinerary,
                distance_matrix,
                coherence_scores,
                optimized_sequence
            )

        print(f"  ✓ Optimized itinerary created", flush=True)
        print(f"  ✓ Distance score: {scores['distance_score']:.2f}, Coherence: {scores['coherence_score']:.2f}", flush=True)
        if solver_stats:
            print(f"  ✓ Solver: {solver_stats.get('status', 'N/A')} in {solver_stats.get('solve_time', 0)}s", flush=True)

        result = {
            'itinerary': itinerary,
            'optimization_scores': scores,
            'constraints_violated': violations,
            'metadata': {
                'city': city,
                'duration_days': duration_days,
                'total_pois': len(selected_pois),
                'start_time': start_time,
                'optimization_mode': mode
            }
        }

        if solver_stats:
            result['solver_stats'] = solver_stats

        return result

    def _enrich_pois_with_metadata(
        self,
        selected_pois: List[Dict[str, Any]],
        city: str
    ) -> List[Dict[str, Any]]:
        """
        Load full POI metadata including coordinates and opening hours.

        Args:
            selected_pois: POIs from selector (may have minimal info)
            city: City name

        Returns:
            Enriched POIs with full metadata and combo ticket groups
        """
        poi_research_dir = Path("poi_research") / city
        enriched = []

        for poi in selected_pois:
            poi_name = poi.get('poi', '')

            # Find matching YAML file
            yaml_files = list(poi_research_dir.glob(f"{poi_name.replace(' ', '_')}.yaml"))
            if not yaml_files:
                # Try alternate naming
                yaml_files = list(poi_research_dir.glob(f"{poi_name.replace(' ', '-')}.yaml"))

            if yaml_files:
                with open(yaml_files[0], 'r', encoding='utf-8') as f:
                    full_data = yaml.safe_load(f)

                # Merge selected POI data with full metadata
                enriched_poi = {
                    **poi,  # Keep selector data (reason, suggested_day, etc.)
                    'coordinates': full_data.get('poi', {}).get('metadata', {}).get('coordinates', {}),
                    'operation_hours': full_data.get('poi', {}).get('metadata', {}).get('operation_hours', {}),
                    'visit_info': full_data.get('poi', {}).get('metadata', {}).get('visit_info', {}),
                    'period': full_data.get('poi', {}).get('basic_info', {}).get('period', ''),
                    'date_built': full_data.get('poi', {}).get('basic_info', {}).get('date_built', '')
                }

                # Set default visit duration if not specified
                if 'estimated_hours' not in enriched_poi:
                    typical_minutes = enriched_poi.get('visit_info', {}).get('typical_duration_minutes', 120)
                    enriched_poi['estimated_hours'] = typical_minutes / 60.0

                enriched.append(enriched_poi)
            else:
                # No metadata found, use as-is with defaults
                print(f"  Warning: No metadata found for {poi_name}, using defaults", flush=True)
                poi_copy = poi.copy()
                if 'estimated_hours' not in poi_copy:
                    poi_copy['estimated_hours'] = 2.0
                enriched.append(poi_copy)

        # Enrich with combo ticket data
        combo_loader = ComboTicketLoader()
        combo_tickets = combo_loader.load_city_combo_tickets(city)
        enriched = combo_loader.enrich_pois_with_combo_tickets(enriched, combo_tickets)

        return enriched

    def _build_distance_matrix(
        self,
        pois: List[Dict[str, Any]]
    ) -> Dict[Tuple[str, str], float]:
        """
        Calculate distances between all POI pairs using Haversine formula.

        Args:
            pois: List of POIs with coordinates

        Returns:
            Distance matrix as dict of (poi1, poi2) -> distance_km
        """
        matrix = {}

        for i, poi1 in enumerate(pois):
            for j, poi2 in enumerate(pois):
                if i == j:
                    matrix[(poi1['poi'], poi2['poi'])] = 0.0
                else:
                    coords1 = poi1.get('coordinates', {})
                    coords2 = poi2.get('coordinates', {})

                    if coords1.get('latitude') and coords2.get('latitude'):
                        distance = self._haversine_distance(
                            coords1['latitude'],
                            coords1['longitude'],
                            coords2['latitude'],
                            coords2['longitude']
                        )
                        matrix[(poi1['poi'], poi2['poi'])] = distance
                    else:
                        # No coordinates, assume moderate distance
                        matrix[(poi1['poi'], poi2['poi'])] = 2.0  # 2km default

        return matrix

    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate distance between two coordinates using Haversine formula.

        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)

        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def _calculate_coherence_scores(
        self,
        pois: List[Dict[str, Any]]
    ) -> Dict[Tuple[str, str], float]:
        """
        Calculate storytelling coherence between POI pairs.

        Considers:
        - Chronological order (earlier → later in history)
        - Thematic similarity (same period, related people/events)

        Args:
            pois: List of POIs

        Returns:
            Coherence matrix as dict of (poi1, poi2) -> score (0.0-1.0)
        """
        scores = {}

        for i, poi1 in enumerate(pois):
            for j, poi2 in enumerate(pois):
                if i == j:
                    scores[(poi1['poi'], poi2['poi'])] = 1.0
                else:
                    score = self._calculate_pair_coherence(poi1, poi2)
                    scores[(poi1['poi'], poi2['poi'])] = score

        return scores

    def _calculate_pair_coherence(
        self,
        poi1: Dict[str, Any],
        poi2: Dict[str, Any]
    ) -> float:
        """
        Calculate coherence score between two POIs.

        Returns:
            Score 0.0-1.0 (higher = better storytelling flow)
        """
        score = 0.0

        # 1. Chronological order bonus (40%)
        period1 = poi1.get('period', '')
        period2 = poi2.get('period', '')

        chronological_order = self._get_chronological_order(period1, period2)
        if chronological_order > 0:  # poi1 comes before poi2
            score += 0.4
        elif chronological_order == 0:  # same period
            score += 0.3

        # 2. Same period bonus (30%)
        if period1 and period2 and period1 == period2:
            score += 0.3

        # 3. Date proximity (30%)
        date1 = self._extract_year(poi1.get('date_built', ''))
        date2 = self._extract_year(poi2.get('date_built', ''))

        if date1 and date2:
            year_diff = abs(date1 - date2)
            if year_diff < 50:
                score += 0.3
            elif year_diff < 200:
                score += 0.2
            elif year_diff < 500:
                score += 0.1

        return min(score, 1.0)

    def _get_chronological_order(self, period1: str, period2: str) -> int:
        """
        Compare two historical periods.

        Returns:
            -1 if period1 < period2, 0 if equal, 1 if period1 > period2
        """
        period_order = {
            'Classical Greece': 1,
            'Hellenistic': 2,
            'Roman Empire': 3,
            'Byzantine': 4,
            'Ottoman': 5,
            'Modern': 6
        }

        order1 = period_order.get(period1, 0)
        order2 = period_order.get(period2, 0)

        if order1 < order2:
            return 1  # poi1 comes before poi2
        elif order1 > order2:
            return -1
        else:
            return 0

    def _extract_year(self, date_str: str) -> int:
        """
        Extract year from date string.

        Examples: "447-432 BC", "131-132 AD", "1687"

        Returns:
            Year as integer (negative for BC), or None if not parseable
        """
        if not date_str:
            return None

        # Handle BC dates
        if 'BC' in date_str.upper():
            # Extract first number
            import re
            match = re.search(r'(\d+)', date_str)
            if match:
                return -int(match.group(1))

        # Handle AD dates
        if 'AD' in date_str.upper():
            import re
            match = re.search(r'(\d+)', date_str)
            if match:
                return int(match.group(1))

        # Handle plain years
        if date_str.isdigit():
            return int(date_str)

        # Handle ranges (take midpoint)
        import re
        match = re.search(r'(\d+)-(\d+)', date_str)
        if match:
            year1, year2 = int(match.group(1)), int(match.group(2))
            return (year1 + year2) // 2

        return None

    def _optimize_sequence(
        self,
        pois: List[Dict[str, Any]],
        distance_matrix: Dict[Tuple[str, str], float],
        coherence_scores: Dict[Tuple[str, str], float],
        preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Optimize POI sequence using hybrid scoring.

        Uses greedy nearest-neighbor algorithm with hybrid score:
        - Distance (minimize walking)
        - Coherence (maximize storytelling)
        - Context-aware weights

        Args:
            pois: List of POIs
            distance_matrix: Distances between POIs
            coherence_scores: Coherence scores between POIs
            preferences: User preferences

        Returns:
            Optimized POI sequence
        """
        if not pois:
            return []

        # Get weights from preferences (default: balanced)
        distance_weight = preferences.get('distance_weight', 0.5)
        coherence_weight = preferences.get('coherence_weight', 0.5)

        # Start with highest priority POI or first POI
        remaining = pois.copy()

        # Find starting POI (highest priority or first in list)
        start_poi = remaining[0]
        for poi in remaining:
            if poi.get('priority') == 'high':
                start_poi = poi
                break

        sequence = [start_poi]
        remaining.remove(start_poi)

        # Greedy algorithm: always pick best next POI
        while remaining:
            current = sequence[-1]

            best_poi = None
            best_score = -1

            for candidate in remaining:
                # Calculate hybrid score
                distance = distance_matrix[(current['poi'], candidate['poi'])]
                coherence = coherence_scores[(current['poi'], candidate['poi'])]

                # Normalize distance (shorter = higher score)
                # Assume max useful distance is 5km
                distance_score = max(0, 1 - (distance / 5.0))

                # Weighted hybrid score
                hybrid_score = (distance_weight * distance_score +
                               coherence_weight * coherence)

                if hybrid_score > best_score:
                    best_score = hybrid_score
                    best_poi = candidate

            sequence.append(best_poi)
            remaining.remove(best_poi)

        return sequence

    def _schedule_days(
        self,
        sequence: List[Dict[str, Any]],
        duration_days: int,
        start_time: str,
        distance_matrix: Dict[Tuple[str, str], float],
        max_hours_per_day: float = 7.5
    ) -> List[Dict[str, Any]]:
        """
        Schedule POIs into day-by-day itinerary.

        Args:
            sequence: Optimized POI sequence
            duration_days: Number of days
            start_time: Daily start time (e.g., "09:00")
            distance_matrix: Distances for travel time calculation
            max_hours_per_day: Maximum hours per day based on pace

        Returns:
            List of day schedules
        """
        itinerary = []

        # Parse start time
        hour, minute = map(int, start_time.split(':'))

        day_num = 1
        current_day_pois = []
        current_day_hours = 0.0
        current_day_walking = 0.0

        for i, poi in enumerate(sequence):
            visit_hours = poi.get('estimated_hours', 2.0)

            # Calculate travel time from previous POI
            travel_hours = 0.0
            if current_day_pois:
                prev_poi = current_day_pois[-1]
                distance_km = distance_matrix[(prev_poi['poi'], poi['poi'])]
                travel_hours = distance_km / self.walking_speed_kmh
                current_day_walking += distance_km

            # Check if this POI fits in current day
            total_hours_needed = visit_hours + travel_hours

            if current_day_hours + total_hours_needed <= max_hours_per_day:
                # Fits in current day
                current_day_pois.append(poi)
                current_day_hours += total_hours_needed
            else:
                # Start new day
                if current_day_pois:
                    itinerary.append({
                        'day': day_num,
                        'pois': current_day_pois,
                        'total_hours': round(current_day_hours, 1),
                        'total_walking_km': round(current_day_walking, 2),
                        'start_time': start_time
                    })

                day_num += 1
                current_day_pois = [poi]
                current_day_hours = visit_hours
                current_day_walking = 0.0

        # Add final day
        if current_day_pois:
            itinerary.append({
                'day': day_num,
                'pois': current_day_pois,
                'total_hours': round(current_day_hours, 1),
                'total_walking_km': round(current_day_walking, 2),
                'start_time': start_time
            })

        return itinerary

    def _schedule_days_with_assignments(
        self,
        sequence: List[Dict[str, Any]],
        day_assignments: Dict[str, int],
        duration_days: int,
        start_time: str,
        distance_matrix: Dict[Tuple[str, str], float]
    ) -> List[Dict[str, Any]]:
        """
        Schedule POIs into days using ILP day assignments.

        Args:
            sequence: Optimized POI sequence
            day_assignments: POI name -> day number mapping from ILP
            duration_days: Number of days
            start_time: Daily start time
            distance_matrix: Distances for travel time calculation

        Returns:
            List of day schedules
        """
        # Group POIs by assigned day
        days_pois = [[] for _ in range(duration_days)]

        for poi in sequence:
            day = day_assignments.get(poi['poi'], 0)
            if day < duration_days:
                days_pois[day].append(poi)

        # Build itinerary
        itinerary = []
        for day_num, day_pois in enumerate(days_pois):
            if not day_pois:
                continue

            total_hours = 0.0
            total_walking = 0.0

            for i, poi in enumerate(day_pois):
                visit_hours = poi.get('estimated_hours', 2.0)
                total_hours += visit_hours

                # Add travel time
                if i > 0:
                    prev_poi = day_pois[i - 1]
                    distance_km = distance_matrix.get((prev_poi['poi'], poi['poi']), 0)
                    travel_hours = distance_km / self.walking_speed_kmh
                    total_hours += travel_hours
                    total_walking += distance_km

            itinerary.append({
                'day': day_num + 1,
                'pois': day_pois,
                'total_hours': round(total_hours, 1),
                'total_walking_km': round(total_walking, 2),
                'start_time': start_time
            })

        return itinerary

    def _is_ilp_available(self) -> bool:
        """
        Check if ILP optimization is available.

        Returns:
            True if OR-Tools is installed and ILP is enabled in config
        """
        try:
            import ortools
            ilp_enabled = self.config.get('optimization', {}).get('ilp_enabled', False)
            return ilp_enabled
        except ImportError:
            return False

    def _validate_constraints(
        self,
        itinerary: List[Dict[str, Any]],
        max_hours_per_day: float = 7.5
    ) -> List[str]:
        """
        Validate itinerary against constraints.

        Args:
            itinerary: Day-by-day itinerary
            max_hours_per_day: Maximum hours per day based on pace

        Returns:
            List of constraint violation messages
        """
        violations = []

        for day in itinerary:
            # Check hours per day
            if day['total_hours'] > max_hours_per_day:
                violations.append(
                    f"Day {day['day']}: Exceeds {max_hours_per_day}h limit "
                    f"({day['total_hours']}h scheduled)"
                )

            # Check excessive walking
            if day['total_walking_km'] > 5.0:
                violations.append(
                    f"Day {day['day']}: Excessive walking "
                    f"({day['total_walking_km']}km, recommend < 5km)"
                )

        return violations

    def _calculate_scores(
        self,
        itinerary: List[Dict[str, Any]],
        distance_matrix: Dict[Tuple[str, str], float],
        coherence_scores: Dict[Tuple[str, str], float],
        sequence: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Calculate optimization quality scores.

        Args:
            itinerary: Day-by-day itinerary
            distance_matrix: Distances
            coherence_scores: Coherence scores
            sequence: POI sequence

        Returns:
            Score dictionary
        """
        # Distance score (lower total distance = higher score)
        total_distance = sum(day['total_walking_km'] for day in itinerary)
        max_possible_distance = len(sequence) * 3.0  # Assume avg 3km between POIs
        distance_score = max(0, 1 - (total_distance / max_possible_distance))

        # Coherence score (average coherence between consecutive POIs)
        coherence_sum = 0.0
        coherence_count = 0

        for i in range(len(sequence) - 1):
            poi1 = sequence[i]
            poi2 = sequence[i + 1]
            coherence_sum += coherence_scores[(poi1['poi'], poi2['poi'])]
            coherence_count += 1

        coherence_score = coherence_sum / coherence_count if coherence_count > 0 else 0.5

        # Overall score (balanced)
        overall_score = (distance_score + coherence_score) / 2

        return {
            'distance_score': round(distance_score, 2),
            'coherence_score': round(coherence_score, 2),
            'overall_score': round(overall_score, 2),
            'total_distance_km': round(total_distance, 2)
        }
