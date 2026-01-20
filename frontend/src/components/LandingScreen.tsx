import { Button } from './ui/button';
import { Sparkles, TrendingUp, Eye, Shield } from 'lucide-react';
import { UrlInputForm } from './UrlInputForm';

interface LandingScreenProps {
  onStart: (url: string) => void;
  onLoginClick?: () => void;
  onSignUpClick?: () => void;
}

export function LandingScreen({ onStart, onLoginClick, onSignUpClick }: LandingScreenProps) {

  return (
    <div className="min-h-screen flex flex-col items-center pt-5 px-4 relative overflow-hidden">
      {/* Ambient background effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-violet-600/20 rounded-full blur-[120px] animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600/20 rounded-full blur-[120px] animate-pulse delay-700"></div>
      </div>

      {/* Top Right Header - Only show if auth callbacks provided */}
      {onLoginClick && onSignUpClick && (
        <div className="absolute top-5 right-5 z-50 flex gap-3">
          <Button 
            variant="ghost" 
            onClick={onLoginClick}
            className="text-gray-300 hover:text-white hover:bg-white/10"
          >
            Log in
          </Button>
          <Button 
            onClick={onSignUpClick}
            className="bg-white text-black hover:bg-gray-100 font-medium"
          >
            Sign up
          </Button>
        </div>
      )}

      <div className="relative z-10 max-w-4xl mx-auto text-center space-y-8">
        {/* Logo/Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-violet-500/10 border border-violet-500/20 backdrop-blur-sm">
          <Sparkles className="w-4 h-4 text-violet-400" />
          <span className="text-sm text-violet-300">GEO Intelligence Platform</span>
        </div>

        {/* Main headline */}
        <div className="space-y-4">
          <h1 className="text-5xl md:text-6xl lg:text-7xl tracking-tight bg-gradient-to-b from-white to-gray-400 bg-clip-text text-transparent">
            See how AI recommends your brand before customers do
          </h1>
          
          <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto leading-relaxed">
            Simulate how GPT, Claude, Gemini, and Perplexity perceive, recommend, or ignore your brand. 
            Optimize for AI visibility before it impacts your pipeline.
          </p>
        </div>

        {/* Input form */}
        <UrlInputForm 
          onSubmit={onStart}
          buttonText="Sign up to Run AI Brand Simulation"
          subtext="Free preview. No credit card required."
          className="mt-12"
        />

        {/* Value props */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 max-w-3xl mx-auto">
          <div className="p-6 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-3">
            <div className="w-12 h-12 rounded-lg bg-violet-500/10 flex items-center justify-center">
              <Eye className="w-6 h-6 text-violet-400" />
            </div>
            <h3 className="text-white">AI Visibility</h3>
            <p className="text-sm text-gray-400">
              Discover if AI models can find, understand, and recommend your brand
            </p>
          </div>

          <div className="p-6 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-3">
            <div className="w-12 h-12 rounded-lg bg-blue-500/10 flex items-center justify-center">
              <Shield className="w-6 h-6 text-blue-400" />
            </div>
            <h3 className="text-white">Trust Signals</h3>
            <p className="text-sm text-gray-400">
              Measure how AI perceives your authority and credibility
            </p>
          </div>

          <div className="p-6 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-3">
            <div className="w-12 h-12 rounded-lg bg-cyan-500/10 flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-cyan-400" />
            </div>
            <h3 className="text-white">Competitive Edge</h3>
            <p className="text-sm text-gray-400">
              See where you stand vs. competitors in AI-driven recommendations
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
