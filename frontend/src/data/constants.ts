import { ICP, IntentData, Step } from "@/types";
import { AlertCircle, BarChart, Brain, Cpu, Eye, FileCheck, FileText, Filter, Globe, MessageCircle, MessageSquare, Network, Tags, Target, TrendingUp, Users } from "lucide-react";

export const defaultIcps: ICP[] = [
  {
    id: "icp_001",
    website_id: "site_123",
    name: "Sarah Chen",
    title: "VP of Marketing",
    description:
      "Senior marketing executive at a mid-market B2B SaaS company focused on pipeline growth and brand authority in AI-driven discovery channels.",
    sequence_number: 1,
    avatar:
      "https://images.unsplash.com/photo-1758518727888-ffa196002e59?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
    prompts: [
      { id: "p_001", text: "How do AI tools recommend B2B SaaS platforms for demand generation?" },
      { id: "p_002", text: "Which SaaS brands are trusted by AI for enterprise marketing teams?" },
      { id: "p_003", text: "What signals make a brand appear credible to large language models?" }
    ],
    demographics: {
      age_range: "35-45",
      gender: "Female",
      location: "North America",
      income_level: "$180k–$250k",
      education: "MBA"
    },
    professional_profile: {
      job_titles: ["VP of Marketing", "Head of Growth"],
      company_size: "200–500",
      industry: "B2B SaaS",
      seniority: "Executive"
    },
    pain_points: [
      "Unclear brand visibility in AI-generated answers",
      "Difficulty measuring trust and influence beyond search rankings"
    ],
    goals: [
      "Increase AI-driven brand recommendations",
      "Strengthen category leadership perception"
    ],
    motivations: {
      primary: "Pipeline growth",
      secondary: "Executive credibility"
    },
    objections: [
      "Skeptical of black-box AI tools",
      "Needs defensible metrics"
    ],
    decision_factors: [
      "Strategic insight",
      "Accuracy of competitive analysis",
      "Executive-ready reporting"
    ],
    information_sources: [
      "Industry reports",
      "Peer networks",
      "Analyst blogs"
    ],
    buying_journey_stage: "consideration",
    is_active: true,
    conversation_count: 10,
    created_at: "2026-01-01T10:00:00Z",
    updated_at: "2026-01-01T10:00:00Z"
  },
  {
    id: "icp_002",
    website_id: "site_123",
    name: "Marcus Rodriguez",
    title: "SEO Manager",
    description:
      "Enterprise SEO Manager responsible for organic visibility, technical SEO, and adapting strategy to AI-driven search behavior.",
    sequence_number: 2,
    avatar:
      "https://images.unsplash.com/photo-1581065178047-8ee15951ede6?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
    prompts: [
      { id: "p_004", text: "How do large language models choose which brands to mention first?" },
      { id: "p_005", text: "What content signals influence AI recommendations for software tools?" },
      { id: "p_006", text: "How can SEO teams optimize for AI-generated answers?" }
    ],
    demographics: {
      age_range: "30-40",
      location: "United States",
      education: "Bachelor’s in Computer Science"
    },
    professional_profile: {
      job_titles: ["SEO Manager", "Technical SEO Lead"],
      company_size: "500–2000",
      industry: "Technology",
      seniority: "Manager"
    },
    pain_points: [
      "Loss of traffic visibility due to AI answers",
      "No tooling to measure AI citation share"
    ],
    goals: [
      "Understand AI brand mention mechanics",
      "Protect and grow organic influence"
    ],
    motivations: {
      primary: "Search visibility",
      secondary: "Technical mastery"
    },
    objections: [
      "Prefers transparent methodologies",
      "Avoids vanity metrics"
    ],
    decision_factors: [
      "Granular data access",
      "Prompt-level analysis",
      "Repeatable simulations"
    ],
    information_sources: [
      "SEO communities",
      "Technical blogs",
      "Search engine documentation"
    ],
    buying_journey_stage: "evaluation",
    is_active: true,
    conversation_count: 15,
    created_at: "2026-01-01T10:05:00Z",
    updated_at: "2026-01-01T10:05:00Z"
  },
  {
    id: "icp_003",
    website_id: "site_123",
    name: "Emily Watson",
    title:"Content Marketing Director",
    description:
      "Content marketing leader balancing thought leadership with performance-driven content in an AI-influenced discovery ecosystem.",
    sequence_number: 3,
    avatar:
      "https://images.unsplash.com/photo-1758525589763-b9ad2a75bfe8?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
    prompts: [
      { id: "p_007", text: "What content formats do AI models trust the most?" },
      { id: "p_008", text: "How does AI evaluate thought leadership content?" }
    ],
    demographics: {
      age_range: "32-42",
      location: "Europe",
      education: "Master’s in Marketing"
    },
    professional_profile: {
      job_titles: ["Content Marketing Director"],
      company_size: "50–200",
      industry: "SaaS",
      seniority: "Director"
    },
    pain_points: [
      "Unclear ROI of thought leadership",
      "Content not reflected in AI responses"
    ],
    goals: [
      "Increase perceived authority in AI answers",
      "Align content with AI trust signals"
    ],
    motivations: {
      primary: "Authority building",
      secondary: "Content ROI"
    },
    buying_journey_stage: "awareness",
    is_active: true,
    conversation_count: 8,
    created_at: "2026-01-01T10:10:00Z",
    updated_at: "2026-01-01T10:10:00Z"
  },
  {
    id: "icp_004",
    website_id: "site_123",
    name: "David Park",
    title:"Growth Marketing Lead",
    description:
      "Growth marketing lead at a competitive SaaS company, responsible for scaling acquisition channels and improving conversion efficiency in AI-influenced buyer journeys.",
    sequence_number: 4,
    avatar:
      "https://images.unsplash.com/photo-1752859951149-7d3fc700a7ec?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080",
    prompts: [
      { id: "p_009", text: "Which growth tools do AI models recommend for scaling SaaS acquisition?" },
      { id: "p_010", text: "How does AI compare growth platforms for conversion optimization?" },
      { id: "p_011", text: "What signals make a growth tool appear high-ROI in AI answers?" }
    ],
    demographics: {
      age_range: "33-43",
      location: "Asia-Pacific",
      income_level: "$140k–$200k",
      education: "MBA"
    },
    professional_profile: {
      job_titles: ["Growth Marketing Lead", "Head of Growth"],
      company_size: "100–500",
      industry: "SaaS",
      seniority: "Senior Manager"
    },
    pain_points: [
      "Unclear AI-driven attribution on acquisition decisions",
      "Difficulty proving ROI of growth experiments"
    ],
    goals: [
      "Increase AI-sourced demand quality",
      "Position the brand as a high-ROI growth solution"
    ],
    motivations: {
      primary: "Revenue growth",
      secondary: "Operational leverage"
    },
    objections: [
      "Avoids tools without measurable lift",
      "Skeptical of purely qualitative insights"
    ],
    decision_factors: [
      "ROI clarity",
      "Speed of experimentation",
      "Cross-channel visibility"
    ],
    information_sources: [
      "Growth communities",
      "Founder networks",
      "Case studies"
    ],
    buying_journey_stage: "decision",
    is_active: true,
    conversation_count: 12,
    created_at: "2026-01-01T10:15:00Z",
    updated_at: "2026-01-01T10:15:00Z"
  }
];

