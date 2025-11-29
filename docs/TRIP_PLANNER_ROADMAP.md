# Trip Planner Feature Roadmap

This document outlines the future development phases for the Trip Planning Agent system.

## ✅ Completed Phases

### Phase 2.1: AI-Powered POI Selection ✅
**Status:** Completed and committed

**Features:**
- Multi-provider support (Anthropic, OpenAI, Google)
- Automatic POI loading from `poi_research/` directory
- AI-driven Starting POI selection based on user profile
- Smart Back-up POI generation with similarity scoring
- Natural language reasoning for selections

**Files:**
- `src/trip_planner/poi_selector_agent.py`
- `test_poi_selector.py`

---

### Phase 2.2: Itinerary Optimization ✅
**Status:** Completed and committed

**Features:**
- Geographic distance calculation (Haversine formula)
- Storytelling coherence scoring (chronological/thematic flow)
- Hybrid optimization: Distance + Narrative coherence
- Day-by-day scheduling with time constraints
- Constraint validation (hours/day, walking distance)
- Quality scoring system

**Files:**
- `src/trip_planner/itinerary_optimizer.py`
- `test_itinerary_optimizer.py`

---

## 🚧 Future Phases

### Phase 2.3: Dynamic Re-Planning & POI Swapping
**Status:** Planned
**Priority:** High
**Estimated Effort:** 2-3 days

#### Overview
Allow users to swap POIs in their itinerary and automatically re-optimize the schedule while showing before/after comparisons.

#### Key Features

**1. POI Swap Engine**
```python
class POISwapEngine:
    def swap_poi(
        self,
        itinerary: Dict,
        old_poi: str,
        new_poi: str,
        backup_pois: Dict
    ) -> Dict:
        """
        Swap a POI and re-optimize itinerary.

        Returns:
        {
            'old_itinerary': {...},
            'new_itinerary': {...},
            'impact_analysis': {
                'distance_change': +0.5,  # km
                'coherence_change': -0.1,
                'time_change': +30,  # minutes
                'day_affected': 2,
                'recommendations': [...]
            }
        }
        """
```

**2. Impact Analysis**
- Compare before/after optimization scores
- Calculate changes in:
  - Total walking distance
  - Storytelling coherence
  - Daily time allocation
  - Opening hours conflicts
- Provide recommendations (e.g., "This swap creates a 6km walk, consider swapping to Temple of Olympian Zeus instead")

**3. Constraint Violation Detection**
- Opening hours conflicts
- Excessive daily hours (>8h)
- Walking distance warnings (>5km/day)
- Day overflow (too many POIs for available days)

**4. Proactive Back-up Suggestions**
When a swap violates constraints, suggest alternatives:
```
⚠️  Swapping to "Temple X" creates 6.5km walking on Day 2

Recommended alternatives:
1. Temple of Olympian Zeus (1.2km, 0.85 similarity)
2. Ancient Agora (2.1km, 0.78 similarity)
3. Keep original: Arch of Hadrian
```

#### Implementation Plan

**Step 1: Swap Engine Core**
- `swap_poi()` method in ItineraryOptimizerAgent
- Re-run optimization with new POI set
- Preserve user preferences (weights, start time)

**Step 2: Impact Analyzer**
- Calculate delta metrics (distance, coherence, time)
- Identify affected days
- Generate human-readable impact summary

**Step 3: Constraint Checker**
- Validate opening hours compatibility
- Check time budget per day
- Flag excessive walking distances

**Step 4: Recommendation Engine**
- Rank back-up POIs by:
  - Similarity to original
  - Distance improvement
  - Constraint satisfaction
- Provide top 3 alternatives

**Files to Create:**
- `src/trip_planner/swap_engine.py`
- `src/trip_planner/impact_analyzer.py`
- `test_poi_swap.py`

---

### Phase 2.4: Multi-Day Opening Hours Validation
**Status:** Planned
**Priority:** Medium
**Estimated Effort:** 1-2 days

#### Overview
Ensure POIs are scheduled only during their opening hours and respect closure days.

#### Key Features

**1. Opening Hours Parser**
```python
def is_open(
    poi_hours: Dict,
    visit_day: str,  # "Monday", "Tuesday", etc.
    visit_time: str  # "14:30"
) -> bool:
    """Check if POI is open at specific day/time"""
```

**2. Schedule Adjustments**
- Automatically reschedule POIs to open hours
- Swap days if needed (move closed POI to different day)
- Warning system for edge cases:
  - "Acropolis closes at 15:00 on Sundays, scheduled for 14:00 (tight)"
  - "Museum X closed on Mondays, moved to Day 3"

**3. Special Cases**
- Seasonal hours (summer vs winter)
- Holiday closures
- Last entry times (different from closing time)

#### Implementation Plan

