"""
Itinerary Reoptimizer - Smart re-optimization for POI replacements.

Implements 3-tier optimization strategy:
- Tier 1: Local enumeration (single POI, small day)
- Tier 2: Greedy + 2-opt on affected days
- Tier 3: Full tour re-optimization

Uses distance caching to minimize computation.
"""

import math
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import yaml
from trip_planner.itinerary_optimizer import ItineraryOptimizerAgent


class ItineraryReoptimizer:
    """
    Handles re-optimization of existing itineraries after POI replacements.

    Supports three optimization tiers:
    - Local swap: Position optimization within a single day
    - Day-level: Re-optimize specific days only
    - Full tour: Complete re-optimization
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.optimizer = ItineraryOptimizerAgent(config)
        self.walking_speed_kmh = 4.0  # Average walking speed
        self.max_hours_per_day = 8  # Maximum activity hours per day

    def reoptimize(
        self,
        tour_data: Dict,
        replacements: List[Dict],  # [{ original_poi, replacement_poi, day }, ...]
        city: str,
        preferences: Dict = None
    ) -> Dict:
        """
        Main entry point for re-optimization.

        Args:
            tour_data: Tour data dictionary
            replacements: List of replacement dicts
            city: City name
            preferences: User preferences for optimization

        Returns:
            {
                'itinerary': [...],  # Updated itinerary
                'optimization_scores': {...},
                'strategy_used': 'local_swap' | 'day_level' | 'full_tour',
                'distance_cache': {...}  # Updated distance cache
            }
        """
        preferences = preferences or {}

        # Initialize or update distance cache
        self._update_distance_cache(tour_data, replacements, city)

        # Determine optimization strategy
        strategy = self._determine_strategy(tour_data, replacements)

        print(f"  [REOPTIMIZER] Using strategy: {strategy}", flush=True)

        if strategy == 'local_swap':
            return self._local_swap_optimization(tour_data, replacements[0], city)
        elif strategy == 'day_level':
            return self._day_level_optimization(tour_data, replacements, city, preferences)
        else:  # 'full_tour'
            return self._full_tour_optimization(tour_data, replacements, city, preferences)

    def _determine_strategy(self, tour_data: Dict, replacements: List[Dict]) -> str:
        """
        Decide which optimization strategy to use.

        Args:
            tour_data: Tour data dictionary
            replacements: List of replacement dicts

        Returns:
            'local_swap' | 'day_level' | 'full_tour'
        """
        if len(replacements) == 1:
            # Single replacement - check day size
            day_num = replacements[0]['day']

            # Find the day
            for day in tour_data['itinerary']:
                if day['day'] == day_num:
                    # If day has <= 5 POIs, use local swap
                    if len(day['pois']) <= 5:
                        return 'local_swap'
                    break

        # Check if all replacements are on same day or adjacent days
        affected_days = set(r['day'] for r in replacements)

        if len(affected_days) <= 2:
            # 1-2 days affected - use day-level optimization
            return 'day_level'
        else:
            # Multiple days - full re-optimization
            return 'full_tour'

    def _update_distance_cache(
        self,
        tour_data: Dict,
        replacements: List[Dict],
        city: str
    ):
        """
        Update distance cache with new POIs.

        Args:
            tour_data: Tour data dictionary
            replacements: List of replacement dicts
            city: City name
        """
        if 'distance_cache' not in tour_data:
            tour_data['distance_cache'] = {}

        cache = tour_data['distance_cache']

        # Get all POIs currently in tour
        all_pois = set()
        for day in tour_data['itinerary']:
            for poi_obj in day['pois']:
                all_pois.add(poi_obj['poi'])

        # Add replacement POIs that need new distance calculations
        for repl in replacements:
            new_poi = repl['replacement_poi']

            # Skip if already cached
            if any(new_poi in key for key in cache.keys()):
                continue

            # Load metadata for new POI
            metadata = self._load_poi_metadata(city, new_poi)
            new_coords = metadata.get('coordinates', {})

            if not new_coords.get('latitude') or not new_coords.get('longitude'):
                print(f"  Warning: No coordinates for {new_poi}, using default distances", flush=True)
                # Use default distance if no coordinates
                for existing_poi in all_pois:
                    if existing_poi != new_poi:
                        cache[(new_poi, existing_poi)] = 2.0  # 2km default
                        cache[(existing_poi, new_poi)] = 2.0
                continue

            # Calculate distances to all existing POIs
            for existing_poi in all_pois:
                if existing_poi == new_poi:
                    cache[(new_poi, new_poi)] = 0.0
                    continue

                # Load coords for existing POI
                existing_metadata = self._load_poi_metadata(city, existing_poi)
                existing_coords = existing_metadata.get('coordinates', {})

                if existing_coords.get('latitude') and existing_coords.get('longitude'):
                    distance = self.optimizer._haversine_distance(
                        new_coords['latitude'],
                        new_coords['longitude'],
                        existing_coords['latitude'],
                        existing_coords['longitude']
                    )
                    cache[(new_poi, existing_poi)] = distance
                    cache[(existing_poi, new_poi)] = distance
                else:
                    # No coordinates for existing POI
                    cache[(new_poi, existing_poi)] = 2.0
                    cache[(existing_poi, new_poi)] = 2.0

        print(f"  [CACHE] Updated distance cache, now has {len(cache)} entries", flush=True)

    def _load_poi_metadata(self, city: str, poi_name: str) -> Dict:
        """
        Load POI metadata from research YAML file.

        Args:
            city: City name
            poi_name: POI name

        Returns:
            Dict with coordinates, operation_hours, visit_info, etc.
        """
        from utils import load_poi_metadata_from_research
        return load_poi_metadata_from_research(city, poi_name)

    def _local_swap_optimization(
        self,
        tour_data: Dict,
        replacement: Dict,
        city: str
    ) -> Dict:
        """
        Tier 1: Try all positions within the same day.

        Algorithm:
        1. Find the day with the replacement
        2. Try inserting replacement POI at each position
        3. Calculate hybrid score for each position
        4. Pick best position

        Args:
            tour_data: Tour data dictionary
            replacement: Single replacement dict
            city: City name

        Returns:
            Result dict with itinerary, scores, strategy
        """
        print(f"  [TIER 1] Local swap optimization for day {replacement['day']}", flush=True)

        day_num = replacement['day']
        original_poi = replacement['original_poi']
        replacement_poi = replacement['replacement_poi']

        # Find the day
        target_day = None
        for day in tour_data['itinerary']:
            if day['day'] == day_num:
                target_day = day
                break

        if not target_day:
            # Fallback to day-level
            print(f"  Warning: Day {day_num} not found, falling back to day-level", flush=True)
            return self._day_level_optimization(tour_data, [replacement], city, {})

        # Load replacement POI data
        replacement_metadata = self._load_poi_metadata(city, replacement_poi)

        # Find original POI index
        original_idx = None
        for i, poi_obj in enumerate(target_day['pois']):
            if poi_obj['poi'] == original_poi:
                original_idx = i
                break

        if original_idx is None:
            print(f"  Warning: Original POI {original_poi} not found in day {day_num}", flush=True)
            return self._day_level_optimization(tour_data, [replacement], city, {})

        # Create replacement POI object
        replacement_poi_obj = {
            'poi': replacement_poi,
            'reason': f'Replacement for {original_poi}',
            'suggested_day': day_num,
            'estimated_hours': replacement_metadata.get('estimated_hours', 2.0),
            'priority': 'medium',
            'coordinates': replacement_metadata.get('coordinates', {}),
            'operation_hours': replacement_metadata.get('operation_hours', {}),
            'visit_info': replacement_metadata.get('visit_info', {}),
            'period': replacement_metadata.get('period'),
            'date_built': replacement_metadata.get('date_built')
        }

        # Try all positions (simple: just swap in place for now)
        # In a more sophisticated version, we'd try all positions
        pois_on_day = target_day['pois'].copy()
        pois_on_day[original_idx] = replacement_poi_obj

        # Recalculate day metrics
        target_day['pois'] = pois_on_day
        self._recalculate_day_metrics(target_day, tour_data['distance_cache'])

        # Calculate overall scores
        scores = self._calculate_overall_scores(tour_data)

        print(f"  ✓ Local swap complete. Score: {scores['overall_score']:.2f}", flush=True)

        return {
            'itinerary': tour_data['itinerary'],
            'optimization_scores': scores,
            'strategy_used': 'local_swap',
            'distance_cache': tour_data['distance_cache']
        }

    def _day_level_optimization(
        self,
        tour_data: Dict,
        replacements: List[Dict],
        city: str,
        preferences: Dict
    ) -> Dict:
        """
        Tier 2: Re-optimize only affected days using greedy + 2-opt.

        Algorithm:
        1. Identify affected days
        2. Extract POIs for those days
        3. Run greedy nearest-neighbor on those POIs
        4. Apply 2-opt improvement
        5. Re-schedule those days
        6. Keep other days unchanged

        Args:
            tour_data: Tour data dictionary
            replacements: List of replacement dicts
            city: City name
            preferences: User preferences

        Returns:
            Result dict with itinerary, scores, strategy
        """
        affected_days_nums = set(r['day'] for r in replacements)
        print(f"  [TIER 2] Day-level optimization for days: {sorted(affected_days_nums)}", flush=True)

        # Apply all replacements first
        replacement_map = {r['original_poi']: r['replacement_poi'] for r in replacements}

        for day in tour_data['itinerary']:
            if day['day'] in affected_days_nums:
                for i, poi_obj in enumerate(day['pois']):
                    if poi_obj['poi'] in replacement_map:
                        replacement_poi = replacement_map[poi_obj['poi']]

                        # Load replacement metadata
                        replacement_metadata = self._load_poi_metadata(city, replacement_poi)

                        # Update POI
                        day['pois'][i] = {
                            'poi': replacement_poi,
                            'reason': f'Replacement for {poi_obj["poi"]}',
                            'suggested_day': day['day'],
                            'estimated_hours': replacement_metadata.get('estimated_hours', 2.0),
                            'priority': poi_obj.get('priority', 'medium'),
                            'coordinates': replacement_metadata.get('coordinates', {}),
                            'operation_hours': replacement_metadata.get('operation_hours', {}),
                            'visit_info': replacement_metadata.get('visit_info', {}),
                            'period': replacement_metadata.get('period'),
                            'date_built': replacement_metadata.get('date_built')
                        }

        # Re-optimize each affected day
        for day in tour_data['itinerary']:
            if day['day'] in affected_days_nums:
                # Run greedy + 2-opt on this day's POIs
                optimized_pois = self._optimize_poi_sequence(
                    day['pois'],
                    tour_data['distance_cache'],
                    preferences
                )

                # Apply 2-opt improvement
                optimized_pois = self._two_opt_improve(
                    optimized_pois,
                    tour_data['distance_cache']
                )

                # Update day
                day['pois'] = optimized_pois
                self._recalculate_day_metrics(day, tour_data['distance_cache'])

        # Calculate overall scores
        scores = self._calculate_overall_scores(tour_data)

        print(f"  ✓ Day-level optimization complete. Score: {scores['overall_score']:.2f}", flush=True)

        return {
            'itinerary': tour_data['itinerary'],
            'optimization_scores': scores,
            'strategy_used': 'day_level',
            'distance_cache': tour_data['distance_cache']
        }

    def _full_tour_optimization(
        self,
        tour_data: Dict,
        replacements: List[Dict],
        city: str,
        preferences: Dict
    ) -> Dict:
        """
        Tier 3: Full re-optimization using existing ItineraryOptimizerAgent.

        This is essentially the same as generating a new tour.

        Args:
            tour_data: Tour data dictionary
            replacements: List of replacement dicts
            city: City name
            preferences: User preferences

        Returns:
            Result dict with itinerary, scores, strategy
        """
        print(f"  [TIER 3] Full tour re-optimization", flush=True)

        # Apply all replacements to build new POI list
        replacement_map = {r['original_poi']: r['replacement_poi'] for r in replacements}

        all_pois = []
        for day in tour_data['itinerary']:
            for poi_obj in day['pois']:
                poi_name = poi_obj['poi']

                if poi_name in replacement_map:
                    # Replace with new POI
                    replacement_poi = replacement_map[poi_name]
                    replacement_metadata = self._load_poi_metadata(city, replacement_poi)

                    all_pois.append({
                        'poi': replacement_poi,
                        'reason': f'Replacement for {poi_name}',
                        'suggested_day': day['day'],
                        'estimated_hours': replacement_metadata.get('estimated_hours', 2.0),
                        'priority': poi_obj.get('priority', 'medium'),
                        'coordinates': replacement_metadata.get('coordinates', {}),
                        'operation_hours': replacement_metadata.get('operation_hours', {}),
                        'visit_info': replacement_metadata.get('visit_info', {}),
                        'period': replacement_metadata.get('period'),
                        'date_built': replacement_metadata.get('date_built')
                    })
                else:
                    # Keep existing POI
                    all_pois.append(poi_obj)

        # Run full optimization
        duration_days = len(tour_data['itinerary'])
        start_time = tour_data['itinerary'][0].get('start_time', '09:00') if tour_data['itinerary'] else '09:00'

        result = self.optimizer.optimize_itinerary(
            selected_pois=all_pois,
            city=city,
            duration_days=duration_days,
            start_time=start_time,
            preferences=preferences
        )

        # Update distance cache with newly calculated distances
        # The optimizer doesn't expose distance matrix, so we'll rebuild it
        tour_data['distance_cache'] = {}
        self._update_distance_cache(tour_data, [], city)

        print(f"  ✓ Full tour optimization complete. Score: {result['optimization_scores']['overall_score']:.2f}", flush=True)

        return {
            'itinerary': result['itinerary'],
            'optimization_scores': result['optimization_scores'],
            'strategy_used': 'full_tour',
            'distance_cache': tour_data.get('distance_cache', {})
        }

    def _optimize_poi_sequence(
        self,
        pois: List[Dict],
        distance_cache: Dict,
        preferences: Dict
    ) -> List[Dict]:
        """
        Greedy nearest-neighbor optimization for POI sequence.

        Args:
            pois: List of POI objects
            distance_cache: Distance cache
            preferences: User preferences

        Returns:
            Optimized POI sequence
        """
        if not pois:
            return []

        distance_weight = preferences.get('distance_weight', 0.5)
        coherence_weight = preferences.get('coherence_weight', 0.5)

        # Start with first POI
        remaining = pois.copy()
        sequence = [remaining.pop(0)]

        # Greedy algorithm
        while remaining:
            current = sequence[-1]
            best_poi = None
            best_score = -1

            for candidate in remaining:
                # Get distance from cache or calculate
                cache_key = (current['poi'], candidate['poi'])
                if cache_key in distance_cache:
                    distance = distance_cache[cache_key]
                else:
                    # Fallback to default
                    distance = 2.0

                # Distance score (shorter = better)
                distance_score = max(0, 1 - (distance / 5.0))

                # Simple coherence (would use full coherence calculation in production)
                coherence = 0.5  # Default neutral score

                # Hybrid score
                hybrid_score = distance_weight * distance_score + coherence_weight * coherence

                if hybrid_score > best_score:
                    best_score = hybrid_score
                    best_poi = candidate

            sequence.append(best_poi)
            remaining.remove(best_poi)

        return sequence

    def _two_opt_improve(
        self,
        sequence: List[Dict],
        distance_cache: Dict
    ) -> List[Dict]:
        """
        Apply 2-opt local search to improve sequence.

        Args:
            sequence: POI sequence
            distance_cache: Distance cache

        Returns:
            Improved POI sequence
        """
        if len(sequence) <= 2:
            return sequence

        improved = True
        max_iterations = 10
        iteration = 0

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1

            for i in range(len(sequence) - 1):
                for j in range(i + 2, len(sequence)):
                    # Try reversing segment [i+1:j+1]
                    new_sequence = (
                        sequence[:i+1] +
                        sequence[i+1:j+1][::-1] +
                        sequence[j+1:]
                    )

                    # Compare total distance
                    old_dist = self._calculate_sequence_distance(sequence, distance_cache)
                    new_dist = self._calculate_sequence_distance(new_sequence, distance_cache)

                    if new_dist < old_dist:
                        sequence = new_sequence
                        improved = True
                        break

                if improved:
                    break

        return sequence

    def _calculate_sequence_distance(
        self,
        sequence: List[Dict],
        distance_cache: Dict
    ) -> float:
        """
        Calculate total distance for a POI sequence.

        Args:
            sequence: POI sequence
            distance_cache: Distance cache

        Returns:
            Total distance in km
        """
        total = 0.0
        for i in range(len(sequence) - 1):
            poi1 = sequence[i]['poi']
            poi2 = sequence[i + 1]['poi']

            cache_key = (poi1, poi2)
            if cache_key in distance_cache:
                total += distance_cache[cache_key]
            else:
                total += 2.0  # Default

        return total

    def _recalculate_day_metrics(
        self,
        day: Dict,
        distance_cache: Dict
    ):
        """
        Recalculate day metrics (total hours, walking distance).

        Args:
            day: Day dictionary
            distance_cache: Distance cache
        """
        total_hours = 0.0
        total_walking = 0.0

        for i, poi_obj in enumerate(day['pois']):
            # Add visit time
            total_hours += poi_obj.get('estimated_hours', 2.0)

            # Add walking time to next POI
            if i < len(day['pois']) - 1:
                next_poi = day['pois'][i + 1]

                cache_key = (poi_obj['poi'], next_poi['poi'])
                if cache_key in distance_cache:
                    distance = distance_cache[cache_key]
                else:
                    distance = 2.0  # Default

                walking_time = distance / self.walking_speed_kmh

                total_hours += walking_time
                total_walking += distance

                # Update POI object with walking info
                poi_obj['distance_to_next_km'] = round(distance, 2)
                poi_obj['walking_time_to_next'] = f"{int(walking_time * 60)}min"

        day['total_hours'] = round(total_hours, 1)
        day['total_walking_km'] = round(total_walking, 2)

    def _calculate_overall_scores(
        self,
        tour_data: Dict
    ) -> Dict[str, float]:
        """
        Calculate optimization quality scores.

        Args:
            tour_data: Tour data dictionary

        Returns:
            Score dictionary
        """
        # Distance score (lower total distance = higher score)
        total_distance = sum(
            day.get('total_walking_km', 0)
            for day in tour_data['itinerary']
        )

        # Count total POIs
        total_pois = sum(
            len(day['pois'])
            for day in tour_data['itinerary']
        )

        max_possible_distance = total_pois * 3.0  # Assume avg 3km between POIs
        distance_score = max(0, 1 - (total_distance / max_possible_distance))

        # Coherence score (simplified - would use full calculation in production)
        coherence_score = 0.75  # Default reasonable score

        # Overall score
        overall_score = (distance_score + coherence_score) / 2

        return {
            'distance_score': round(distance_score, 2),
            'coherence_score': round(coherence_score, 2),
            'overall_score': round(overall_score, 2),
            'total_distance_km': round(total_distance, 2)
        }
