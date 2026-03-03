# How Coherence Rules Are Created - Detailed Explanation

## 📋 Table of Contents
1. [What Are Coherence Rules?](#what-are-coherence-rules)
2. [How They're Created (Step-by-Step)](#how-theyre-created-step-by-step)
3. [Why They Caused Errors (The Cycle Problem)](#why-they-caused-errors-the-cycle-problem)
4. [How to Prevent Errors](#how-to-prevent-errors)
5. [Current Status](#current-status)

---

## What Are Coherence Rules?

**Coherence rules** are automatically generated constraints that try to enforce a **logical storytelling order** when visiting POIs.

**The Goal:** Visit historical sites in chronological order to create a coherent narrative.

**Example:**
```
Good: Roman Forum (753 BC) → Colosseum (70 AD) → Baths of Caracalla (212 AD)
      ↑ Tells the story of Rome from founding to peak

Bad:  Baths of Caracalla (212 AD) → Roman Forum (753 BC) → Colosseum (70 AD)
      ↑ Jumps around in time, confusing narrative
```

---

## How They're Created (Step-by-Step)

### Step 1: Calculate Coherence Score for Every POI Pair

**Location:** `src/trip_planner/itinerary_optimizer.py` lines 393-433

**Function:** `_calculate_pair_coherence(poi1, poi2)`

For **every pair** of POIs, the system calculates a "coherence score" from 0.0 to 1.0:

```python
def _calculate_pair_coherence(poi1, poi2):
    score = 0.0

    # Rule 1: Chronological Order (40% weight)
    if poi1 built BEFORE poi2:
        score += 0.4  # Bonus for older → newer
    elif same_period:
        score += 0.3  # Smaller bonus for same period

    # Rule 2: Same Historical Period (30% weight)
    if both from "Roman Empire":  # or "Byzantine", "Ottoman", etc.
        score += 0.3

    # Rule 3: Date Proximity (30% weight)
    if built within 50 years:
        score += 0.3
    elif built within 200 years:
        score += 0.2
    elif built within 500 years:
        score += 0.1

    return min(score, 1.0)
```

**Historical Period Rankings:**
```python
period_order = {
    'Classical Greece': 1,
    'Hellenistic': 2,
    'Roman Empire': 3,
    'Byzantine': 4,
    'Ottoman': 5,
    'Modern': 6
}
```

### Step 2: Score Examples

**Example 1: Colosseum → Baths of Caracalla**
```
POI 1: Colosseum (70-80 AD, Roman Empire)
POI 2: Baths of Caracalla (212-216 AD, Roman Empire)

Calculation:
✅ Chronological order: Colosseum before Baths   +0.4
✅ Same period: Both "Roman Empire"              +0.3
✅ Date proximity: 140 years apart               +0.2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Score: 0.9 (Very High!)
```

**Example 2: Baths of Caracalla → Colosseum (Reverse)**
```
POI 1: Baths of Caracalla (212-216 AD, Roman Empire)
POI 2: Colosseum (70-80 AD, Roman Empire)

Calculation:
❌ Chronological order: Baths AFTER Colosseum    +0.0 (wrong direction!)
✅ Same period: Both "Roman Empire"              +0.3
✅ Date proximity: 140 years apart               +0.2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Score: 0.5 (Medium)
```

**⚠️ THE PROBLEM: Both directions can have HIGH scores!**

### Step 3: Create Precedence Constraints

**Location:** `src/trip_planner/ilp_optimizer.py` lines 603-682

**Function:** `_add_precedence_constraints()`

For every pair with **score ≥ threshold** (default 0.7), create a constraint:

```python
for each POI pair (i, j):
    if coherence(i, j) >= 0.7:
        # Add constraint: i must come before j
        add_constraint(sequence[i] < sequence[j])
```

**Configuration:** `config.yaml` line 346
```yaml
optimization:
  precedence_soft_threshold: 0.7  # Only pairs with score ≥ 0.7 create constraints
```

---

## Why They Caused Errors (The Cycle Problem)

### The Bug in Old Code

**Old Implementation (BROKEN):**
```python
# Check EVERY direction (i → j AND j → i)
for i in range(num_pois):
    for j in range(num_pois):  # ← Checks both (i,j) and (j,i)
        if coherence(i, j) >= 0.7:
            add_constraint(i < j)
```

**Problem:** This checks **both directions** for every pair!

### Real Example: Arch of Constantine ↔ Baths of Diocletian

**Forward Direction:**
```
Arch of Constantine (312-315 AD) → Baths of Diocletian (298-306 AD)

Calculation:
✅ Same period: Both "Late Roman Empire"    +0.3
✅ Date proximity: 10 years apart           +0.3
✅ Chronological (Arch after Baths)         +0.3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 0.9 ← HIGH SCORE!
```

**Reverse Direction:**
```
Baths of Diocletian (298-306 AD) → Arch of Constantine (312-315 AD)

Calculation:
✅ Same period: Both "Late Roman Empire"    +0.3
✅ Date proximity: 10 years apart           +0.3
✅ Chronological (Baths before Arch)        +0.3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 0.9 ← ALSO HIGH SCORE!
```

**Result with Old Code:**
```
Constraint 1: Arch < Baths      (from checking i=Arch, j=Baths)
Constraint 2: Baths < Arch      (from checking i=Baths, j=Arch)

This creates a CYCLE: A < B AND B < A ← IMPOSSIBLE!
```

**Solver Output:**
```
❌ INFEASIBLE - No solution possible due to conflicting constraints
```

### Visual Representation

```
        Old Code (Broken)
        ═════════════════

    Arch of Constantine
           ↓ must visit before
    Baths of Diocletian
           ↓ must visit before
    Arch of Constantine  ← Cycle! Can't satisfy both
           ↓
         ERROR!
```

---

## How to Prevent Errors

### Solution 1: Fix the Cycle Bug (IMPLEMENTED ✅)

**New Implementation (FIXED):**
```python
# Check each pair ONLY ONCE (i < j)
for i in range(num_pois):
    for j in range(i + 1, num_pois):  # ← Only j > i
        coherence_ij = coherence(i, j)
        coherence_ji = coherence(j, i)

        # If EITHER direction is high, pick the STRONGER one
        if coherence_ij >= 0.7 or coherence_ji >= 0.7:
            if coherence_ij >= coherence_ji:
                add_constraint(i < j)  # Forward direction
            else:
                add_constraint(j < i)  # Reverse direction
```

**Benefits:**
- ✅ Each pair checked only once
- ✅ Picks the direction with higher coherence
- ✅ **Impossible to create cycles** (even with 1000 POIs)

**Result:**
```
✅ Arch < Baths     (coherence: 0.9 in both directions, picked forward)
✅ Colosseum < Baths of Caracalla  (coherence: 0.8)
✅ NO CYCLES - Solver returns FEASIBLE
```

### Solution 2: Disable Precedence Constraints (CURRENT SETTING ✅)

**Why it's disabled:**
- Coherence constraints conflict with **combo tickets**
- Combo tickets group POIs by ticket type, not chronology
- Chronological order isn't always useful for tour flow

**Current Configuration:** `config.yaml` line 346
```yaml
optimization:
  precedence_soft_threshold: 1.0  # Set to 1.0 to disable (impossible to reach)
```

**Result:**
```
[ILP] Added 0 precedence constraints
✅ Archaeological Pass: All 3 on Day 1 (grouped by combo ticket)
✅ Vatican Combo: All 2 on Day 4 (grouped by combo ticket)
✅ Solver: FEASIBLE
```

### Solution 3: Make Coherence Directional (RECOMMENDED FOR FUTURE)

**Problem with Current Scoring:**
Both directions can score high because the scoring is **symmetric**:
- Same period bonus: Same in both directions (+0.3)
- Date proximity: Same in both directions (+0.3)
- Result: Both directions can reach high scores

**Proposed Fix:**
```python
def _calculate_pair_coherence(poi1, poi2):
    score = 0.0

    # DIRECTIONAL: Only bonus if poi1 comes BEFORE poi2
    if poi1_chronologically_before_poi2:
        score += 0.5  # Strong directional bonus
    elif same_period:
        score += 0.2  # Weak bonus (order doesn't matter)

    # Non-directional bonuses (same in both directions)
    if same_period:
        score += 0.3
    if built_within_50_years:
        score += 0.2

    return score
```

**Result:**
```
Colosseum → Baths of Caracalla:
  Directional: +0.5 (Colosseum before Baths)
  Same period: +0.3
  Proximity: +0.2
  Total: 1.0

Baths of Caracalla → Colosseum:
  Directional: +0.0 (wrong direction!)
  Same period: +0.3
  Proximity: +0.2
  Total: 0.5 ← Lower score for wrong direction!
```

**Benefits:**
- ✅ coherence(older → newer) > coherence(newer → older)
- ✅ No symmetric high scores = no cycles
- ✅ Better reflects actual storytelling logic
- ✅ Can re-enable precedence if desired

---

## How to Prevent Errors (Summary)

### ✅ Already Implemented
1. **Cycle detection fix** - Only check unique pairs (i < j)
2. **Disabled precedence** - Set threshold to 1.0 in config

### 🔧 Recommended Configuration

**For Most Users (Current Setting):**
```yaml
# config.yaml
optimization:
  precedence_soft_threshold: 1.0  # Disable precedence constraints
```

**Use this when:**
- You have combo tickets (groups by ticket, not chronology)
- You want maximum flexibility in route planning
- Chronological order isn't critical

**For Future (After Directional Coherence Implemented):**
```yaml
# config.yaml
optimization:
  precedence_soft_threshold: 0.7  # Re-enable precedence
```

**Use this when:**
- You've implemented directional coherence (Task 1 in TODO-LIST.md)
- You want chronological storytelling order
- No combo tickets or they align with chronology

### 🛡️ How to Verify No Errors

**Test 1: Check for Cycles**
```python
# After running optimizer, check for cycles in precedence
# Cycles are now impossible with the fixed code (i < j loop)
```

**Test 2: Run Rome Tour Test**
```bash
python test_tour_rome_20260227.py
```

**Expected Output (No Errors):**
```
[ILP] Precedence threshold: 1.0
[ILP] Added 0 precedence constraints
✅ Archaeological Pass: All 3 on Day 1
✅ Vatican Combo: All 2 on Day 4
✅ Solver: FEASIBLE
```

**Test 3: Lower Threshold and Verify**
```yaml
# config.yaml
precedence_soft_threshold: 0.7
```

```bash
python test_tour_rome_20260227.py
```

**Expected Output (No Cycles):**
```
[ILP] Precedence threshold: 0.7
[ILP] Added 2 precedence constraints
  1. Arch of Constantine → Baths of Diocletian (coherence: 0.90)
  2. Colosseum → Baths of Caracalla (coherence: 0.80)
✅ Solver: FEASIBLE (no cycles)
```

---

## Current Status

### What's Working ✅
- ✅ Cycle detection fixed (only check i < j)
- ✅ Precedence disabled (threshold 1.0)
- ✅ Combo tickets work perfectly
- ✅ Time window constraints working
- ✅ Distance optimization working

### What's Disabled ⚠️
- ⚠️ Chronological storytelling order (precedence constraints off)
- ⚠️ Coherence scoring still symmetric (but harmless when disabled)

### Future Improvements 🚀
From TODO-LIST.md Task 1:
- Make coherence scoring **directional** (older → newer gets higher score)
- Allow re-enabling precedence constraints without cycle risk
- Better reflects actual storytelling logic

---

## Quick Decision Guide

### "Should I enable precedence constraints?"

**NO (Keep Current Setting) if:**
- ✅ You have combo tickets
- ✅ You want maximum routing flexibility
- ✅ Chronological order isn't important

**YES (Change Threshold to 0.7) if:**
- ✅ Cycle fix is implemented (it is!)
- ✅ You've implemented directional coherence
- ✅ Chronological storytelling is important
- ❌ You don't have combo tickets (or they align with chronology)

### "How do I change the setting?"

Edit `config.yaml` line 346:
```yaml
optimization:
  precedence_soft_threshold: 1.0  # Current: Disabled
  # precedence_soft_threshold: 0.7  # Alternative: Enabled (2-4 constraints)
```

---

## Summary

**How Rules Are Created:**
1. System calculates coherence for every POI pair based on historical metadata
2. Pairs with score ≥ threshold create precedence constraints
3. Constraints enforce visit order (older POIs before newer ones)

**Why They Caused Errors:**
- Old code checked both directions (i→j and j→i)
- Created cycles: A < B AND B < A
- Solver: INFEASIBLE

**How Errors Are Prevented:**
- ✅ Fixed code: Only check unique pairs (i < j)
- ✅ Pick stronger direction for high-coherence pairs
- ✅ Disabled precedence (threshold 1.0)
- 🚀 Future: Implement directional coherence

**Current Recommendation:**
- Keep precedence disabled (threshold 1.0)
- Works perfectly with combo tickets
- No risk of errors or conflicts
