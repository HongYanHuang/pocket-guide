"""
ILP Optimizer Module - Integer Linear Programming optimizer using OR-Tools CP-SAT solver.

This module provides optimal POI sequence optimization with support for:
- Time window constraints (booking requirements)
- Precedence constraints (storytelling order)
- Clustered visits (combo tickets)
- Fixed start/end points
- Multi-objective optimization (distance + coherence)
"""

from typing import Dict, List, Any, Tuple, Optional
from ortools.sat.python import cp_model
import logging
from datetime import datetime, timedelta
from collections import defaultdict


class ILPOptimizer:
    """Integer Linear Programming optimizer using OR-Tools CP-SAT solver"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ILP optimizer.

        Args:
            config: Application configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Get optimization settings
        opt_config = config.get('optimization', {})
        self.max_seconds = opt_config.get('ilp_max_seconds', 30)
        self.distance_weight = opt_config.get('distance_weight', 0.5)
        self.coherence_weight = opt_config.get('coherence_weight', 0.5)
        self.constraint_penalty_weight = opt_config.get('constraint_penalty_weight', 0.3)
        self.fallback_enabled = opt_config.get('ilp_fallback_enabled', True)

        # Solver configuration
        self.walking_speed_kmh = 4.0  # Average walking speed
        self.max_hours_per_day = 8    # Maximum activity hours per day

    def optimize_sequence(
        self,
        pois: List[Dict[str, Any]],
        distance_matrix: Dict[Tuple[str, str], float],
        coherence_scores: Dict[Tuple[str, str], float],
        duration_days: int,
        preferences: Dict[str, Any],
        start_location: Optional[Dict] = None,
        end_location: Optional[Dict] = None,
        trip_start_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Optimize POI sequence using CP-SAT solver.

        Args:
            pois: List of POIs with metadata
            distance_matrix: Distances between POI pairs (km)
            coherence_scores: Coherence scores between POI pairs (0-1)
            duration_days: Number of days for the trip
            preferences: User preferences
            start_location: Optional starting point
            end_location: Optional ending point

        Returns:
            {
                'sequence': [ordered POI dicts],
                'day_assignments': {poi_name: day_number},
                'scores': {distance_score, coherence_score, overall_score},
                'solver_stats': {status, solve_time, objective_value}
            }
        """
        try:
            self.logger.info(f"Starting ILP optimization for {len(pois)} POIs over {duration_days} days")

            # Create CP-SAT model
            model = cp_model.CpModel()

            # Create decision variables
            visit_vars, sequence_vars, day_vars = self._create_variables(
                model, pois, duration_days
            )

            # Add basic TSP constraints
            self._add_tsp_constraints(model, visit_vars, pois, duration_days, day_vars)

            # Add warm start hint from greedy solution to speed up solving
            self.logger.info("Generating warm start hint from greedy solution...")
            self._add_warm_start_hint(
                model, visit_vars, pois, distance_matrix, coherence_scores,
                duration_days, preferences
            )

            # Add advanced constraints
            self.logger.info("Adding time window constraints...")
            self._add_time_window_constraints(
                model, visit_vars, pois, duration_days, start_time="09:00",
                trip_start_date=trip_start_date
            )

            self.logger.info("Adding precedence constraints...")
            self._add_precedence_constraints(
                model, visit_vars, sequence_vars, pois, coherence_scores, duration_days
            )

            self.logger.info("Adding clustered visit constraints...")
            self._add_clustered_visit_constraints(
                model, visit_vars, pois, duration_days, day_vars
            )

            if start_location or end_location:
                self.logger.info("Adding start/end location constraints...")
                self._add_start_end_constraints(
                    model, visit_vars, pois, duration_days,
                    start_location, end_location, distance_matrix
                )

            # Calculate and set objective
            objective_value = self._set_objective(
                model, visit_vars, sequence_vars, pois,
                distance_matrix, coherence_scores, preferences
            )

            # Add symmetry breaking (fix first POI to reduce search space)
            if len(pois) > 0:
                # Fix the first POI at position 0 of day 0 to break symmetry
                # (routes are symmetric, so we can arbitrarily fix one POI's position)
                model.Add(visit_vars[0][0][0] == 1)
                self.logger.info("Added symmetry breaking constraint")

            # Solve the model
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = self.max_seconds
            solver.parameters.num_search_workers = 4  # Parallel search
            solver.parameters.log_search_progress = False  # Quiet mode
            solver.parameters.cp_model_presolve = True  # Enable presolve
            solver.parameters.relative_gap_limit = 0.05  # Stop if within 5% of optimal

            self.logger.info(f"Solving ILP model (timeout: {self.max_seconds}s, gap limit: 5%)...")
            status = solver.Solve(model)

            # Extract solution
            if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                result = self._extract_solution(
                    solver, visit_vars, sequence_vars, day_vars,
                    pois, duration_days, distance_matrix, coherence_scores
                )
                result['solver_stats'] = {
                    'status': solver.StatusName(status),
                    'solve_time': round(solver.WallTime(), 2),
                    'objective_value': solver.ObjectiveValue()
                }
                self.logger.info(f"ILP optimization completed: {solver.StatusName(status)} in {solver.WallTime():.2f}s")
                return result
            else:
                raise Exception(f"Solver failed with status: {solver.StatusName(status)}")

        except Exception as e:
            self.logger.error(f"ILP optimization failed: {e}")
            if self.fallback_enabled:
                self.logger.info("Falling back to greedy algorithm")
                return self._fallback_to_greedy(
                    pois, distance_matrix, coherence_scores, duration_days, preferences
                )
            else:
                raise

    def _create_variables(
        self,
        model: cp_model.CpModel,
        pois: List[Dict[str, Any]],
        duration_days: int
    ) -> Tuple[Dict, Dict, Dict]:
        """
        Create decision variables for the optimization model.

        Args:
            model: CP-SAT model
            pois: List of POIs
            duration_days: Number of days

        Returns:
            (visit_vars, sequence_vars, day_vars)
        """
        num_pois = len(pois)
        max_pois_per_day = max(3, num_pois // duration_days + 2)  # Estimate

        # Binary variables: visit[poi_idx][day][position] = 1 if POI i is at position p on day d
        visit_vars = {}
        for i, poi in enumerate(pois):
            visit_vars[i] = {}
            for day in range(duration_days):
                visit_vars[i][day] = {}
                for pos in range(max_pois_per_day):
                    visit_vars[i][day][pos] = model.NewBoolVar(
                        f'visit_{i}_{day}_{pos}'
                    )

        # Sequence variables: track global order
        sequence_vars = {}
        for i in range(num_pois):
            sequence_vars[i] = model.NewIntVar(0, num_pois - 1, f'seq_{i}')

        # Day assignment variables
        day_vars = {}
        for i in range(num_pois):
            day_vars[i] = model.NewIntVar(0, duration_days - 1, f'day_{i}')

        return visit_vars, sequence_vars, day_vars

    def _add_tsp_constraints(
        self,
        model: cp_model.CpModel,
        visit_vars: Dict,
        pois: List[Dict[str, Any]],
        duration_days: int,
        day_vars: Dict = None
    ):
        """
        Add basic TSP constraints to the model.

        Args:
            model: CP-SAT model
            visit_vars: Visit decision variables
            pois: List of POIs
            duration_days: Number of days
            day_vars: Day assignment variables (optional)
        """
        num_pois = len(pois)
        max_pois_per_day = len(list(visit_vars[0][0].keys()))

        # Constraint 1: Each POI is visited exactly once
        for i in range(num_pois):
            model.Add(
                sum(
                    visit_vars[i][day][pos]
                    for day in range(duration_days)
                    for pos in range(max_pois_per_day)
                ) == 1
            )

        # Channeling constraint: Link day_vars to visit_vars
        # day_vars[i] == d  IFF  POI i is visited on day d
        if day_vars is not None:
            for i in range(num_pois):
                # Create boolean for each day: is POI i on day d?
                day_booleans = []
                for d in range(duration_days):
                    poi_on_day_d = model.NewBoolVar(f'poi_{i}_on_day_{d}')
                    day_booleans.append(poi_on_day_d)

                    # Link boolean to visit_vars
                    count_on_day_d = sum(visit_vars[i][d][pos] for pos in range(max_pois_per_day))
                    model.Add(count_on_day_d == 1).OnlyEnforceIf(poi_on_day_d)
                    model.Add(count_on_day_d == 0).OnlyEnforceIf(poi_on_day_d.Not())

                    # If boolean is true, day_vars[i] must equal d
                    model.Add(day_vars[i] == d).OnlyEnforceIf(poi_on_day_d)

                # Exactly one day boolean must be true (redundant but helps solver)
                model.Add(sum(day_booleans) == 1)

            print(f"  [ILP] Added channeling constraints linking day_vars to visit_vars", flush=True)

        # Constraint 2: Each position on each day has at most one POI
        for day in range(duration_days):
            for pos in range(max_pois_per_day):
                model.Add(
                    sum(visit_vars[i][day][pos] for i in range(num_pois)) <= 1
                )

        # Constraint 3: Consecutive positions (no gaps in sequence)
        for day in range(duration_days):
            for pos in range(1, max_pois_per_day):
                # If position pos is occupied, position pos-1 must also be occupied
                pos_occupied = model.NewBoolVar(f'pos_{day}_{pos}_occupied')
                prev_pos_occupied = model.NewBoolVar(f'pos_{day}_{pos - 1}_occupied')

                model.Add(
                    sum(visit_vars[i][day][pos] for i in range(num_pois)) >= 1
                ).OnlyEnforceIf(pos_occupied)
                model.Add(
                    sum(visit_vars[i][day][pos] for i in range(num_pois)) == 0
                ).OnlyEnforceIf(pos_occupied.Not())

                model.Add(
                    sum(visit_vars[i][day][pos - 1] for i in range(num_pois)) >= 1
                ).OnlyEnforceIf(prev_pos_occupied)
                model.Add(
                    sum(visit_vars[i][day][pos - 1] for i in range(num_pois)) == 0
                ).OnlyEnforceIf(prev_pos_occupied.Not())

                # If current position is occupied, previous must be too
                model.AddImplication(pos_occupied, prev_pos_occupied)

    def _set_objective(
        self,
        model: cp_model.CpModel,
        visit_vars: Dict,
        sequence_vars: Dict,
        pois: List[Dict[str, Any]],
        distance_matrix: Dict[Tuple[str, str], float],
        coherence_scores: Dict[Tuple[str, str], float],
        preferences: Dict[str, Any]
    ) -> Any:
        """
        Set the objective function for multi-objective optimization.

        Args:
            model: CP-SAT model
            visit_vars: Visit decision variables
            sequence_vars: Sequence variables
            pois: List of POIs
            distance_matrix: Distances between POIs
            coherence_scores: Coherence scores between POIs
            preferences: User preferences

        Returns:
            Objective variable
        """
        num_pois = len(pois)
        duration_days = len(list(visit_vars[0].keys()))
        max_pois_per_day = len(list(visit_vars[0][0].keys()))

        # Get weights from preferences (override config defaults)
        distance_weight = preferences.get('distance_weight', self.distance_weight)
        coherence_weight = preferences.get('coherence_weight', self.coherence_weight)

        # Normalize weights
        total_weight = distance_weight + coherence_weight
        if total_weight > 0:
            distance_weight /= total_weight
            coherence_weight /= total_weight

        # Scale factor for integer arithmetic (CP-SAT uses integers)
        SCALE = 1000

        # Calculate distance component
        distance_terms = []
        for day in range(duration_days):
            for pos in range(max_pois_per_day - 1):
                for i in range(num_pois):
                    for j in range(num_pois):
                        if i != j:
                            poi1_name = pois[i]['poi']
                            poi2_name = pois[j]['poi']
                            distance = distance_matrix.get((poi1_name, poi2_name), 0)

                            # Create a boolean for this transition
                            transition = model.NewBoolVar(f'trans_{i}_{j}_{day}_{pos}')

                            # transition = 1 if POI i is at pos AND POI j is at pos+1
                            model.AddMultiplicationEquality(
                                transition,
                                [visit_vars[i][day][pos], visit_vars[j][day][pos + 1]]
                            )

                            # Add scaled distance cost
                            distance_terms.append(int(distance * SCALE) * transition)

        total_distance = sum(distance_terms) if distance_terms else 0

        # Calculate coherence component (maximize, so negate)
        coherence_terms = []
        for day in range(duration_days):
            for pos in range(max_pois_per_day - 1):
                for i in range(num_pois):
                    for j in range(num_pois):
                        if i != j:
                            poi1_name = pois[i]['poi']
                            poi2_name = pois[j]['poi']
                            coherence = coherence_scores.get((poi1_name, poi2_name), 0)

                            # Create a boolean for this transition
                            transition = model.NewBoolVar(f'coh_trans_{i}_{j}_{day}_{pos}')

                            # transition = 1 if POI i is at pos AND POI j is at pos+1
                            model.AddMultiplicationEquality(
                                transition,
                                [visit_vars[i][day][pos], visit_vars[j][day][pos + 1]]
                            )

                            # Add scaled coherence benefit (negative because we minimize)
                            coherence_terms.append(-int(coherence * SCALE) * transition)

        total_coherence_penalty = sum(coherence_terms) if coherence_terms else 0

        # Add soft constraint penalties
        penalty_terms = self._calculate_soft_penalties(
            model, visit_vars, pois, duration_days
        )

        penalty_weight = preferences.get('constraint_penalty_weight', self.constraint_penalty_weight)

        # Combine objectives with weights
        objective = (
            int(distance_weight * SCALE) * total_distance +
            int(coherence_weight * SCALE) * total_coherence_penalty +
            int(penalty_weight * SCALE) * sum(penalty_terms)
        )

        model.Minimize(objective)
        return objective

    def _calculate_soft_penalties(
        self,
        model: cp_model.CpModel,
        visit_vars: Dict,
        pois: List[Dict[str, Any]],
        duration_days: int
    ) -> List[Any]:
        """
        Calculate soft constraint penalty terms.

        Args:
            model: CP-SAT model
            visit_vars: Visit decision variables
            pois: List of POIs
            duration_days: Number of days

        Returns:
            List of penalty terms to add to objective
        """
        penalties = []
        num_pois = len(pois)
        max_pois_per_day = len(list(visit_vars[0][0].keys()))

        # Penalty for violating flexible time windows
        for i, poi in enumerate(pois):
            booking_info = poi.get('metadata', {}).get('booking_info', {})
            if booking_info.get('required') and booking_info.get('time_window', {}).get('flexible'):
                # Add penalty variable for each time window violation
                penalty = model.NewIntVar(0, 1000, f'time_penalty_{i}')
                penalties.append(penalty)

                # Calculate violation amount (simplified)
                # In practice, this would measure how far outside the window we are

        # Penalty for excessive daily walking
        for day in range(duration_days):
            # Create penalty for if this day exceeds 5km walking
            day_penalty = model.NewIntVar(0, 1000, f'walking_penalty_day_{day}')
            penalties.append(day_penalty)

            # Simplified: just add a small penalty to encourage balanced days

        return penalties if penalties else [0]

    def _add_time_window_constraints(
        self,
        model: cp_model.CpModel,
        visit_vars: Dict,
        pois: List[Dict[str, Any]],
        duration_days: int,
        start_time: str = "09:00",
        trip_start_date: Optional[datetime] = None
    ):
        """
        Add time window constraints based on Google Maps opening hours.

        Uses operation_hours.periods format from Google Maps Places API:
        - day: 0 (Sunday) to 6 (Saturday)
        - time: HHMM format (e.g., "0800" for 8:00 AM)

        Args:
            model: CP-SAT model
            visit_vars: Visit decision variables
            pois: List of POIs
            duration_days: Number of days
            start_time: Daily start time
            trip_start_date: Starting date of trip (to determine day of week)
        """
        from datetime import datetime, timedelta

        num_pois = len(pois)
        max_pois_per_day = len(list(visit_vars[0][0].keys()))
        start_minutes = self._time_to_minutes(start_time)

        # If no start date provided, use today
        if trip_start_date is None:
            trip_start_date = datetime.now()

        for i, poi in enumerate(pois):
            # Get operation hours from Google Maps format
            operation_hours = poi.get('metadata', {}).get('operation_hours', {})
            periods = operation_hours.get('periods', [])

            if not periods:
                continue

            # Check if booking is required (stricter enforcement)
            booking_required = poi.get('metadata', {}).get('booking_info', {}).get('required', False)

            # Get preferred time slots if booking required
            preferred_slots = []
            if booking_required:
                booking_info = poi.get('metadata', {}).get('booking_info', {})
                preferred_slots = booking_info.get('preferred_time_slots', [])

            # For each day in the trip
            for day in range(duration_days):
                # Calculate the day of week for this day (0=Sunday, 6=Saturday)
                trip_date = trip_start_date + timedelta(days=day)
                day_of_week = trip_date.weekday()  # 0=Monday, 6=Sunday
                # Convert to Google Maps format (0=Sunday)
                google_day_of_week = (day_of_week + 1) % 7

                # Find opening hours for this day of week
                day_periods = [p for p in periods if p.get('open', {}).get('day') == google_day_of_week]

                if not day_periods:
                    # Closed on this day - POI cannot be visited
                    for pos in range(max_pois_per_day):
                        model.Add(visit_vars[i][day][pos] == 0)
                    continue

                # For each position in the day
                for pos in range(max_pois_per_day):
                    # Calculate estimated arrival time at this position
                    # Simplified: assumes 2.5 hours per POI (2h visit + 30min travel)
                    estimated_arrival_minutes = start_minutes + (pos * 150)

                    # Convert to HHMM format for comparison
                    estimated_hours = estimated_arrival_minutes // 60
                    estimated_mins = estimated_arrival_minutes % 60
                    estimated_time_hhmm = estimated_hours * 100 + estimated_mins

                    # Check if this time falls within any opening period
                    is_open = False
                    for period in day_periods:
                        open_time = int(period.get('open', {}).get('time', '0000'))
                        close_time = int(period.get('close', {}).get('time', '2359'))

                        if open_time <= estimated_time_hhmm <= close_time:
                            is_open = True
                            break

                    # If booking required, also check preferred time slots
                    if booking_required and preferred_slots:
                        in_preferred_slot = False
                        for slot in preferred_slots:
                            slot_start = self._time_to_minutes(slot.get('start', '00:00'))
                            slot_end = self._time_to_minutes(slot.get('end', '23:59'))

                            if slot_start <= estimated_arrival_minutes <= slot_end:
                                in_preferred_slot = True
                                break

                        # Must be both open AND in preferred slot
                        if not (is_open and in_preferred_slot):
                            model.Add(visit_vars[i][day][pos] == 0)
                    else:
                        # Just check if open
                        if not is_open:
                            model.Add(visit_vars[i][day][pos] == 0)

    def _add_precedence_constraints(
        self,
        model: cp_model.CpModel,
        visit_vars: Dict,
        sequence_vars: Dict,
        pois: List[Dict[str, Any]],
        coherence_scores: Dict[Tuple[str, str], float],
        duration_days: int
    ):
        """
        Add precedence constraints based on storytelling order.

        Args:
            model: CP-SAT model
            visit_vars: Visit decision variables
            sequence_vars: Sequence variables
            pois: List of POIs
            coherence_scores: Coherence scores between POI pairs
            duration_days: Number of days
        """
        num_pois = len(pois)
        max_pois_per_day = len(list(visit_vars[0][0].keys()))

        # Get precedence threshold from config
        precedence_threshold = self.config.get('optimization', {}).get('precedence_soft_threshold', 0.7)

        # Link sequence variables to visit variables
        for i in range(num_pois):
            for day in range(duration_days):
                for pos in range(max_pois_per_day):
                    global_pos = day * max_pois_per_day + pos
                    # If POI i is at (day, pos), then its sequence position is global_pos
                    model.Add(sequence_vars[i] == global_pos).OnlyEnforceIf(visit_vars[i][day][pos])

        # Enforce precedence based on high coherence scores
        for i in range(num_pois):
            for j in range(num_pois):
                if i == j:
                    continue

                poi_i_name = pois[i]['poi']
                poi_j_name = pois[j]['poi']
                coherence = coherence_scores.get((poi_i_name, poi_j_name), 0)

                # If coherence is high, enforce that i comes before j
                if coherence >= precedence_threshold:
                    model.Add(sequence_vars[i] < sequence_vars[j])

        # Also check for explicit precedence constraints in metadata
        for i, poi in enumerate(pois):
            must_visit_after = poi.get('metadata', {}).get('precedence', {}).get('must_visit_after', [])
            for prereq_name in must_visit_after:
                # Find the index of the prerequisite POI
                for j, other_poi in enumerate(pois):
                    if other_poi['poi'] == prereq_name:
                        # j must come before i
                        model.Add(sequence_vars[j] < sequence_vars[i])
                        break

    def _add_clustered_visit_constraints(
        self,
        model: cp_model.CpModel,
        visit_vars: Dict,
        pois: List[Dict[str, Any]],
        duration_days: int,
        day_vars: Dict = None
    ):
        """
        Add clustered visit constraints for combo ticket groups.

        Args:
            model: CP-SAT model
            visit_vars: Visit decision variables
            pois: List of POIs
            duration_days: Number of days
        """
        num_pois = len(pois)
        max_pois_per_day = len(list(visit_vars[0][0].keys()))

        # Group POIs by combo ticket groups (from enriched data)
        from collections import defaultdict
        groups = defaultdict(list)

        print(f"  [ILP] Checking {len(pois)} POIs for combo ticket constraints...", flush=True)

        for i, poi in enumerate(pois):
            # Use enriched combo_ticket_groups from ComboTicketLoader
            combo_groups = poi.get('metadata', {}).get('combo_ticket_groups', [])

            if combo_groups:
                print(f"  [ILP] POI '{poi.get('poi')}' has {len(combo_groups)} combo ticket(s)", flush=True)

            for group in combo_groups:
                constraints = group.get('constraints', {})
                if constraints.get('must_visit_together'):
                    group_id = group.get('id')
                    if group_id:
                        groups[group_id].append(i)
                        print(f"  [ILP] Added '{poi.get('poi')}' to combo group '{group_id}'", flush=True)

            # Fallback: support old format for backward compatibility
            old_combo_info = poi.get('metadata', {}).get('combo_ticket', {})
            if old_combo_info.get('must_visit_together'):
                group_id = old_combo_info.get('group_id')
                if group_id and group_id not in groups:
                    groups[group_id].append(i)

        # For each group, enforce constraints
        if groups:
            print(f"  [ILP] Applying combo ticket constraints for {len(groups)} group(s)", flush=True)
            for group_id, poi_indices in groups.items():
                poi_names = [pois[i].get('poi') for i in poi_indices]
                print(f"  [ILP] Group '{group_id}': {poi_names} (must visit same day)", flush=True)
        else:
            print(f"  [ILP] No combo ticket groups found, skipping constraints", flush=True)

        for group_id, poi_indices in groups.items():
            if len(poi_indices) <= 1:
                continue

            poi_names = [pois[i].get('poi') for i in poi_indices]
            print(f"  [ILP] Enforcing same-day constraint for group '{group_id}': {poi_names}", flush=True)

            # SIMPLE SOLUTION: Use day_vars to directly constrain all POIs to same day
            # All POIs in group must have the same day assignment
            first_poi_idx = poi_indices[0]
            for poi_idx in poi_indices[1:]:
                model.Add(day_vars[poi_idx] == day_vars[first_poi_idx])
                print(f"  [ILP]   Constraint: day[{pois[poi_idx].get('poi')}] == day[{pois[first_poi_idx].get('poi')}]", flush=True)

            # Constraint 2: POIs in group must be consecutive
            # Find positions of group members and ensure they're consecutive
            for day in range(duration_days):
                for idx_in_group in range(len(poi_indices) - 1):
                    poi_i = poi_indices[idx_in_group]
                    poi_j = poi_indices[idx_in_group + 1]

                    # Find position variables for these POIs on this day
                    pos_i = model.NewIntVar(0, max_pois_per_day - 1, f'pos_{poi_i}_day_{day}')
                    pos_j = model.NewIntVar(0, max_pois_per_day - 1, f'pos_{poi_j}_day_{day}')

                    # Link position variables to visit variables
                    for pos in range(max_pois_per_day):
                        model.Add(pos_i == pos).OnlyEnforceIf(visit_vars[poi_i][day][pos])
                        model.Add(pos_j == pos).OnlyEnforceIf(visit_vars[poi_j][day][pos])

                    # If both are on this day, they should be consecutive
                    both_on_day = model.NewBoolVar(f'both_{poi_i}_{poi_j}_day_{day}')
                    model.Add(
                        sum(visit_vars[poi_i][day][pos] for pos in range(max_pois_per_day)) >= 1
                    ).OnlyEnforceIf(both_on_day)

                    # If both on same day, j should be right after i
                    model.Add(pos_j == pos_i + 1).OnlyEnforceIf(both_on_day)

    def _add_start_end_constraints(
        self,
        model: cp_model.CpModel,
        visit_vars: Dict,
        pois: List[Dict[str, Any]],
        duration_days: int,
        start_location: Optional[Dict],
        end_location: Optional[Dict],
        distance_matrix: Dict[Tuple[str, str], float]
    ):
        """
        Add constraints for fixed start and end locations.

        Args:
            model: CP-SAT model
            visit_vars: Visit decision variables
            pois: List of POIs
            duration_days: Number of days
            start_location: Starting location (if provided)
            end_location: Ending location (if provided)
            distance_matrix: Distance matrix
        """
        num_pois = len(pois)
        max_pois_per_day = len(list(visit_vars[0][0].keys()))

        if start_location:
            # Encourage first POI on day 0 to be close to start location
            # We can do this by finding the closest POI and preferring it at position 0
            closest_poi_idx = None
            min_distance = float('inf')

            start_coords = start_location.get('coordinates', {})
            if start_coords.get('latitude'):
                for i, poi in enumerate(pois):
                    poi_coords = poi.get('coordinates', {})
                    if poi_coords.get('latitude'):
                        # Calculate distance (simplified Haversine)
                        from math import radians, sin, cos, sqrt, asin
                        lat1, lon1 = radians(start_coords['latitude']), radians(start_coords['longitude'])
                        lat2, lon2 = radians(poi_coords['latitude']), radians(poi_coords['longitude'])
                        dlat, dlon = lat2 - lat1, lon2 - lon1
                        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                        distance = 2 * 6371 * asin(sqrt(a))

                        if distance < min_distance:
                            min_distance = distance
                            closest_poi_idx = i

                # Prefer closest POI at position 0, day 0 (soft constraint via objective)
                # For now, we'll enforce it as a hint rather than hard constraint
                if closest_poi_idx is not None:
                    model.AddHint(visit_vars[closest_poi_idx][0][0], 1)

        if end_location:
            # Similarly, encourage last POI to be close to end location
            closest_poi_idx = None
            min_distance = float('inf')

            end_coords = end_location.get('coordinates', {})
            if end_coords.get('latitude'):
                for i, poi in enumerate(pois):
                    poi_coords = poi.get('coordinates', {})
                    if poi_coords.get('latitude'):
                        from math import radians, sin, cos, sqrt, asin
                        lat1, lon1 = radians(end_coords['latitude']), radians(end_coords['longitude'])
                        lat2, lon2 = radians(poi_coords['latitude']), radians(poi_coords['longitude'])
                        dlat, dlon = lat2 - lat1, lon2 - lon1
                        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                        distance = 2 * 6371 * asin(sqrt(a))

                        if distance < min_distance:
                            min_distance = distance
                            closest_poi_idx = i

                if closest_poi_idx is not None:
                    # Encourage this POI to be at the end
                    last_day = duration_days - 1
                    # Try multiple positions near the end
                    for pos in range(max_pois_per_day - 3, max_pois_per_day):
                        if pos >= 0:
                            model.AddHint(visit_vars[closest_poi_idx][last_day][pos], 1)

    def _time_to_minutes(self, time_str: str) -> int:
        """
        Convert time string to minutes since midnight.

        Args:
            time_str: Time in format "HH:MM"

        Returns:
            Minutes since midnight
        """
        if not time_str or ':' not in time_str:
            return 540  # Default 9:00 AM

        try:
            hours, minutes = map(int, time_str.split(':'))
            return hours * 60 + minutes
        except:
            return 540

    def _add_warm_start_hint(
        self,
        model: cp_model.CpModel,
        visit_vars: Dict,
        pois: List[Dict[str, Any]],
        distance_matrix: Dict[Tuple[str, str], float],
        coherence_scores: Dict[Tuple[str, str], float],
        duration_days: int,
        preferences: Dict[str, Any]
    ):
        """
        Add warm start hint from greedy solution to speed up ILP solving.

        Args:
            model: CP-SAT model
            visit_vars: Visit decision variables
            pois: List of POIs
            distance_matrix: Distances
            coherence_scores: Coherence scores
            duration_days: Number of days
            preferences: User preferences
        """
        try:
            # Import greedy optimizer to generate initial solution
            from .itinerary_optimizer import ItineraryOptimizerAgent

            greedy_optimizer = ItineraryOptimizerAgent(self.config)

            # Generate greedy sequence
            greedy_sequence = greedy_optimizer._optimize_sequence(
                pois, distance_matrix, coherence_scores, preferences
            )

            # Distribute across days
            max_pois_per_day = len(list(visit_vars[0][0].keys()))
            pois_per_day = max(1, len(greedy_sequence) // duration_days)

            # Create hints for visit variables
            current_day = 0
            current_pos = 0

            for poi in greedy_sequence:
                # Find POI index
                poi_idx = None
                for i, p in enumerate(pois):
                    if p['poi'] == poi['poi']:
                        poi_idx = i
                        break

                if poi_idx is not None:
                    # Add hint: this POI should be at (current_day, current_pos)
                    if current_day < duration_days and current_pos < max_pois_per_day:
                        model.AddHint(visit_vars[poi_idx][current_day][current_pos], 1)

                    # Move to next position
                    current_pos += 1
                    if current_pos >= pois_per_day and current_day < duration_days - 1:
                        current_day += 1
                        current_pos = 0

            self.logger.info(f"Added warm start hints for {len(greedy_sequence)} POIs")

        except Exception as e:
            self.logger.warning(f"Failed to add warm start hint: {e}")
            # Continue without warm start if it fails

    def _extract_solution(
        self,
        solver: cp_model.CpSolver,
        visit_vars: Dict,
        sequence_vars: Dict,
        day_vars: Dict,
        pois: List[Dict[str, Any]],
        duration_days: int,
        distance_matrix: Dict[Tuple[str, str], float],
        coherence_scores: Dict[Tuple[str, str], float]
    ) -> Dict[str, Any]:
        """
        Extract solution from solved model.

        Args:
            solver: Solved CP-SAT solver
            visit_vars: Visit decision variables
            sequence_vars: Sequence variables
            day_vars: Day assignment variables
            pois: List of POIs
            duration_days: Number of days
            distance_matrix: Distances
            coherence_scores: Coherence scores

        Returns:
            Solution dictionary
        """
        num_pois = len(pois)
        max_pois_per_day = len(list(visit_vars[0][0].keys()))

        # Extract POI assignments
        assignments = []  # List of (poi_idx, day, position)

        for i in range(num_pois):
            for day in range(duration_days):
                for pos in range(max_pois_per_day):
                    if solver.Value(visit_vars[i][day][pos]) == 1:
                        assignments.append((i, day, pos))

        # Sort by day and position
        assignments.sort(key=lambda x: (x[1], x[2]))

        # Build sequence and day_assignments
        sequence = []
        day_assignments = {}

        for poi_idx, day, pos in assignments:
            poi = pois[poi_idx].copy()
            sequence.append(poi)
            day_assignments[poi['poi']] = day

        # Calculate scores
        total_distance = 0
        coherence_sum = 0
        coherence_count = 0

        for i in range(len(sequence) - 1):
            poi1_name = sequence[i]['poi']
            poi2_name = sequence[i + 1]['poi']

            total_distance += distance_matrix.get((poi1_name, poi2_name), 0)
            coherence_sum += coherence_scores.get((poi1_name, poi2_name), 0)
            coherence_count += 1

        # Normalize scores
        max_possible_distance = len(sequence) * 3.0  # Assume avg 3km
        distance_score = max(0, 1 - (total_distance / max_possible_distance))
        coherence_score = coherence_sum / coherence_count if coherence_count > 0 else 0.5
        overall_score = (distance_score + coherence_score) / 2

        return {
            'sequence': sequence,
            'day_assignments': day_assignments,
            'scores': {
                'distance_score': round(distance_score, 2),
                'coherence_score': round(coherence_score, 2),
                'overall_score': round(overall_score, 2),
                'total_distance_km': round(total_distance, 2)
            }
        }

    def _fallback_to_greedy(
        self,
        pois: List[Dict[str, Any]],
        distance_matrix: Dict[Tuple[str, str], float],
        coherence_scores: Dict[Tuple[str, str], float],
        duration_days: int,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fallback to greedy algorithm if ILP fails.

        Args:
            pois: List of POIs
            distance_matrix: Distances
            coherence_scores: Coherence scores
            duration_days: Number of days
            preferences: User preferences

        Returns:
            Greedy solution
        """
        # Import here to avoid circular dependency
        from .itinerary_optimizer import ItineraryOptimizerAgent

        self.logger.info("Using greedy algorithm as fallback")
        greedy_optimizer = ItineraryOptimizerAgent(self.config)

        # Use the greedy optimizer's sequence optimization
        sequence = greedy_optimizer._optimize_sequence(
            pois, distance_matrix, coherence_scores, preferences
        )

        # Build day assignments (simple distribution)
        pois_per_day = len(sequence) // duration_days
        day_assignments = {}
        for i, poi in enumerate(sequence):
            day = min(i // pois_per_day, duration_days - 1)
            day_assignments[poi['poi']] = day

        # Calculate scores
        total_distance = sum(
            day['total_walking_km']
            for day in greedy_optimizer._schedule_days(
                sequence, duration_days, "09:00", distance_matrix
            )
        )

        coherence_sum = 0
        coherence_count = 0
        for i in range(len(sequence) - 1):
            poi1_name = sequence[i]['poi']
            poi2_name = sequence[i + 1]['poi']
            coherence_sum += coherence_scores.get((poi1_name, poi2_name), 0)
            coherence_count += 1

        max_possible_distance = len(sequence) * 3.0
        distance_score = max(0, 1 - (total_distance / max_possible_distance))
        coherence_score = coherence_sum / coherence_count if coherence_count > 0 else 0.5

        return {
            'sequence': sequence,
            'day_assignments': day_assignments,
            'scores': {
                'distance_score': round(distance_score, 2),
                'coherence_score': round(coherence_score, 2),
                'overall_score': round((distance_score + coherence_score) / 2, 2),
                'total_distance_km': round(total_distance, 2)
            },
            'solver_stats': {
                'status': 'GREEDY_FALLBACK',
                'solve_time': 0,
                'objective_value': 0
            }
        }
