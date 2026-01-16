An AI Visibility & Trust Platform that simulates how LLMs perceive and recommend brands rather than traditional page scoring. It models question clusters, maps entity dominance, and analyzes LLM answer construction patterns.               
  ---
  Key Architectural Decisions
  ┌─────────────────┬───────────────────────────┬────────────────────────────────────────────────────────────────────────┐
  │    Decision     │          Choice           │                               Rationale                                │
  ├─────────────────┼───────────────────────────┼────────────────────────────────────────────────────────────────────────┤
  │ Processing      │ 6-stage pipeline          │ Website → ICP → Conversations → Classification → LLM Simulation →      │
  │ Model           │                           │ Brand Analysis                                                         │
  ├─────────────────┼───────────────────────────┼────────────────────────────────────────────────────────────────────────┤
  │ Data            │ Polyglot persistence      │ PostgreSQL (relational), Neo4j (graph), Redis (cache), Elasticsearch   │
  │ Architecture    │                           │ (search), S3 (objects)                                                 │
  ├─────────────────┼───────────────────────────┼────────────────────────────────────────────────────────────────────────┤
  │ LLM Integration │ Multi-provider parallel   │ OpenAI, Gemini, Claude, Perplexity - captures variance across models   │
  │                 │ queries                   │                                                                        │
  ├─────────────────┼───────────────────────────┼────────────────────────────────────────────────────────────────────────┤
  │ Backend         │ Python/FastAPI + Celery   │ Async-first with background job processing                             │
  │ Framework       │                           │                                                                        │
  ├─────────────────┼───────────────────────────┼────────────────────────────────────────────────────────────────────────┤
  │ Orchestration   │ Kubernetes on EKS         │ Horizontal scaling with HPA based on CPU/queue depth                   │
  ├─────────────────┼───────────────────────────┼────────────────────────────────────────────────────────────────────────┤
  │ Graph Database  │ Neo4j for belief mapping  │ Models brand co-mentions, ICP-concern-intent-brand paths               │
  └─────────────────┴───────────────────────────┴────────────────────────────────────────────────────────────────────────┘
  ---
  Core Data Models

  Brand State Classification:
  LLMBrandState: ignored | mentioned | trusted | recommended | compared
  BeliefType: truth | superiority | outcome | transaction | identity | social_proof

  Prompt Classification:
  UserIntent {
    intent_type: informational | evaluation | decision
    funnel_stage: awareness | consideration | purchase
    buying_signal: 0.0-1.0
    trust_need: 0.0-1.0
  }

  Key Tables: websites, icps (5 per site), conversation_sequences (50 per site), prompt_classifications, llm_responses,   
  llm_brand_states, llm_answer_belief_maps, share_of_voice, substitution_patterns

  ---
  API Surface

  - Auth: JWT with refresh tokens
  - Websites: CRUD + scrape triggers (hard scrape limited to 1/week)
  - ICPs: 5 auto-generated profiles per website
  - Simulations: Trigger multi-LLM queries, filter by ICP/intent
  - Brand Analysis: Presence breakdown, belief distribution, by-provider metrics
  - Share of Voice: Visibility/trust scores, competitive comparison, trends
  - Knowledge Graph: Belief maps, co-mention networks, ICP journey paths

  ---
  Deployment Requirements
  ┌────────────────┬────────────────────────────────────────────────────────────────────────────────────────────┐
  │   Component    │                                       Specification                                        │
  ├────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Compute        │ EKS cluster: API (3 pods), Scraper (5), Simulator (10), Celery workers (10-50 auto-scaled) │        
  ├────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Database       │ RDS PostgreSQL db.r6g.xlarge Multi-AZ                                                      │
  ├────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Cache          │ ElastiCache Redis 3-node cluster                                                           │
  ├────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Search         │ OpenSearch 3-node cluster                                                                  │
  ├────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Graph          │ Neo4j Aura Professional (managed)                                                          │
  ├────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Storage        │ S3 with cross-region replication                                                           │
  ├────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Estimated Cost │ $5,100-13,100/month (LLM API costs variable)                                               │
  └────────────────┴────────────────────────────────────────────────────────────────────────────────────────────┘
  DR: RTO 4 hours, RPO 5 minutes (PostgreSQL), Multi-AZ failover

  ---
  Critical Constraints

  1. Hard scrape limit: 1 per week per website (enforced via Redis TTL)
  2. Rate limits: Auth 10/min, reads 100/min, writes 30/min, simulations 5/hour
  3. One dominant state per brand per answer - no multi-classification
  4. 25 core conversations constant after initial generation (5 per ICP)