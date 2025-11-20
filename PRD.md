# Product Requirements Document: AI Customized Walking Tour Guide

## 1. Product Overview

**Product Name:** Pocket Guide
**Version:** 1.0 (Phase 1)
**Platform:** Progressive Web App (PWA)

**Vision:** An AI-powered walking tour guide that generates personalized audio narratives for tourist points based on user interests and available time, supporting multiple major languages.

**Target MVP Scope:** Single city with 10-30 points of interest

---

## 2. Goals & Success Metrics

### Primary Goals
- Deliver personalized, high-quality audio tour content in real-time
- Support 5-10 major languages (English, Spanish, Mandarin, French, German, etc.)
- Provide seamless offline experience via PWA capabilities

### Success Metrics
- Audio generation time: <30 seconds per tour point
- User engagement: >70% completion rate per tour
- Content quality: >4/5 user rating
- Language accuracy: >90% user satisfaction across all supported languages

---

## 3. User Stories

### As a tourist, I want to:
- Select my interests (history, art, food, architecture, etc.) so the tour content is relevant to me
- Specify how much time I have so the tour fits my schedule
- Listen to tour content in my native language
- Use the app offline without internet connectivity
- Navigate between tour points easily with a map interface

### As a content curator, I want to:
- Add new tourist points with basic information (location, name, category)
- Review and approve AI-generated content before it goes live (future phase)

---

## 4. Functional Requirements - Phase 1

### 4.1 User Onboarding
- **FR-1.1:** User selects interests from predefined categories (history, art, food, architecture, culture, nature, etc.)
- **FR-1.2:** User specifies available tour time (30 min, 1 hour, 2 hours, 4+ hours)
- **FR-1.3:** User selects preferred language from 5-10 supported options
- **FR-1.4:** System generates personalized tour route with relevant points

### 4.2 AI Content Generation
- **FR-2.1:** System generates unique text content for each tourist point based on:
  - User's selected interests
  - Available time (depth and length of content)
  - Language preference
- **FR-2.2:** Content includes: historical context, interesting facts, practical tips, and connections to user interests
- **FR-2.3:** Text is optimized for oral delivery (conversational tone, natural pacing)

### 4.3 Text-to-Speech Conversion
- **FR-3.1:** Convert AI-generated text into natural-sounding audio
- **FR-3.2:** Support multiple voice options per language (male/female, different accents if applicable)
- **FR-3.3:** Maintain consistent voice throughout the tour
- **FR-3.4:** Audio files are cached for offline playback

### 4.4 Tour Navigation
- **FR-4.1:** Display interactive map with tour points
- **FR-4.2:** Show user's current location and next suggested point
- **FR-4.3:** Allow users to skip or go back to previous points
- **FR-4.4:** Auto-play audio when user arrives at a point (optional)

### 4.5 PWA Features
- **FR-5.1:** App works offline after initial data download
- **FR-5.2:** Installable on mobile devices (Add to Home Screen)
- **FR-5.3:** Fast loading with service worker caching
- **FR-5.4:** Responsive design for various screen sizes

---

## 5. Technical Requirements

### 5.1 Performance
- Content generation: <30 seconds per point
- TTS conversion: <10 seconds per minute of audio
- App load time: <3 seconds on 4G
- Offline mode: Full functionality without internet

### 5.2 Data Storage
- Tourist point database with metadata (location, category, images)
- User preference persistence (local storage)
- Audio cache management (service worker)

### 5.3 Scalability Considerations
- Modular architecture to add new cities easily
- Content generation pipeline that can handle multiple concurrent requests
- CDN for audio file delivery

---

## 6. Phase 1 Implementation Flow

```
User Input → AI Content Generation → Speech Transcript Optimization → TTS Generation → Audio Playback
   ↓              ↓                          ↓                          ↓               ↓
[Interests]  [LLM API]              [Formatting/SSML]           [TTS Service]    [PWA Player]
[Time]       [Custom prompt]         [Oral optimization]        [Audio file]     [Offline cache]
[Language]   [Multilingual]          [Language-specific]        [Multi-lang]     [Controls]
```

