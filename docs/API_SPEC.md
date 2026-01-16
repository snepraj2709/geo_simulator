# LLM Brand Influence Monitor - API Specification

## Overview

This document defines the REST API for the LLM Brand Influence Monitor platform. The API follows RESTful conventions and uses JSON for request/response payloads.

**Base URL:** `https://api.llmbrandmonitor.com/v1`

**Authentication:** Bearer token (JWT)

---

## Authentication

### POST /auth/register

Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "name": "John Doe",
  "organization_name": "Acme Corp"
}
```

**Response (201 Created):**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "John Doe",
    "organization_id": "uuid"
  },
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### POST /auth/login

Authenticate user and receive tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200 OK):**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "John Doe",
    "organization_id": "uuid",
    "role": "admin"
  },
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 3600
}
```

### POST /auth/refresh

Refresh access token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200 OK):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 3600
}
```

### POST /auth/logout

Invalidate current session.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (204 No Content)**

---

## Websites

### POST /websites

Submit a new website for tracking.

**Request:**
```json
{
  "url": "https://example.com",
  "name": "Example Company",
  "scrape_depth": 3
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "domain": "example.com",
  "url": "https://example.com",
  "name": "Example Company",
  "status": "pending",
  "scrape_depth": 3,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### GET /websites

List all tracked websites.

**Query Parameters:**
- `page` (int, default: 1)
- `limit` (int, default: 20, max: 100)
- `status` (string): Filter by status

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "uuid",
      "domain": "example.com",
      "url": "https://example.com",
      "name": "Example Company",
      "status": "completed",
      "last_scraped_at": "2024-01-15T10:30:00Z",
      "icp_count": 5,
      "conversation_count": 50
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "pages": 3
  }
}
```

### GET /websites/{website_id}

Get website details.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "domain": "example.com",
  "url": "https://example.com",
  "name": "Example Company",
  "description": "Auto-generated description",
  "status": "completed",
  "scrape_depth": 3,
  "last_scraped_at": "2024-01-15T10:30:00Z",
  "last_hard_scrape_at": "2024-01-08T10:30:00Z",
  "created_at": "2024-01-01T10:30:00Z",
  "analysis": {
    "industry": "Technology",
    "business_model": "b2b",
    "primary_offerings": [
      {"name": "Product A", "type": "product"},
      {"name": "Service B", "type": "service"}
    ],
    "value_propositions": ["Fast", "Reliable", "Affordable"]
  },
  "stats": {
    "pages_scraped": 150,
    "icps_generated": 5,
    "conversations_generated": 50,
    "simulations_run": 12
  }
}
```

### POST /websites/{website_id}/scrape

Trigger a scrape for a website.

**Request:**
```json
{
  "type": "incremental"
}
```

**Type Options:**
- `incremental` - Only scrape new/changed pages
- `hard` - Full re-scrape (limited to 1/week)

**Response (202 Accepted):**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "type": "incremental",
  "estimated_pages": 150
}
```

**Error Response (429 Too Many Requests):**
```json
{
  "error": "hard_scrape_limit_exceeded",
  "message": "Hard scrape limit reached. Next available: 2024-01-22T10:30:00Z",
  "next_available_at": "2024-01-22T10:30:00Z"
}
```

### DELETE /websites/{website_id}

Remove a tracked website.

**Response (204 No Content)**

---

## Scraped Pages

### GET /websites/{website_id}/pages

List scraped pages for a website.

**Query Parameters:**
- `page` (int)
- `limit` (int)
- `page_type` (string): homepage, product, service, blog, about, contact
- `search` (string): Full-text search

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "uuid",
      "url": "https://example.com/products",
      "title": "Our Products",
      "page_type": "product",
      "word_count": 1500,
      "scraped_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {...}
}
```

### GET /websites/{website_id}/pages/{page_id}

Get page content details.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "url": "https://example.com/products",
  "title": "Our Products",
  "meta_description": "Explore our product catalog",
  "content_text": "Full page content...",
  "page_type": "product",
  "word_count": 1500,
  "http_status": 200,
  "scraped_at": "2024-01-15T10:30:00Z"
}
```

---

## Ideal Customer Profiles (ICPs)

### GET /websites/{website_id}/icps

List ICPs for a website.

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Tech-Savvy Product Manager",
      "sequence_number": 1,
      "description": "Mid-level product managers at SaaS companies...",
      "demographics": {
        "age_range": "28-42",
        "location": "Urban, US/EU",
        "education": "bachelor+"
      },
      "professional_profile": {
        "job_titles": ["Product Manager", "Senior PM"],
        "company_size": "50-500",
        "industry": "Technology"
      },
      "pain_points": [
        "Difficulty prioritizing features",
        "Stakeholder alignment challenges"
      ],
      "goals": [
        "Ship products faster",
        "Improve team collaboration"
      ],
      "conversation_count": 10,
      "is_active": true
    }
  ]
}
```