export const intentData: IntentData[] = [
    {
      category: 'High Intent',
      count: 18,
      percentage: 45,
      color: 'from-green-500 to-emerald-500',
      icon: Target,
    },
    {
      category: 'Medium Intent',
      count: 14,
      percentage: 35,
      color: 'from-blue-500 to-cyan-500',
      icon: TrendingUp,
    },
    {
      category: 'Low Intent',
      count: 6,
      percentage: 15,
      color: 'from-yellow-500 to-orange-500',
      icon: AlertCircle,
    },
    {
      category: 'Research',
      count: 2,
      percentage: 5,
      color: 'from-purple-500 to-pink-500',
      icon: Users,
    },
];

export interface Message {
  id: string;
  model: 'gpt' | 'gemini' | 'claude' | 'perplexity';
  prompt: string;
  response: string;
  status: 'queued' | 'processing' | 'complete';
}

export const modelConfig = {
  gpt: {
    name: 'GPT-4',
    color: 'from-green-500 to-emerald-500',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/20',
    textColor: 'text-green-400',
  },
  gemini: {
    name: 'Gemini Pro',
    color: 'from-blue-500 to-cyan-500',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/20',
    textColor: 'text-blue-400',
  },
  claude: {
    name: 'Claude 3',
    color: 'from-purple-500 to-pink-500',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/20',
    textColor: 'text-purple-400',
  },
  perplexity: {
    name: 'Perplexity',
    color: 'from-orange-500 to-amber-500',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/20',
    textColor: 'text-orange-400',
  },
};

export const geoScore = 78;
  
export const brandStates = [
  { state: 'Recommended', count: 12, percentage: 30, color: '#10b981', trend: 'up' },
  { state: 'Compared', count: 8, percentage: 20, color: '#3b82f6', trend: 'up' },
  { state: 'Mentioned', count: 14, percentage: 35, color: '#8b5cf6', trend: 'neutral' },
  { state: 'Trusted', count: 4, percentage: 10, color: '#06b6d4', trend: 'up' },
  { state: 'Ignored', count: 2, percentage: 5, color: '#ef4444', trend: 'down' },
];

