#!/usr/bin/env python3
"""
Minimal ILP test with only 5 POIs (2 combo groups) to debug constraint conflicts.
Shows exactly which constraints are added and which cause INFEASIBLE.
"""

from ortools.sat.python import cp_model
from datetime import datetime

# Test data: Only the 5 POIs we care about
test_pois = [
    {
        'poi': 'Colosseum',
        'estimated_hours': 2.0,
        'priority': 'high',
        'metadata': {
            'combo_ticket_groups': [
                {
                    'id': 'archaeological_pass_rome',
                    'constraints': {'must_visit_together': True}
                }
            ]
        }
    },
    {
        'poi': 'Roman Forum',
        'estimated_hours': 2.0,
        'priority': 'high',
        'metadata': {
            'combo_ticket_groups': [
                {
                    'id': 'archaeological_pass_rome',
                    'constraints': {'must_visit_together': True}
                }
            ]
        }
    },
    {
        'poi': 'Palatine Hill',
        'estimated_hours': 1.5,
        'priority': 'high',
        'metadata': {
            'combo_ticket_groups': [
                {
                    'id': 'archaeological_pass_rome',
                    'constraints': {'must_visit_together': True}
                }
            ]
        }
    },
    {
        'poi': 'Vatican Museums',
        'estimated_hours': 3.0,
        'priority': 'high',
        'metadata': {
            'combo_ticket_groups': [
                {
                    'id': 'vatican_combo',
                    'constraints': {'must_visit_together': True}
                }
            ]
        }
    },
    {
        'poi': 'Sistine Chapel',
        'estimated_hours': 0.8,
        'priority': 'high',
        'metadata': {
            'combo_ticket_groups': [
                {
                    'id': 'vatican_combo',
                    'constraints': {'must_visit_together': True}
                }
            ]
        }
    }
]

# Configuration
NUM_POIS = 5
DURATION_DAYS = 2
MAX_POIS_PER_DAY = 4  # max(3, 5//2 + 2) = 4
MAX_HOURS_PER_DAY = 8.5  # Normal pace
SCALE = 100  # For integer arithmetic

print("=" * 70)
print("ILP MINIMAL TEST - CONSTRAINT ANALYSIS")
print("=" * 70)
print(f"\nConfiguration:")
print(f"  POIs: {NUM_POIS}")
print(f"  Days: {DURATION_DAYS}")
print(f"  Max POIs per day: {MAX_POIS_PER_DAY}")
print(f"  Max hours per day: {MAX_HOURS_PER_DAY}h")
print(f"\nPOIs:")
for i, poi in enumerate(test_pois):
    print(f"  [{i}] {poi['poi']}: {poi['estimated_hours']}h")

# Create model
model = cp_model.CpModel()
constraint_count = 0

print(f"\n{'=' * 70}")
print("STEP 1: CREATE VARIABLES")
print("=" * 70)

# Variables: visit[poi][day][position] = 1 if POI i is at position p on day d
visit_vars = {}
for i in range(NUM_POIS):
    visit_vars[i] = {}
    for day in range(DURATION_DAYS):
        visit_vars[i][day] = {}
        for pos in range(MAX_POIS_PER_DAY):
            visit_vars[i][day][pos] = model.NewBoolVar(f'visit_{i}_day{day}_pos{pos}')

print(f"Created {NUM_POIS * DURATION_DAYS * MAX_POIS_PER_DAY} visit variables")
print(f"  Format: visit[poi_idx][day][position]")

# Sequence variables (for objective)
sequence_vars = {}
for i in range(NUM_POIS):
    sequence_vars[i] = model.NewIntVar(0, NUM_POIS - 1, f'seq_{i}')

print(f"Created {NUM_POIS} sequence variables")

print(f"\n{'=' * 70}")
print("STEP 2: ADD TSP CONSTRAINTS")
print("=" * 70)

# Constraint 1: Each POI is visited exactly once
for i in range(NUM_POIS):
    visits = []
    for day in range(DURATION_DAYS):
        for pos in range(MAX_POIS_PER_DAY):
            visits.append(visit_vars[i][day][pos])
    model.Add(sum(visits) == 1)
    constraint_count += 1
    print(f"✓ POI {i} ({test_pois[i]['poi']}): visited exactly once")

print(f"\nAdded {constraint_count} constraints (each POI visited exactly once)")

# Constraint 2: Each position used at most once per day
for day in range(DURATION_DAYS):
    for pos in range(MAX_POIS_PER_DAY):
        visits_at_pos = []
        for i in range(NUM_POIS):
            visits_at_pos.append(visit_vars[i][day][pos])
        model.Add(sum(visits_at_pos) <= 1)
        constraint_count += 1

