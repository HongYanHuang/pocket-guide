# How Coherence Scores Are Calculated - Complete Data Flow

## 🎯 Short Answer

**It's calculated by OUR CODE** - simple math using POI metadata. No AI, no ML, just:
```
Read POI metadata → Apply hardcoded formula → Get score
```

---

## 📊 Complete Data Flow

### Step 1: POI Metadata Storage (Where Data Comes From)

**Source Files:** `poi_research/Rome/{poi_name}.yaml`

**Example: Colosseum**
```yaml
# poi_research/Rome/colosseum.yaml
poi:
  basic_info:
    period: "Roman Empire"           ← Used in calculation!
    date_built: "70-80 AD"            ← Used in calculation!
    date_relative: "about 1,950 years ago"
    current_state: "Partially ruined amphitheater..."
```

**Example: Baths of Caracalla**
```yaml
# poi_research/Rome/baths_of_caracalla.yaml
poi:
  basic_info:
    period: "Roman Empire"           ← Used in calculation!
    date_built: "212-216 AD"          ← Used in calculation!
    date_relative: "about 1,800 years ago"
    current_state: "Massive brick ruins..."
```

**These fields are added by:**
- AI during POI research phase (`./pocket-guide poi research Rome`)
- AI analyzes historical data and assigns period + build date
- Stored in YAML format for human readability

---

### Step 2: Code Reads the Metadata

**Location:** `src/trip_planner/itinerary_optimizer.py` line 393

```python
def _calculate_pair_coherence(self, poi1: Dict, poi2: Dict) -> float:
    """Calculate coherence score between two POIs"""
    score = 0.0

    # Extract metadata from POI dictionaries
    period1 = poi1.get('period', '')      # ← Reads from POI data
    period2 = poi2.get('period', '')
    date1 = poi1.get('date_built', '')    # ← Reads from POI data
    date2 = poi2.get('date_built', '')

    # ... then applies formula (see below)
```

**Where does `poi1` come from?**
```python
# During tour planning:
pois = load_pois_from_city(city="Rome")
# Each POI dictionary contains:
# {
#   'poi': 'Colosseum',
#   'period': 'Roman Empire',      ← From YAML file
#   'date_built': '70-80 AD',       ← From YAML file
#   'coordinates': {...},
#   ...
# }
```

---

### Step 3: Apply Hardcoded Formula

**The Formula (100% in our code, zero AI/ML):**

```python
def _calculate_pair_coherence(poi1, poi2):
    score = 0.0

    # ════════════════════════════════════════════
    # RULE 1: Chronological Order (40% weight)
    # ════════════════════════════════════════════
    period1 = poi1.get('period', '')
    period2 = poi2.get('period', '')

    chronological_order = self._get_chronological_order(period1, period2)
    if chronological_order > 0:  # poi1 comes BEFORE poi2
        score += 0.4  # ← HARDCODED WEIGHT (you can change this!)
    elif chronological_order == 0:  # Same period
        score += 0.3  # ← HARDCODED WEIGHT (you can change this!)

    # ════════════════════════════════════════════
    # RULE 2: Same Period Bonus (30% weight)
    # ════════════════════════════════════════════
    if period1 and period2 and period1 == period2:
        score += 0.3  # ← HARDCODED WEIGHT (you can change this!)

    # ════════════════════════════════════════════
    # RULE 3: Date Proximity (30% weight)
    # ════════════════════════════════════════════
    date1 = self._extract_year(poi1.get('date_built', ''))
    date2 = self._extract_year(poi2.get('date_built', ''))

    if date1 and date2:
        year_diff = abs(date1 - date2)
        if year_diff < 50:    # ← HARDCODED THRESHOLD
            score += 0.3      # ← HARDCODED WEIGHT
        elif year_diff < 200: # ← HARDCODED THRESHOLD
            score += 0.2      # ← HARDCODED WEIGHT
        elif year_diff < 500: # ← HARDCODED THRESHOLD
            score += 0.1      # ← HARDCODED WEIGHT

    return min(score, 1.0)  # Cap at 1.0
```

---

## 📈 Real Example: Colosseum → Baths of Caracalla

### Input Data (from YAML files)
```
POI 1: Colosseum
  - period: "Roman Empire"
  - date_built: "70-80 AD"  → Extracted year: 75

POI 2: Baths of Caracalla
  - period: "Roman Empire"
  - date_built: "212-216 AD"  → Extracted year: 214
```

### Calculation (step by step)