---

## 7. Recommended Tech Stack

### 7.1 Frontend (PWA)

#### Framework
- **Next.js 14+** with App Router (React framework)
  - Built-in PWA support via `next-pwa`
  - Server-side rendering for initial load performance
  - API routes for backend logic

#### UI/UX
- **Tailwind CSS** - Rapid styling
- **shadcn/ui** or **Radix UI** - Accessible component library
- **Mapbox GL JS** or **Leaflet** - Interactive maps
- **Framer Motion** - Smooth animations

#### Audio Playback
- **Howler.js** - Cross-browser audio library with caching
- Native HTML5 Audio API with fallback

#### PWA
- **Workbox** (via next-pwa) - Service worker management
- **IndexedDB** (via Dexie.js) - Local data storage for audio and metadata

### 7.2 Backend / API Layer

#### Option A - Serverless (Recommended for MVP)
- **Vercel** - Deploy Next.js with edge functions
- **Vercel KV** or **Upstash Redis** - Cache AI responses
- **Vercel Postgres** or **Supabase** - Tourist point database

#### Option B - Traditional Backend
- **Node.js + Express** or **FastAPI (Python)**
- **PostgreSQL** + **PostGIS** - Location data
- **Redis** - Caching layer

### 7.3 AI Content Generation

#### Primary LLM
- **OpenAI GPT-4** or **GPT-4 Turbo**
  - Excellent multilingual support
  - Custom system prompts for tour guide persona
  - Structured output for consistent formatting

#### Alternative options
- **Anthropic Claude 3.5 Sonnet** - Great for nuanced, conversational content
- **Google Gemini Pro** - Strong multilingual capabilities, cost-effective

#### Implementation
- Use streaming for faster perceived performance
- Implement retry logic and fallbacks
- Cache common content patterns

### 7.4 Text-to-Speech (TTS)

#### Recommended: Multi-provider approach

**Primary TTS:**
- **ElevenLabs** - Most natural voices, multiple languages
  - Pros: Exceptional quality, voice cloning capability
  - Cons: Higher cost (~$0.18-0.30 per 1000 characters)

**Alternative/Fallback:**
- **OpenAI TTS** - Good quality, affordable
  - 6 voices, multiple languages
  - Cost: ~$0.015 per 1000 characters

- **Google Cloud Text-to-Speech** - Wide language support
  - Neural2 and WaveNet voices
  - 220+ voices across 40+ languages
  - Cost: ~$0.000016 per character

- **Amazon Polly** - Reliable, many languages
  - Neural voices available
  - Cost-effective for high volume

**Recommendation for MVP:**
- Start with **OpenAI TTS** (good balance of quality/cost)
- Implement provider abstraction for easy switching
- Pre-generate and cache audio files for all tour points

### 7.5 Content Pipeline Architecture

```typescript
// Suggested architecture
class TourContentGenerator {
  async generateTourPoint(params: {
    pointId: string;
    userInterests: string[];
    timeConstraint: number;
    language: string;
    depth: 'brief' | 'moderate' | 'detailed';
  }): Promise<TourContent> {
    // 1. Fetch point data
    // 2. Generate AI content with custom prompt
    // 3. Optimize for speech (add SSML tags if needed)
    // 4. Convert to audio via TTS
    // 5. Cache audio file (CDN/S3)
    // 6. Return content + audio URL
  }
}
```

### 7.6 Database Schema (Core Tables)

