import { Button } from './ui/button';
import { Sparkles, ArrowRight } from 'lucide-react';

interface EmptyDashboardProps {
  onNavigate: () => void;
}

export function EmptyDashboard({ onNavigate }: EmptyDashboardProps) {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-violet-600/10 rounded-full blur-[100px] animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-[100px] animate-pulse delay-700"></div>
      </div>

      <div className="relative z-10 max-w-2xl mx-auto text-center space-y-8">
        <div className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-violet-500/20 to-blue-500/20 border border-violet-500/30 flex items-center justify-center">
          <Sparkles className="w-10 h-10 text-violet-400" />
        </div>

        <div className="space-y-3">
          <h1 className="text-4xl text-white">Welcome to GEO Platform</h1>
          <p className="text-lg text-gray-400 max-w-lg mx-auto">
            Start your journey to AI visibility by running your first brand simulation
          </p>
        </div>

        <div className="p-8 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-6">
          <div className="space-y-4">
            <h2 className="text-xl text-white">Get Started</h2>
            <p className="text-gray-400">
              Discover how GPT, Claude, Gemini, and Perplexity perceive your brand. 
              Our AI will analyze your website, generate personas, and simulate real-world queries.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
            <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
              <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center text-violet-400">
                1
              </div>
              <p className="text-gray-300">Scrape & analyze your website</p>
            </div>

            <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
              <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center text-blue-400">
                2
              </div>
              <p className="text-gray-300">Generate AI-powered personas</p>
            </div>

            <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
              <div className="w-8 h-8 rounded-lg bg-cyan-500/20 flex items-center justify-center text-cyan-400">
                3
              </div>
              <p className="text-gray-300">Simulate LLM responses</p>
            </div>
          </div>

          <Button
            onClick={onNavigate}
            className="h-12 px-8 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 text-white shadow-lg shadow-violet-500/25"
          >
            Run Brand Simulator Engine
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>

        <p className="text-sm text-gray-500">
          Simulation takes approximately 2-3 minutes
        </p>
      </div>
    </div>
  );
}