```python
score = 0.0

# RULE 1: Chronological Order
period1 = "Roman Empire"  # Colosseum
period2 = "Roman Empire"  # Baths
chronological_order = _get_chronological_order(period1, period2)
# Both "Roman Empire" → returns 0 (same period)
# chronological_order == 0:
score += 0.3  # Same period bonus
# Current score: 0.3

# RULE 2: Same Period Bonus
if period1 == period2:  # "Roman Empire" == "Roman Empire"
    score += 0.3
# Current score: 0.6

# RULE 3: Date Proximity
year1 = 75   # Colosseum
year2 = 214  # Baths
year_diff = abs(75 - 214) = 139 years

if year_diff < 50:     # 139 < 50? No
    pass
elif year_diff < 200:  # 139 < 200? YES!
    score += 0.2
# Current score: 0.8

# Final score: 0.8 (HIGH!)
```

### Why This Score?
```
✅ Same period (Roman Empire):        +0.3
✅ Same period bonus:                  +0.3
✅ Built 139 years apart (< 200):      +0.2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total:                                  0.8 ← Above threshold (0.7)!
                                           Creates precedence constraint!
```

---

## 🔍 What Data Affects the Score Most?

### Impact Analysis

| Factor | Max Contribution | Impact |
|--------|-----------------|--------|
| **Chronological Order** | +0.4 | 🔴 HIGH (40% of max score) |
| **Same Period** | +0.3 | 🟡 MEDIUM (30% of max score) |
| **Same Period (duplicate)** | +0.3 | 🟡 MEDIUM (30% of max score) |
| **Date Proximity** | +0.3 | 🟡 MEDIUM (30% of max score) |

**Total Maximum:** 1.0 (capped)

### Which Field Matters Most?

**1. Period (60% of possible score)**
```python
# If same period:
score += 0.3  # Rule 1: Same period bonus
score += 0.3  # Rule 2: Same period bonus again
# Total: 0.6 just from having same period!
```

**2. Date Proximity (30% of possible score)**
```python
# If built < 50 years apart:
score += 0.3
```

**3. Chronological Order (40% but only in one direction)**
```python
# Only if poi1 built BEFORE poi2:
score += 0.4
# Otherwise: +0.0
```

---

## ⚙️ Parameters You Can Adjust

### Location: `src/trip_planner/itinerary_optimizer.py` lines 393-433

### Adjustable Parameters:

#### 1. Chronological Order Weights
```python
# Line 411-414
if chronological_order > 0:
    score += 0.4  # ← CHANGE THIS (currently 40%)
elif chronological_order == 0:
    score += 0.3  # ← CHANGE THIS (currently 30%)
```

**Recommendation:**
```python
# Make it more directional:
if chronological_order > 0:
    score += 0.5  # Increase older→newer bonus
elif chronological_order == 0:
    score += 0.2  # Decrease same-period bonus
```

#### 2. Same Period Weight
```python
# Line 417-418
if period1 and period2 and period1 == period2:
    score += 0.3  # ← CHANGE THIS (currently 30%)
```

**Recommendation:**
```python
# Reduce duplicate bonus:
if period1 and period2 and period1 == period2:
    score += 0.2  # Reduce to 20% (already counted in Rule 1)
```

#### 3. Date Proximity Thresholds and Weights
```python
# Lines 424-431
year_diff = abs(date1 - date2)
if year_diff < 50:      # ← CHANGE THIS threshold
    score += 0.3        # ← CHANGE THIS weight
elif year_diff < 200:   # ← CHANGE THIS threshold
    score += 0.2        # ← CHANGE THIS weight
elif year_diff < 500:   # ← CHANGE THIS threshold
    score += 0.1        # ← CHANGE THIS weight
```

**Recommendation:**
```python
# Tighten proximity requirements:
if year_diff < 25:      # Stricter (was 50)
    score += 0.3
elif year_diff < 100:   # Stricter (was 200)
    score += 0.2
elif year_diff < 300:   # Stricter (was 500)
    score += 0.1
```

#### 4. Period Rankings
```python
# Lines 442-449
period_order = {
    'Classical Greece': 1,    # ← ADD/MODIFY periods here
    'Hellenistic': 2,
    'Roman Empire': 3,
    'Byzantine': 4,
    'Ottoman': 5,
    'Modern': 6
}
```

**Recommendation:**
```python
# Add more granular periods:
period_order = {
    'Classical Greece': 1,
    'Hellenistic': 2,
    'Roman Republic': 3,      # NEW: Split Roman era
    'Roman Empire': 4,        # NEW: Early/Peak Roman
    'Late Roman Empire': 5,   # NEW: Decline period
    'Byzantine': 6,
    'Medieval': 7,            # NEW
    'Ottoman': 8,
    'Modern': 9
}
```

#### 5. Overall Threshold (Config File)
```yaml
# config.yaml line 346
optimization:
  precedence_soft_threshold: 0.7  # ← CHANGE THIS
```

**Options:**
```yaml
# Disable completely:
precedence_soft_threshold: 1.0  # Current setting

# Very strict (only perfect matches):
precedence_soft_threshold: 0.9

# Moderate (current):
precedence_soft_threshold: 0.7

# Loose (many constraints):
precedence_soft_threshold: 0.5  # Not recommended!
```

