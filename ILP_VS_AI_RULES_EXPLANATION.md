# ILP Models: Manual Rules vs AI-Generated Rules

## 🎯 TL;DR

**Current System:**
- We manually write rules in Python code
- ILP solver uses those rules to find optimal solution
- ILP does NOT create rules - it just solves the math problem we give it

**Can AI Generate Rules?**
- YES! But it's a different approach
- AI can generate the scoring formulas and constraints
- Hybrid approach: AI generates rules → ILP optimizes

---

## 📚 What Is ILP and How Does It Work?

### ILP = Integer Linear Programming (Pure Mathematics, No AI)

ILP is a **mathematical optimization technique** that finds the best solution given:

1. **Variables** (decisions to make)
2. **Constraints** (rules that MUST be satisfied)
3. **Objective Function** (what to maximize/minimize)

**Important:** ILP does NOT create rules, learn patterns, or use AI. It's just very fast at solving math equations.

---

## 🔧 Current System: Manual Rule Creation

### How Our System Works Now

```
┌─────────────────────────────────────────────────────────┐
│ Step 1: WE WRITE RULES IN PYTHON CODE                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  def _calculate_coherence(poi1, poi2):                 │
│      score = 0.0                                        │
│      if same_period:      score += 0.3  ← MANUAL RULE  │
│      if years_close:      score += 0.2  ← MANUAL RULE  │
│      if chronological:    score += 0.4  ← MANUAL RULE  │
│      return score                                       │
│                                                          │
├─────────────────────────────────────────────────────────┤
│ Step 2: WE CREATE CONSTRAINTS IN CODE                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  # Combo ticket constraint (manual)                    │
│  if poi_group has combo_ticket:                        │
│      model.Add(all_on_same_day)  ← MANUAL CONSTRAINT   │
│                                                          │
│  # Time window constraint (manual)                     │
│  if poi has opening_hours:                             │
│      model.Add(visit_time within hours)  ← MANUAL      │
│                                                          │
├─────────────────────────────────────────────────────────┤
│ Step 3: WE DEFINE OBJECTIVE FUNCTION                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  objective = (                                          │
│      0.6 * distance_score +      ← MANUAL WEIGHT       │
│      0.4 * coherence_score       ← MANUAL WEIGHT       │
│  )                                                       │
│  model.Maximize(objective)                              │
│                                                          │
├─────────────────────────────────────────────────────────┤
│ Step 4: ILP SOLVER FINDS OPTIMAL SOLUTION               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ILP Solver (Google OR-Tools):                         │
│  - Takes our constraints (hard rules)                  │
│  - Takes our objective (what to optimize)              │
│  - Finds best solution that satisfies ALL constraints  │
│  - Uses mathematical algorithms (no AI/ML)             │
│                                                          │
└─────────────────────────────────────────────────────────┘

Result: Tour itinerary optimized according to OUR rules
```

---

## 🤖 How ILP Uses Our Parameters

### What We Give ILP

**1. Decision Variables**
```python
# We tell ILP: "Decide which POI goes on which day at which position"
visit_vars[poi_index][day][position] = True/False

# Example:
visit_vars[0][1][2] = True   # POI 0 (Colosseum) on Day 1, Position 2
visit_vars[1][1][0] = True   # POI 1 (Forum) on Day 1, Position 0
```

**2. Constraints (Hard Rules)**
```python
# Constraint 1: Each POI visited at most once
for each POI:
    model.Add(sum(visit_vars[poi][all_days][all_positions]) <= 1)

# Constraint 2: Combo tickets on same day (MANUAL RULE)
if [Colosseum, Forum, Palatine] are combo ticket:
    model.Add(
        Colosseum.day == Forum.day == Palatine.day
    )

# Constraint 3: Time windows (MANUAL RULE)
if Pantheon opens 9am-7pm:
    model.Add(
        visit_time >= 9am AND visit_time <= 7pm
    )

# Constraint 4: Precedence (MANUAL RULE from coherence)
if coherence(A, B) >= 0.7:
    model.Add(sequence[A] < sequence[B])
```

**3. Objective Function (What to Optimize)**
```python
# We calculate scores using MANUAL FORMULAS
total_distance = sum(distances between consecutive POIs)
total_coherence = sum(coherence scores for consecutive POIs)

# We set MANUAL WEIGHTS
objective = (
    0.6 * (1.0 - normalized_distance) +  # Minimize distance (60% weight)
    0.4 * normalized_coherence           # Maximize coherence (40% weight)
)

# Tell ILP to maximize
model.Maximize(objective)
```

### What ILP Does

```python
# ILP Solver's job:
# "Find the assignment of POIs to days/positions that:
#  1. Satisfies ALL constraints
#  2. Maximizes the objective function"

# It uses mathematical algorithms:
# - Branch and bound
# - Linear programming relaxation
# - Constraint propagation
# - NO machine learning, NO AI

# Output:
# Day 1: [POI A, POI B, POI C]
# Day 2: [POI D, POI E, POI F]
# (with maximum objective score)
```

