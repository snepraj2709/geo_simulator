# LLM Brand Influence Monitor - Data Model

## Overview

This document defines the database schemas for the LLM Brand Influence Monitor platform. The system uses a polyglot persistence architecture:

- **PostgreSQL** - Primary relational data (users, websites, ICPs, prompts, simulations)
- **Neo4j** - Knowledge graph (brand relationships, belief maps, co-mentions)
- **Redis** - Caching and session management
- **Elasticsearch** - Full-text search indexes
- **S3/MinIO** - Object storage for scraped content

---

## PostgreSQL Schemas

### Core Entities

#### Users & Organizations

```sql
-- Organizations (multi-tenant support)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan_type VARCHAR(50) DEFAULT 'free', -- free, pro, enterprise
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'member', -- admin, member, viewer
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_organization ON users(organization_id);
CREATE INDEX idx_users_email ON users(email);
```

#### Websites & Scraping

```sql
-- Tracked Websites
CREATE TABLE websites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    url VARCHAR(2048) NOT NULL,
    name VARCHAR(255),
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending', -- pending, scraping, completed, failed
    last_scraped_at TIMESTAMP WITH TIME ZONE,
    last_hard_scrape_at TIMESTAMP WITH TIME ZONE,
    scrape_depth INTEGER DEFAULT 3,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(organization_id, domain)
);

CREATE INDEX idx_websites_organization ON websites(organization_id);
CREATE INDEX idx_websites_domain ON websites(domain);
CREATE INDEX idx_websites_status ON websites(status);

-- Scraped Pages
CREATE TABLE scraped_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE,
    url VARCHAR(2048) NOT NULL,
    url_hash VARCHAR(64) NOT NULL, -- SHA-256 of URL for quick lookup
    title VARCHAR(512),
    meta_description TEXT,
    content_text TEXT,
    content_html_path VARCHAR(512), -- S3 path to full HTML
    word_count INTEGER,
    page_type VARCHAR(50), -- homepage, product, service, blog, about, contact
    http_status INTEGER,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(website_id, url_hash)
);

CREATE INDEX idx_scraped_pages_website ON scraped_pages(website_id);
CREATE INDEX idx_scraped_pages_url_hash ON scraped_pages(url_hash);
CREATE INDEX idx_scraped_pages_type ON scraped_pages(page_type);

-- Website Analysis Results
CREATE TABLE website_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE UNIQUE,
    industry VARCHAR(255),
    business_model VARCHAR(100), -- b2b, b2c, b2b2c, marketplace
    primary_offerings JSONB, -- Array of products/services
    value_propositions JSONB,
    target_markets JSONB,
    competitors_mentioned JSONB,
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_website_analysis_website ON website_analysis(website_id);
```

#### Ideal Customer Profiles (ICPs)

```sql
-- ICPs (5 per website)
CREATE TABLE icps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sequence_number INTEGER NOT NULL, -- 1-5

    -- Demographics
    demographics JSONB NOT NULL,
    /*
    {
        "age_range": "25-45",
        "gender": "any",
        "location": "Urban, US/EU",
        "income_level": "middle-upper",
        "education": "bachelor+"
    }
    */

    -- Professional
    professional_profile JSONB NOT NULL,
    /*
    {
        "job_titles": ["Product Manager", "Engineering Lead"],
        "company_size": "50-500",
        "industry": "Technology",
        "seniority": "mid-senior"
    }
    */

    -- Psychographics
    pain_points JSONB NOT NULL, -- Array of pain points
    goals JSONB NOT NULL, -- Array of goals
    motivations JSONB NOT NULL,
    objections JSONB, -- Common buying objections

    -- Behavior
    decision_factors JSONB, -- What influences their decisions
    information_sources JSONB, -- Where they research
    buying_journey_stage VARCHAR(50), -- typical entry stage

    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(website_id, sequence_number)
);

CREATE INDEX idx_icps_website ON icps(website_id);
CREATE INDEX idx_icps_active ON icps(is_active) WHERE is_active = true;
```

