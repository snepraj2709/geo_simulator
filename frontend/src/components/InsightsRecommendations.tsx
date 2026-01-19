import { TrendingUp, AlertTriangle, CheckCircle, Lightbulb, Target } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';

export function InsightsRecommendations() {
  return (
    <div className="min-h-screen px-4 py-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl text-white mb-2">Insights & Recommendations</h1>
          <p className="text-gray-400">Actionable recommendations to improve your GEO performance</p>
        </div>

        {/* Filter Tabs */}
        <Tabs defaultValue="all" className="space-y-6">
          <TabsList className="bg-white/5 border border-white/10">
            <TabsTrigger value="all">All Insights</TabsTrigger>
            <TabsTrigger value="persona">By Persona</TabsTrigger>
            <TabsTrigger value="prompt">By Prompt</TabsTrigger>
            <TabsTrigger value="model">By Model</TabsTrigger>
          </TabsList>

          {/* All Insights */}
          <TabsContent value="all" className="space-y-6">
            {/* Priority Recommendations */}
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl text-white">High Priority Actions</h2>
                <span className="px-3 py-1 rounded-full bg-red-500/20 text-red-400 text-sm">
                  3 critical
                </span>
              </div>

              <div className="space-y-3">
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 space-y-3">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <h3 className="text-white mb-1">Zero Brand Mentions in Perplexity</h3>
                      <p className="text-sm text-gray-400 mb-3">
                        Your brand is not being cited in any Perplexity responses across 40 prompts
                      </p>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>Impact: High</span>
                        <span>•</span>
                        <span>Effort: Medium</span>
                      </div>
                    </div>
                  </div>
                  <div className="pl-8 pt-3 border-t border-red-500/20 space-y-2">
                    <p className="text-sm text-gray-300">Recommended Actions:</p>
                    <ul className="text-sm text-gray-400 space-y-1">
                      <li>• Create authoritative comparison content</li>
                      <li>• Build backlinks from industry publications</li>
                      <li>• Publish research and data-driven reports</li>
                    </ul>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20 space-y-3">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <h3 className="text-white mb-1">Low Trust Signals for VP Personas</h3>
                      <p className="text-sm text-gray-400 mb-3">
                        Executive-level personas receive 40% fewer recommendations than manager personas
                      </p>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>Impact: High</span>
                        <span>•</span>
                        <span>Effort: High</span>
                      </div>
                    </div>
                  </div>
                  <div className="pl-8 pt-3 border-t border-yellow-500/20 space-y-2">
                    <p className="text-sm text-gray-300">Recommended Actions:</p>
                    <ul className="text-sm text-gray-400 space-y-1">
                      <li>• Add executive-focused case studies</li>
                      <li>• Create ROI calculators and business impact content</li>
                      <li>• Publish thought leadership from your C-suite</li>
                    </ul>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20 space-y-3">
                  <div className="flex items-start gap-3">
                    <TrendingUp className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <h3 className="text-white mb-1">Competitor D Outranks You by 12%</h3>
                      <p className="text-sm text-gray-400 mb-3">
                        Competitor D is recommended 3x more often in decision-stage prompts
                      </p>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>Impact: Medium</span>
                        <span>•</span>
                        <span>Effort: Medium</span>
                      </div>
                    </div>
                  </div>
                  <div className="pl-8 pt-3 border-t border-yellow-500/20 space-y-2">
                    <p className="text-sm text-gray-300">Recommended Actions:</p>
                    <ul className="text-sm text-gray-400 space-y-1">
                      <li>• Analyze their content strategy and differentiation</li>
                      <li>• Create head-to-head comparison content</li>
                      <li>• Highlight unique features and use cases</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Wins */}
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl text-white">Quick Wins</h2>
                <span className="px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-sm">
                  Low effort, high impact
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  {
                    title: 'Add FAQ schema markup',
                    description: 'Improves Claude response quality by 23%',
                    icon: CheckCircle,
                  },
                  {
                    title: 'Create "Best for" sections',
                    description: 'Increases recommendations in comparison prompts',
                    icon: Target,
                  },
                  {
                    title: 'Update meta descriptions',
                    description: 'Better snippet extraction across all models',
                    icon: Lightbulb,
                  },
                  {
                    title: 'Add pricing transparency',
                    description: 'Mentioned 2x more in bottom-funnel queries',
                    icon: TrendingUp,
                  },
                ].map((item, index) => {
                  const Icon = item.icon;
                  return (
                    <div
                      key={index}
                      className="p-4 rounded-xl bg-green-500/10 border border-green-500/20 flex items-start gap-3"
                    >
                      <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center flex-shrink-0">
                        <Icon className="w-5 h-5 text-green-400" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-white mb-1">{item.title}</h3>
                        <p className="text-sm text-gray-400">{item.description}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Content Gaps */}
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-4">
              <h2 className="text-xl text-white">Content Gaps Identified</h2>
              <div className="space-y-3">
                {[
                  {
                    gap: 'Integration guides',
                    frequency: '18 prompts',
                    competitors: 'HubSpot, Marketo',
                  },
                  {
                    gap: 'ROI case studies',
                    frequency: '14 prompts',
                    competitors: 'Salesforce, Adobe',
                  },
                  {
                    gap: 'Implementation timelines',
                    frequency: '12 prompts',
                    competitors: 'HubSpot, ActiveCampaign',
                  },
                ].map((item, index) => (
                  <div
                    key={index}
                    className="p-4 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between"
                  >
                    <div className="flex-1">
                      <h3 className="text-white mb-1">{item.gap}</h3>
                      <p className="text-sm text-gray-400">
                        Missing in {item.frequency} • Competitors: {item.competitors}
                      </p>
                    </div>
                    <button className="px-4 py-2 rounded-lg bg-violet-500/20 hover:bg-violet-500/30 border border-violet-500/30 text-violet-400 text-sm transition-colors">
                      Create Content
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>

          {/* By Persona */}
          <TabsContent value="persona" className="space-y-6">
            {[
              {
                name: 'Sarah Chen - VP of Marketing',
                avatar: 'https://images.unsplash.com/photo-1758518727888-ffa196002e59?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=200',
                score: 75,
                insights: [
                  'Needs more executive-level ROI content',
                  'Looking for strategic alignment resources',
                  'Wants vendor comparison data',
                ],
              },
              {
                name: 'Marcus Rodriguez - SEO Manager',
                avatar: 'https://images.unsplash.com/photo-1581065178047-8ee15951ede6?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=200',
                score: 82,
                insights: [
                  'Performing well on technical content',
                  'Wants more integration documentation',
                  'Interested in API capabilities',
                ],
              },
            ].map((persona, index) => (
              <div
                key={index}
                className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-4"
              >
                <div className="flex items-center gap-4">
                  <img
                    src={persona.avatar}
                    alt={persona.name}
                    className="w-16 h-16 rounded-full object-cover ring-2 ring-violet-500/20"
                  />
                  <div className="flex-1">
                    <h3 className="text-white mb-1">{persona.name}</h3>
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-gray-400">GEO Score:</span>
                      <span className="text-lg text-white tabular-nums">{persona.score}</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="text-sm text-gray-300">Key Insights:</h4>
                  <ul className="space-y-2">
                    {persona.insights.map((insight, idx) => (
                      <li
                        key={idx}
                        className="flex items-start gap-2 text-sm text-gray-400"
                      >
                        <Lightbulb className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
                        {insight}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </TabsContent>

          {/* By Prompt */}
          <TabsContent value="prompt" className="space-y-4">
            {[
              {
                prompt: 'Best marketing automation platforms for B2B SaaS',
                status: 'good',
                mentions: 3,
                models: ['GPT-4', 'Claude', 'Gemini'],
              },
              {
                prompt: 'How to improve pipeline quality and conversion rates',
                status: 'poor',
                mentions: 0,
                models: [],
              },
              {
                prompt: 'Marketing attribution modeling best practices',
                status: 'medium',
                mentions: 1,
                models: ['Claude'],
              },
            ].map((item, index) => (
              <div
                key={index}
                className="p-4 rounded-xl bg-white/5 border border-white/10 flex items-start justify-between gap-4"
              >
                <div className="flex-1">
                  <p className="text-white mb-2">{item.prompt}</p>
                  <div className="flex items-center gap-3 text-sm">
                    <span className="text-gray-400">
                      {item.mentions} mention{item.mentions !== 1 ? 's' : ''}
                    </span>
                    {item.models.length > 0 && (
                      <>
                        <span className="text-gray-600">•</span>
                        <span className="text-gray-400">{item.models.join(', ')}</span>
                      </>
                    )}
                  </div>
                </div>
                <div
                  className={`px-3 py-1 rounded-full text-xs ${
                    item.status === 'good'
                      ? 'bg-green-500/20 text-green-400'
                      : item.status === 'medium'
                      ? 'bg-yellow-500/20 text-yellow-400'
                      : 'bg-red-500/20 text-red-400'
                  }`}
                >
                  {item.status === 'good' && 'Performing well'}
                  {item.status === 'medium' && 'Needs work'}
                  {item.status === 'poor' && 'Not visible'}
                </div>
              </div>
            ))}
          </TabsContent>

          {/* By Model */}
          <TabsContent value="model" className="space-y-6">
            {[
              {
                name: 'GPT-4',
                score: 82,
                color: 'green',
                strengths: ['Feature comparisons', 'Use case matching'],
                weaknesses: ['Pricing transparency'],
              },
              {
                name: 'Claude 3',
                score: 78,
                color: 'green',
                strengths: ['Technical documentation', 'Integration guides'],
                weaknesses: ['Executive content'],
              },
              {
                name: 'Perplexity',
                score: 45,
                color: 'red',
                strengths: [],
                weaknesses: ['Brand visibility', 'Citation frequency', 'Authority signals'],
              },
            ].map((model, index) => (
              <div
                key={index}
                className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-4"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-xl text-white">{model.name}</h3>
                  <div className="text-right">
                    <div className="text-sm text-gray-400">Score</div>
                    <div className={`text-2xl tabular-nums ${
                      model.color === 'green' ? 'text-green-400' :
                      model.color === 'yellow' ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>
                      {model.score}
                    </div>
                  </div>
                </div>

                {model.strengths.length > 0 && (
                  <div>
                    <h4 className="text-sm text-green-400 mb-2">Strengths:</h4>
                    <ul className="space-y-1">
                      {model.strengths.map((strength, idx) => (
                        <li key={idx} className="flex items-center gap-2 text-sm text-gray-400">
                          <CheckCircle className="w-4 h-4 text-green-400" />
                          {strength}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {model.weaknesses.length > 0 && (
                  <div>
                    <h4 className="text-sm text-red-400 mb-2">Weaknesses:</h4>
                    <ul className="space-y-1">
                      {model.weaknesses.map((weakness, idx) => (
                        <li key={idx} className="flex items-center gap-2 text-sm text-gray-400">
                          <AlertTriangle className="w-4 h-4 text-red-400" />
                          {weakness}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