---

## ❓ Do We Need to Create Many Rules?

### Current Approach: YES, We Manually Define Everything

**What We Manually Define:**

1. **Coherence Scoring Rules** (~40 lines of code)
   ```python
   if same_period:        score += 0.3
   if chronological:      score += 0.4
   if years_close < 50:   score += 0.3
   # ... all hardcoded
   ```

2. **Constraint Rules** (~500 lines of code)
   ```python
   # Combo ticket constraints
   # Time window constraints
   # Precedence constraints
   # Capacity constraints
   # Day length constraints
   # ... all hardcoded
   ```

3. **Objective Weights** (~50 lines of code)
   ```python
   distance_weight = 0.6  # Hardcoded
   coherence_weight = 0.4 # Hardcoded
   ```

**Total: ~600 lines of manual rule code**

### Problem with Manual Rules

```python
# If we want to improve coherence formula:
# ❌ We have to manually figure out:
#    - What weights work best?
#    - What thresholds are optimal?
#    - How to balance different factors?

# Example dilemma:
# - Should same period be worth 0.3 or 0.2?
# - Should date proximity be < 50 years or < 100 years?
# - Should distance be 60% or 70% of objective?

# Current method: TRIAL AND ERROR (time-consuming!)
```

---

## 🤖 Can AI Generate the Rules? YES!

### Approach 1: AI Generates Scoring Formulas (Meta-Learning)

**Instead of hardcoding, ask AI to generate the formula:**

```python
# Step 1: Give AI examples of "good" vs "bad" tour orders
examples = [
    {
        "tour": "Colosseum → Forum → Palatine",
        "feedback": "excellent",  # User rating
        "coherence_should_be": "high"
    },
    {
        "tour": "Vatican → Colosseum → Vatican Museums",
        "feedback": "poor",  # Too much travel
        "coherence_should_be": "low"
    }
]

# Step 2: AI generates scoring formula
ai_prompt = """
Given these tour examples and user feedback, generate a Python function
that calculates coherence score between POI pairs.

Input: poi1, poi2 (with metadata: period, date, location)
Output: score 0.0-1.0

The function should favor tours that users rated highly.
"""

# Step 3: AI outputs code
generated_code = llm.generate(ai_prompt, examples)

# Example AI-generated output:
def ai_generated_coherence(poi1, poi2):
    score = 0.0

    # AI learns from examples that same period is important
    if poi1.period == poi2.period:
        score += 0.35  # AI learned this weight

    # AI learns that proximity matters
    if distance(poi1, poi2) < 2km:
        score += 0.25  # AI learned this

    # AI learns chronology matters less than we thought
    if chronologically_ordered(poi1, poi2):
        score += 0.15  # Lower weight than our manual 0.4

    return score

# Step 4: Use AI-generated formula in ILP
coherence_scores = {}
for poi1, poi2 in all_pairs:
    coherence_scores[(poi1, poi2)] = ai_generated_coherence(poi1, poi2)

# Step 5: ILP optimizes using AI-generated scores
model.Maximize(objective_using_ai_scores)
```

**Benefits:**
- ✅ AI learns from user feedback
- ✅ Automatically finds optimal weights
- ✅ No manual tuning needed
- ⚠️ Requires user feedback data

---

### Approach 2: AI Generates Constraints Dynamically (LLM Code Generation)

**Let AI write the constraint code:**

```python
# Step 1: Describe constraints in natural language
user_requirements = """
1. All Colosseum ticket group POIs must be on the same day
2. Vatican Museums must be visited before Sistine Chapel
3. POIs should be visited in chronological order when possible
4. No more than 8 hours of activities per day
"""

# Step 2: AI generates ILP constraints
ai_prompt = f"""
Generate Python code using Google OR-Tools CP-SAT to implement
these constraints for an itinerary optimizer:

{user_requirements}

Variables available:
- visit_vars[poi][day][position]: Boolean, True if POI at day/position
- pois: List of POI dictionaries with metadata
"""

# Step 3: AI outputs constraint code
generated_constraints = llm.generate(ai_prompt)

# Example AI-generated code:
def add_ai_generated_constraints(model, visit_vars, pois):
    # Constraint 1: Combo tickets same day
    colosseum_group = ["Colosseum", "Roman Forum", "Palatine Hill"]
    for i, poi1 in enumerate(colosseum_group):
        for poi2 in colosseum_group[i+1:]:
            # Force same day
            model.Add(get_day(poi1) == get_day(poi2))

    # Constraint 2: Vatican sequence
    vatican_idx = find_poi("Vatican Museums")
    sistine_idx = find_poi("Sistine Chapel")
    model.Add(sequence[vatican_idx] < sequence[sistine_idx])

    # Constraint 3: Chronological order (soft)
    for poi1, poi2 in chronologically_ordered_pairs:
        if coherence(poi1, poi2) > 0.7:
            model.Add(sequence[poi1] < sequence[poi2])

    # Constraint 4: Time limits
    for day in range(num_days):
        model.Add(sum(visit_hours[day]) <= 8)

# Step 4: Use AI-generated constraints
add_ai_generated_constraints(model, visit_vars, pois)
model.Maximize(objective)
```