#### Conversations & Prompts

```sql
-- Conversation Sequences (50 per website: 10 topics x 5 ICPs)
CREATE TABLE conversation_sequences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE,
    icp_id UUID REFERENCES icps(id) ON DELETE CASCADE,
    topic VARCHAR(255) NOT NULL,
    context TEXT, -- Situational context
    expected_outcome TEXT,
    is_core_conversation BOOLEAN DEFAULT false, -- True for the 5 constant ones per ICP
    sequence_number INTEGER NOT NULL, -- 1-10 per ICP
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(icp_id, sequence_number)
);

CREATE INDEX idx_conversations_website ON conversation_sequences(website_id);
CREATE INDEX idx_conversations_icp ON conversation_sequences(icp_id);
CREATE INDEX idx_conversations_core ON conversation_sequences(is_core_conversation)
    WHERE is_core_conversation = true;

-- Individual Prompts within Conversations
CREATE TABLE prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversation_sequences(id) ON DELETE CASCADE,
    prompt_text TEXT NOT NULL,
    prompt_type VARCHAR(50) NOT NULL, -- primary, follow_up, clarification
    sequence_order INTEGER NOT NULL, -- Order within conversation
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_prompts_conversation ON prompts(conversation_id);
CREATE INDEX idx_prompts_type ON prompts(prompt_type);

-- Prompt Classifications
CREATE TABLE prompt_classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_id UUID REFERENCES prompts(id) ON DELETE CASCADE UNIQUE,

    -- UserIntent fields
    intent_type VARCHAR(50) NOT NULL, -- informational, evaluation, decision
    funnel_stage VARCHAR(50) NOT NULL, -- awareness, consideration, purchase
    buying_signal DECIMAL(3,2) NOT NULL CHECK (buying_signal >= 0 AND buying_signal <= 1),
    trust_need DECIMAL(3,2) NOT NULL CHECK (trust_need >= 0 AND trust_need <= 1),

    -- Additional classification
    query_intent VARCHAR(50), -- Commercial, Informational, Navigational, Transactional

    confidence_score DECIMAL(3,2),
    classified_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    classifier_version VARCHAR(50)
);

CREATE INDEX idx_classifications_prompt ON prompt_classifications(prompt_id);
CREATE INDEX idx_classifications_intent ON prompt_classifications(intent_type);
CREATE INDEX idx_classifications_funnel ON prompt_classifications(funnel_stage);
```

#### LLM Simulations

```sql
-- Simulation Runs
CREATE TABLE simulation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed
    total_prompts INTEGER,
    completed_prompts INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_simulation_runs_website ON simulation_runs(website_id);
CREATE INDEX idx_simulation_runs_status ON simulation_runs(status);

-- LLM Responses
CREATE TABLE llm_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_run_id UUID REFERENCES simulation_runs(id) ON DELETE CASCADE,
    prompt_id UUID REFERENCES prompts(id) ON DELETE CASCADE,

    llm_provider VARCHAR(50) NOT NULL, -- openai, google, anthropic, perplexity
    llm_model VARCHAR(100) NOT NULL, -- gpt-4, gemini-pro, claude-3, etc.

    response_text TEXT NOT NULL,
    response_tokens INTEGER,
    latency_ms INTEGER,

    -- Raw extraction results
    brands_mentioned JSONB, -- Array of brand names found

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(simulation_run_id, prompt_id, llm_provider)
);

CREATE INDEX idx_llm_responses_simulation ON llm_responses(simulation_run_id);
CREATE INDEX idx_llm_responses_prompt ON llm_responses(prompt_id);
CREATE INDEX idx_llm_responses_provider ON llm_responses(llm_provider);
```

#### Brand Analysis

