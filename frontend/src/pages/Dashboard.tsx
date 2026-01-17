import { ICPGenerationScreen } from '@/components/ICPGenerationScreen';
import { IntentAnalysisScreen } from '@/components/IntentAnalysisScreen';
import { LandingScreen } from '@/components/LandingScreen';
import { LLMSimulationScreen } from '@/components/LLMSimulationScreen';
import { PromptGenerationScreen } from '@/components/PromptGenerationScreen';
import { ReportDashboard } from '@/components/ReportDashboard';
import { ScrapingScreen } from '@/components/ScrapingScreen';
import { ICP, SimulationStep } from '@/types';
import { useState } from 'react';

export default function Dashboard() {
const [currentStep, setCurrentStep] = useState<SimulationStep>('landing');
  const [brandUrl, setBrandUrl] = useState('');
  const [icps, setICPs] = useState<ICP[]>([]);

  const handleStartSimulation = (url: string) => {
    setBrandUrl(url);
    setCurrentStep('scraping');
  };

  const handleScrapingComplete = () => {
    setCurrentStep('icp-generation');
  };

  const handleICPsGenerated = (generatedICPs: ICP[]) => {
    setICPs(generatedICPs);
    setCurrentStep('prompt-generation');
  };

  const handlePromptsApproved = (updatedICPs: ICP[]) => {
    setICPs(updatedICPs);
    setCurrentStep('llm-simulation');
  };

  const handleSimulationComplete = () => {
    setCurrentStep('intent-analysis');
  };

  const handleAnalysisComplete = () => {
    setCurrentStep('report');
  };

  return (
    <div className="dark min-h-screen bg-[#0a0a0f] text-foreground pb-10">
      {currentStep === 'landing' && (
        <LandingScreen onStart={handleStartSimulation} />
      )}
      
      {currentStep === 'scraping' && (
        <ScrapingScreen 
          brandUrl={brandUrl} 
          onComplete={handleScrapingComplete} 
        />
      )}
      
      {currentStep === 'icp-generation' && (
        <ICPGenerationScreen onComplete={handleICPsGenerated} />
      )}
      
      {currentStep === 'prompt-generation' && (
        <PromptGenerationScreen 
          icps={icps} 
          onComplete={handlePromptsApproved} 
        />
      )}
      
      {currentStep === 'llm-simulation' && (
        <LLMSimulationScreen 
          icps={icps} 
          onComplete={handleSimulationComplete} 
        />
      )}
      
      {currentStep === 'intent-analysis' && (
        <IntentAnalysisScreen onComplete={handleAnalysisComplete} />
      )}
      
      {currentStep === 'report' && (
        <ReportDashboard brandUrl={brandUrl} />
      )}
    </div>
  );
}
