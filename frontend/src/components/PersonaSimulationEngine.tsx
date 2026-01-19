import { useState } from 'react';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Sparkles, TrendingUp, AlertTriangle, Users } from 'lucide-react';

export function PersonaSimulationEngine() {
  const [selectedModel, setSelectedModel] = useState('chatgpt');
  const [selectedPersona, setSelectedPersona] = useState('sarah-chen');
  const [prompt, setPrompt] = useState('');
  const [hasResponse, setHasResponse] = useState(false);

  const handleRunSimulation = () => {
    setHasResponse(true);
  };

  const mockResponse = `Based on current market analysis, if you're looking for marketing automation platforms for B2B SaaS, here are some top contenders:

**HubSpot** is a comprehensive solution with robust CRM integration, ideal for companies looking for an all-in-one platform. Their enterprise tier offers advanced features.

**Marketo** (Adobe) provides sophisticated campaign management and is particularly strong in enterprise environments with complex workflows.

**Pardot** (Salesforce) seamlessly integrates with Salesforce CRM and is excellent for B2B organizations already in the Salesforce ecosystem.

**ActiveCampaign** offers a good balance of features and affordability, suitable for mid-market companies.

Each platform has its strengths depending on your specific needs, team size, and existing tech stack.`;

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl text-white mb-2">Persona Simulation Engine</h1>
          <p className="text-gray-400">Test how AI models respond to different personas and prompts</p>
        </div>

        {/* Split View */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Panel - Simulation */}
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-6">
              <h2 className="text-xl text-white">Simulation Controls</h2>

              {/* LLM Model Selector */}
              <div className="space-y-2">
                <Label className="text-gray-300">LLM Model</Label>
                <Select value={selectedModel} onValueChange={setSelectedModel}>
                  <SelectTrigger className="bg-white/5 border-white/10 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="chatgpt">ChatGPT</SelectItem>
                    <SelectItem value="perplexity">Perplexity</SelectItem>
                    <SelectItem value="claude">Claude</SelectItem>
                    <SelectItem value="gemini">Gemini</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Persona Selector */}
              <div className="space-y-2">
                <Label className="text-gray-300">Persona</Label>
                <Select value={selectedPersona} onValueChange={setSelectedPersona}>
                  <SelectTrigger className="bg-white/5 border-white/10 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sarah-chen">Sarah Chen - VP of Marketing</SelectItem>
                    <SelectItem value="marcus-rodriguez">Marcus Rodriguez - SEO Manager</SelectItem>
                    <SelectItem value="emily-watson">Emily Watson - Content Marketing Director</SelectItem>
                    <SelectItem value="david-park">David Park - Growth Marketing Lead</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Prompt Input */}
              <div className="space-y-2">
                <Label className="text-gray-300">Prompt</Label>
                <Textarea
                  placeholder="Enter a custom prompt or select from existing..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="min-h-32 bg-white/5 border-white/10 text-white placeholder:text-gray-500"
                />
              </div>

              {/* Quick Prompts */}
              <div className="space-y-2">
                <Label className="text-gray-300">Quick Prompts</Label>
                <div className="flex flex-wrap gap-2">
                  {[
                    'Best marketing automation platforms for B2B SaaS',
                    'How to improve pipeline quality',
                    'Measuring marketing ROI effectively',
                  ].map((quickPrompt, index) => (
                    <button
                      key={index}
                      onClick={() => setPrompt(quickPrompt)}
                      className="px-3 py-1.5 text-xs rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 text-gray-300 transition-colors"
                    >
                      {quickPrompt}
                    </button>
                  ))}
                </div>
              </div>

              {/* Run Button */}
              <Button
                onClick={handleRunSimulation}
                disabled={!prompt}
                className="w-full h-11 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 text-white"
              >
                <Sparkles className="w-4 h-4 mr-2" />
                Run Simulation
              </Button>
            </div>

            {/* Response Output */}
            {hasResponse && (
              <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-4">
                <div className="flex items-center gap-3">
                  <div className="px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/20">
                    <span className="text-xs text-green-400">ChatGPT</span>
                  </div>
                  <span className="text-sm text-gray-400">Response</span>
                </div>
                <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-line">
                  {mockResponse}
                </div>
              </div>
            )}
          </div>

          {/* Right Panel - Analysis */}
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-6">
              <h2 className="text-xl text-white">Response Analysis</h2>

              {!hasResponse ? (
                <div className="py-12 text-center">
                  <div className="w-16 h-16 mx-auto rounded-xl bg-violet-500/10 flex items-center justify-center mb-4">
                    <Sparkles className="w-8 h-8 text-violet-400" />
                  </div>
                  <p className="text-gray-400">Run a simulation to see analysis</p>
                </div>
              ) : (
                <>
                  {/* Brand Mentions */}
                  <div className="space-y-3">
                    <h3 className="text-white">Brand Mentions</h3>
                    <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/20">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-300">Your Brand</span>
                        <span className="text-lg text-green-400 tabular-nums">0</span>
                      </div>
                      <p className="text-xs text-gray-400">Not mentioned in this response</p>
                    </div>
                  </div>

                  {/* Competitor Mentions */}
                  <div className="space-y-3">
                    <h3 className="text-white">Competitor Mentions</h3>
                    <div className="space-y-2">
                      {[
                        { name: 'HubSpot', count: 2, context: 'Positive' },
                        { name: 'Marketo', count: 1, context: 'Positive' },
                        { name: 'Pardot', count: 1, context: 'Positive' },
                        { name: 'ActiveCampaign', count: 1, context: 'Neutral' },
                      ].map((competitor, index) => (
                        <div
                          key={index}
                          className="p-3 rounded-lg bg-white/5 border border-white/10 flex items-center justify-between"
                        >
                          <div className="flex items-center gap-3">
                            <span className="text-sm text-gray-300">{competitor.name}</span>
                            <span
                              className={`text-xs px-2 py-0.5 rounded ${
                                competitor.context === 'Positive'
                                  ? 'bg-green-500/20 text-green-400'
                                  : 'bg-gray-500/20 text-gray-400'
                              }`}
                            >
                              {competitor.context}
                            </span>
                          </div>
                          <span className="text-sm text-gray-400 tabular-nums">
                            {competitor.count}x
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Trust Metrics */}
                  <div className="space-y-3">
                    <h3 className="text-white">Trust Variance</h3>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
                        <div className="flex items-center gap-2">
                          <TrendingUp className="w-4 h-4 text-blue-400" />
                          <span className="text-xs text-gray-400">Authority</span>
                        </div>
                        <div className="text-2xl text-white tabular-nums">High</div>
                      </div>
                      <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
                        <div className="flex items-center gap-2">
                          <Users className="w-4 h-4 text-violet-400" />
                          <span className="text-xs text-gray-400">Relevance</span>
                        </div>
                        <div className="text-2xl text-white tabular-nums">High</div>
                      </div>
                    </div>
                  </div>

                  {/* Optimization Suggestions */}
                  <div className="space-y-3">
                    <h3 className="text-white">Optimization Suggestions</h3>
                    <div className="space-y-3">
                      <div className="flex items-start gap-3 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                        <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <p className="text-sm text-yellow-300 mb-1">Zero Brand Visibility</p>
                          <p className="text-xs text-gray-400">
                            Your brand was not mentioned. Consider creating comparison content and case studies.
                          </p>
                        </div>
                      </div>

                      <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                        <TrendingUp className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <p className="text-sm text-blue-300 mb-1">Competitor Dominance</p>
                          <p className="text-xs text-gray-400">
                            Create content that directly compares your solution with HubSpot and Marketo.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