```sql
-- Brands (known entities)
CREATE TABLE brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255) NOT NULL, -- lowercase, trimmed
    domain VARCHAR(255),
    industry VARCHAR(255),
    is_tracked BOOLEAN DEFAULT false, -- User's own brand
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(normalized_name)
);

CREATE INDEX idx_brands_normalized ON brands(normalized_name);
CREATE INDEX idx_brands_tracked ON brands(is_tracked) WHERE is_tracked = true;

-- Brand States per LLM Response
CREATE TABLE llm_brand_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    llm_response_id UUID REFERENCES llm_responses(id) ON DELETE CASCADE,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,

    -- LLMBrandState
    presence VARCHAR(50) NOT NULL, -- ignored, mentioned, trusted, recommended, compared
    position_rank INTEGER, -- Position in response (1 = first mentioned)

    -- BeliefType sold
    belief_sold VARCHAR(50), -- truth, superiority, outcome, transaction, identity, social_proof

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(llm_response_id, brand_id)
);

CREATE INDEX idx_brand_states_response ON llm_brand_states(llm_response_id);
CREATE INDEX idx_brand_states_brand ON llm_brand_states(brand_id);
CREATE INDEX idx_brand_states_presence ON llm_brand_states(presence);
CREATE INDEX idx_brand_states_belief ON llm_brand_states(belief_sold);

-- LLM Answer Belief Maps (Aggregated view)
CREATE TABLE llm_answer_belief_maps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    llm_response_id UUID REFERENCES llm_responses(id) ON DELETE CASCADE,
    prompt_classification_id UUID REFERENCES prompt_classifications(id),
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,

    -- Denormalized for query performance
    intent_type VARCHAR(50),
    funnel_stage VARCHAR(50),
    buying_signal DECIMAL(3,2),
    trust_need DECIMAL(3,2),

    presence VARCHAR(50),
    position_rank INTEGER,
    belief_sold VARCHAR(50),

    llm_provider VARCHAR(50),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_belief_maps_response ON llm_answer_belief_maps(llm_response_id);
CREATE INDEX idx_belief_maps_brand ON llm_answer_belief_maps(brand_id);
CREATE INDEX idx_belief_maps_intent ON llm_answer_belief_maps(intent_type);
CREATE INDEX idx_belief_maps_provider ON llm_answer_belief_maps(llm_provider);
```

#### Competitive Analysis

```sql
-- Competitor Relationships
CREATE TABLE competitor_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE,
    primary_brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    competitor_brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50), -- direct, indirect, substitute
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(website_id, primary_brand_id, competitor_brand_id)
);

CREATE INDEX idx_competitors_website ON competitor_relationships(website_id);
CREATE INDEX idx_competitors_primary ON competitor_relationships(primary_brand_id);

-- Share of Voice Metrics
CREATE TABLE share_of_voice (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    llm_provider VARCHAR(50) NOT NULL,

    -- Metrics
    mention_count INTEGER DEFAULT 0,
    recommendation_count INTEGER DEFAULT 0,
    first_position_count INTEGER DEFAULT 0,
    total_responses INTEGER DEFAULT 0,

    -- Calculated scores
    visibility_score DECIMAL(5,2),
    trust_score DECIMAL(5,2),
    recommendation_rate DECIMAL(5,2),

    -- Time period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(website_id, brand_id, llm_provider, period_start, period_end)
);

CREATE INDEX idx_sov_website ON share_of_voice(website_id);
CREATE INDEX idx_sov_brand ON share_of_voice(brand_id);
CREATE INDEX idx_sov_period ON share_of_voice(period_start, period_end);

-- Substitution Patterns
CREATE TABLE substitution_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE,
    missing_brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    substitute_brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,

    occurrence_count INTEGER DEFAULT 1,
    avg_position DECIMAL(3,1),

    llm_provider VARCHAR(50),

    period_start DATE,
    period_end DATE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_substitution_website ON substitution_patterns(website_id);
CREATE INDEX idx_substitution_missing ON substitution_patterns(missing_brand_id);
```

---

## Neo4j Graph Schema

### Node Types