### GET /websites/{website_id}/icps/{icp_id}

Get ICP details.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "website_id": "uuid",
  "name": "Tech-Savvy Product Manager",
  "sequence_number": 1,
  "description": "Mid-level product managers at SaaS companies...",
  "demographics": {
    "age_range": "28-42",
    "gender": "any",
    "location": "Urban, US/EU",
    "income_level": "upper-middle",
    "education": "bachelor+"
  },
  "professional_profile": {
    "job_titles": ["Product Manager", "Senior PM", "Group PM"],
    "company_size": "50-500",
    "industry": "Technology",
    "seniority": "mid-senior"
  },
  "pain_points": [
    "Difficulty prioritizing features",
    "Stakeholder alignment challenges",
    "Technical debt management"
  ],
  "goals": [
    "Ship products faster",
    "Improve team collaboration",
    "Drive product adoption"
  ],
  "motivations": {
    "primary": "Career advancement",
    "secondary": "Making user impact"
  },
  "objections": [
    "Price concerns",
    "Integration complexity"
  ],
  "decision_factors": [
    "Ease of use",
    "Integration capabilities",
    "Customer support"
  ],
  "information_sources": [
    "Product Hunt",
    "LinkedIn",
    "Industry blogs"
  ],
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### PUT /websites/{website_id}/icps/{icp_id}

Update an ICP.

**Request:**
```json
{
  "name": "Updated ICP Name",
  "pain_points": ["Updated pain point 1", "Pain point 2"],
  "is_active": true
}
```

**Response (200 OK):** Updated ICP object

### POST /websites/{website_id}/icps/regenerate

Regenerate all ICPs for a website.

**Response (202 Accepted):**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "ICP regeneration started. This will also regenerate conversations."
}
```

---

## Conversations

### GET /websites/{website_id}/conversations

List conversation sequences.

**Query Parameters:**
- `icp_id` (uuid): Filter by ICP
- `is_core` (boolean): Filter core conversations only
- `page`, `limit`

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "uuid",
      "icp_id": "uuid",
      "icp_name": "Tech-Savvy Product Manager",
      "topic": "Evaluating project management tools",
      "context": "Planning Q2 roadmap, needs better tracking",
      "is_core_conversation": true,
      "sequence_number": 1,
      "prompt_count": 4
    }
  ],
  "pagination": {...}
}
```

### GET /websites/{website_id}/conversations/{conversation_id}