**Step 1: Time Utilities**
- Parse `operation_hours.weekday_text` from POI metadata
- Convert to structured format
- Handle "Open 24 hours", closed days, etc.

**Step 2: Scheduling Validator**
- Check each POI against its opening hours
- Calculate visit windows
- Detect conflicts

**Step 3: Auto-Rescheduler**
- Move POIs to valid time slots
- Swap between days if needed
- Maintain optimization scores

**Files to Create:**
- `src/trip_planner/hours_validator.py`
- `src/utils/time_utils.py`
- `test_opening_hours.py`

---

### Phase 2.5: Travel Time Integration
**Status:** Planned
**Priority:** Medium
**Estimated Effort:** 2-3 days

#### Overview
Replace simple walking distance with realistic travel times using public transit, walking, and taxi options.

#### Key Features

**1. Multi-Modal Transportation**
```python
class TransportCalculator:
    def calculate_travel(
        self,
        from_poi: Dict,
        to_poi: Dict,
        mode: str = "auto"  # "walk", "metro", "taxi", "auto"
    ) -> Dict:
        """
        Returns:
        {
            'duration_minutes': 25,
            'distance_km': 3.2,
            'mode': 'metro',
            'cost': 1.40,  # EUR
            'instructions': [
                'Walk to Monastiraki Station (5 min)',
                'Take Line 1 to Thissio (8 min)',
                'Walk to destination (3 min)'
            ]
        }
        """
```

**2. Integration Options**
- **Option A:** Google Maps Directions API (requires API key)
- **Option B:** Pre-computed distance matrices (faster, offline)
- **Option C:** Simple heuristics based on distance
  - 0-1km: Walking (12 min/km)
  - 1-3km: Walking or metro
  - 3km+: Metro or taxi

**3. Cost Optimization**
- Include transportation costs in daily budgets
- Suggest day passes when beneficial
- Compare walk vs metro vs taxi

#### Implementation Plan

**Step 1: Distance Matrix Pre-computation**
- Generate distance matrices for common cities
- Store as JSON in `poi_distances/{city}/matrix.json`
- Include walk, metro, taxi times

**Step 2: Transport Calculator**
- Load distance matrix
- Calculate multi-modal options
- Select best mode based on distance/time

**Step 3: Optimizer Integration**
- Replace Haversine distance with realistic travel time
- Add mode switching costs (10 min penalty for metro vs walking)
- Consider transportation costs in optimization

**Files to Create:**
- `src/trip_planner/transport_calculator.py`
- `poi_distances/{city}/matrix.json`
- `scripts/generate_distance_matrix.py`
- `test_transport.py`

---

### Phase 2.6: Weather-Aware Scheduling
**Status:** Planned
**Priority:** Low
**Estimated Effort:** 1-2 days

#### Overview
Optimize indoor/outdoor POI distribution based on weather forecasts.

#### Key Features

**1. Weather Integration**
```python
def optimize_with_weather(
    itinerary: Dict,
    forecast: List[Dict]  # [{day: 1, condition: 'rain', temp: 18}, ...]
) -> Dict:
    """
    Reschedule POIs based on weather:
    - Rainy days: Indoor POIs (museums, churches)
    - Sunny days: Outdoor POIs (Acropolis, gardens)
    - Hot days: Morning outdoor, afternoon indoor
    """
```

**2. POI Metadata Enhancement**
```yaml
visit_info:
  indoor_outdoor: "outdoor"  # "indoor", "outdoor", "mixed"
  weather_dependent: true
  best_conditions: ["sunny", "partly_cloudy"]
```

**3. Dynamic Rescheduling**
- API integration: OpenWeatherMap (5-day forecast)
- Automatic day swapping
- User override option

#### Implementation Plan

**Step 1: Weather API Integration**
- Fetch 5-day forecast for city
- Parse conditions (rain, sun, temp)
- Store in cache

**Step 2: Indoor/Outdoor Tagging**
- Tag all POIs with `indoor_outdoor` in metadata
- Use AI to infer if missing

**Step 3: Weather-Aware Optimizer**
- Penalty for outdoor POIs on rainy days
- Bonus for indoor POIs on rainy days
- Re-optimize when weather changes

**Files to Create:**
- `src/trip_planner/weather_optimizer.py`
- `src/services/weather_api.py`
- `test_weather.py`

---

### Phase 2.7: Budget Planning
**Status:** Planned
**Priority:** Low
**Estimated Effort:** 2 days

#### Overview
Add cost tracking and budget constraints to trip planning.

#### Key Features

**1. Cost Metadata**
```yaml
poi:
  costs:
    admission_price: 20.00  # EUR
    currency: "EUR"
    discounts:
      - type: "student"
        price: 10.00
      - type: "senior"
        price: 15.00
    free_days: ["first Sunday of month"]
```

