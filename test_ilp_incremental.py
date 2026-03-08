#!/usr/bin/env python3
"""
Incremental ILP test - add constraints one by one to find which causes INFEASIBLE
"""

from ortools.sat.python import cp_model

# Test data: Only the 5 POIs
test_pois = [
    {'poi': 'Colosseum', 'estimated_hours': 2.0},
    {'poi': 'Roman Forum', 'estimated_hours': 2.0},
    {'poi': 'Palatine Hill', 'estimated_hours': 1.5},
    {'poi': 'Vatican Museums', 'estimated_hours': 3.0},
    {'poi': 'Sistine Chapel', 'estimated_hours': 0.8}
]

NUM_POIS = 5
DURATION_DAYS = 2
MAX_POIS_PER_DAY = 4
MAX_HOURS_PER_DAY = 8.5
SCALE = 100

def create_variables(model):
    """Create visit and sequence variables"""
    visit_vars = {}
    for i in range(NUM_POIS):
        visit_vars[i] = {}
        for day in range(DURATION_DAYS):
            visit_vars[i][day] = {}
            for pos in range(MAX_POIS_PER_DAY):
                visit_vars[i][day][pos] = model.NewBoolVar(f'v_{i}_d{day}_p{pos}')

    sequence_vars = {}
    for i in range(NUM_POIS):
        sequence_vars[i] = model.NewIntVar(0, NUM_POIS - 1, f'seq_{i}')

    return visit_vars, sequence_vars

def test_configuration(constraints_to_add):
    """Test ILP with specific set of constraints"""
    model = cp_model.CpModel()
    visit_vars, sequence_vars = create_variables(model)

    # 1. Each POI visited exactly once (ALWAYS INCLUDE)
    for i in range(NUM_POIS):
        visits = []
        for day in range(DURATION_DAYS):
            for pos in range(MAX_POIS_PER_DAY):
                visits.append(visit_vars[i][day][pos])
        model.Add(sum(visits) == 1)

    # 2. Each position used at most once per day
    if 'position_unique' in constraints_to_add:
        for day in range(DURATION_DAYS):
            for pos in range(MAX_POIS_PER_DAY):
                visits_at_pos = []
                for i in range(NUM_POIS):
                    visits_at_pos.append(visit_vars[i][day][pos])
                model.Add(sum(visits_at_pos) <= 1)

    # 3. Positions filled left-to-right
    if 'position_ordering' in constraints_to_add:
        for day in range(DURATION_DAYS):
            for pos in range(MAX_POIS_PER_DAY - 1):
                used_pos = []
                used_next_pos = []
                for i in range(NUM_POIS):
                    used_pos.append(visit_vars[i][day][pos])
                    used_next_pos.append(visit_vars[i][day][pos + 1])
                model.Add(sum(used_pos) >= sum(used_next_pos))

    # 3b. Sequence variable channeling
    if 'sequence_channeling' in constraints_to_add:
        for i in range(NUM_POIS):
            for day in range(DURATION_DAYS):
                for pos in range(MAX_POIS_PER_DAY):
                    model.Add(sequence_vars[i] == day * MAX_POIS_PER_DAY + pos).OnlyEnforceIf(visit_vars[i][day][pos])

    # 4. Combo ticket constraints
    if 'combo_tickets' in constraints_to_add:
        # Archaeological group
        arch_indices = [0, 1, 2]  # Colosseum, Roman Forum, Palatine
        for day in range(DURATION_DAYS):
            pois_on_day = []
            for poi_idx in arch_indices:
                on_day = model.NewBoolVar(f'arch_{poi_idx}_d{day}')
                visits = sum(visit_vars[poi_idx][day][pos] for pos in range(MAX_POIS_PER_DAY))
                model.Add(visits == 1).OnlyEnforceIf(on_day)
                model.Add(visits == 0).OnlyEnforceIf(on_day.Not())
                pois_on_day.append(on_day)

            # All must be equal
            for poi_on_day in pois_on_day[1:]:
                model.Add(poi_on_day == pois_on_day[0])

        # Vatican group
        vat_indices = [3, 4]  # Vatican Museums, Sistine Chapel
        for day in range(DURATION_DAYS):
            pois_on_day = []
            for poi_idx in vat_indices:
                on_day = model.NewBoolVar(f'vat_{poi_idx}_d{day}')
                visits = sum(visit_vars[poi_idx][day][pos] for pos in range(MAX_POIS_PER_DAY))
                model.Add(visits == 1).OnlyEnforceIf(on_day)
                model.Add(visits == 0).OnlyEnforceIf(on_day.Not())
                pois_on_day.append(on_day)

            # All must be equal
            model.Add(pois_on_day[1] == pois_on_day[0])

    # 5. Daily hour constraints
    if 'daily_hours' in constraints_to_add:
        for day in range(DURATION_DAYS):
            hour_terms = []

            # Visit hours
            for i, poi in enumerate(test_pois):
                visit_hours = poi['estimated_hours']
                scaled_hours = int(visit_hours * SCALE)
                on_this_day = model.NewBoolVar(f'hr_{i}_d{day}')
                model.AddMaxEquality(on_this_day, [visit_vars[i][day][pos] for pos in range(MAX_POIS_PER_DAY)])
                hour_terms.append(scaled_hours * on_this_day)

            # Walking hours
            for i in range(NUM_POIS):
                on_this_day = model.NewBoolVar(f'walk_{i}_d{day}')
                model.AddMaxEquality(on_this_day, [visit_vars[i][day][pos] for pos in range(MAX_POIS_PER_DAY)])
                hour_terms.append(20 * on_this_day)  # 0.2h walking

            model.Add(sum(hour_terms) <= int(MAX_HOURS_PER_DAY * SCALE))

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = False
    status = solver.Solve(model)

    return solver.StatusName(status), len(model.Proto().constraints)

# Test incrementally
print("=" * 70)
print("INCREMENTAL CONSTRAINT TEST")
print("=" * 70)

tests = [
    ([], "Baseline: Only 'each POI visited once'"),
    (['position_unique'], "+ Position uniqueness"),
    (['position_unique', 'position_ordering'], "+ Position ordering (left-to-right)"),
    (['position_unique', 'position_ordering', 'sequence_channeling'], "+ Sequence channeling"),
    (['position_unique', 'position_ordering', 'combo_tickets'], "+ Combo ticket constraints"),
    (['position_unique', 'position_ordering', 'daily_hours'], "+ Daily hour constraints (NO combo)"),
    (['position_unique', 'position_ordering', 'combo_tickets', 'daily_hours'], "+ ALL constraints (NO channeling)"),
    (['position_unique', 'position_ordering', 'sequence_channeling', 'combo_tickets', 'daily_hours'], "+ ALL constraints (WITH channeling)"),
]

for constraints, description in tests:
    status, num_constraints = test_configuration(constraints)
    status_symbol = "✓" if status in ['OPTIMAL', 'FEASIBLE'] else "❌"
    print(f"\n{status_symbol} {description}")
    print(f"   Status: {status}, Constraints: {num_constraints}")

print("\n" + "=" * 70)
print("CONCLUSION")
print("=" * 70)
print("\nThe first INFEASIBLE result shows which constraint causes the conflict.")