Get conversation with all prompts.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "icp_id": "uuid",
  "topic": "Evaluating project management tools",
  "context": "Planning Q2 roadmap, needs better team visibility",
  "expected_outcome": "Shortlist 2-3 tools for trial",
  "is_core_conversation": true,
  "prompts": [
    {
      "id": "uuid",
      "prompt_text": "What are the best project management tools for a 50-person tech team?",
      "prompt_type": "primary",
      "sequence_order": 1,
      "classification": {
        "intent_type": "evaluation",
        "funnel_stage": "consideration",
        "buying_signal": 0.65,
        "trust_need": 0.7,
        "query_intent": "Commercial"
      }
    },
    {
      "id": "uuid",
      "prompt_text": "How does Asana compare to Monday.com for agile teams?",
      "prompt_type": "follow_up",
      "sequence_order": 2,
      "classification": {
        "intent_type": "evaluation",
        "funnel_stage": "consideration",
        "buying_signal": 0.75,
        "trust_need": 0.8,
        "query_intent": "Commercial"
      }
    }
  ]
}
```

---

## Prompt Classifications

### GET /websites/{website_id}/classifications

Get all prompt classifications with filtering.

**Query Parameters:**
- `intent_type` (string): informational, evaluation, decision
- `funnel_stage` (string): awareness, consideration, purchase
- `min_buying_signal` (float)
- `min_trust_need` (float)

**Response (200 OK):**
```json
{
  "data": [
    {
      "prompt_id": "uuid",
      "prompt_text": "What are the best...",
      "conversation_id": "uuid",
      "icp_id": "uuid",
      "classification": {
        "intent_type": "evaluation",
        "funnel_stage": "consideration",
        "buying_signal": 0.65,
        "trust_need": 0.7,
        "query_intent": "Commercial"
      }
    }
  ],
  "summary": {
    "total": 50,
    "by_intent_type": {
      "informational": 15,
      "evaluation": 25,
      "decision": 10
    },
    "by_funnel_stage": {
      "awareness": 12,
      "consideration": 28,
      "purchase": 10
    },
    "avg_buying_signal": 0.58,
    "avg_trust_need": 0.72
  }
}
```

---

## Simulations

### POST /websites/{website_id}/simulations

Start a new LLM simulation run.

**Request:**
```json
{
  "llm_providers": ["openai", "google", "anthropic", "perplexity"],
  "prompt_filter": {
    "icp_ids": ["uuid1", "uuid2"],
    "intent_types": ["evaluation", "decision"],
    "core_only": false
  }
}
```

**Response (202 Accepted):**
```json
{
  "id": "uuid",
  "status": "queued",
  "total_prompts": 50,
  "llm_providers": ["openai", "google", "anthropic", "perplexity"],
  "estimated_completion": "2024-01-15T11:00:00Z",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### GET /websites/{website_id}/simulations

List simulation runs.

**Query Parameters:**
- `status` (string): pending, running, completed, failed
- `page`, `limit`

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "uuid",
      "status": "completed",
      "total_prompts": 50,
      "completed_prompts": 50,
      "llm_providers": ["openai", "google", "anthropic", "perplexity"],
      "started_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:45:00Z"
    }
  ],
  "pagination": {...}
}
```

### GET /websites/{website_id}/simulations/{simulation_id}

Get simulation details and results.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "status": "completed",
  "total_prompts": 50,
  "completed_prompts": 50,
  "llm_providers": ["openai", "google", "anthropic", "perplexity"],
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:45:00Z",
  "summary": {
    "brands_discovered": 45,
    "your_brand_mentions": 32,
    "your_brand_recommendations": 8,
    "top_competitors": [
      {"name": "Competitor A", "mentions": 28},
      {"name": "Competitor B", "mentions": 22}
    ]
  }
}
```

### GET /websites/{website_id}/simulations/{simulation_id}/responses

Get detailed LLM responses.

**Query Parameters:**
- `llm_provider` (string)
- `prompt_id` (uuid)
- `brand_id` (uuid)
- `presence` (string): ignored, mentioned, trusted, recommended, compared
- `page`, `limit`

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "uuid",
      "prompt_id": "uuid",
      "prompt_text": "What are the best project management tools?",
      "llm_provider": "openai",
      "llm_model": "gpt-4",
      "response_text": "There are several excellent project management tools...",
      "brands_mentioned": [
        {
          "brand_id": "uuid",
          "brand_name": "Asana",
          "presence": "recommended",
          "position_rank": 1,
          "belief_sold": "superiority"
        },
        {
          "brand_id": "uuid",
          "brand_name": "Monday.com",
          "presence": "compared",
          "position_rank": 2,
          "belief_sold": "truth"
        }
      ],
      "response_tokens": 350,
      "latency_ms": 1250
    }
  ],
  "pagination": {...}
}
```

---

## Brand Analysis

### GET /websites/{website_id}/brands

List all brands discovered for a website.

**Query Parameters:**
- `is_tracked` (boolean): Filter tracked brands
- `min_mentions` (int): Minimum mention count
- `search` (string)

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Your Brand",
      "domain": "yourbrand.com",
      "is_tracked": true,
      "stats": {
        "total_mentions": 32,
        "recommendations": 8,
        "comparisons": 15,
        "avg_position": 2.3
      }
    }
  ],
  "pagination": {...}
}
```

### POST /websites/{website_id}/brands/track

Mark a brand as tracked (your brand).

**Request:**
```json
{
  "brand_id": "uuid"
}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "name": "Your Brand",
  "is_tracked": true
}
```

### GET /websites/{website_id}/brands/{brand_id}/analysis

Get detailed brand analysis.

