// Pipeline stage enumeration matching ARCHITECTURE.md
export enum PipelineStage {
  WEBSITE_SCRAPING = 'website_scraping',
  ICP_GENERATION = 'icp_generation',
  CONVERSATION_CREATION = 'conversation_creation',
  PROMPT_CLASSIFICATION = 'prompt_classification',
  LLM_SIMULATION = 'llm_simulation',
  BRAND_DETECTION = 'brand_detection',
  KNOWLEDGE_GRAPH_BUILDING = 'knowledge_graph_building',
  COMPETITIVE_ANALYSIS = 'competitive_analysis',
}

// Status for each stage
export type StageStatus = 'pending' | 'in-progress' | 'completed' | 'error';

// Individual stage data
export interface PipelineStageData {
  stage: PipelineStage;
  status: StageStatus;
  progress: number; // 0-100
  currentAction?: string;
  estimatedTimeRemaining?: number; // seconds
  startedAt?: string;
  completedAt?: string;
  error?: string;
  metadata?: Record<string, any>; // e.g., { pagesScraped: 3, totalPages: 5 }
}

// Overall pipeline state
export interface PipelineState {
  id: string;
  websiteId: string;
  overallProgress: number; // 0-100
  stages: PipelineStageData[];
  startedAt: string;
  estimatedCompletion?: string;
}

// WebSocket message types
export interface PipelineUpdateMessage {
  type: 'pipeline_update';
  data: PipelineState;
}

export interface PipelineErrorMessage {
  type: 'pipeline_error';
  pipelineId: string;
  error: string;
}

export type PipelineMessage = PipelineUpdateMessage | PipelineErrorMessage;

// Stage display metadata
export interface StageMetadata {
  name: string;
  description: string;
  icon: string; // Icon identifier
}

export const STAGE_METADATA: Record<PipelineStage, StageMetadata> = {
  [PipelineStage.WEBSITE_SCRAPING]: {
    name: 'Website Scraping',
    description: 'Crawling and extracting website content',
    icon: 'globe',
  },
  [PipelineStage.ICP_GENERATION]: {
    name: 'ICP Generation',
    description: 'Creating Ideal Customer Profiles',
    icon: 'users',
  },
  [PipelineStage.CONVERSATION_CREATION]: {
    name: 'Conversation Creation',
    description: 'Generating realistic conversation flows',
    icon: 'message-circle',
  },
  [PipelineStage.PROMPT_CLASSIFICATION]: {
    name: 'Prompt Classification',
    description: 'Categorizing prompts by intent and funnel stage',
    icon: 'tag',
  },
  [PipelineStage.LLM_SIMULATION]: {
    name: 'LLM Simulation',
    description: 'Querying multiple LLM providers',
    icon: 'cpu',
  },
  [PipelineStage.BRAND_DETECTION]: {
    name: 'Brand Detection',
    description: 'Analyzing brand presence in responses',
    icon: 'search',
  },
  [PipelineStage.KNOWLEDGE_GRAPH_BUILDING]: {
    name: 'Knowledge Graph Building',
    description: 'Building Neo4j knowledge graph',
    icon: 'network',
  },
  [PipelineStage.COMPETITIVE_ANALYSIS]: {
    name: 'Competitive Analysis',
    description: 'Mapping competitive substitution patterns',
    icon: 'bar-chart',
  },
};
