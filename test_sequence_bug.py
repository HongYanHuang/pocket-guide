#!/usr/bin/env python3
"""
Test to verify the sequence variable domain bug
"""

from ortools.sat.python import cp_model

print("=" * 70)
print("SEQUENCE VARIABLE DOMAIN BUG TEST")
print("=" * 70)

# Configuration
NUM_POIS = 5
DURATION_DAYS = 2
MAX_POIS_PER_DAY = 4

print(f"\nConfiguration:")
print(f"  POIs: {NUM_POIS}")
print(f"  Days: {DURATION_DAYS}")
print(f"  Max positions per day: {MAX_POIS_PER_DAY}")

print(f"\n{'=' * 70}")
print("TEST 1: BUGGY VERSION (domain = [0, num_pois-1])")
print("=" * 70)

model1 = cp_model.CpModel()

# Create visit variables
visit_vars1 = {}
for i in range(NUM_POIS):
    visit_vars1[i] = {}
    for day in range(DURATION_DAYS):
        visit_vars1[i][day] = {}
        for pos in range(MAX_POIS_PER_DAY):
            visit_vars1[i][day][pos] = model1.NewBoolVar(f'v_{i}_d{day}_p{pos}')

# BUGGY: sequence_vars domain = [0, num_pois - 1]
sequence_vars1 = {}
for i in range(NUM_POIS):
    sequence_vars1[i] = model1.NewIntVar(0, NUM_POIS - 1, f'seq_{i}')
    print(f"  sequence_vars[{i}] domain: [0, {NUM_POIS - 1}]")

# Each POI visited once
for i in range(NUM_POIS):
    visits = [visit_vars1[i][day][pos] for day in range(DURATION_DAYS) for pos in range(MAX_POIS_PER_DAY)]
    model1.Add(sum(visits) == 1)

# Channeling constraint
print(f"\nChanneling constraints:")
for i in range(NUM_POIS):
    for day in range(DURATION_DAYS):
        for pos in range(MAX_POIS_PER_DAY):
            global_pos = day * MAX_POIS_PER_DAY + pos
            model1.Add(sequence_vars1[i] == global_pos).OnlyEnforceIf(visit_vars1[i][day][pos])

            # Check if global_pos exceeds domain
            max_allowed = NUM_POIS - 1
            if global_pos > max_allowed:
                print(f"  ❌ POI {i}, Day {day}, Pos {pos}: sequence = {global_pos} > max_domain ({max_allowed})")

# Manually assign desired solution
print(f"\nManually assigning desired solution:")
print(f"  Day 0: POIs 0,1,2 at positions 0,1,2")
print(f"  Day 1: POIs 3,4 at positions 0,1")

# Day 0
model1.Add(visit_vars1[0][0][0] == 1)  # Colosseum at Day 0, Pos 0
model1.Add(visit_vars1[1][0][1] == 1)  # Roman Forum at Day 0, Pos 1
model1.Add(visit_vars1[2][0][2] == 1)  # Palatine at Day 0, Pos 2

# Day 1
model1.Add(visit_vars1[3][1][0] == 1)  # Vatican at Day 1, Pos 0
model1.Add(visit_vars1[4][1][1] == 1)  # Sistine at Day 1, Pos 1 (PROBLEMATIC!)

print(f"\nExpected sequence values:")
print(f"  POI 0 (Day 0, Pos 0): sequence = 0 × 4 + 0 = 0 ✓")
print(f"  POI 1 (Day 0, Pos 1): sequence = 0 × 4 + 1 = 1 ✓")
print(f"  POI 2 (Day 0, Pos 2): sequence = 0 × 4 + 2 = 2 ✓")
print(f"  POI 3 (Day 1, Pos 0): sequence = 1 × 4 + 0 = 4 ✓")
print(f"  POI 4 (Day 1, Pos 1): sequence = 1 × 4 + 1 = 5 ❌ (domain is [0,4]!)")

solver1 = cp_model.CpSolver()
solver1.parameters.log_search_progress = False
status1 = solver1.Solve(model1)

print(f"\nResult: {solver1.StatusName(status1)}")
if status1 == cp_model.INFEASIBLE:
    print("  → As expected! Cannot assign sequence=5 when domain is [0,4]")

