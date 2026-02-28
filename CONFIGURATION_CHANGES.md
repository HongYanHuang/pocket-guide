# Configuration Changes - Precedence Disabled

## Change Made

**File**: `config.yaml` (line 346)

**Before:**
```yaml
precedence_soft_threshold: 0.7  # Only enforce if coherence > 0.7
```

**After:**
```yaml
precedence_soft_threshold: 1.0  # Disabled (was 0.7) - no precedence constraints
```

---

## Why This Change?

### Problem
Precedence constraints were:
1. Creating cyclic dependencies (A before B AND B before A)
2. Conflicting with combo ticket requirements
3. Not providing significant value for tour planning

### Solution
Disable precedence constraints entirely by setting threshold to 1.0 (impossible to reach).

---

## Test Results (SUCCESSFUL ✅)

```bash
python test_tour_rome_20260227.py
```

**Output:**
```
[ILP] Precedence threshold: 1.0
[ILP] Added 0 precedence constraints (coherence >= 1.0)
[ILP] Solver finished with status: FEASIBLE

✅ Archaeological Pass: All 3 POIs on Day 1
   - Colosseum
   - Roman Forum
   - Palatine Hill

✅ Vatican Combo: All 2 POIs on Day 3
   - Vatican Museums
   - Sistine Chapel

Solver: FEASIBLE in 30.02s
Distance score: 0.64
Coherence: 0.34
```

---

## What Still Works

| Feature | Status |
|---------|--------|
| Combo ticket same-day requirements | ✅ Working |
| Time window constraints (opening hours) | ✅ Working |
| Distance optimization | ✅ Working |
| TSP constraints | ✅ Working |
| Coherence scoring | ✅ Working (for objective, not constraints) |

---

## What's Removed

| Feature | Status |
|---------|--------|
| Precedence constraints (chronological ordering) | ❌ Disabled |

**Impact**: Minimal - chronological ordering is less important than:
- Visiting combo ticket POIs together (saves money)
- Respecting opening hours (can't visit closed sites)
- Minimizing walking distance (better experience)

---

## If You Want to Re-enable

Edit `config.yaml` line 346:

```yaml
precedence_soft_threshold: 0.7  # Re-enable precedence
```

**Note**: This may cause INFEASIBLE issues if coherence scores create cycles. The cycle-prevention fix is already in place, so it should work, but disabling is recommended.

---

## For Future Setup

When setting up on a new machine or for other users:

1. Copy `config.example.yaml` to `config.yaml`
2. Add your API keys
3. **Set this value**:
   ```yaml
   optimization:
     precedence_soft_threshold: 1.0  # Recommended: disabled
   ```

---

## Technical Details

**What precedence constraints do:**
- Enforce visiting order based on "coherence" (thematic similarity)
- Example: Visit older monuments before newer ones for chronological storytelling

**Why they conflict:**
- Combo tickets group by ticket type (not chronology)
- Symmetric coherence creates cycles (A→B score 0.8, B→A score 0.8)
- Adds complexity without clear benefit

**Conclusion:** Better to disable and let combo tickets + distance + time windows drive the optimization.

---

## Verification Commands

Check current setting:
```bash
grep precedence_soft_threshold config.yaml
```

Run test:
```bash
python test_tour_rome_20260227.py
```

Expected: `[ILP] Added 0 precedence constraints`