print(f"Added {DURATION_DAYS * MAX_POIS_PER_DAY} constraints (each position used ≤ once)")

# Constraint 3: Positions filled from left (TSP sequencing)
for day in range(DURATION_DAYS):
    for pos in range(MAX_POIS_PER_DAY - 1):
        used_pos = []
        used_next_pos = []
        for i in range(NUM_POIS):
            used_pos.append(visit_vars[i][day][pos])
            used_next_pos.append(visit_vars[i][day][pos + 1])
        # If position p+1 is used, position p must be used
        model.Add(sum(used_pos) >= sum(used_next_pos))
        constraint_count += 1

print(f"Added {DURATION_DAYS * (MAX_POIS_PER_DAY - 1)} constraints (positions filled left-to-right)")

# Link visit_vars to sequence_vars
for i in range(NUM_POIS):
    for day in range(DURATION_DAYS):
        for pos in range(MAX_POIS_PER_DAY):
            model.Add(sequence_vars[i] == day * MAX_POIS_PER_DAY + pos).OnlyEnforceIf(visit_vars[i][day][pos])

print(f"Added {NUM_POIS * DURATION_DAYS * MAX_POIS_PER_DAY} channeling constraints (visit ↔ sequence)")
constraint_count += NUM_POIS * DURATION_DAYS * MAX_POIS_PER_DAY

print(f"\nTotal TSP constraints: {constraint_count}")

print(f"\n{'=' * 70}")
print("STEP 3: ADD COMBO TICKET CONSTRAINTS")
print("=" * 70)

# Group POIs by combo ticket
from collections import defaultdict
groups = defaultdict(list)

for i, poi in enumerate(test_pois):
    combo_groups = poi.get('metadata', {}).get('combo_ticket_groups', [])
    for group in combo_groups:
        if group.get('constraints', {}).get('must_visit_together'):
            group_id = group.get('id')
            if group_id:
                groups[group_id].append(i)

combo_constraint_count = 0
for group_id, poi_indices in groups.items():
    poi_names = [test_pois[i]['poi'] for i in poi_indices]
    print(f"\nGroup '{group_id}': {poi_names}")
    print(f"  Constraint: All {len(poi_indices)} POIs must be on the same day")

    for day in range(DURATION_DAYS):
        print(f"  Day {day}:")
        pois_on_day_d = []
        for poi_idx in poi_indices:
            poi_name = test_pois[poi_idx]['poi']
            on_day = model.NewBoolVar(f'combo_{group_id}_poi{poi_idx}_day{day}')
            visits_on_day = sum(visit_vars[poi_idx][day][pos] for pos in range(MAX_POIS_PER_DAY))

            # on_day = 1 iff visits_on_day == 1
            model.Add(visits_on_day == 1).OnlyEnforceIf(on_day)
            model.Add(visits_on_day == 0).OnlyEnforceIf(on_day.Not())
            combo_constraint_count += 2

            pois_on_day_d.append(on_day)
            print(f"    {poi_name}: on_day = (visits == 1)")

        # All must be equal (all on this day OR all not on this day)
        first_poi_on_day = pois_on_day_d[0]
        for poi_on_day in pois_on_day_d[1:]:
            model.Add(poi_on_day == first_poi_on_day)
            combo_constraint_count += 1
            print(f"    Constraint: on_day[POI{poi_indices[pois_on_day_d.index(poi_on_day)]}] == on_day[POI{poi_indices[0]}]")

print(f"\nTotal combo ticket constraints: {combo_constraint_count}")
constraint_count += combo_constraint_count

print(f"\n{'=' * 70}")
print("STEP 4: ADD DAILY HOUR CONSTRAINTS")
print("=" * 70)

