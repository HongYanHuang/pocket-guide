# Testing Guide for Re-Optimization System

## Overview

There are two test scripts for the re-optimization system:

1. **`test_reoptimizer.py`** - Tests the NEW algorithm only (3-tier strategy)
2. **`test_comparison.py`** - Compares OLD vs NEW algorithms (recommended!)

## Test Script 1: test_reoptimizer.py

### What It Does
- Tests the NEW 3-tier optimization strategy
- Shows which tier was selected (Tier 1/2/3)
- Displays optimization scores
- Validates that replacement was successful

### When to Use
- Quick verification that the new algorithm works
- Testing after code changes
- Checking if optimization improves scores

### How to Run
```bash
python test_reoptimizer.py
```

### Sample Output
```
Testing with tour: rome-tour-20260205-121250-11edf4 in rome

Original tour:
  Days: 3
  Total POIs: 10
  Current score: 0.42

Test replacement:
  Original POI: Theater of Marcellus
  Replacement POI: Colosseum
  Day: 1

============================================================
TEST 1: Local Swap (Tier 1)
============================================================
  [REOPTIMIZER] Using strategy: local_swap
  [TIER 1] Local swap optimization for day 1
  ✓ Local swap complete. Score: 0.61

Result:
  Strategy used: local_swap
  New score: 0.61 (improved from 0.42!)
  Distance score: 0.47
  Coherence score: 0.75
  Total distance: 16.0 km
```

### Limitations
- ❌ Does NOT compare with old algorithm
- ❌ Cannot select specific tour
- ❌ Only tests one replacement per run

---

## Test Script 2: test_comparison.py ⭐ RECOMMENDED

### What It Does
- **Compares OLD vs NEW algorithms side-by-side**
- Lets you select which tour to test
- Shows execution time comparison
- Shows score improvements
- Displays tour structure changes
- Provides detailed verdict

### When to Use
- **Evaluating performance improvements** (speed + quality)
- **Demonstrating algorithm benefits** to stakeholders
- **Testing specific tours** with known issues
- **Understanding strategy selection** (why Tier 1/2/3 was chosen)

### How to Run

#### Interactive Mode (Recommended)
```bash
python test_comparison.py
```

Then select a tour from the list:
```
======================================================================
Available Tours for Testing
======================================================================

1. rome-tour-20260205-121250-11edf4
   City: Rome
   Days: 3
   POIs: 10
   Backup POIs: 1

2. rome-tour-20260206-114644-2c8011
   City: Rome
   Days: 2
   POIs: 7
   Backup POIs: 7

======================================================================

Select tour (1-9) or 'q' to quit: 1
```

### Sample Output

#### Performance Comparison
```
======================================================================
PERFORMANCE COMPARISON
======================================================================

⏱️  Execution Time:
  Old: 0.793s
  New: 0.170s
  Speedup: 4.7x faster! 🚀

📊 Overall Score:
  Old: 0.42
  New: 0.61
  Result: 45.2% better! ✅

🚶 Total Walking Distance:
  Old: 18.0 km
  New: 16.0 km
  Result: 2.00 km shorter! 👍

🎯 Strategy Insights:
  Old approach: Always runs full tour optimization
  New approach: Selected 'local_swap' strategy
  Reason: Single POI replacement on small day → Fast optimization

======================================================================
VERDICT
======================================================================
✅ NEW algorithm is FASTER and BETTER quality!
```

#### Tour Structure Comparison
```
======================================================================
TOUR STRUCTURE COMPARISON
======================================================================

OLD Algorithm Tour Structure:
  Day 1: 4 POIs
    - Pantheon
    - Colosseum ← NEW!
    - Baths of Caracalla
    - Roman Forum
  Day 2: 3 POIs
    - Palatine Hill
    - St. Peter's Basilica
    - Vatican Museums

NEW Algorithm Tour Structure:
  Day 1: 4 POIs
    - Colosseum ← NEW!
    - Baths of Caracalla
    - Pantheon
    - Roman Forum
  Day 2: 3 POIs
    - Palatine Hill
    - St. Peter's Basilica
    - Vatican Museums

✗ POI order is DIFFERENT (algorithms reordered POIs differently)
```

### Features

#### 1. Tour Selection
- Lists all available tours with backup POIs
- Shows tour details (days, POIs, backups)
- Interactive selection

#### 2. Algorithm Comparison
- **OLD Algorithm**: Full tour re-optimization every time
- **NEW Algorithm**: Smart 3-tier strategy (auto-selects Tier 1/2/3)

#### 3. Metrics Compared
- ⏱️ **Execution Time**: How fast each algorithm runs
- 📊 **Optimization Scores**: Overall, distance, coherence
- 🚶 **Walking Distance**: Total km walking per day
- 🎯 **Strategy Used**: Which tier was selected (NEW only)

#### 4. Detailed Verdict
The script provides a clear verdict:
- ✅ "FASTER and BETTER quality"
- ✅ "MUCH FASTER with similar quality"
- ✅ "BETTER results"
- ⚠️ "Mixed results" (if neither faster nor better)

#### 5. Tour Structure Analysis
Shows exactly how POIs were reordered:
- Marks the NEW POI (←)
- Compares day-by-day structure
- Identifies if order changed

### Test Multiple Replacements

After each test, you can:
- Test another replacement (press 'y')
- Exit (press 'n')

This allows comparing multiple scenarios in one session.

---

## Comparison: Test Scripts