**Benefits:**
- ✅ Natural language to code
- ✅ Fast iteration (no manual coding)
- ✅ Can handle complex requirements
- ⚠️ Needs validation (AI might generate bugs)

---

### Approach 3: Reinforcement Learning (AI Learns from Tours)

**AI learns optimal rules by trying different tours:**

```python
# Step 1: Set up RL environment
class TourEnvironment:
    def step(self, action):
        # Action: Assign POI to day/position
        # Reward: User satisfaction score

        # Simulate tour
        tour = execute_action(action)

        # Get feedback
        reward = get_user_rating(tour)  # 0-10 score

        return next_state, reward

# Step 2: Train AI agent
ai_agent = ReinforcementLearningAgent()

for episode in range(10000):
    state = initial_tour_state()

    while not done:
        # AI decides which POI to add next
        action = ai_agent.choose_action(state)

        # Execute and get reward
        next_state, reward = env.step(action)

        # AI learns from feedback
        ai_agent.learn(state, action, reward, next_state)

        state = next_state

# Step 3: After training, AI has learned rules
# AI can now generate tours without ILP!
optimal_tour = ai_agent.generate_tour(pois, days)
```

**Benefits:**
- ✅ Learns from real user preferences
- ✅ No need to specify rules manually
- ✅ Can discover novel patterns
- ⚠️ Requires lots of training data
- ⚠️ Computationally expensive

---

### Approach 4: Hybrid (Best of Both Worlds)

**Use AI for rule generation, ILP for optimization:**

```python
# Step 1: AI generates scoring functions
coherence_func = ai_generate_coherence_formula(user_feedback)
distance_func = ai_generate_distance_penalty(user_feedback)

# Step 2: AI suggests constraint priorities
constraint_weights = ai_analyze_constraints(tour_examples)
# Output: {
#   'combo_tickets': 1.0,      # Must satisfy (hard)
#   'time_windows': 0.9,       # Very important
#   'chronological': 0.3,      # Nice to have (soft)
# }

# Step 3: Convert AI weights to ILP constraints
for constraint, weight in constraint_weights.items():
    if weight >= 0.8:
        # Hard constraint
        model.Add(constraint)
    else:
        # Soft constraint (penalty in objective)
        objective -= weight * violation_penalty(constraint)

# Step 4: ILP optimizes with AI-generated rules
model.Maximize(objective)
solution = solver.Solve(model)
```

**Benefits:**
- ✅ AI handles rule generation (learns from data)
- ✅ ILP handles optimization (fast, guaranteed optimal)
- ✅ Best of both approaches
- ✅ More maintainable than pure manual rules

---

## 📊 Comparison Table

| Approach | Rules Created By | Optimization By | Pros | Cons |
|----------|------------------|-----------------|------|------|
| **Current (Manual + ILP)** | Human (code) | ILP solver | ✅ Explainable<br>✅ Predictable<br>✅ Fast optimization | ❌ Time-consuming tuning<br>❌ Hard to find optimal weights<br>❌ Doesn't learn from feedback |
| **AI-Generated Formulas** | AI (from examples) | ILP solver | ✅ Learns from data<br>✅ Auto-tunes weights<br>✅ Fast optimization | ⚠️ Needs training data<br>⚠️ Less explainable |
| **LLM Code Generation** | AI (from NL) | ILP solver | ✅ Fast iteration<br>✅ Natural language input<br>✅ Fast optimization | ⚠️ Validation needed<br>⚠️ May generate bugs |
| **Reinforcement Learning** | AI (self-learning) | AI (no ILP) | ✅ Learns from feedback<br>✅ Discovers patterns<br>✅ No manual rules | ❌ Expensive training<br>❌ Lots of data needed<br>❌ Slower than ILP |
| **Hybrid (AI + ILP)** | AI (formulas) | ILP solver | ✅ Best of both<br>✅ Learning + optimization<br>✅ Maintainable | ⚠️ More complex system<br>⚠️ Needs data |

---

## 🎯 Recommendation for Your System

### Short Term (Now): Manual Rules + ILP
```python
# Keep current system but improve coherence formula
# See TODO-LIST.md Task 1: Make coherence directional

# Advantages:
# ✅ Already working
# ✅ Fast optimization
# ✅ Explainable results
# ✅ No training data needed

# Quick improvements:
# 1. Fix symmetric scoring (directional coherence)
# 2. Adjust weights based on user feedback
# 3. Keep precedence disabled (threshold 1.0)
```

