import { useEffect, useState } from 'react';
import { FileText, Tags, Network } from 'lucide-react';
import { Progress } from './ui/progress';
import { ScrapingStats } from '@/types';
import { steps } from '@/data/constants';

interface ScrapingScreenProps {
  brandUrl: string;
  onComplete: () => void;
}

export function ScrapingScreen({ brandUrl, onComplete }: ScrapingScreenProps) {
  const [stats, setStats] = useState<ScrapingStats>({
    pagesScraped: 0,
    entitiesExtracted: 0,
    topicsMapped: 0,
  });
  const [currentStep, setCurrentStep] = useState(1);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Simulate scraping process
    const maxPages = 147;
    const maxEntities = 892;
    const maxTopics = 34;
    
    const interval = setInterval(() => {
      setStats(prev => {
        const newPages = Math.min(prev.pagesScraped + Math.floor(Math.random() * 8) + 3, maxPages);
        const newEntities = Math.min(prev.entitiesExtracted + Math.floor(Math.random() * 20) + 10, maxEntities);
        const newTopics = Math.min(prev.topicsMapped + Math.floor(Math.random() * 2) + 1, maxTopics);
        
        return {
          pagesScraped: newPages,
          entitiesExtracted: newEntities,
          topicsMapped: newTopics,
        };
      });
      
      setProgress(prev => {
        const newProgress = Math.min(prev + Math.random() * 3 + 1, 100);
        return newProgress;
      });
    }, 200);

    // Update steps
    const stepInterval = setInterval(() => {
      setCurrentStep(prev => {
        if (prev < 4) return prev + 1;
        return prev;
      });
    }, 2000);

    // Complete after 8 seconds
    const timeout = setTimeout(() => {
      clearInterval(interval);
      clearInterval(stepInterval);
      setStats({ pagesScraped: maxPages, entitiesExtracted: maxEntities, topicsMapped: maxTopics });
      setProgress(100);
      setCurrentStep(4);
      setTimeout(onComplete, 1000);
    }, 8000);

    return () => {
      clearInterval(interval);
      clearInterval(stepInterval);
      clearTimeout(timeout);
    };
  }, [onComplete]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/3 w-96 h-96 bg-violet-600/10 rounded-full blur-[100px] animate-pulse"></div>
        <div className="absolute bottom-1/3 right-1/3 w-96 h-96 bg-cyan-600/10 rounded-full blur-[100px] animate-pulse delay-500"></div>
      </div>

      <div className="relative z-10 max-w-4xl mx-auto w-full space-y-12">
        {/* Header */}
        <div className="text-center space-y-3 mt-6">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20">
            <div className="w-2 h-2 rounded-full bg-violet-400 animate-pulse"></div>
            <span className="text-sm text-violet-300">Analyzing {brandUrl}</span>
          </div>
          <h2 className="text-4xl text-white mt-6">Discovering your digital footprint</h2>
          <p className="text-gray-400">Mapping content structure and extracting key entities</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-8 rounded-2xl bg-gradient-to-br from-violet-500/10 to-violet-500/5 border border-violet-500/20 backdrop-blur-sm">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-violet-500/20 flex items-center justify-center">
                <FileText className="w-5 h-5 text-violet-400" />
              </div>
              <span className="text-sm text-gray-400">Pages Scraped</span>
            </div>
            <div className="text-4xl text-white tabular-nums">{stats.pagesScraped}</div>
          </div>

          <div className="p-8 rounded-2xl bg-gradient-to-br from-cyan-500/10 to-cyan-500/5 border border-cyan-500/20 backdrop-blur-sm">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center">
                <Tags className="w-5 h-5 text-cyan-400" />
              </div>
              <span className="text-sm text-gray-400">Entities Extracted</span>
            </div>
            <div className="text-4xl text-white tabular-nums">{stats.entitiesExtracted}</div>
          </div>

          <div className="p-8 rounded-2xl bg-gradient-to-br from-blue-500/10 to-blue-500/5 border border-blue-500/20 backdrop-blur-sm">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Network className="w-5 h-5 text-blue-400" />
              </div>
              <span className="text-sm text-gray-400">Topics Mapped</span>
            </div>
            <div className="text-4xl text-white tabular-nums">{stats.topicsMapped}</div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="space-y-4">
          <Progress value={progress} className="h-2 bg-white/5" />
          <div className="text-center text-sm text-gray-500">{Math.round(progress)}% complete</div>
        </div>

        {/* Step indicator */}
        <div className="space-y-4">
          {steps.map((step) => {
            const Icon = step.icon;
            const isActive = currentStep === step.id;
            const isComplete = currentStep > step.id;
            
            return (
              <div
                key={step.id}
                className={`flex items-center gap-4 p-4 rounded-xl border transition-all duration-500 ${
                  isActive
                    ? 'bg-white/10 border-violet-500/50 shadow-lg shadow-violet-500/10'
                    : isComplete
                    ? 'bg-white/5 border-white/10'
                    : 'bg-transparent border-white/5 opacity-40'
                }`}
              >
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all ${
                    isActive
                      ? 'bg-violet-500/20 text-violet-400'
                      : isComplete
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-white/5 text-gray-600'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <span className={isActive || isComplete ? 'text-white' : 'text-gray-600'}>
                  {step.name}
                </span>
                {isActive && (
                  <div className="ml-auto flex gap-1">
                    <div className="w-2 h-2 bg-violet-400 rounded-full animate-pulse"></div>
                    <div className="w-2 h-2 bg-violet-400 rounded-full animate-pulse delay-100"></div>
                    <div className="w-2 h-2 bg-violet-400 rounded-full animate-pulse delay-200"></div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
