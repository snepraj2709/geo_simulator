import { Sparkles } from 'lucide-react';
import { UrlInputForm } from './UrlInputForm';
import { brand_simulation_steps } from '@/data/constants';

interface EmptyDashboardProps {
  onStart: (url: string) => void;
}

export function EmptyDashboard({ onStart }: EmptyDashboardProps) {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-violet-600/10 rounded-full blur-[100px] animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-[100px] animate-pulse delay-700"></div>
      </div>

      <div className="relative z-10 max-w-2xl mx-auto text-center space-y-8">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-violet-500/10 border border-violet-500/20 backdrop-blur-sm">
          <Sparkles className="w-4 h-4 text-violet-400" />
          <span className="text-sm text-violet-300">GEO Intelligence Platform</span>
        </div>

        <div className="space-y-3">
          <h1 className="text-4xl text-white">Welcome to GEO Platform</h1>
          <p className="text-lg text-gray-400 max-w-lg mx-auto">
            Start your journey to AI visibility by running your first brand simulation
          </p>
        </div>

        <div className="p-8 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-6">
          <div className="space-y-4">
            <p className="text-gray-400">
              Discover how GPT, Claude, Gemini, and Perplexity perceive your brand. 
              Our AI will analyze your website, generate personas, and simulate real-world queries.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
            {brand_simulation_steps.map((step) => (
              <div key={step.id} className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
                <div className={`w-8 h-8 mx-auto rounded-lg ${step.iconBg} flex items-center justify-center ${step.iconColor}`}>
                  {step.id}
                </div>
                <p className="text-gray-300 text-center">
                  {step.text}
                </p>
              </div>
            ))}
          </div>

          {/* Input form */}
          <UrlInputForm 
            onSubmit={onStart}
            buttonText="Run AI Brand Simulation"
            className="mt-12"
          />
        </div>

        <p className="text-sm text-gray-500">
          Simulation takes approximately 2-3 minutes
        </p>
      </div>
    </div>
  );
}
