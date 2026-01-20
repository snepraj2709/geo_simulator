import { useState, useEffect } from 'react';
import { LandingScreen } from './LandingScreen';
import { ScrapingScreen } from './ScrapingScreen';
import { ICPGenerationScreen } from './ICPGenerationScreen';
import { PromptGenerationScreen } from './PromptGenerationScreen';
import { LLMSimulationScreen } from './LLMSimulationScreen';
import { IntentAnalysisScreen } from './IntentAnalysisScreen';
import { ReportDashboard } from './ReportDashboard';
import { ICP, SimulationStep } from '@/types';

interface SimulationFlowProps {
  onComplete: () => void;
  initialUrl?: string;
} 

export function SimulationFlow({ onComplete, initialUrl }: SimulationFlowProps) {
  const [currentStep, setCurrentStep] = useState<SimulationStep>('landing');
  const [brandUrl, setBrandUrl] = useState(initialUrl || '');
  const [icps, setICPs] = useState<ICP[]>([]);

  useEffect(() => {
    if (initialUrl) {
      setCurrentStep('scraping');
    }
  }, [initialUrl]);

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

  const handleReportComplete = () => {
    onComplete();
  };

  return (
    <>
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
        <ReportDashboard brandUrl={brandUrl} onComplete={handleReportComplete}/>
      )}
    </>
  );
}
