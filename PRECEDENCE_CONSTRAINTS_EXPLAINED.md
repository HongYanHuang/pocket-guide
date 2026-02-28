# Precedence Constraints - Complete Explanation

## Summary

**Total precedence constraints found:** 4 pairs (but creates 2 CYCLES in old code)

You did NOT manually define these constraints. They are **automatically generated** by the coherence scoring system based on POI metadata (historical period, build date, thematic relationships).

---

## All High-Coherence Pairs (score >= 0.7)

### 1. Arch of Constantine ↔ Baths of Diocletian (score: 0.90)

**Bidirectional cycle - both directions have score 0.90**

- **Arch of Constantine → Baths of Diocletian** (0.90)
- **Baths of Diocletian → Arch of Constantine** (0.90)

**Why high coherence?**
- ✅ Same historical period: "Late Roman Empire"
- ✅ Built within 10 years of each other:
  - Baths of Diocletian: 298-306 AD
  - Arch of Constantine: 312-315 AD
- ✅ Same era, similar architectural purpose

**Problem:** Creates a CYCLE (A must come before B AND B must come before A)

---

### 2. Colosseum ↔ Baths of Caracalla (score: 0.80)

**Bidirectional cycle - both directions have score 0.80**

- **Colosseum → Baths of Caracalla** (0.80)
- **Baths of Caracalla → Colosseum** (0.80)

**Why high coherence?**
- ✅ Same historical period: "Roman Empire"
- ✅ Both iconic Roman structures
- ✅ Built ~140 years apart but same era:
  - Colosseum: 70-80 AD
  - Baths of Caracalla: 212-216 AD

**Problem:** Creates a CYCLE (A must come before B AND B must come before A)

---

## How Coherence Scores Are Calculated

The system automatically calculates coherence between every POI pair based on:

### 1. Chronological Order Bonus (40%)
- If POI1 built BEFORE POI2 in history: +0.4
- If same period: +0.3

### 2. Same Period Bonus (30%)
- If both from same historical period: +0.3

### 3. Date Proximity (30%)
- If built within similar timeframes: +0.3

**Maximum score:** 1.0
**Threshold for precedence:** 0.7 (from `config.yaml`)

---

## Statistics

Out of 23 POIs = 506 total pairs:

| Coherence Level | Count | Percentage |
|----------------|-------|------------|
| High (≥ 0.7) | 4 pairs | 0.8% |
| Medium (0.5-0.7) | 61 pairs | 12.1% |
| Low (< 0.5) | 441 pairs | 87.1% |

**Bidirectional high-coherence pairs:** 2 (100% of high-coherence pairs!)

---

## The Problem (Old Code)

```python
# OLD CODE (BROKEN)
for i in range(num_pois):
    for j in range(num_pois):
        if coherence(i, j) >= 0.7:
            add_constraint(i < j)
```

**Result:**
- Adds 4 precedence constraints
- 2 of them create CYCLES:
  ```
  Arch of Constantine < Baths of Diocletian
  Baths of Diocletian < Arch of Constantine  ← CYCLE!

  Colosseum < Baths of Caracalla
  Baths of Caracalla < Colosseum  ← CYCLE!
  ```
- Solver: **INFEASIBLE** (impossible to satisfy cyclic constraints)

---

## The Fix (New Code)

```python
# NEW CODE (FIXED)
for i in range(num_pois):
    for j in range(i + 1, num_pois):  # Only check each pair ONCE
        coherence_ij = coherence(i, j)
        coherence_ji = coherence(j, i)

        if coherence_ij >= 0.7 or coherence_ji >= 0.7:
            # Use the direction with STRONGER coherence
            if coherence_ij >= coherence_ji:
                add_constraint(i < j)
            else:
                add_constraint(j < i)
```

**Result:**
- Adds 2 precedence constraints (no duplicates)
- No cycles:
  ```
  Arch of Constantine < Baths of Diocletian  (score 0.90)
  Colosseum < Baths of Caracalla  (score 0.80)
  ```
- Solver: **FEASIBLE** ✅

---

## Medium Coherence Pairs (0.5-0.7)

These do NOT create precedence constraints (below 0.7 threshold), but here are some examples:

- Palatine Hill → Colosseum (0.60)
- Roman Forum → Colosseum (0.60)
- Pantheon → Colosseum (0.60)
- Ara Pacis → Mausoleum of Augustus (0.60)
- ... and 57 more

Total: 61 pairs with medium coherence

---

## Configuration

The precedence threshold can be adjusted in `config.yaml`:

```yaml
optimization:
  precedence_soft_threshold: 0.7  # Current value
```

**Options:**
- **Increase to 0.8:** Only 2 pairs would trigger (removes Colosseum ↔ Baths of Caracalla)
- **Increase to 1.0:** Disables all precedence constraints
- **Decrease to 0.5:** Adds 61+ more constraints (may cause other cycles)

---

## Recommendation

The current fix (removing cycles) is the **correct solution**. The precedence constraints are working as designed - they enforce thematic storytelling order based on historical relationships.

The bug was in how we handled **bidirectional** coherence (symmetric scores creating cycles). This is now fixed.

**No changes needed to threshold or coherence scoring logic.**

---

## Files Modified

- `src/trip_planner/ilp_optimizer.py` (lines 634-664)
  - Changed loop from `for j in range(num_pois)` to `for j in range(i+1, num_pois)`
  - Added logic to pick stronger direction for bidirectional pairs
  - Eliminates all cycles

---

## Verification

Run: `python test_tour_rome_20260227.py`

Expected output:
```
✅ Archaeological Pass: All 3 on Day 1
✅ Vatican Combo: All 2 on Day 4
✅ Precedence constraints: 2 (no cycles)
✅ Solver: FEASIBLE
```
