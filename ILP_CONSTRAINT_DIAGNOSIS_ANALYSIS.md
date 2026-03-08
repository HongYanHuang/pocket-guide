# ILP Constraint Diagnosis - Analysis

## Question 1: POI Selector Priority - Categorical or Numeric?

### Answer: **CATEGORICAL ONLY** (high / medium / low)

**Evidence from Code:**

`src/trip_planner/poi_selector_agent.py:375`:
```json
{
  "poi": "Acropolis",
  "priority": "high"  // ← String value only
}
```

**Evidence from Actual Tour:**
```bash
$ grep priority rome-tour-20260303-174552-fcf057/tour_zh-tw.json
6 POIs with "priority": "high"
3 POIs with "priority": "medium"
0 POIs with "priority": "low"
```

**Available Priority Values:**
- `"high"` - Must-see POIs
- `"medium"` - Nice-to-have POIs
- `"low"` - Optional POIs (rarely used)

**Implication:**
- Cannot directly compare priorities numerically (no 0.8 vs 0.6)
- Need to map to numbers for removal logic:
  ```python
  priority_score = {'high': 3, 'medium': 2, 'low': 1}
  ```
- Multiple POIs may have same priority (can't distinguish "most important high" from "least important high")

---

## Question 2: Can ILP Identify Which Constraint Causes Infeasibility?

### Answer: **NO - By Default, ILP Only Says "INFEASIBLE"**

**Test Result:**
```python
# Simple infeasible model
model.Add(x >= 5)
model.Add(x <= 3)  # Conflict!

status = solver.Solve(model)
# Output: Status: INFEASIBLE
# Output: SolutionInfo: Problem proven infeasible during initial copy.
```

CP-SAT does NOT automatically tell you:
- ❌ Which constraint caused the problem
- ❌ Which POI to remove
- ❌ Which day is over-packed

It only tells you:
- ✅ The model is infeasible (no solution exists)
- ✅ Number of conflicts explored (low-level search metric)

### Advanced Technique: Assumptions (Optional)

CP-SAT has a feature to identify problematic constraints, but it requires **pre-planning**:

**Method: Use Assumptions**
```python
# Mark each constraint as conditional
poi_included = {}
for i, poi in enumerate(pois):
    poi_included[i] = model.NewBoolVar(f'include_poi_{i}')

    # Make all constraints for this POI conditional
    for day in range(duration_days):
        for pos in range(max_pois_per_day):
            # Only enforce if POI is included
            model.Add(visit_vars[i][day][pos] == 0).OnlyEnforceIf(poi_included[i].Not())

# Solve with assumptions (assume all POIs should be included)
assumptions = [poi_included[i] for i in range(len(pois))]
status = solver.SolveWithAssumptions(model, assumptions)

if status == cp_model.INFEASIBLE:
    # Get which assumptions caused infeasibility
    problematic_pois = solver.SufficientAssumptionsForInfeasibility()
    print(f"Remove POIs at indices: {problematic_pois}")
```

**Pros:**
- Automatically identifies problematic POIs
- Minimal subset (removes fewest POIs needed)

**Cons:**
- Complex implementation (need to rewrite all constraints as conditional)
- Not all constraints support `OnlyEnforceIf()` (some OR-Tools limitations)
- Significant code refactoring required

**Reference:**
- [OR-Tools Issue #973: Best way to find infeasible constraints](https://github.com/google/or-tools/issues/973)
- [CP-SAT Primer: Parameters and Debugging](https://d-krupke.github.io/cpsat-primer/05_parameters.html)

### Practical Approach: Iterative Removal

Since ILP can't automatically identify which POI to remove, we need to:

**Option A: Remove by Priority (Simpler)**
```python
priority_order = {'low': 1, 'medium': 2, 'high': 3}

while status == cp_model.INFEASIBLE and retries < max_retries:
    # Find lowest priority POI
    lowest_poi = min(pois, key=lambda p: priority_order[p.get('priority', 'medium')])

    # Remove it
    pois.remove(lowest_poi)
    print(f"  Removing low-priority POI: {lowest_poi['poi']}")

    # Rebuild model and retry
    model = rebuild_model(pois)
    status = solver.Solve(model)
```

**Pros:**
- Simple to implement
- Uses existing priority information
- Fast (only rebuild model once per retry)

**Cons:**
- May remove wrong POI (priority doesn't mean it's causing infeasibility)
- If all POIs are "high" priority, which one to remove?
- Doesn't know if it's a daily hour issue or combo ticket issue

**Option B: Binary Search Removal (Faster)**
```python
# Try removing POIs in batches to narrow down the problem
def find_infeasible_pois_binary(pois):
    if solver.Solve(model_with_pois(pois)) != INFEASIBLE:
        return []  # All POIs are fine

    if len(pois) == 1:
        return pois  # This single POI causes infeasibility

    # Split in half
    mid = len(pois) // 2
    left_pois = pois[:mid]
    right_pois = pois[mid:]

    # Test each half
    left_infeasible = find_infeasible_pois_binary(left_pois)
    right_infeasible = find_infeasible_pois_binary(right_pois)

    return left_infeasible + right_infeasible
```

**Pros:**
- Faster than one-by-one removal (O(log n) instead of O(n))
- Identifies all problematic POIs

**Cons:**
- Still requires multiple solver runs
- Complex logic
- May identify multiple POIs when only one needs removal

**Option C: Remove One at a Time (Most Reliable)**
```python
for poi_to_test in sorted(pois, key=lambda p: priority_order[p.get('priority')]):
    # Try removing this POI
    test_pois = [p for p in pois if p != poi_to_test]

    model = rebuild_model(test_pois)
    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print(f"  Found solution by removing: {poi_to_test['poi']}")
        return test_pois
```

**Pros:**
- Guaranteed to find a working solution (if one exists)
- Tests removing each POI individually

**Cons:**
- Slowest approach (O(n) solver calls)
- Rebuilding model is expensive
- May need to remove multiple POIs (this only removes one)

---

## Recommendation

**Best Approach for Our Use Case:**

1. **Use Option A (Remove by Priority)** with **smart constraints**:
   ```python
   attempt = 0
   max_attempts = 5
   current_pois = pois.copy()

   while attempt < max_attempts:
       status = solver.Solve(model)

       if status == cp_model.INFEASIBLE:
           # Remove lowest priority POI
           priority_scores = {'low': 1, 'medium': 2, 'high': 3}

           # Sort by priority, then by estimated_hours (remove longer POIs first)
           lowest = min(
               current_pois,
               key=lambda p: (
                   priority_scores.get(p.get('priority', 'medium'), 2),
                   -p.get('estimated_hours', 2.0)  # Negative = longer hours first
               )
           )

           print(f"  [ILP] Removing: {lowest['poi']} (priority={lowest['priority']}, hours={lowest['estimated_hours']})")
           current_pois.remove(lowest)

           # Rebuild model with fewer POIs
           model = self._build_model(current_pois, ...)
           attempt += 1
       else:
           # Success!
           return current_pois
   ```

2. **Why This Works:**
   - Daily hour constraint is usually the issue → remove longer POIs helps most
   - Priority ensures we keep must-see POIs
   - Only 3-5 iterations needed in practice (fast)
   - No complex assumptions or model refactoring needed

3. **When It Fails:**
   - If still INFEASIBLE after 5 removals → fallback to greedy
   - If TIMEOUT or MODEL_INVALID → fallback to greedy (different issue)

---

## Summary

**Q1: Priority Score Format**
- ❌ Not numeric (0-1 scale)
- ✅ Categorical: "high" / "medium" / "low"
- Need to map to numbers for comparison

**Q2: ILP Constraint Diagnosis**
- ❌ ILP cannot automatically identify problematic constraint
- ❌ No "this constraint caused infeasibility" output
- ✅ Can use advanced "assumptions" feature (complex, requires refactoring)
- ✅ Practical solution: Remove POIs iteratively by priority + duration

**Recommended Implementation:**
- Iterative removal by priority (lowest first)
- Secondary sort by duration (remove longer POIs first, they impact hours most)
- 3-5 max retries before greedy fallback
- Simple, fast, effective for daily hour constraint issues

---

**Next Steps:**
1. Implement daily hour constraint in ILP
2. Add retry loop with priority-based POI removal
3. Test with infeasible tour (rome-tour-20260303-174552-fcf057)
