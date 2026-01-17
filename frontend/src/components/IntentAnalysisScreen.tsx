import { useEffect, useState } from 'react';
import { Button } from './ui/button';
import { Sparkles, TrendingUp } from 'lucide-react';
import { IntentData } from '@/types';
import { intentData } from '@/data/constants';

interface IntentAnalysisScreenProps {
  onComplete: () => void;
}

export function IntentAnalysisScreen({ onComplete }: IntentAnalysisScreenProps) {
  const [analyzing, setAnalyzing] = useState(true);
  const [visibleData, setVisibleData] = useState<IntentData[]>([]);

  useEffect(() => {
    // Show analyzing message
    const timer1 = setTimeout(() => {
      setAnalyzing(false);
      
      // Reveal data one by one
      intentData.forEach((_, index) => {
        setTimeout(() => {
          setVisibleData(prev => [...prev, intentData[index]]);
        }, index * 400);
      });
    }, 3000);

    return () => clearTimeout(timer1);
  }, []);

  const funnelStages = [
    { stage: 'Awareness', count: 8, percentage: 20 },
    { stage: 'Consideration', count: 16, percentage: 40 },
    { stage: 'Decision', count: 12, percentage: 30 },
    { stage: 'Retention', count: 4, percentage: 10 },
  ];

  return (
    <div className="min-h-screen flex flex-col items-center px-4 pt-5 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 right-1/3 w-96 h-96 bg-violet-600/10 rounded-full blur-[100px] animate-pulse"></div>
      </div>

      <div className="relative z-10 max-w-5xl mx-auto w-full space-y-12">
        {analyzing ? (
          // Analyzing State
          <div className="text-center space-y-6">
            <div className="inline-flex items-center gap-3 px-6 py-3 rounded-full bg-violet-500/10 border border-violet-500/20 backdrop-blur-sm">
              <Sparkles className="w-5 h-5 text-violet-400 animate-pulse" />
              <span className="text-violet-300">AI Analysis in Progress</span>
            </div>

            <h2 className="text-4xl text-white">Analyzing Intent Signals</h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Our AI is analyzing all LLM responses to classify user intent, identify funnel stages, 
              and map engagement patterns across your customer journey
            </p>

            <div className="flex justify-center gap-2 pt-8">
              <div className="w-3 h-3 bg-violet-400 rounded-full animate-pulse"></div>
              <div className="w-3 h-3 bg-violet-400 rounded-full animate-pulse delay-150"></div>
              <div className="w-3 h-3 bg-violet-400 rounded-full animate-pulse delay-300"></div>
            </div>
          </div>
        ) : (
          // Results State
          <>
            {/* Header */}
            <div className="text-center space-y-3">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10 border border-green-500/20">
                <Sparkles className="w-4 h-4 text-green-400" />
                <span className="text-sm text-green-300">Analysis Complete</span>
              </div>
              <h2 className="text-4xl text-white">Intent Classification Results</h2>
              <p className="text-gray-400">
                AI-powered analysis of user intent across all simulated prompts
              </p>
            </div>

            {/* Intent Distribution */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {visibleData.map((intent, index) => {
                const Icon = intent.icon;
                
                return (
                  <div
                    key={intent.category}
                    className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500"
                    style={{ animationDelay: `${index * 100}ms` }}
                  >
                    <div className="flex items-center justify-between">
                      <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${intent.color} flex items-center justify-center`}>
                        <Icon className="w-6 h-6 text-white" />
                      </div>
                      <span className="text-2xl text-white tabular-nums">{intent.count}</span>
                    </div>
                    
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-400">{intent.category}</span>
                        <span className="text-gray-400 tabular-nums">{intent.percentage}%</span>
                      </div>
                      <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className={`h-full bg-gradient-to-r ${intent.color} transition-all duration-1000 ease-out`}
                          style={{ width: `${intent.percentage}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Funnel Stage Analysis */}
            <div className="p-8 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-violet-500/20 flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-violet-400" />
                </div>
                <div>
                  <h3 className="text-white">Funnel Stage Distribution</h3>
                  <p className="text-sm text-gray-400">Where users are in their buyer journey</p>
                </div>
              </div>

              <div className="space-y-4">
                {funnelStages.map((stage, index) => (
                  <div
                    key={stage.stage}
                    className="space-y-2 animate-in fade-in slide-in-from-left-4 duration-500"
                    style={{ animationDelay: `${(index + 4) * 100}ms` }}
                  >
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-300">{stage.stage}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-gray-400 tabular-nums">{stage.count} prompts</span>
                        <span className="text-gray-400 tabular-nums w-12 text-right">{stage.percentage}%</span>
                      </div>
                    </div>
                    <div className="h-3 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-violet-500 to-blue-500 transition-all duration-1000 ease-out"
                        style={{ width: `${stage.percentage}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Continue Button */}
            <div className="flex justify-center py-8">
              <Button
                onClick={onComplete}
                className="px-8 h-12 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 text-white shadow-lg shadow-violet-500/25"
              >
                View Final Report
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