| Feature | test_reoptimizer.py | test_comparison.py |
|---------|---------------------|-------------------|
| **Tests NEW algorithm** | ✅ | ✅ |
| **Tests OLD algorithm** | ❌ | ✅ |
| **Side-by-side comparison** | ❌ | ✅ |
| **Tour selection** | ❌ Auto-selects | ✅ Interactive |
| **Execution time** | ❌ | ✅ |
| **Score improvements** | ✅ | ✅ Better display |
| **Strategy insights** | ✅ | ✅ With explanation |
| **Tour structure comparison** | ❌ | ✅ |
| **Verdict** | ❌ | ✅ |
| **Multiple tests** | ❌ | ✅ |
| **Best for** | Quick validation | Performance evaluation |

---

## Real-World Results

Based on actual test runs:

### Example 1: Single POI Replacement (Tier 1)
```
Tour: Rome 3-day tour, 10 POIs
Replacement: Theater of Marcellus → Colosseum

OLD Algorithm:
  - Time: 0.793s
  - Strategy: full_tour_always
  - Score: 0.42
  - Distance: 18.0 km

NEW Algorithm:
  - Time: 0.170s (4.7x faster! 🚀)
  - Strategy: local_swap (auto-selected)
  - Score: 0.61 (45.2% better!)
  - Distance: 16.0 km (2 km shorter!)

Verdict: ✅ FASTER and BETTER quality!
```

### Example 2: Multiple POIs (Tier 2 Expected)
```
Tour: Rome 2-day tour, 7 POIs
Replacements: 2 POIs on same day

Expected Results:
  - NEW algorithm selects Tier 2 (day-level)
  - 2-3x faster than OLD
  - Similar or better quality
```

### Example 3: Multi-Day Changes (Tier 3)
```
Tour: Rome 3-day tour, 10 POIs
Replacements: 3 POIs across 3 days

Expected Results:
  - NEW algorithm selects Tier 3 (full tour)
  - Similar speed to OLD (both do full optimization)
  - Similar quality
  - But NEW has distance caching for next time!
```

---

## Interpreting Results

### Speed Improvements
- **1-2x faster**: Modest improvement
- **2-5x faster**: Significant improvement (typical for Tier 1/2)
- **5-10x faster**: Exceptional (Tier 1 on small day)

### Score Improvements
- **Same score (±0.05)**: Both algorithms found similar solutions
- **5-20% better**: NEW algorithm found better route
- **>20% better**: Significant improvement (check if original tour was suboptimal)

### Distance Changes
- **Shorter distance**: Better (less walking)
- **Same distance**: Both algorithms found similar routes
- **Longer distance**: May indicate different optimization priorities (check coherence score)

### Strategy Selection
- **Tier 1 (local_swap)**: Single POI, small day → Ultra-fast
- **Tier 2 (day_level)**: Few POIs, 1-2 days → Fast + good quality
- **Tier 3 (full_tour)**: Many POIs, 3+ days → Thorough but slower

---

## Troubleshooting

### "No tours found"
**Problem**: No tours in `tours/` directory
**Solution**: Generate a tour first using the main application

### "No tours with backup POIs found"
**Problem**: Tours don't have backup POIs
**Solution**: Regenerate tours or manually add backup POIs

### "No suitable replacement found"
**Problem**: Selected tour has no POIs with backups
**Solution**: Choose a different tour from the list

### "Warning: No coordinates for POI"
**Problem**: POI research YAML missing coordinates
**Solution**: This is non-blocking. System uses 2km default distance.
**To fix**: Add coordinates to `poi_research/{city}/{poi}.yaml`

### "Score worse with NEW algorithm"
**Problem**: NEW algorithm produces lower score than OLD
**Reason**: Different optimization paths (greedy can get stuck in local optima)
**Solution**: This is rare. Try Tier 3 explicitly or accept trade-off for speed.

---

## Best Practices

### 1. Start with test_comparison.py
Always use the comparison test first to:
- Verify performance improvements
- Understand which strategy is selected
- Validate score improvements

### 2. Test Multiple Tours
Different tours may benefit differently:
- Small tours (1-2 days): Expect high speedup (Tier 1)
- Medium tours (2-3 days): Expect moderate speedup (Tier 2)
- Large tours (3+ days): Expect similar speed but cached distances

### 3. Test Multiple Replacements
Use the "test another replacement" feature to:
- Compare different scenarios
- Validate consistency
- Find edge cases

### 4. Check Tour Structure
Always review the tour structure comparison to:
- Verify POI order makes sense
- Ensure new POI is in expected day
- Confirm no POIs were lost

### 5. Document Results
Save test outputs for:
- Performance benchmarking
- Regression testing
- Stakeholder reports

---

## Common Questions

### Q: Why different scores for same replacement?
**A**: Greedy algorithms are not deterministic when breaking ties. Small differences are normal.

### Q: When would NEW be slower than OLD?
**A**: Rarely. Only if:
- Tier 3 selected (same speed as OLD)
- Distance cache initialization overhead (first run only)

### Q: Should I always use re-optimization mode?
**A**: Depends:
- Use **simple mode** for quick swaps (no route changes)
- Use **reoptimize mode** for better routes (accepts longer execution)

### Q: How do I know which tier will be selected?
**A**: The system automatically selects based on:
- Number of replacements
- Days affected
- POIs per day
- See "Strategy Insights" in test output

---

## Next Steps

1. **Run test_comparison.py** on your tours
2. **Document performance improvements** (time + scores)
3. **Share results** with team/stakeholders
4. **Deploy to production** with confidence!

For implementation details, see: `docs/reoptimization_implementation.md`