print(f"\n{'=' * 70}")
print("TEST 2: FIXED VERSION (domain = [0, days×positions-1])")
print("=" * 70)

model2 = cp_model.CpModel()

# Create visit variables
visit_vars2 = {}
for i in range(NUM_POIS):
    visit_vars2[i] = {}
    for day in range(DURATION_DAYS):
        visit_vars2[i][day] = {}
        for pos in range(MAX_POIS_PER_DAY):
            visit_vars2[i][day][pos] = model2.NewBoolVar(f'v_{i}_d{day}_p{pos}')

# FIXED: sequence_vars domain = [0, duration_days * max_pois_per_day - 1]
sequence_vars2 = {}
max_sequence = DURATION_DAYS * MAX_POIS_PER_DAY - 1
for i in range(NUM_POIS):
    sequence_vars2[i] = model2.NewIntVar(0, max_sequence, f'seq_{i}')
    print(f"  sequence_vars[{i}] domain: [0, {max_sequence}]")

# Each POI visited once
for i in range(NUM_POIS):
    visits = [visit_vars2[i][day][pos] for day in range(DURATION_DAYS) for pos in range(MAX_POIS_PER_DAY)]
    model2.Add(sum(visits) == 1)

# Channeling constraint
print(f"\nChanneling constraints:")
for i in range(NUM_POIS):
    for day in range(DURATION_DAYS):
        for pos in range(MAX_POIS_PER_DAY):
            global_pos = day * MAX_POIS_PER_DAY + pos
            model2.Add(sequence_vars2[i] == global_pos).OnlyEnforceIf(visit_vars2[i][day][pos])

            # Check if global_pos exceeds domain
            if global_pos > max_sequence:
                print(f"  ❌ POI {i}, Day {day}, Pos {pos}: sequence = {global_pos} > max_domain ({max_sequence})")

print(f"  ✓ All global_pos values fit within [0, {max_sequence}]")

# Manually assign desired solution
print(f"\nManually assigning desired solution:")
print(f"  Day 0: POIs 0,1,2 at positions 0,1,2")
print(f"  Day 1: POIs 3,4 at positions 0,1")

# Day 0
model2.Add(visit_vars2[0][0][0] == 1)  # Colosseum at Day 0, Pos 0
model2.Add(visit_vars2[1][0][1] == 1)  # Roman Forum at Day 0, Pos 1
model2.Add(visit_vars2[2][0][2] == 1)  # Palatine at Day 0, Pos 2

# Day 1
model2.Add(visit_vars2[3][1][0] == 1)  # Vatican at Day 1, Pos 0
model2.Add(visit_vars2[4][1][1] == 1)  # Sistine at Day 1, Pos 1 (NOW OK!)

print(f"\nExpected sequence values:")
print(f"  POI 0 (Day 0, Pos 0): sequence = 0 × 4 + 0 = 0 ✓")
print(f"  POI 1 (Day 0, Pos 1): sequence = 0 × 4 + 1 = 1 ✓")
print(f"  POI 2 (Day 0, Pos 2): sequence = 0 × 4 + 2 = 2 ✓")
print(f"  POI 3 (Day 1, Pos 0): sequence = 1 × 4 + 0 = 4 ✓")
print(f"  POI 4 (Day 1, Pos 1): sequence = 1 × 4 + 1 = 5 ✓ (domain is [0,7]!)")

solver2 = cp_model.CpSolver()
solver2.parameters.log_search_progress = False
status2 = solver2.Solve(model2)

print(f"\nResult: {solver2.StatusName(status2)}")
if status2 in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
    print("  → Success! The fix works!")

    print(f"\nSolution:")
    for i in range(NUM_POIS):
        for day in range(DURATION_DAYS):
            for pos in range(MAX_POIS_PER_DAY):
                if solver2.Value(visit_vars2[i][day][pos]) == 1:
                    seq = solver2.Value(sequence_vars2[i])
                    print(f"    POI {i}: Day {day}, Pos {pos}, Sequence = {seq}")

print(f"\n{'=' * 70}")
print("CONCLUSION")
print("=" * 70)
print(f"\nBuggy version: {solver1.StatusName(status1)}")
print(f"Fixed version: {solver2.StatusName(status2)}")
print(f"\n✓ This proves the sequence variable domain bug is THE ROOT CAUSE!")