```sql
-- Tourist Points
CREATE TABLE tourist_points (
  id UUID PRIMARY KEY,
  name VARCHAR(255),
  location GEOGRAPHY(Point),
  category VARCHAR(50),
  base_info JSONB, -- historical data, facts
  images TEXT[],
  created_at TIMESTAMP
);

-- User Tours (for analytics)
CREATE TABLE user_tours (
  id UUID PRIMARY KEY,
  interests TEXT[],
  time_constraint INTEGER,
  language VARCHAR(10),
  points_visited JSONB,
  created_at TIMESTAMP
);

-- Content Cache
CREATE TABLE content_cache (
  id UUID PRIMARY KEY,
  point_id UUID REFERENCES tourist_points(id),
  interests_hash VARCHAR(64), -- hash of interests combo
  language VARCHAR(10),
  content_text TEXT,
  audio_url TEXT,
  duration INTEGER, -- seconds
  created_at TIMESTAMP,
  UNIQUE(point_id, interests_hash, language)
);
```

### 7.7 Additional Services

#### Storage
- **AWS S3** or **Cloudflare R2** - Audio file storage
- **Cloudflare CDN** - Fast audio delivery worldwide

#### Monitoring
- **Vercel Analytics** - Core web vitals
- **Sentry** - Error tracking
- **PostHog** or **Mixpanel** - User analytics

#### DevOps
- **GitHub Actions** - CI/CD
- **Docker** - Containerization (if not using serverless)

---

## 8. Development Phases Breakdown

### Phase 1.1 - Foundation (Week 1-2)
- Set up Next.js PWA with offline support
- Implement map interface with mock data
- Create user preference collection flow
- Set up database and basic API structure

### Phase 1.2 - AI Integration (Week 3-4)
- Implement AI content generation with OpenAI/Claude
- Create prompt engineering templates for different:
  - Interest categories
  - Time constraints
  - Languages
  - Detail levels
- Build content caching system

### Phase 1.3 - TTS Integration (Week 5)
- Integrate TTS provider(s)
- Implement audio generation pipeline
- Set up audio caching and CDN delivery
- Test audio quality across languages

### Phase 1.4 - Polish & Testing (Week 6)
- Offline mode testing
- Cross-browser compatibility
- Performance optimization
- User testing with 10-30 points for one city

---

## 9. Cost Estimates (Monthly - MVP Scale)

### AI Content Generation
- 1,000 unique content generations/month
- GPT-4 Turbo: ~$20-40/month

### Text-to-Speech
- 1,000 audio files × ~500 chars each
- OpenAI TTS: ~$7.50/month
- Storage (S3): ~$5/month

### Infrastructure
- Vercel Pro: $20/month
- Supabase Pro: $25/month
- CDN: ~$10/month

**Total: ~$87.50-112.50/month** for MVP with modest traffic

---

## 10. Key Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| AI content quality varies | Implement content validation, human review queue, A/B testing prompts |
| TTS sounds robotic | Use premium TTS (ElevenLabs), add SSML prosody controls |
| Slow content generation | Pre-generate common combinations, implement aggressive caching |
| Offline mode failures | Thorough PWA testing, graceful degradation, clear user feedback |
| Multilingual accuracy | Native speaker review for each language, cultural sensitivity checks |

---

## 11. Future Enhancements (Post-Phase 1)

- Real-time adaptation based on user engagement
- AR features for visual points of interest
- Social features (share tours, rate content)
- User-generated content integration
- Voice interaction (ask questions about points)
- Integration with city tourism boards

---

## Tech Stack Summary

```yaml
Frontend:
  Framework: Next.js 14+ (React)
  Styling: Tailwind CSS + shadcn/ui
  Maps: Mapbox GL JS
  Audio: Howler.js
  PWA: next-pwa (Workbox)
  Storage: IndexedDB (Dexie.js)

Backend:
  Platform: Vercel (Serverless)
  Database: Supabase (PostgreSQL + PostGIS)
  Cache: Upstash Redis

AI Services:
  LLM: OpenAI GPT-4 Turbo (primary)
  TTS: OpenAI TTS (MVP) → ElevenLabs (premium upgrade)

Storage & CDN:
  Files: Cloudflare R2
  CDN: Cloudflare

DevOps:
  Hosting: Vercel
  CI/CD: GitHub Actions
  Monitoring: Sentry + Vercel Analytics
```