```cypher
// Brand Node
CREATE CONSTRAINT brand_name IF NOT EXISTS
FOR (b:Brand) REQUIRE b.name IS UNIQUE;

(:Brand {
    id: String,           // UUID from PostgreSQL
    name: String,
    normalized_name: String,
    domain: String,
    industry: String,
    is_tracked: Boolean
})

// ICP Node
(:ICP {
    id: String,
    name: String,
    website_id: String,
    demographics: Map,
    pain_points: List<String>,
    goals: List<String>
})

// Intent Node
(:Intent {
    id: String,
    prompt_id: String,
    intent_type: String,      // informational, evaluation, decision
    funnel_stage: String,     // awareness, consideration, purchase
    buying_signal: Float,
    trust_need: Float,
    query_text: String
})

// Concern Node (Pain Points)
(:Concern {
    id: String,
    description: String,
    category: String
})

// BeliefType Node
(:BeliefType {
    type: String    // truth, superiority, outcome, transaction, identity, social_proof
})

// LLMProvider Node
(:LLMProvider {
    name: String,   // openai, google, anthropic, perplexity
    model: String
})

// Conversation Node
(:Conversation {
    id: String,
    topic: String,
    context: String
})
```

### Relationship Types

```cypher
// Brand relationships
(b1:Brand)-[:CO_MENTIONED {
    count: Integer,
    avg_position_delta: Float,
    llm_provider: String
}]->(b2:Brand)

(b:Brand)-[:COMPETES_WITH {
    relationship_type: String
}]->(competitor:Brand)

// ICP relationships
(icp:ICP)-[:HAS_CONCERN {
    priority: Integer
}]->(c:Concern)

(icp:ICP)-[:INITIATES]->(conv:Conversation)

// Intent relationships
(c:Concern)-[:TRIGGERS]->(i:Intent)

(conv:Conversation)-[:CONTAINS]->(i:Intent)

// Brand-Intent relationships
(b:Brand)-[:RANKS_FOR {
    position: Integer,
    presence: String,
    llm_provider: String,
    count: Integer
}]->(i:Intent)

// Belief relationships
(b:Brand)-[:INSTALLS_BELIEF {
    intent_id: String,
    llm_provider: String,
    count: Integer,
    confidence: Float
}]->(bt:BeliefType)

// LLM Provider relationships
(llm:LLMProvider)-[:RECOMMENDS {
    intent_id: String,
    position: Integer,
    belief_type: String
}]->(b:Brand)

(llm:LLMProvider)-[:IGNORES {
    intent_id: String,
    competitor_mentioned: String
}]->(b:Brand)
```

### Example Graph Queries

```cypher
// Find all brands co-mentioned with target brand
MATCH (target:Brand {name: $brandName})-[r:CO_MENTIONED]-(other:Brand)
RETURN other.name, r.count, r.avg_position_delta
ORDER BY r.count DESC;

// Get belief map for a brand across all intents
MATCH (b:Brand {name: $brandName})-[r:INSTALLS_BELIEF]->(bt:BeliefType)
RETURN bt.type, SUM(r.count) as total, AVG(r.confidence) as avg_confidence
ORDER BY total DESC;

// Find substitution patterns (who shows up when brand is ignored)
MATCH (llm:LLMProvider)-[:IGNORES]->(missing:Brand {name: $brandName})
MATCH (llm)-[rec:RECOMMENDS]->(substitute:Brand)
WHERE rec.intent_id IN [/* intent ids where brand was ignored */]
RETURN substitute.name, COUNT(*) as substitution_count
ORDER BY substitution_count DESC;

// ICP concern to brand recommendation path
MATCH path = (icp:ICP)-[:HAS_CONCERN]->(c:Concern)-[:TRIGGERS]->(i:Intent)<-[:RANKS_FOR]-(b:Brand)
WHERE icp.id = $icpId
RETURN path;
```

---

## Redis Data Structures

### Session Management

```
# User sessions
session:{session_id} -> Hash {
    user_id: String,
    organization_id: String,
    created_at: Timestamp,
    expires_at: Timestamp
}
TTL: 24 hours

# Active simulation tracking
simulation:active:{simulation_id} -> Hash {
    status: String,
    progress: Integer,
    total: Integer,
    started_at: Timestamp
}
TTL: 1 hour after completion
```

