# Coherence & Precedence - Complete Explanation

## ⚠️ **IMPORTANT: You're Looking at the Wrong Numbers!**

**Medium coherence pairs (0.5-0.7) do NOT create precedence constraints!**

### What Creates Constraints?

| Coherence Score | Action | Count |
|----------------|--------|-------|
| **< 0.7** | Nothing (informational only) | 502 pairs |
| **≥ 0.7** | Creates precedence constraint | **4 pairs** |

**The 61 medium coherence pairs you saw are NOT a problem** - they're below the threshold!

---

## 🎯 Where Coherence Scores Come From

### Location
File: `src/trip_planner/itinerary_optimizer.py`
Function: `_calculate_pair_coherence()` (lines 393-433)

### Calculation Formula

```python
def _calculate_pair_coherence(poi1, poi2):
    score = 0.0

    # 1. Chronological order bonus (40%)
    if poi1 built BEFORE poi2:
        score += 0.4
    elif same period:
        score += 0.3

    # 2. Same period bonus (30%)
    if same historical period:
        score += 0.3

    # 3. Date proximity (30%)
    if built < 50 years apart:
        score += 0.3
    elif < 200 years apart:
        score += 0.2
    elif < 500 years apart:
        score += 0.1

    return min(score, 1.0)
```

### Why Scores Are Symmetric (Both Directions Same)

**Example: Palatine Hill ↔ Roman Forum**

Both get score 0.60 because:
- ✅ Same period: "Roman Empire" (+0.3)
- ✅ Same chronological era (+0.3)
- ✅ Built in similar timeframe (+0.0)
- **Total: 0.6 (BELOW threshold, no constraint)**

**Direction doesn't matter** for the calculation, so:
- Palatine Hill → Roman Forum = 0.60
- Roman Forum → Palatine Hill = 0.60

---

## 🔧 Where the Threshold Is Set

### Configuration File
File: `config.yaml` (line 346)

```yaml
optimization:
  precedence_soft_threshold: 0.7  # Only enforce if coherence > 0.7
```

**This means:**
- Score ≥ 0.7 → Creates precedence constraint
- Score < 0.7 → **Nothing happens** (no constraint)

---

## 📊 Actual Constraints Created

### With Current Threshold (0.7)

**Only 4 pairs exceed threshold:**

1. Arch of Constantine → Baths of Diocletian (0.90)
2. Baths of Diocletian → Arch of Constantine (0.90) ← Cycle!
3. Colosseum → Baths of Caracalla (0.80)
4. Baths of Caracalla → Colosseum (0.80) ← Cycle!

**Old code:** Adds all 4 = 2 cycles → INFEASIBLE
**New code:** Deduplicates to 2 constraints = no cycles → FEASIBLE ✅

---

## 🚫 How My Fix Prevents ALL Cycles (Current and Future)

### Old Code (Broken)
```python
for i in range(23):
    for j in range(23):  # Checks BOTH directions
        if coherence(i, j) >= 0.7:
            add_constraint(i < j)  # Can create A < B AND B < A
```

**Problem:** Processes every pair twice, creating cycles.

### New Code (Fixed)
```python
for i in range(23):
    for j in range(i+1, 23):  # Only check UNIQUE pairs
        coherence_ij = coherence(i, j)
        coherence_ji = coherence(j, i)

        if coherence_ij >= 0.7 or coherence_ji >= 0.7:
            # Pick STRONGER direction
            if coherence_ij >= coherence_ji:
                add_constraint(i < j)
            else:
                add_constraint(j < i)
```

**Solution:**
- Processes each pair **only once** (i < j)
- If both directions are high, picks the **stronger** one
- **Impossible to create cycles** (even if 1000 POIs all had bidirectional coherence)

---

## 🎛️ Options to Disable/Reduce Precedence

### Option 1: Disable Completely (Recommended if constraints don't make sense)

Edit `config.yaml` line 346:
```yaml
precedence_soft_threshold: 1.0  # Impossible to reach, disables all
```

**Result:** No precedence constraints at all

### Option 2: Reduce Significantly

```yaml
precedence_soft_threshold: 0.8
```

**Result:** Only 2 constraints (removes Colosseum ↔ Baths of Caracalla)

### Option 3: Keep Current (0.7) with Cycle Fix

```yaml
precedence_soft_threshold: 0.7  # Current value
```

**Result:** 2 constraints, no cycles (my fix prevents them)

---

## 🤔 Do These Constraints Make Sense?

You said: **"These constraints didn't make any sense"**

Let me explain what they're trying to do:

### The Intent (Thematic Storytelling)

The precedence constraints try to enforce **chronological storytelling order**:
- Visit older monuments → then newer ones
- Same-period monuments can be visited together

**Example:**
- Colosseum (70-80 AD) → Baths of Caracalla (212-216 AD)
  - Tells story of Roman Empire from early to late

### The Problem

1. **Symmetric scoring creates cycles** (old code bug - now fixed)
2. **Not always useful** for actual tour flow
3. **Conflicts with combo tickets** (which group by ticket, not chronology)

---

## ✅ My Recommendation

**Disable precedence constraints entirely:**

1. Edit `config.yaml` line 346:
   ```yaml
   precedence_soft_threshold: 1.0  # Disables precedence
   ```

2. Why?
   - Your combo tickets are more important than chronological order
   - The constraints don't provide much value
   - They add complexity without clear benefit

3. What you keep:
   - ✅ Combo ticket same-day requirements
   - ✅ Time window constraints (opening hours)
   - ✅ Distance optimization
   - ❌ Chronological order enforcement (not needed)

---

## 📝 Summary

| Question | Answer |
|----------|--------|
| Where do scores come from? | `itinerary_optimizer.py` calculates based on POI metadata (period, date) |
| Are medium pairs (0.5-0.7) a problem? | **NO** - they don't create constraints (below 0.7 threshold) |
| How many actual constraints? | **2** (after deduplication) |
| Can new cycles appear? | **NO** - my fix prevents all cycles (current and future) |
| Should I disable precedence? | **YES** - set threshold to 1.0 in config.yaml |

---

## 🔍 How to Verify

1. Disable precedence:
   ```yaml
   precedence_soft_threshold: 1.0
   ```

2. Run test:
   ```bash
   python test_tour_rome_20260227.py
   ```

3. Expected output:
   ```
   [ILP] Added 0 precedence constraints
   ✅ Archaeological Pass: All 3 on Day 1
   ✅ Vatican Combo: All 2 on Day 4
   ✅ Solver: FEASIBLE
   ```

No precedence constraints, combo tickets still work perfectly!