### Medium Term: Add AI-Generated Weights
```python
# Use AI to suggest optimal weights from user feedback

# Collect data:
user_feedback = [
    {"tour_id": "rome-123", "rating": 9, "comment": "Perfect flow"},
    {"tour_id": "rome-456", "rating": 5, "comment": "Too much walking"}
]

# Ask AI to analyze:
ai_prompt = """
Analyze these tour ratings and suggest optimal weights for:
- distance_weight (currently 0.6)
- coherence_weight (currently 0.4)
- same_period_bonus (currently 0.3)
- date_proximity_bonus (currently 0.3)

Based on user feedback patterns.
"""

suggested_weights = llm.analyze(ai_prompt, user_feedback)

# Update config with AI suggestions
config['optimization']['distance_weight'] = suggested_weights['distance']
config['optimization']['coherence_weight'] = suggested_weights['coherence']
```

### Long Term: Hybrid System
```python
# AI generates formulas, ILP optimizes

# 1. Collect tour feedback database
# 2. Train AI model to generate coherence formulas
# 3. Use AI formulas in ILP optimization
# 4. Continuously improve from new feedback
```

---

## 💡 Practical Example: Using AI to Generate Rules

### Example: Ask Claude/ChatGPT to Generate Coherence Formula

**Prompt to AI:**
```
I have POIs with metadata:
- period (e.g., "Roman Empire", "Byzantine")
- date_built (e.g., "70-80 AD")
- location (latitude, longitude)

I want to calculate a coherence score (0-1) between two POIs
for tour planning. High coherence = good storytelling flow.

User feedback shows:
- Tours with chronologically ordered POIs rate 8+/10
- Tours jumping periods randomly rate 5/10
- Tours with nearby POIs rate 7+/10

Generate a Python function that calculates coherence score.
Make it directional (A→B different from B→A).
```

**AI Response:**
```python
def ai_generated_coherence(poi1, poi2):
    """
    Calculate directional coherence score.
    Higher score = better storytelling flow A→B
    """
    score = 0.0

    # Extract metadata
    period1 = poi1.get('period', '')
    period2 = poi2.get('period', '')
    year1 = extract_year(poi1.get('date_built', ''))
    year2 = extract_year(poi2.get('date_built', ''))
    dist = distance(poi1['coords'], poi2['coords'])

    # Rule 1: Chronological flow (DIRECTIONAL)
    # Only reward if poi1 comes before poi2
    if year1 and year2:
        if year1 < year2:  # Correct chronological order
            time_gap = year2 - year1
            if time_gap < 100:
                score += 0.5  # Strong recent continuity
            elif time_gap < 300:
                score += 0.3  # Moderate flow
            else:
                score += 0.1  # Weak but still forward
        # If reverse (year1 > year2): score += 0.0 (no reward)

    # Rule 2: Same period (non-directional)
    if period1 == period2:
        score += 0.25

    # Rule 3: Geographic proximity (non-directional)
    if dist < 1.0:  # Within 1 km
        score += 0.25
    elif dist < 3.0:  # Within 3 km
        score += 0.15

    return min(score, 1.0)

# This is DIRECTIONAL:
# Rome (70 AD) → Baths (212 AD) = 0.8 (high)
# Baths (212 AD) → Rome (70 AD) = 0.25 (low - only same period)
```

**Benefits of AI-Generated Formula:**
- ✅ Directional (fixes the cycle problem)
- ✅ Based on actual user preferences
- ✅ Can regenerate easily with different feedback
- ✅ More sophisticated than manual formula

---

## 📝 Summary

### How ILP Works
- ILP is **pure mathematics** (no AI/ML)
- We give it **constraints** and **objective**
- It finds **optimal solution** very fast
- It does NOT create or learn rules

### Do We Need Many Manual Rules?
- **Currently: YES** (~600 lines of manual rules)
- **Problem:** Trial-and-error to find good weights
- **Alternative:** Use AI to generate rules

### Can AI Generate Rules?
- **YES!** Multiple approaches:
  1. **AI generates formulas** from user feedback
  2. **LLM generates code** from natural language
  3. **RL learns** from tour simulations
  4. **Hybrid:** AI rules + ILP optimization

### Best Approach for You
1. **Short term:** Fix directional coherence (manual)
2. **Medium term:** Use AI to suggest weights
3. **Long term:** Hybrid (AI formulas + ILP optimization)

### Quick Win
Ask Claude/ChatGPT to generate a better coherence formula:
```
"Generate a directional coherence scoring function
based on these user feedback examples: [paste examples]"
```

Then use the AI-generated formula in your ILP model!
