# LLM Brand Influence Monitor - System Architecture

## Overview

The LLM Brand Influence Monitor is an AI Visibility & Trust Platform that simulates and audits LLM answers to measure brand presence, competitive positioning, and belief formation across major language models.

Unlike traditional SEO tools that score pages, this platform **simulates how LLMs perceive and recommend brands** by modeling question clusters, mapping entity dominance, and analyzing LLM answer construction patterns.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   Web Dashboard │  │   API Clients   │  │  Webhook Subs   │                  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘                  │
└───────────┼─────────────────────┼─────────────────────┼──────────────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Authentication │ Rate Limiting │ Request Routing │ Response Caching   │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CORE SERVICES LAYER                                    │
│                                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐              │
│  │  Website Scraper │  │   ICP Generator  │  │ Conversation     │              │
│  │     Service      │  │     Service      │  │   Generator      │              │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘              │
│           │                     │                     │                         │
│           ▼                     ▼                     ▼                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐              │
│  │ Prompt Classifier│  │  LLM Simulation  │  │  Brand Presence  │              │
│  │     Engine       │  │      Layer       │  │    Detector      │              │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘              │
│           │                     │                     │                         │
│           ▼                     ▼                     ▼                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐              │
│  │  Knowledge Graph │  │   Competitive    │  │   Analytics &    │              │
│  │     Builder      │  │  Substitution    │  │    Reporting     │              │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘              │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                             │
│                                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐              │
│  │    PostgreSQL    │  │      Neo4j       │  │      Redis       │              │
│  │  (Primary Data)  │  │ (Knowledge Graph)│  │     (Cache)      │              │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘              │
│                                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                                     │
│  │   Elasticsearch  │  │    S3/MinIO      │                                     │
│  │    (Search)      │  │  (File Storage)  │                                     │
│  └──────────────────┘  └──────────────────┘                                     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL INTEGRATIONS                                     │
│                                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │   OpenAI     │ │   Gemini     │ │   Claude     │ │  Perplexity  │           │
│  │     API      │ │     API      │ │     API      │ │     API      │           │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘           │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Website Scraper Service

**Purpose:** Performs deep crawling of submitted websites to extract content, structure, and semantic information.

**Key Features:**
- Full-site recursive crawling with configurable depth
- Content extraction (text, metadata, structured data)
- Service/product offering identification
- Hard scrape limiting (1 per week per domain)
- Incremental update support

**Technology Stack:**
- Playwright/Puppeteer for JavaScript-rendered pages
- Scrapy for high-volume crawling
- BeautifulSoup for HTML parsing

```
┌─────────────────────────────────────────┐
│          Website Scraper Service         │
├─────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────────┐   │
│  │ URL Queue   │  │ Content Parser  │   │
│  │  Manager    │──│                 │   │
│  └─────────────┘  └────────┬────────┘   │
│                            │            │
│  ┌─────────────┐  ┌────────▼────────┐   │
│  │ Rate        │  │ Entity          │   │
│  │ Limiter     │──│ Extractor       │   │
│  └─────────────┘  └────────┬────────┘   │
│                            │            │
│                   ┌────────▼────────┐   │
│                   │ Storage Handler │   │
│                   └─────────────────┘   │
└─────────────────────────────────────────┘
```

### 2. ICP Generator Service

**Purpose:** Analyzes scraped website data to generate 5 Ideal Customer Profiles.

**Process Flow:**
1. Analyze product/service offerings
2. Identify target market segments
3. Generate demographic and psychographic profiles
4. Define pain points and goals
5. Map customer journey stages

**Output:** 5 detailed ICP objects containing:
- Demographics
- Job roles/titles
- Pain points
- Goals and motivations
- Preferred communication channels
- Decision-making factors

### 3. Conversation Generator Service

**Purpose:** Creates realistic chat conversation sequences that ICPs might have with LLMs.

