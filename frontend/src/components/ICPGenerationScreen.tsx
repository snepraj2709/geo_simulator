import { useEffect, useState } from 'react';
import { Button } from './ui/button';
import { Sparkles, Check } from 'lucide-react';
import type { ICP } from '../types';
import { generatePromptsForICP } from '@/data';
import { defaultIcps } from '@/data/constants';

interface ICPGenerationScreenProps {
  onComplete: (icps: ICP[]) => void;
}

export function ICPGenerationScreen({ onComplete }: ICPGenerationScreenProps) {
  const [visibleICPs, setVisibleICPs] = useState<ICP[]>([]);
  const [approvedICPs, setApprovedICPs] = useState<Set<number>>(new Set());

  useEffect(() => {
    // Reveal ICPs one by one
    defaultIcps.forEach((_, index) => {
      setTimeout(() => {
        setVisibleICPs((prev) => [...prev, defaultIcps[index]]);
      }, index * 1200);
    });
  }, []);

  const handleApprove = (index: number) => {
    setApprovedICPs(prev => new Set(prev).add(index));
  };

  const handleContinue = () => {
    const icpsWithPrompts: ICP[] = visibleICPs.map((icp) => ({
      ...icp,
      prompts: [...(icp.prompts || []), ...generatePromptsForICP(icp.title)],
    }));
    onComplete(icpsWithPrompts);
  };

  const allApproved = visibleICPs.length > 0 && visibleICPs.length === approvedICPs.size;

  return (
    <div className="min-h-screen flex flex-col px-4 py-16 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-violet-600/10 rounded-full blur-[100px] animate-pulse"></div>
      </div>

      <div className="relative z-10 max-w-5xl mx-auto w-full space-y-8">
        {/* Header */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20">
            <Sparkles className="w-4 h-4 text-violet-400" />
            <span className="text-sm text-violet-300">AI-Generated Personas</span>
          </div>
          <h2 className="text-4xl text-white">Your Ideal Customer Profiles</h2>
          <p className="text-gray-400">Review and approve the personas we identified based on your content</p>
        </div>

        {/* ICP Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-12">
          {visibleICPs.map((icp, index) => {
            const isApproved = approvedICPs.has(index);
            
            return (
              <div
                key={icp.id}
                className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                {/* AI Generated Badge */}
                <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-violet-500/10 border border-violet-500/20">
                  <Sparkles className="w-3 h-3 text-violet-400" />
                  <span className="text-xs text-violet-300">AI Generated</span>
                </div>

                {/* Avatar and Info */}
                <div className="flex items-start gap-4">
                  <div className="relative">
                    <img
                      src={icp.avatar}
                      alt={icp.name}
                      className="w-16 h-16 rounded-full object-cover ring-2 ring-violet-500/20"
                    />
                    <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-violet-500 rounded-full flex items-center justify-center border-2 border-[#0a0a0f]">
                      <Sparkles className="w-3 h-3 text-white" />
                    </div>
                  </div>

                  <div className="flex-1 min-w-0">
                    <h3 className="text-white mb-1">{icp.name}</h3>
                    <p className="text-sm text-violet-400 mb-2">{icp.title}</p>
                    <p className="text-sm text-gray-400 leading-relaxed">{icp.description}</p>
                  </div>
                </div>

                {/* Approve Button */}
                <Button
                  onClick={() => handleApprove(index)}
                  disabled={isApproved}
                  className={`w-full ${
                    isApproved
                      ? 'bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/20'
                      : 'bg-white/5 hover:bg-white/10 text-white border border-white/10'
                  }`}
                  variant="outline"
                >
                  {isApproved ? (
                    <>
                      <Check className="w-4 h-4 mr-2" />
                      Approved
                    </>
                  ) : (
                    'Approve Persona'
                  )}
                </Button>
              </div>
            );
          })}
        </div>

        {/* Continue Button */}
        {allApproved && (
          <div className="flex justify-center pt-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <Button
              onClick={handleContinue}
              className="px-8 h-12 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 text-white shadow-lg shadow-violet-500/25"
            >
              Continue to Prompt Generation
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}