**Response (200 OK):**
```json
{
  "brand": {
    "id": "uuid",
    "name": "Your Brand",
    "domain": "yourbrand.com",
    "industry": "Technology"
  },
  "presence_breakdown": {
    "ignored": 18,
    "mentioned": 45,
    "trusted": 22,
    "recommended": 8,
    "compared": 15
  },
  "by_llm_provider": {
    "openai": {
      "mentions": 12,
      "recommendations": 3,
      "avg_position": 2.1
    },
    "google": {
      "mentions": 8,
      "recommendations": 2,
      "avg_position": 2.8
    },
    "anthropic": {
      "mentions": 7,
      "recommendations": 2,
      "avg_position": 2.5
    },
    "perplexity": {
      "mentions": 5,
      "recommendations": 1,
      "avg_position": 3.2
    }
  },
  "belief_distribution": {
    "truth": 12,
    "superiority": 8,
    "outcome": 15,
    "transaction": 3,
    "identity": 5,
    "social_proof": 2
  },
  "by_intent_type": {
    "informational": {
      "mentions": 10,
      "presence_rate": 0.45
    },
    "evaluation": {
      "mentions": 18,
      "presence_rate": 0.72
    },
    "decision": {
      "mentions": 4,
      "presence_rate": 0.40
    }
  },
  "by_funnel_stage": {
    "awareness": {
      "mentions": 8,
      "presence_rate": 0.42
    },
    "consideration": {
      "mentions": 20,
      "presence_rate": 0.71
    },
    "purchase": {
      "mentions": 4,
      "presence_rate": 0.40
    }
  }
}
```

---

## Share of Voice

### GET /websites/{website_id}/share-of-voice

Get share of voice metrics.

**Query Parameters:**
- `period` (string): 7d, 30d, 90d (default: 30d)
- `llm_provider` (string): Filter by provider

**Response (200 OK):**
```json
{
  "period": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  },
  "your_brand": {
    "id": "uuid",
    "name": "Your Brand",
    "visibility_score": 72.5,
    "trust_score": 68.3,
    "recommendation_rate": 0.25,
    "avg_position": 2.3
  },
  "competitors": [
    {
      "id": "uuid",
      "name": "Competitor A",
      "visibility_score": 85.2,
      "trust_score": 71.5,
      "recommendation_rate": 0.32,
      "avg_position": 1.8
    },
    {
      "id": "uuid",
      "name": "Competitor B",
      "visibility_score": 65.8,
      "trust_score": 62.1,
      "recommendation_rate": 0.18,
      "avg_position": 2.9
    }
  ],
  "by_llm_provider": {
    "openai": {
      "your_brand_share": 0.28,
      "leader": "Competitor A",
      "leader_share": 0.35
    },
    "google": {
      "your_brand_share": 0.22,
      "leader": "Competitor A",
      "leader_share": 0.38
    }
  }
}
```

### GET /websites/{website_id}/share-of-voice/trends

Get share of voice trends over time.

**Query Parameters:**
- `period` (string): 30d, 90d, 180d
- `granularity` (string): daily, weekly

**Response (200 OK):**
```json
{
  "period": {
    "start": "2024-01-01",
    "end": "2024-03-31",
    "granularity": "weekly"
  },
  "your_brand": {
    "id": "uuid",
    "name": "Your Brand",
    "trend": [
      {"date": "2024-01-07", "visibility_score": 68.2},
      {"date": "2024-01-14", "visibility_score": 70.5},
      {"date": "2024-01-21", "visibility_score": 72.1}
    ]
  },
  "top_competitors": [
    {
      "name": "Competitor A",
      "trend": [
        {"date": "2024-01-07", "visibility_score": 82.5},
        {"date": "2024-01-14", "visibility_score": 84.2}
      ]
    }
  ]
}
```

---

## Competitive Analysis

### GET /websites/{website_id}/competitors

Get competitor relationships.

**Response (200 OK):**
```json
{
  "tracked_brand": {
    "id": "uuid",
    "name": "Your Brand"
  },
  "competitors": [
    {
      "id": "uuid",
      "name": "Competitor A",
      "domain": "competitora.com",
      "relationship_type": "direct",
      "co_mention_frequency": 45,
      "substitution_frequency": 12
    }
  ]
}
```

### GET /websites/{website_id}/substitution-map