**2. Budget Optimization**
```python
def optimize_with_budget(
    pois: List[Dict],
    daily_budget: float,
    duration_days: int
) -> Dict:
    """
    Optimize itinerary within budget constraints.

    Consider:
    - Admission costs
    - Transportation costs
    - Free/discounted days
    - Meal costs (assumed)
    """
```

**3. Cost Breakdown**
```
Day 1 Budget: €50.00
├─ Acropolis: €20.00 (admission)
├─ Transport: €5.00 (day pass)
├─ Meals: €20.00 (estimated)
└─ Remaining: €5.00
```

**4. Free Alternatives**
- Suggest free POIs when budget-constrained
- Highlight free days/times
- Show cost savings for different schedules

#### Implementation Plan

**Step 1: Cost Collection**
- Add `costs` to POI metadata
- Use AI to research prices
- Update existing POIs

**Step 2: Budget Tracker**
- Calculate daily/total costs
- Track by category (admission, transport, meals)
- Show remaining budget

**Step 3: Budget-Aware Optimizer**
- Constraint: daily_budget
- Prefer free POIs when over budget
- Suggest schedule changes for free days

**Files to Create:**
- `src/trip_planner/budget_optimizer.py`
- `test_budget.py`

---

### Phase 2.8: Meal & Rest Break Scheduling
**Status:** Planned
**Priority:** Medium
**Estimated Effort:** 1 day

#### Overview
Automatically schedule meal breaks and rest periods in daily itineraries.

#### Key Features

**1. Break Scheduling**
```python
def schedule_breaks(
    daily_itinerary: Dict,
    meal_times: Dict = {
        'breakfast': '08:00',
        'lunch': '13:00',
        'dinner': '19:00'
    }
) -> Dict:
    """
    Insert meal breaks between POIs.

    Rules:
    - 1 hour lunch break (12:00-14:00)
    - 1.5 hour dinner break (19:00-20:30)
    - 15 min rest after 3+ hours walking
    """
```

**2. Restaurant Recommendations**
- Suggest nearby restaurants during meal breaks
- Filter by cuisine type
- Consider budget constraints

**3. Energy Management**
- Detect "heavy" days (>6h activity)
- Suggest rest breaks
- Balance intensive POIs with light ones

#### Implementation Plan

**Step 1: Break Insertion**
- Calculate time slots between POIs
- Insert breaks at meal times
- Respect min/max break durations

**Step 2: Restaurant API**
- Integration with Google Places API
- Filter by location, rating, price
- Show top 3 options per break

**Step 3: Energy Balancing**
- Tag POIs by intensity (light, moderate, heavy)
- Alternate intensive/light POIs
- Warn about exhausting days

**Files to Create:**
- `src/trip_planner/break_scheduler.py`
- `test_breaks.py`

---

### Phase 2.9: Export & Sharing
**Status:** Planned
**Priority:** Medium
**Estimated Effort:** 1-2 days

#### Overview
Export itineraries in multiple formats and enable sharing.

#### Key Features

**1. Export Formats**
- **PDF:** Print-friendly itinerary with maps
- **Google Calendar:** Import events directly
- **Apple Wallet:** Passes for each POI
- **JSON:** Machine-readable format
- **Markdown:** Human-readable checklist

**2. Map Integration**
```python
def export_to_google_maps(
    itinerary: Dict
) -> str:
    """
    Returns Google Maps URL with all POIs as waypoints
    """
```

**3. Sharing Options**
- Generate shareable link
- QR code for mobile access
- Email/SMS itinerary

#### Implementation Plan

**Step 1: PDF Generator**
- Use `reportlab` or `weasyprint`
- Include daily maps (static Google Maps images)
- Format POI details, times, notes

**Step 2: Calendar Export**
- Generate `.ics` file (iCalendar format)
- One event per POI with location and notes
- Compatible with Google/Apple/Outlook

**Step 3: Sharing Service**
- Store itineraries in database (optional)
- Generate short URLs
- QR code generation

**Files to Create:**
- `src/trip_planner/exporters/pdf_exporter.py`
- `src/trip_planner/exporters/calendar_exporter.py`
- `src/trip_planner/exporters/map_exporter.py`
- `test_export.py`

---

### Phase 2.10: Mobile Companion App (Optional)
**Status:** Planned
**Priority:** Low
**Estimated Effort:** 2-4 weeks

#### Overview
Mobile app for real-time itinerary access and updates during travel.

#### Key Features

**1. Offline Access**
- Download itinerary + POI transcripts
- Offline maps
- No internet required during trip

**2. Real-Time Updates**
- Live location tracking
- "Navigate to next POI" button
- Adjust schedule based on actual progress

**3. Check-In System**
- Mark POIs as "visited"
- Rate/review POIs
- Add photos and notes

