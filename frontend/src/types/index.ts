// ============================================================================
// Core Entities
// ============================================================================

export interface User {
  id: string;
  organization_id: string;
  email: string;
  name: string;
  role: 'admin' | 'member' | 'viewer';
  is_active: boolean;
  last_login_at?: string;
  created_at: string;
  updated_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan_type: 'free' | 'pro' | 'enterprise';
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Authentication
// ============================================================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
  organization_name: string;
}

export interface AuthResponse {
  user: User;
  token: string;
  refresh_token: string;
  expires_in?: number;
}

// ============================================================================
// Websites & Scraping
// ============================================================================
export interface Step {
  id: number;
  name: string;
  description: string;
  icon: React.ElementType;
}

export interface Website {
  id: string;
  organization_id: string;
  domain: string;
  url: string;
  name: string;
  description?: string;
  status: 'pending' | 'scraping' | 'completed' | 'failed';
  last_scraped_at?: string;
  last_hard_scrape_at?: string;
  scrape_depth: number;
  created_at: string;
  updated_at: string;
  stats?: {
    pages_scraped: number;
    icps_generated: number;
    conversations_generated: number;
    simulations_run: number;
  };
  analysis?: WebsiteAnalysis;
}

export interface WebsiteAnalysis {
  industry?: string;
  business_model?: 'b2b' | 'b2c' | 'b2b2c' | 'marketplace';
  primary_offerings?: Array<{ name: string; type: 'product' | 'service' }>;
  value_propositions?: string[];
  target_markets?: string[];
  competitors_mentioned?: string[];
}

export interface ScrapingStats {
  pagesScraped: number;
  entitiesExtracted: number;
  topicsMapped: number;
}

export interface ScrapedPage {
  id: string;
  website_id: string;
  url: string;
  title?: string;
  meta_description?: string;
  content_text?: string;
  word_count?: number;
  page_type?: 'homepage' | 'product' | 'service' | 'blog' | 'about' | 'contact';
  http_status?: number;
  scraped_at: string;
}

export interface ScrapeRequest {
  type: 'incremental' | 'hard';
}

export interface ScrapeJob {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  type: 'incremental' | 'hard';
  estimated_pages?: number;
}

// ============================================================================
// Ideal Customer Profiles (ICPs)
// ============================================================================

export type SimulationStep = 
  | 'landing' 
  | 'scraping' 
  | 'icp-generation' 
  | 'prompt-generation' 
  | 'llm-simulation' 
  | 'intent-analysis' 
  | 'report';