### Caching

```
# Website analysis cache
cache:website:{website_id}:analysis -> JSON
TTL: 1 hour

# LLM response cache (for repeated prompts)
cache:llm:{provider}:{prompt_hash} -> JSON {
    response: String,
    brands: Array,
    cached_at: Timestamp
}
TTL: 24 hours

# Share of voice dashboard cache
cache:sov:{website_id}:{period} -> JSON
TTL: 15 minutes

# Brand co-mention graph cache
cache:graph:{website_id}:comention -> JSON
TTL: 30 minutes
```

### Rate Limiting

```
# API rate limiting
ratelimit:api:{user_id}:{endpoint} -> Counter
TTL: 1 minute (sliding window)

# Hard scrape limiting
ratelimit:scrape:{website_id} -> Timestamp (last hard scrape)
TTL: 7 days

# LLM API cost tracking
ratelimit:llm:{organization_id}:{provider}:daily -> Counter
TTL: Until midnight
```

### Queues (Celery/Redis)

```
# Task queues
queue:scraping -> List of scraping jobs
queue:simulation -> List of simulation jobs
queue:analysis -> List of analysis jobs

# Priority queues
queue:scraping:high -> High priority scraping
queue:scraping:low -> Low priority scraping
```

---

## Elasticsearch Indices

### Website Content Index

```json
{
  "mappings": {
    "properties": {
      "website_id": { "type": "keyword" },
      "page_id": { "type": "keyword" },
      "url": { "type": "keyword" },
      "title": {
        "type": "text",
        "analyzer": "english"
      },
      "content": {
        "type": "text",
        "analyzer": "english"
      },
      "meta_description": { "type": "text" },
      "page_type": { "type": "keyword" },
      "scraped_at": { "type": "date" },
      "products": {
        "type": "nested",
        "properties": {
          "name": { "type": "text" },
          "description": { "type": "text" }
        }
      },
      "services": {
        "type": "nested",
        "properties": {
          "name": { "type": "text" },
          "description": { "type": "text" }
        }
      }
    }
  }
}
```

### Brand Mentions Index

```json
{
  "mappings": {
    "properties": {
      "brand_id": { "type": "keyword" },
      "brand_name": { "type": "keyword" },
      "llm_provider": { "type": "keyword" },
      "prompt_id": { "type": "keyword" },
      "response_id": { "type": "keyword" },
      "context": { "type": "text" },
      "presence": { "type": "keyword" },
      "position": { "type": "integer" },
      "belief_type": { "type": "keyword" },
      "intent_type": { "type": "keyword" },
      "funnel_stage": { "type": "keyword" },
      "timestamp": { "type": "date" }
    }
  }
}
```

---

## S3/MinIO Object Storage

### Bucket Structure

```
llm-brand-monitor/
├── scraped-content/
│   └── {website_id}/
│       └── {page_id}/
│           ├── raw.html
│           ├── cleaned.txt
│           └── metadata.json
│
├── llm-responses/
│   └── {simulation_run_id}/
│       └── {response_id}.json
│
├── exports/
│   └── {organization_id}/
│       └── {export_id}/
│           └── report.pdf
│
└── backups/
    └── {date}/
        └── pg_dump.sql.gz
```

---

## Data Retention Policies

| Data Type | Retention Period | Archive Strategy |
|-----------|-----------------|------------------|
| User data | Account lifetime + 30 days | Cold storage |
| Scraped content | 90 days | S3 Glacier |
| LLM responses | 180 days | S3 Glacier |
| Analytics/Metrics | 2 years | Compressed archives |
| Audit logs | 7 years | Compliance storage |
| Cache data | TTL-based | Auto-expire |

---

## Migration Strategy

### Version Control
- All schema changes tracked in migration files
- Sequential versioning (V001, V002, etc.)
- Rollback scripts for each migration

### Tools
- PostgreSQL: Alembic (Python) or Flyway
- Neo4j: Neo4j Migrations
- Elasticsearch: Index aliases for zero-downtime updates
