import { useState } from 'react';
import { AuthScreen } from './components/auth/AuthScreen';
import { AppLayout } from './components/layout/AppLayout';
import { SimulationFlow } from './components/SimulationFlow';
import { AllPersonasScreen } from './components/AllPersonasScreen';
import { PersonaSimulationEngine } from './components/PersonaSimulationEngine';
import { PreFlightChecker } from './components/PreFlightChecker';
import { InsightsRecommendations } from './components/InsightsRecommendations';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { EmptyDashboard } from './components/EmptyDashboard';

export type Route = 
  | 'dashboard'
  | 'run-simulator' 
  | 'all-personas' 
  | 'persona-simulation' 
  | 'preflight-checker' 
  | 'insights';

export interface User {
  name: string;
  email: string;
  avatar?: string;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [currentRoute, setCurrentRoute] = useState<Route>('dashboard');
  const [hasWebsite, setHasWebsite] = useState(false);

  const handleLogin = (userData: User) => {
    setUser(userData);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    setUser(null);
    setIsAuthenticated(false);
    setCurrentRoute('dashboard');
  };

  const handleWebsiteSubmitted = () => {
    setHasWebsite(true);
    setCurrentRoute('dashboard');
  };

  if (!isAuthenticated) {
    return <AuthScreen onLogin={handleLogin} />;
  }

  return (
    <div className="dark min-h-screen bg-[#0a0a0f] text-foreground">
      <AppLayout 
        user={user!} 
        currentRoute={currentRoute}
        onNavigate={setCurrentRoute}
        onLogout={handleLogout}
      >
        {currentRoute === 'dashboard' && !hasWebsite && (
          <EmptyDashboard onNavigate={() => setCurrentRoute('run-simulator')} />
        )}
        
        {currentRoute === 'dashboard' && hasWebsite && (
          <AnalyticsDashboard />
        )}
        
        {currentRoute === 'run-simulator' && (
          <SimulationFlow onComplete={handleWebsiteSubmitted} />
        )}
        
        {currentRoute === 'all-personas' && (
          <AllPersonasScreen />
        )}
        
        {currentRoute === 'persona-simulation' && (
          <PersonaSimulationEngine />
        )}
        
        {currentRoute === 'preflight-checker' && (
          <PreFlightChecker />
        )}
        
        {currentRoute === 'insights' && (
          <InsightsRecommendations />
        )}
      </AppLayout>
    </div>
  );
}

export default App;
