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
import { LandingScreen } from './components/LandingScreen';

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
  
  // New auth flow state
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');
  const [pendingUrl, setPendingUrl] = useState('');

  const handleLogin = (userData: User) => {
    setUser(userData);
    setIsAuthenticated(true);
    setShowAuth(false);
    
    // If we have a pending URL, go straight to simulator
    if (pendingUrl) {
      setHasWebsite(true);
      setCurrentRoute('run-simulator');
    }
  };

  const handleLogout = () => {
    setUser(null);
    setIsAuthenticated(false);
    setCurrentRoute('dashboard');
    setShowAuth(false);
    setPendingUrl('');
  };

  const handleWebsiteSubmitted = () => {
    setHasWebsite(true);
    setCurrentRoute('dashboard');
    // Clear pending URL as it's been processed
    setPendingUrl('');
  };

  const handleLandingStart = (url: string) => {
    setPendingUrl(url);
    setAuthMode('signup');
    setShowAuth(true);
  };

  const handleNewWebsiteSubmit = (url: string) => {
    setPendingUrl(url);
    setCurrentRoute('run-simulator');
    setShowAuth(false);
  };
  // Unauthenticated Flow
  if (!isAuthenticated) {
    return (
      <div className="dark min-h-screen bg-[#0a0a0f] text-foreground">
        {showAuth ? (
          <AuthScreen 
            onLogin={handleLogin} 
            initialMode={authMode} 
          />
        ) : (
          <LandingScreen 
            onStart={handleLandingStart}
            onLoginClick={() => {
              setAuthMode('login');
              setShowAuth(true);
            }}
            onSignUpClick={() => {
              setAuthMode('signup');
              setShowAuth(true);
            }}
          />
        )}
      </div>
    );
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
          <EmptyDashboard onStart={handleNewWebsiteSubmit} />
        )}
        
        {currentRoute === 'dashboard' && hasWebsite && (
          <AnalyticsDashboard />
        )}
        
        {currentRoute === 'run-simulator' && (
          <SimulationFlow 
            onComplete={handleWebsiteSubmitted} 
            initialUrl={pendingUrl}
          />
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