export interface ICP {
  id: string;
  website_id: string;
  name: string;
  title: string;
  description?: string;
  sequence_number: number;
  avatar: string;
  prompts: Array<{
    id: string;
    text: string;
  }>;
  demographics: {
    age_range?: string;
    gender?: string;
    location?: string;
    income_level?: string;
    education?: string;
  };
  professional_profile: {
    job_titles?: string[];
    company_size?: string;
    industry?: string;
    seniority?: string;
  };
  pain_points: string[];
  goals: string[];
  motivations?: {
    primary?: string;
    secondary?: string;
  };
  objections?: string[];
  decision_factors?: string[];
  information_sources?: string[];
  buying_journey_stage?: string;
  is_active: boolean;
  conversation_count?: number;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Conversations & Prompts
// ============================================================================

export interface ConversationSequence {
  id: string;
  website_id: string;
  icp_id: string;
  icp_name?: string;
  topic: string;
  context?: string;
  expected_outcome?: string;
  is_core_conversation: boolean;
  sequence_number: number;
  prompt_count?: number;
  prompts?: Prompt[];
  created_at: string;
}

export interface Prompt {
  id: string;
  conversation_id: string;
  prompt_text: string;
  prompt_type: 'primary' | 'follow_up' | 'clarification';
  sequence_order: number;
  classification?: PromptClassification;
  created_at: string;
}


export interface IntentData {
  category: string;
  count: number;
  percentage: number;
  color: string;
  icon: React.ElementType;
}

export interface PromptClassification {
  id: string;
  prompt_id: string;
  intent_type: 'informational' | 'evaluation' | 'decision';
  funnel_stage: 'awareness' | 'consideration' | 'purchase';
  buying_signal: number; // 0.0 - 1.0
  trust_need: number; // 0.0 - 1.0
  query_intent?: 'Commercial' | 'Informational' | 'Navigational' | 'Transactional';
  confidence_score?: number;
  classified_at: string;
  classifier_version?: string;
}

// ============================================================================
// Simulations
// ============================================================================

export interface SimulationRun {
  id: string;
  website_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  total_prompts: number;
  completed_prompts: number;
  llm_providers?: string[];
  started_at?: string;
  completed_at?: string;
  created_at: string;
  summary?: SimulationSummary;
}

export interface SimulationSummary {
  brands_discovered: number;
  your_brand_mentions: number;
  your_brand_recommendations: number;
  top_competitors: Array<{ name: string; mentions: number }>;
}

export interface CreateSimulationRequest {
  llm_providers: string[];
  prompt_filter?: {
    icp_ids?: string[];
    intent_types?: string[];
    core_only?: boolean;
  };
}

export interface LLMResponse {
  id: string;
  simulation_run_id: string;
  prompt_id: string;
  prompt_text?: string;
  llm_provider: 'openai' | 'google' | 'anthropic' | 'perplexity';
  llm_model: string;
  response_text: string;
  response_tokens?: number;
  latency_ms?: number;
  brands_mentioned?: BrandMention[];
  created_at: string;
}

export interface BrandMention {
  brand_id: string;
  brand_name: string;
  presence: 'ignored' | 'mentioned' | 'trusted' | 'recommended' | 'compared';
  position_rank?: number;
  belief_sold?: BeliefType;
}

export type BeliefType = 'truth' | 'superiority' | 'outcome' | 'transaction' | 'identity' | 'social_proof';

// ============================================================================
// Brand Analysis
// ============================================================================

export interface Brand {
  id: string;
  name: string;
  normalized_name: string;
  domain?: string;
  industry?: string;
  is_tracked: boolean;
  created_at: string;
  stats?: {
    total_mentions: number;
    recommendations: number;
    comparisons: number;
    avg_position: number;
  };
}

export interface BrandAnalysis {
  brand: Brand;
  presence_breakdown: {
    ignored: number;
    mentioned: number;
    trusted: number;
    recommended: number;
    compared: number;
  };
  by_llm_provider: {
    [provider: string]: {
      mentions: number;
      recommendations: number;
      avg_position: number;
    };
  };
  belief_distribution: {
    [belief: string]: number;
  };
  by_intent_type: {
    [intent: string]: {
      mentions: number;
      presence_rate: number;
    };
  };
  by_funnel_stage: {
    [stage: string]: {
      mentions: number;
      presence_rate: number;
    };
  };
}

export interface ShareOfVoice {
  website_id: string;
  brand_id: string;
  brand_name?: string;
  llm_provider: string;
  mention_count: number;
  recommendation_count: number;
  first_position_count: number;
  total_responses: number;
  visibility_score: number;
  trust_score: number;
  recommendation_rate: number;
  period_start: string;
  period_end: string;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}

// ============================================================================
// Query Parameters
// ============================================================================

export interface PaginationParams {
  page?: number;
  limit?: number;
}

export interface WebsiteListParams extends PaginationParams {
  status?: string;
}

export interface ScrapedPageParams extends PaginationParams {
  page_type?: string;
  search?: string;
}

export interface ConversationParams extends PaginationParams {
  icp_id?: string;
  is_core?: boolean;
}

export interface SimulationListParams extends PaginationParams {
  status?: string;
}

export interface SimulationResponseParams extends PaginationParams {
  llm_provider?: string;
  prompt_id?: string;
  brand_id?: string;
  presence?: string;
}

export interface BrandListParams extends PaginationParams {
  is_tracked?: boolean;
  min_mentions?: number;
  search?: string;
}

export interface ClassificationParams extends PaginationParams {
  intent_type?: string;
  funnel_stage?: string;
  min_buying_signal?: number;
  min_trust_need?: number;
}