---

## 🎨 Example Adjustments to Make Scores More Reasonable

### Problem: Scores Too Symmetric (Both Directions High)

**Current Formula (Symmetric):**
```python
# Both directions can score high
Colosseum → Baths: 0.8
Baths → Colosseum: 0.8  # Same score!
```

**Solution: Make Directional**
```python
def _calculate_pair_coherence(poi1, poi2):
    score = 0.0

    # ONLY give chronological bonus in correct direction
    chronological_order = self._get_chronological_order(period1, period2)
    if chronological_order > 0:  # poi1 BEFORE poi2
        score += 0.5  # Strong directional bonus
    elif chronological_order == 0:
        score += 0.2  # Weak bonus (same period, order doesn't matter)
    else:  # chronological_order < 0 (poi1 AFTER poi2)
        score += 0.0  # NO BONUS for wrong direction!

    # Non-directional bonuses
    if period1 == period2:
        score += 0.2  # (Reduced from 0.3 to avoid double-counting)

    # Date proximity (non-directional)
    year_diff = abs(date1 - date2)
    if year_diff < 50:
        score += 0.3

    return score
```

**Result:**
```python
Colosseum → Baths:
  Directional: +0.5 (Colosseum before Baths) ✅
  Same period: +0.2
  Proximity:   +0.2
  Total:        0.9

Baths → Colosseum:
  Directional: +0.0 (Baths AFTER Colosseum) ❌
  Same period: +0.2
  Proximity:   +0.2
  Total:        0.4  ← Much lower!
```

---

## 🛠️ How to Make Changes

### Option 1: Adjust Weights (Easy)

Edit `src/trip_planner/itinerary_optimizer.py` lines 393-433:

```python
# Change these numbers:
score += 0.4  # Chronological order bonus (try 0.5)
score += 0.3  # Same period (try 0.2)
score += 0.3  # Date proximity (try 0.25)
```

### Option 2: Adjust Threshold (Very Easy)

Edit `config.yaml` line 346:

```yaml
# Disable precedence:
precedence_soft_threshold: 1.0  # Current

# Or make stricter:
precedence_soft_threshold: 0.8  # Only very high coherence
```

### Option 3: Implement Directional Coherence (Recommended)

See TODO-LIST.md Task 1 for full implementation guide.

---

## 📊 Score Distribution Example (Rome, 23 POIs)

**Total Pairs:** 506 (23 × 22)

| Score Range | Count | % | Creates Constraint? |
|-------------|-------|---|---------------------|
| **0.9-1.0** (Very High) | 2 | 0.4% | ✅ YES (if threshold 0.7) |
| **0.8-0.9** (High) | 2 | 0.4% | ✅ YES (if threshold 0.7) |
| **0.7-0.8** (Medium-High) | 0 | 0% | ✅ YES (if threshold 0.7) |
| **0.5-0.7** (Medium) | 61 | 12.1% | ❌ NO |
| **< 0.5** (Low) | 441 | 87.1% | ❌ NO |

**With Current Threshold (0.7):** Only 4 pairs create constraints (0.8%)

---

## 🎯 Recommendations for Your Use Case

### If You Have Combo Tickets:
```yaml
# Keep precedence disabled
precedence_soft_threshold: 1.0
```
**Why:** Combo tickets group by ticket type (not chronology), so chronological constraints conflict.

### If You Want Storytelling Order:
1. **Implement directional coherence** (TODO Task 1)
2. **Then enable with threshold 0.7:**
   ```yaml
   precedence_soft_threshold: 0.7
   ```
3. **Adjust weights to emphasize chronology:**
   ```python
   if chronological_order > 0:
       score += 0.6  # Increase directional bonus
   ```

### If You Want Fewer Constraints:
```yaml
# Make threshold stricter
precedence_soft_threshold: 0.9  # Only perfect matches
```

---

## 📝 Summary

| Question | Answer |
|----------|--------|
| **Where does data come from?** | POI research YAML files (`poi_research/{city}/{poi}.yaml`) |
| **Who creates the data?** | AI during research phase (analyzes history, assigns period/date) |
| **How is score calculated?** | Hardcoded Python formula (zero ML, just math) |
| **What affects score most?** | Period (60%) > Date proximity (30%) > Chronology (40%) |
| **Can I adjust it?** | YES! Edit weights in `itinerary_optimizer.py` or threshold in `config.yaml` |
| **What's the current problem?** | Symmetric scoring (both directions high) → causes cycles |
| **What's the fix?** | Make directional (older→newer gets bonus, newer→older doesn't) |

**Current Status:**
- ✅ Cycle bug fixed (only check i < j)
- ✅ Precedence disabled (threshold 1.0)
- ⚠️ Scoring still symmetric (but harmless when disabled)
- 🚀 TODO: Implement directional coherence (Task 1)