for day in range(DURATION_DAYS):
    hour_terms = []
    print(f"\nDay {day} constraint:")

    # Add visit hours for each POI
    for i, poi in enumerate(test_pois):
        visit_hours = poi.get('estimated_hours', 2.0)
        scaled_hours = int(visit_hours * SCALE)

        # Boolean: is this POI on this day?
        on_this_day = model.NewBoolVar(f'poi_{i}_on_day_{day}')
        model.AddMaxEquality(on_this_day, [visit_vars[i][day][pos] for pos in range(MAX_POIS_PER_DAY)])

        hour_terms.append(scaled_hours * on_this_day)
        print(f"  + {scaled_hours} * on_day[{poi['poi']}]  ({visit_hours}h visit)")

    # Add walking time (0.2h per POI)
    avg_walking = 0.20
    scaled_walking = int(avg_walking * SCALE)

    for i in range(NUM_POIS):
        on_this_day = model.NewBoolVar(f'poi_{i}_walk_day_{day}')
        model.AddMaxEquality(on_this_day, [visit_vars[i][day][pos] for pos in range(MAX_POIS_PER_DAY)])
        hour_terms.append(scaled_walking * on_this_day)

    print(f"  + {scaled_walking} * (num_pois_on_day)  ({avg_walking}h walk per POI)")

    # Constraint: total <= max_hours
    total_hours = sum(hour_terms)
    max_scaled = int(MAX_HOURS_PER_DAY * SCALE)
    model.Add(total_hours <= max_scaled)
    constraint_count += 1

    print(f"  <= {max_scaled}  ({MAX_HOURS_PER_DAY}h)")

    # Calculate if manual distribution would satisfy
    if day == 0:
        # Archaeological on Day 0
        arch_visit = 2.0 + 2.0 + 1.5
        arch_walk = 3 * avg_walking
        arch_total = arch_visit + arch_walk
        print(f"\n  Manual check: Archaeological (3 POIs) = {arch_visit}h + {arch_walk}h = {arch_total}h")
        print(f"  Would satisfy? {arch_total <= MAX_HOURS_PER_DAY}")
    else:
        # Vatican on Day 1
        vat_visit = 3.0 + 0.8
        vat_walk = 2 * avg_walking
        vat_total = vat_visit + vat_walk
        print(f"\n  Manual check: Vatican (2 POIs) = {vat_visit}h + {vat_walk}h = {vat_total}h")
        print(f"  Would satisfy? {vat_total <= MAX_HOURS_PER_DAY}")

print(f"\nTotal daily hour constraints: {DURATION_DAYS}")
constraint_count += DURATION_DAYS

print(f"\n{'=' * 70}")
print("STEP 5: SOLVE MODEL")
print("=" * 70)

print(f"\nModel statistics:")
print(f"  Total variables: {len(model.Proto().variables)}")
print(f"  Total constraints: {len(model.Proto().constraints)}")
print(f"  Boolean variables: {sum(1 for v in model.Proto().variables if v.domain == [0, 1])}")

print(f"\nAttempting to solve...")

solver = cp_model.CpSolver()
solver.parameters.log_search_progress = True
status = solver.Solve(model)

print(f"\n{'=' * 70}")
print("RESULTS")
print("=" * 70)

status_name = solver.StatusName(status)
print(f"\nSolver status: {status_name}")
print(f"Solve time: {solver.WallTime():.3f}s")
print(f"Branches: {solver.NumBranches()}")
print(f"Conflicts: {solver.NumConflicts()}")

if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    print(f"\n✓ SOLUTION FOUND!")
    print(f"\nItinerary:")

    for day in range(DURATION_DAYS):
        print(f"\n  Day {day}:")
        day_pois = []
        for pos in range(MAX_POIS_PER_DAY):
            for i in range(NUM_POIS):
                if solver.Value(visit_vars[i][day][pos]) == 1:
                    day_pois.append(test_pois[i]['poi'])
                    print(f"    Position {pos}: {test_pois[i]['poi']} ({test_pois[i]['estimated_hours']}h)")

        # Calculate day total
        day_visit_hours = sum(test_pois[i]['estimated_hours'] for i in range(NUM_POIS)
                             for pos in range(MAX_POIS_PER_DAY)
                             if solver.Value(visit_vars[i][day][pos]) == 1)
        day_walk_hours = len(day_pois) * 0.20
        day_total = day_visit_hours + day_walk_hours
        print(f"    Total: {day_visit_hours}h visits + {day_walk_hours}h walk = {day_total}h")

        if day_total > MAX_HOURS_PER_DAY:
            print(f"    ❌ EXCEEDS LIMIT ({MAX_HOURS_PER_DAY}h)")
        else:
            print(f"    ✓ Within limit ({MAX_HOURS_PER_DAY}h)")

elif status == cp_model.INFEASIBLE:
    print(f"\n❌ INFEASIBLE - No solution exists")
    print(f"\nPossible causes:")
    print(f"  1. Combo ticket constraints force too many POIs on one day")
    print(f"  2. Daily hour constraint is too tight")
    print(f"  3. Position-based time windows block necessary slots")
    print(f"  4. Combination of constraints creates logical impossibility")

    print(f"\nManual verification:")
    print(f"  Archaeological (Day 0): 5.5h visits + 0.6h walk = 6.1h ≤ {MAX_HOURS_PER_DAY}h ✓")
    print(f"  Vatican (Day 1): 3.8h visits + 0.4h walk = 4.2h ≤ {MAX_HOURS_PER_DAY}h ✓")
    print(f"\n  Both days individually satisfy the constraint!")
    print(f"  → The bug must be in how constraints interact, not the constraint itself")

else:
    print(f"\n⚠️  Other status: {status_name}")

print(f"\n{'=' * 70}")