export const competitorData = [
  { name: 'Your Brand', score: 78, color: '#8b5cf6' },
  { name: 'Competitor A', score: 65, color: '#64748b' },
  { name: 'Competitor B', score: 72, color: '#64748b' },
  { name: 'Competitor C', score: 58, color: '#64748b' },
  { name: 'Competitor D', score: 81, color: '#ef4444' },
];

export const radarData = [
  { attribute: 'Visibility', yourBrand: 82, industry: 65 },
  { attribute: 'Authority', yourBrand: 75, industry: 70 },
  { attribute: 'Trust', yourBrand: 78, industry: 68 },
  { attribute: 'Relevance', yourBrand: 85, industry: 72 },
  { attribute: 'Sentiment', yourBrand: 70, industry: 65 },
];

export const modelPerformance = [
  { model: 'GPT-4', mentions: 18, recommendations: 8, ignored: 0 },
  { model: 'Gemini', mentions: 15, recommendations: 6, ignored: 1 },
  { model: 'Claude', mentions: 16, recommendations: 7, ignored: 1 },
  { model: 'Perplexity', mentions: 12, recommendations: 5, ignored: 2 },
];

export const steps:Step[] = [
  {
    id: 1,
    name: "Initializing crawl",
    description:
      "Validating domain, resolving redirects, checking robots.txt, sitemap discovery, and establishing crawl boundaries.",
    icon: Globe,
  },
  {
    id: 2,
    name: "Crawling website structure",
    description:
      "Recursively crawling internal links, rendering JavaScript pages, and mapping site architecture while respecting rate limits.",
    icon: Globe,
  },
  {
    id: 3,
    name: "Extracting raw content",
    description:
      "Extracting visible text, metadata, headings, schema markup, navigation labels, and content hierarchy from each page.",
    icon: FileText,
  },
  {
    id: 4,
    name: "Cleaning & normalizing content",
    description:
      "Removing boilerplate, deduplicating text, resolving encoding issues, and standardizing content for semantic analysis.",
    icon: FileText,
  },
  {
    id: 5,
    name: "Identifying key entities",
    description:
      "Detecting brands, products, competitors, features, technologies, and people mentioned across the site.",
    icon: Tags,
  },
  {
    id: 6,
    name: "Mapping topics & themes",
    description:
      "Clustering content into high-level topics, subtopics, and problem domains relevant to buyer intent.",
    icon: Tags,
  },
  {
    id: 7,
    name: "Inferring brand positioning",
    description:
      "Analyzing language signals to infer authority, differentiation, outcomes, and trust positioning.",
    icon: Target,
  },
  {
    id: 8,
    name: "Generating Ideal Customer Profiles",
    description:
      "Synthesizing ICPs based on content focus, use cases, pain points, and implied buyer roles.",
    icon: Users,
  },
  {
    id: 9,
    name: "Simulating user prompts",
    description:
      "Generating realistic user questions for each ICP across awareness, evaluation, and decision stages.",
    icon: MessageSquare,
  },
  {
    id: 10,
    name: "Classifying intent signals",
    description:
      "Assigning intent type, funnel stage, trust need, and buying signal strength to each prompt.",
    icon: Filter,
  },
  {
    id: 11,
    name: "Running LLM simulations",
    description:
      "Sequentially sending prompts to GPT, Gemini, Claude, and Perplexity to observe brand treatment.",
    icon: Cpu,
  },
  {
    id: 12,
    name: "Capturing LLM responses",
    description:
      "Collecting responses, ranking mentions, identifying framing, and normalizing outputs across models.",
    icon: MessageCircle,
  },
  {
    id: 13,
    name: "Detecting brand presence states",
    description:
      "Classifying whether the brand is ignored, mentioned, trusted, recommended, or compared.",
    icon: Eye,
  },
  {
    id: 14,
    name: "Building knowledge graph",
    description:
      "Linking ICPs, intents, entities, beliefs, and brands into a structured knowledge graph.",
    icon: Network,
  },
  {
    id: 15,
    name: "Analyzing belief formation",
    description:
      "Identifying whether AI responses install trust, superiority, outcome, transactional, or social-proof beliefs.",
    icon: Brain,
  },
  {
    id: 16,
    name: "Computing GEO metrics",
    description:
      "Calculating GEO score, share-of-voice, competitive substitution, and trust-weighted visibility.",
    icon: BarChart,
  },
  {
    id: 17,
    name: "Preparing executive report",
    description:
      "Generating an executive-ready report summarizing AI visibility, risks, and growth opportunities.",
    icon: FileCheck,
  },
];