**Key Features:**
- Generates 10 conversation topics per ICP (50 total)
- Maintains 5 core conversation threads per ICP (25 total, constant after generation)
- Simulates day-to-day problem-solving queries
- Includes follow-up and clarification patterns

**Conversation Structure:**
```
ConversationSequence {
  icp_id: string
  primary_prompt: string
  sub_prompts: string[]  // Follow-up questions
  context: string        // Situational context
  expected_outcome: string
}
```

### 4. Prompt Classifier Engine

**Purpose:** Categorizes all 50 ICP prompts with intent metadata for accurate simulation targeting.

**Classification Output:**
```typescript
UserIntent {
  intent_type: "informational" | "evaluation" | "decision"
  funnel_stage: "awareness" | "consideration" | "purchase"
  buying_signal: number  // 0.0 – 1.0
  trust_need: number     // 0.0 – 1.0
}
```

**Classification Dimensions:**
- **Intent Type:** What is the user trying to accomplish?
- **Funnel Stage:** Where are they in the buying journey?
- **Buying Signal:** How close to purchase decision?
- **Trust Need:** How much authority/proof required?

### 5. LLM Simulation Layer

**Purpose:** Queries multiple LLM providers to capture how brands are positioned in responses.

**Supported Models:**
- ChatGPT (OpenAI GPT-4/GPT-4o)
- Gemini (Google)
- Claude (Anthropic)
- Perplexity

**Capture Metrics:**
- Brands mentioned/cited
- Intent ranking (Commercial, Informational, Navigational, Transactional)
- Priority order of brand mentions
- Contextual framing of brands

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Simulation Layer                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐                                               │
│  │ Prompt Queue │                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Parallel LLM Query Orchestrator              │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │              │              │              │           │
│         ▼              ▼              ▼              ▼           │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐     │
│  │  OpenAI  │   │  Gemini  │   │  Claude  │   │Perplexity│     │
│  │ Adapter  │   │ Adapter  │   │ Adapter  │   │ Adapter  │     │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘     │
│       │              │              │              │             │
│       ▼              ▼              ▼              ▼             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Response Aggregator & Normalizer             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│                    ┌─────────────────┐                          │
│                    │ Brand Extractor │                          │
│                    └─────────────────┘                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6. Brand Presence Detector

**Purpose:** Analyzes LLM responses to determine brand positioning state.

**Brand States:**
```typescript
LLMBrandState {
  presence: "ignored" | "mentioned" | "trusted" | "recommended" | "compared"
  position_rank: number | null
}
```

**State Definitions:**
- `ignored` - Brand not mentioned at all
- `mentioned` - Brand name appears but without context
- `trusted` - Brand cited as authority without sales push
- `recommended` - Brand with clear call-to-action
- `compared` - Brand in neutral evaluation context

**Rule:** One dominant state per brand per answer.

### 7. Knowledge Graph Builder (Neo4j)

**Purpose:** Builds and maintains a graph database of brand relationships, ICP concerns, and belief formations.

**Node Types:**
- Brand
- ICP
- Intent
- Concern/Pain Point
- Conversation
- BeliefType

**Edge Types:**
- MENTIONS (Brand → Brand co-occurrence)
- HAS_CONCERN (ICP → Concern)
- TRIGGERS_INTENT (Concern → Intent)
- RANKS_FOR (Brand → Intent)
- INSTALLS_BELIEF (LLM Response → BeliefType)

**Belief Types:**
```typescript
BeliefType {
  | "truth"        // epistemic clarity, neutrality
  | "superiority"  // better than alternatives
  | "outcome"      // ROI, performance, results
  | "transaction"  // buy now, act
  | "identity"     // people like you use this
  | "social_proof" // others chose this
}
```

### 8. Competitive Substitution Engine

**Purpose:** Identifies which competitors capture share-of-voice when the target brand is absent.

**Metrics Generated:**
- Share-of-Voice by LLM provider
- Substitution patterns (who replaces whom)
- Competitive gap analysis
- Opportunity scoring

