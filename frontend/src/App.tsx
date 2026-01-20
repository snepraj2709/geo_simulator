import { useState } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { AuthScreen } from './components/auth/AuthScreen';
import { AppLayout } from './components/layout/AppLayout';
import { AllPersonasScreen } from './components/AllPersonasScreen';
import { PersonaSimulationEngine } from './components/PersonaSimulationEngine';
import { PreFlightChecker } from './components/PreFlightChecker';
import { InsightsRecommendations } from './components/InsightsRecommendations';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { EmptyDashboard } from './components/EmptyDashboard';
import { LandingScreen } from './components/LandingScreen';
import { ReportDashboard } from './components/ReportDashboard';

export interface User {
  name: string;
  email: string;
  avatar?: string;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [hasWebsite, setHasWebsite] = useState(false);
  const [brandUrl, setBrandUrl] = useState('');
  
  // New auth flow state
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');
  const [pendingUrl, setPendingUrl] = useState('');

  const navigate = useNavigate();

  const handleLogin = (userData: User) => {
    setUser(userData);
    setIsAuthenticated(true);
    setShowAuth(false);
    
    // If we have a pending URL, go straight to simulator
    if (pendingUrl) {
      setHasWebsite(true);
      setBrandUrl(pendingUrl);
      navigate('/run-simulator');
    } else {
      navigate('/dashboard');
    }
  };

  const handleLogout = () => {
    setUser(null);
    setIsAuthenticated(false);
    setShowAuth(false);
    setPendingUrl('');
    setBrandUrl('');
    navigate('/');
  };

  const handleWebsiteSubmitted = () => {
    setHasWebsite(true);
    navigate('/dashboard');
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
    setBrandUrl(url);
    setShowAuth(false);
    navigate('/run-simulator');
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
        onLogout={handleLogout}
      >
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route 
            path="/dashboard" 
            element={
              !hasWebsite ? (
                <EmptyDashboard onStart={handleNewWebsiteSubmit} />
              ) : (
                <AnalyticsDashboard />
              )
            } 
          />
          <Route 
            path="/run-simulator" 
            element={
              <EmptyDashboard 
                onStart={handleNewWebsiteSubmit}
              />
            } 
          />
          <Route path="/all-personas" element={<AllPersonasScreen />} />
          <Route path="/persona-simulation" element={<PersonaSimulationEngine />} />
          <Route path="/preflight-checker" element={<PreFlightChecker />} />
          <Route 
            path="/reports" 
            element={
              <ReportDashboard 
                brandUrl={brandUrl} 
                onComplete={handleWebsiteSubmitted} 
              />
            } 
          />
          <Route path="/insights" element={<InsightsRecommendations />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AppLayout>
    </div>
  );
}

export default App;
