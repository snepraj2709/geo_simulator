import { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { AuthScreen } from './components/auth/AuthScreen';
import { AppLayout } from './components/Layout/AppLayout';
import { AllPersonasScreen } from './components/AllPersonasScreen';
import { PersonaSimulationEngine } from './components/PersonaSimulationEngine';
import { PreFlightChecker } from './components/PreFlightChecker';
import { InsightsRecommendations } from './components/InsightsRecommendations';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { EmptyDashboard } from './components/EmptyDashboard';
import { LandingScreen } from './components/LandingScreen';
import { ReportDashboard } from './components/ReportDashboard';
import { authService } from './services/auth';

export interface User {
  name: string; // User's name
  email: string; // User's email
  avatar?: string; // Optional avatar URL
  organization_id?: string; // Optional organization ID
  id?: string; // Optional user ID
  role?: string; // Optional user role
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(authService.isAuthenticated());
  const [user, setUser] = useState<User | null>(null);
  const [hasWebsite, setHasWebsite] = useState(false);
  const [brandUrl, setBrandUrl] = useState('');
  const [loadingInitial, setLoadingInitial] = useState(true);

  // New auth flow state
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');
  const [pendingUrl, setPendingUrl] = useState('');

  const navigate = useNavigate();

  useEffect(() => {
    const initAuth = async () => {
      if (authService.isAuthenticated()) {
        try {
          const storedUser = localStorage.getItem('user_data');
          if (storedUser) {
            setUser(JSON.parse(storedUser));
            setIsAuthenticated(true);
          } else {
            setIsAuthenticated(true);
            if (!user) setUser({ name: 'User', email: 'user@example.com' });
          }
        } catch (error) {
          console.error("Auth check failed", error);
          handleLogout();
        }
      }
      setLoadingInitial(false);
    };
    initAuth();
  }, []);

  const handleLogin = (userData: User) => {
    setUser(userData);
    setIsAuthenticated(true);
    setShowAuth(false);

    // Persist user data for reload
    localStorage.setItem('user_data', JSON.stringify(userData));

    // If we have a pending URL, go straight to simulator
    if (pendingUrl) {
      setHasWebsite(true);
      setBrandUrl(pendingUrl);
      navigate('/run-simulator');
    } else {
      navigate('/dashboard');
    }
  };

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch (error) {
      console.error("Logout failed", error);
    }
    localStorage.removeItem('user_data');
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

  if (loadingInitial) {
    return (
      <div className="dark min-h-screen bg-[#0a0a0f] text-foreground flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

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