Get substitution patterns (who appears when you're absent).

**Response (200 OK):**
```json
{
  "tracked_brand": {
    "id": "uuid",
    "name": "Your Brand"
  },
  "when_ignored": {
    "total_instances": 18,
    "substitutes": [
      {
        "brand_id": "uuid",
        "brand_name": "Competitor A",
        "occurrence_count": 12,
        "avg_position": 1.5,
        "by_provider": {
          "openai": 5,
          "google": 4,
          "anthropic": 3
        }
      },
      {
        "brand_id": "uuid",
        "brand_name": "Competitor B",
        "occurrence_count": 8,
        "avg_position": 2.1
      }
    ]
  },
  "intent_gaps": [
    {
      "intent_type": "decision",
      "funnel_stage": "purchase",
      "your_presence_rate": 0.20,
      "top_competitor": "Competitor A",
      "competitor_presence_rate": 0.75
    }
  ]
}
```

---

## Knowledge Graph

### GET /websites/{website_id}/graph/belief-map

Get LLM answer belief map data for visualization.

**Query Parameters:**
- `brand_id` (uuid): Filter by brand
- `icp_id` (uuid): Filter by ICP

**Response (200 OK):**
```json
{
  "nodes": [
    {"id": "brand_1", "type": "brand", "name": "Your Brand", "is_tracked": true},
    {"id": "brand_2", "type": "brand", "name": "Competitor A"},
    {"id": "belief_truth", "type": "belief", "name": "truth"},
    {"id": "intent_1", "type": "intent", "name": "evaluation"}
  ],
  "edges": [
    {
      "source": "brand_1",
      "target": "belief_truth",
      "type": "installs_belief",
      "weight": 12
    },
    {
      "source": "brand_1",
      "target": "intent_1",
      "type": "ranks_for",
      "position": 2
    }
  ]
}
```

### GET /websites/{website_id}/graph/co-mentions

Get brand co-mention network.

**Response (200 OK):**
```json
{
  "nodes": [
    {"id": "brand_1", "name": "Your Brand", "mention_count": 32},
    {"id": "brand_2", "name": "Competitor A", "mention_count": 45},
    {"id": "brand_3", "name": "Competitor B", "mention_count": 28}
  ],
  "edges": [
    {
      "source": "brand_1",
      "target": "brand_2",
      "co_mention_count": 18,
      "avg_position_delta": 0.8
    },
    {
      "source": "brand_1",
      "target": "brand_3",
      "co_mention_count": 12,
      "avg_position_delta": -0.5
    }
  ]
}
```

### GET /websites/{website_id}/graph/icp-journey

Get ICP concern to brand recommendation paths.

**Query Parameters:**
- `icp_id` (uuid, required)

**Response (200 OK):**
```json
{
  "icp": {
    "id": "uuid",
    "name": "Tech-Savvy Product Manager"
  },
  "paths": [
    {
      "concern": "Difficulty prioritizing features",
      "triggers_intent": {
        "type": "evaluation",
        "query": "Best tools for feature prioritization"
      },
      "brands_ranked": [
        {"name": "ProductBoard", "position": 1, "presence": "recommended"},
        {"name": "Your Brand", "position": 2, "presence": "compared"},
        {"name": "Aha!", "position": 3, "presence": "mentioned"}
      ]
    }
  ]
}
```

---

## Webhooks

### POST /webhooks

Create a webhook subscription.

**Request:**
```json
{
  "url": "https://yourapp.com/webhooks/llm-monitor",
  "events": [
    "simulation.completed",
    "scrape.completed",
    "brand.position_change"
  ],
  "secret": "your_webhook_secret"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "url": "https://yourapp.com/webhooks/llm-monitor",
  "events": ["simulation.completed", "scrape.completed", "brand.position_change"],
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Webhook Event Payloads

**simulation.completed:**
```json
{
  "event": "simulation.completed",
  "timestamp": "2024-01-15T10:45:00Z",
  "data": {
    "simulation_id": "uuid",
    "website_id": "uuid",
    "status": "completed",
    "summary": {
      "your_brand_mentions": 32,
      "position_change": "+2"
    }
  }
}
```

**brand.position_change:**
```json
{
  "event": "brand.position_change",
  "timestamp": "2024-01-15T10:45:00Z",
  "data": {
    "brand_id": "uuid",
    "brand_name": "Your Brand",
    "previous_avg_position": 3.5,
    "new_avg_position": 2.1,
    "change": "improvement"
  }
}
```

---

## Error Responses

### Standard Error Format

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "url",
        "message": "Must be a valid URL"
      }
    ]
  },
  "request_id": "uuid"
}
```

### Error Codes

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 400 | `validation_error` | Invalid request parameters |
| 401 | `unauthorized` | Missing or invalid authentication |
| 403 | `forbidden` | Insufficient permissions |
| 404 | `not_found` | Resource not found |
| 409 | `conflict` | Resource already exists |
| 429 | `rate_limit_exceeded` | Too many requests |
| 500 | `internal_error` | Server error |

---

## Rate Limits

| Endpoint Category | Limit |
|-------------------|-------|
| Authentication | 10 requests/minute |
| Read operations | 100 requests/minute |
| Write operations | 30 requests/minute |
| Simulation triggers | 5 requests/hour |
| Hard scrapes | 1 per week per website |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705312800
```

---

## Pagination

All list endpoints support cursor-based pagination:

**Query Parameters:**
- `page` (int): Page number (1-indexed)
- `limit` (int): Items per page (default: 20, max: 100)

**Response Format:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```