---

## Data Flow

### Initial Setup Flow

```
User Submits Website
        │
        ▼
┌───────────────────┐
│ Website Scraper   │──────────────────┐
└─────────┬─────────┘                  │
          │                            │
          ▼                            ▼
┌───────────────────┐         ┌───────────────────┐
│ Product/Service   │         │ Content Storage   │
│ Analyzer          │         │ (S3/PostgreSQL)   │
└─────────┬─────────┘         └───────────────────┘
          │
          ▼
┌───────────────────┐
│ ICP Generator     │
│ (5 profiles)      │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Conversation      │
│ Generator (50)    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Prompt Classifier │
│ Engine            │
└───────────────────┘
```

### Simulation Flow

```
Classified Prompts (50)
        │
        ▼
┌───────────────────┐
│ LLM Simulation    │
│ Layer             │
└─────────┬─────────┘
          │
          ├──────────────────────────────────────┐
          ▼                                      ▼
┌───────────────────┐                  ┌───────────────────┐
│ Brand Presence    │                  │ Intent Ranking    │
│ Detector          │                  │ Analyzer          │
└─────────┬─────────┘                  └─────────┬─────────┘
          │                                      │
          └──────────────┬───────────────────────┘
                         │
                         ▼
              ┌───────────────────┐
              │ Knowledge Graph   │
              │ Builder (Neo4j)   │
              └─────────┬─────────┘
                        │
                        ▼
              ┌───────────────────┐
              │ Competitive       │
              │ Substitution Map  │
              └───────────────────┘
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| API Gateway | Kong / AWS API Gateway | Routing, auth, rate limiting |
| Backend Services | Python (FastAPI) | Core business logic |
| Task Queue | Celery + Redis | Async job processing |
| Primary Database | PostgreSQL | Structured data storage |
| Graph Database | Neo4j | Knowledge graph storage |
| Cache | Redis | Session, API response caching |
| Search | Elasticsearch | Full-text search capabilities |
| Object Storage | S3 / MinIO | Scraped content storage |
| Container Orchestration | Kubernetes | Service deployment |
| Monitoring | Prometheus + Grafana | Metrics and alerting |
| Logging | ELK Stack | Centralized logging |

---

## Security Architecture

### Authentication & Authorization
- JWT-based authentication
- Role-based access control (RBAC)
- API key management for external integrations
- OAuth 2.0 for third-party integrations

### Data Protection
- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- PII handling compliance (GDPR, CCPA)
- Regular security audits

### Rate Limiting
- Per-user API rate limits
- Hard scrape limiting (1/week)
- LLM API cost controls

---

## Scalability Considerations

### Horizontal Scaling
- Stateless service design
- Kubernetes HPA for auto-scaling
- Database read replicas

### Caching Strategy
- Redis for hot data
- CDN for static assets
- LLM response caching (TTL-based)

### Async Processing
- Celery workers for long-running tasks
- Priority queues for critical jobs
- Dead letter queues for failed jobs

---

## Module Dependencies

```
                    ┌─────────────────────┐
                    │    API Gateway      │
                    └──────────┬──────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Website Service  │ │ Simulation Svc   │ │ Analytics Svc    │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                    │
         │           ┌────────┴────────┐           │
         │           │                 │           │
         ▼           ▼                 ▼           ▼
┌──────────────────────────────────────────────────────────────┐
│                      Shared Libraries                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ │
│  │ DB Client  │ │ LLM Client │ │ Graph Client│ │ Queue Client││
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## Future Considerations

1. **Multi-tenancy:** Support for agency/enterprise accounts
2. **Real-time Monitoring:** Live tracking of brand mentions
3. **Custom Model Training:** Fine-tuned classifiers per industry
4. **Integration Hub:** Connections to marketing platforms
5. **White-label Support:** Reseller/partner program enablement