**4. Smart Notifications**
- "Leave now to reach Acropolis by 10:00"
- "Museum closing in 30 minutes"
- "Rain forecast, consider indoor alternative"

#### Technology Stack
- **Framework:** React Native (iOS + Android)
- **Maps:** MapBox or Google Maps SDK
- **Storage:** SQLite for offline data
- **Sync:** REST API to main app

#### Implementation Plan
(To be detailed when Phase 2.10 begins)

---

## Implementation Priority

### Immediate Next Steps (Phase 2.3)
1. **Dynamic Re-Planning** - Critical for user experience
2. **POI Swapping** - Core functionality
3. **Impact Analysis** - Show users consequences of changes

### Short-Term (1-2 months)
1. **Opening Hours Validation** (Phase 2.4)
2. **Travel Time Integration** (Phase 2.5)
3. **Meal Break Scheduling** (Phase 2.8)

### Medium-Term (3-6 months)
1. **Weather-Aware Scheduling** (Phase 2.6)
2. **Budget Planning** (Phase 2.7)
3. **Export & Sharing** (Phase 2.9)

### Long-Term (6+ months)
1. **Mobile App** (Phase 2.10)

---

## Technical Debt & Improvements

### Current Limitations

**1. Limited POI Dataset**
- Currently only 2 POIs in Athens
- Need minimum 15-20 POIs per city for realistic testing
- **Action:** Implement POI research pipeline for more locations

**2. No Persistence Layer**
- Itineraries not saved to database
- Must re-generate each time
- **Action:** Add SQLite or PostgreSQL storage

**3. No User Accounts**
- No way to save/load user preferences
- **Action:** Add authentication system (Phase 3?)

**4. Hardcoded Configurations**
- Max hours per day, walking speed, etc. in code
- **Action:** Move to config.yaml

**5. No Analytics**
- Can't track which POIs are most popular
- No optimization based on user feedback
- **Action:** Add usage analytics

### Performance Optimizations

**1. Distance Matrix Caching**
- Currently recalculates distances each time
- **Action:** Pre-compute and cache matrices

**2. AI API Rate Limiting**
- Could hit rate limits with many users
- **Action:** Add request queuing and caching

**3. Large City Scaling**
- O(n²) distance calculations become slow
- **Action:** Use spatial indexing (R-tree)

---

## Testing Strategy

### Phase 2.3 Test Plan

**Unit Tests:**
- `test_swap_poi()` - POI swapping logic
- `test_impact_calculation()` - Delta metrics
- `test_constraint_detection()` - Violation checks
- `test_backup_ranking()` - Recommendation algorithm

**Integration Tests:**
- `test_end_to_end_swap()` - Full swap workflow
- `test_multiple_swaps()` - Sequential swaps
- `test_invalid_swaps()` - Error handling

**User Acceptance Tests:**
- Swap POI and verify itinerary updates
- Check impact analysis accuracy
- Validate constraint warnings
- Test back-up recommendations

---

## Documentation Needs

### For Phase 2.3

**1. API Documentation**
- POISwapEngine class reference
- Method signatures and examples
- Error codes and handling

**2. User Guide**
- How to swap POIs
- Understanding impact analysis
- Interpreting recommendations

**3. Developer Guide**
- Architecture overview
- Adding new constraints
- Extending recommendation engine

---

## Success Metrics

### Phase 2.3 Goals

**Functionality:**
- ✅ Swap any POI with any back-up
- ✅ Show before/after comparison
- ✅ Detect constraint violations
- ✅ Recommend alternatives

**Performance:**
- Swap + re-optimization in <2 seconds
- Accurate impact calculations (±10%)
- Relevant back-up recommendations (top-3 accuracy >80%)

**User Experience:**
- Clear impact visualization
- Actionable recommendations
- No unexpected side effects

---

## Questions for Future Discussion

1. **Should we support multi-city itineraries?**
   - e.g., 3 days Athens + 2 days Santorini
   - Requires inter-city travel time calculation

2. **Should we add group size optimization?**
   - Larger groups need different transportation
   - Some POIs have group discounts

3. **Should we support guided tours?**
   - Some POIs only accessible via tour
   - Need to integrate tour schedules

4. **Should we add accommodation recommendations?**
   - Optimize hotel location based on POIs
   - Consider commute times

5. **Should we build a marketplace?**
   - Let local guides customize itineraries
   - Monetization opportunity

---

## Contact & Contribution

For questions or suggestions about the roadmap:
- Create an issue in the repository
- Tag with `enhancement` or `roadmap`
- Specify which phase you're referencing

**Document Version:** 1.0
**Last Updated:** 2025-11-29
**Author:** Trip Planning Team
**Status:** Living Document (will be updated as phases complete)
