import { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { FileText, Link as LinkIcon, CheckCircle, AlertTriangle, TrendingDown, Lightbulb } from 'lucide-react';

export function PreFlightChecker() {
  const [activeTab, setActiveTab] = useState('input');
  const [blogUrl, setBlogUrl] = useState('');
  const [draftContent, setDraftContent] = useState('');

  const handleAnalyze = () => {
    setActiveTab('simulation');
    setTimeout(() => setActiveTab('scoring'), 2000);
    setTimeout(() => setActiveTab('optimization'), 4000);
  };

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl text-white mb-2">Pre-Flight GEO Checker</h1>
          <p className="text-gray-400">
            Evaluate content before publishing to optimize for AI visibility
          </p>
        </div>

        {/* Flow Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 bg-white/5 border border-white/10">
            <TabsTrigger value="input">Input</TabsTrigger>
            <TabsTrigger value="simulation" disabled={activeTab === 'input'}>Simulation</TabsTrigger>
            <TabsTrigger value="scoring" disabled={activeTab === 'input' || activeTab === 'simulation'}>Scoring</TabsTrigger>
            <TabsTrigger value="optimization" disabled={activeTab !== 'optimization'}>Optimization</TabsTrigger>
          </TabsList>

          {/* Input Tab */}
          <TabsContent value="input" className="space-y-6">
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-6">
              <h2 className="text-xl text-white">Content Input</h2>

              <div className="space-y-2">
                <Label className="text-gray-300 flex items-center gap-2">
                  <LinkIcon className="w-4 h-4" />
                  Blog URL
                </Label>
                <Input
                  type="url"
                  placeholder="https://yourblog.com/post-title"
                  value={blogUrl}
                  onChange={(e) => setBlogUrl(e.target.value)}
                  className="bg-white/5 border-white/10 text-white placeholder:text-gray-500"
                />
              </div>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/10"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-[#0a0a0f] text-gray-500">OR</span>
                </div>
              </div>

              <div className="space-y-2">
                <Label className="text-gray-300 flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Draft Content
                </Label>
                <Textarea
                  placeholder="Paste your draft content here..."
                  value={draftContent}
                  onChange={(e) => setDraftContent(e.target.value)}
                  className="min-h-64 bg-white/5 border-white/10 text-white placeholder:text-gray-500"
                />
              </div>

              <Button
                onClick={handleAnalyze}
                disabled={!blogUrl && !draftContent}
                className="w-full h-11 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 text-white"
              >
                Analyze Content
              </Button>
            </div>
          </TabsContent>

          {/* Simulation Tab */}
          <TabsContent value="simulation" className="space-y-6">
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-6">
              <h2 className="text-xl text-white">Running Simulations</h2>
              <div className="space-y-4">
                {[
                  { model: 'GPT-4', status: 'complete' },
                  { model: 'Claude 3', status: 'complete' },
                  { model: 'Gemini Pro', status: 'processing' },
                  { model: 'Perplexity', status: 'queued' },
                ].map((item, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10"
                  >
                    <span className="text-white">{item.model}</span>
                    {item.status === 'complete' && (
                      <CheckCircle className="w-5 h-5 text-green-400" />
                    )}
                    {item.status === 'processing' && (
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse delay-100"></div>
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse delay-200"></div>
                      </div>
                    )}
                    {item.status === 'queued' && (
                      <span className="text-sm text-gray-500">Queued</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>

          {/* Scoring Tab */}
          <TabsContent value="scoring" className="space-y-6">
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-6">
              <h2 className="text-xl text-white">Content Scores</h2>

              {/* Overall Score */}
              <div className="p-6 rounded-xl bg-gradient-to-br from-violet-500/20 to-blue-500/20 border border-violet-500/30 text-center">
                <div className="text-sm text-gray-300 mb-2">Overall GEO Score</div>
                <div className="text-5xl text-white tabular-nums mb-2">62</div>
                <div className="text-sm text-yellow-400">Room for improvement</div>
              </div>

              {/* Scores by Dimension */}
              <div className="space-y-4">
                <h3 className="text-white">Scores by Persona</h3>
                {[
                  { name: 'Sarah Chen - VP of Marketing', score: 68 },
                  { name: 'Marcus Rodriguez - SEO Manager', score: 72 },
                  { name: 'Emily Watson - Content Director', score: 58 },
                  { name: 'David Park - Growth Lead', score: 52 },
                ].map((persona, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-300">{persona.name}</span>
                      <span className="text-white tabular-nums">{persona.score}/100</span>
                    </div>
                    <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-1000 ${
                          persona.score >= 70 ? 'bg-green-500' :
                          persona.score >= 50 ? 'bg-yellow-500' :
                          'bg-red-500'
                        }`}
                        style={{ width: `${persona.score}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Scores by Model */}
              <div className="space-y-4">
                <h3 className="text-white">Scores by LLM Model</h3>
                {[
                  { name: 'GPT-4', score: 65 },
                  { name: 'Claude 3', score: 70 },
                  { name: 'Gemini Pro', score: 58 },
                  { name: 'Perplexity', score: 55 },
                ].map((model, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-300">{model.name}</span>
                      <span className="text-white tabular-nums">{model.score}/100</span>
                    </div>
                    <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 transition-all duration-1000"
                        style={{ width: `${model.score}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>

          {/* Optimization Tab */}
          <TabsContent value="optimization" className="space-y-6">
            {/* Missing Attributes */}
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-4">
              <h2 className="text-xl text-white flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-yellow-400" />
                Missing Content Attributes
              </h2>
              <div className="space-y-3">
                {[
                  'No clear use cases or success stories',
                  'Missing pricing or value proposition',
                  'Lacks technical implementation details',
                  'No comparison with alternatives',
                ].map((item, index) => (
                  <div key={index} className="flex items-start gap-3 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                    <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
                    <span className="text-sm text-gray-300">{item}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Competitor Citations */}
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-4">
              <h2 className="text-xl text-white flex items-center gap-2">
                <TrendingDown className="w-5 h-5 text-red-400" />
                Why Competitors Are Cited
              </h2>
              <div className="space-y-3">
                {[
                  { competitor: 'HubSpot', reason: 'More comprehensive feature documentation' },
                  { competitor: 'Marketo', reason: 'Better case study library for enterprise' },
                  { competitor: 'Pardot', reason: 'Clear integration guides with Salesforce' },
                ].map((item, index) => (
                  <div key={index} className="p-4 rounded-lg bg-white/5 border border-white/10">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-white">{item.competitor}</span>
                      <span className="text-xs px-2 py-1 rounded bg-red-500/20 text-red-400">
                        Preferred
                      </span>
                    </div>
                    <p className="text-sm text-gray-400">{item.reason}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Suggested Edits */}
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-4">
              <h2 className="text-xl text-white flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-blue-400" />
                Suggested Content Edits
              </h2>
              <div className="space-y-3">
                {[
                  'Add a "How it works" section with step-by-step implementation',
                  'Include 2-3 customer success stories with metrics',
                  'Create a comparison table with HubSpot and Marketo',
                  'Add pricing information or "Request a quote" CTA',
                  'Include integration capabilities and API documentation',
                ].map((item, index) => (
                  <div key={index} className="flex items-start gap-3 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                    <CheckCircle className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
                    <span className="text-sm text-gray-300">{item}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Persona-Specific Guidance */}
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-4">
              <h2 className="text-xl text-white">Persona-Specific Optimization</h2>
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                  <h3 className="text-white mb-2">For Growth Marketing Leads</h3>
                  <p className="text-sm text-gray-400 mb-3">
                    Current score: 52/100 - Needs more data-driven content
                  </p>
                  <ul className="text-sm text-gray-400 space-y-1 list-disc list-inside">
                    <li>Add conversion rate benchmarks</li>
                    <li>Include A/B testing capabilities</li>
                    <li>Showcase analytics and reporting features</li>
                  </ul>
                </div>

                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                  <h3 className="text-white mb-2">For Content Marketing Directors</h3>
                  <p className="text-sm text-gray-400 mb-3">
                    Current score: 58/100 - Needs workflow examples
                  </p>
                  <ul className="text-sm text-gray-400 space-y-1 list-disc list-inside">
                    <li>Add content planning workflow examples</li>
                    <li>Include team collaboration features</li>
                    <li>Showcase content distribution capabilities</li>
                  </ul>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
