import { useState } from 'react';
import { LoginForm } from './LoginForm';
import { SignUpForm } from './SignUpForm';
import type { User } from '../../App';

interface AuthScreenProps {
  onLogin: (user: User) => void;
}

export function AuthScreen({ onLogin }: AuthScreenProps) {
  const [mode, setMode] = useState<'login' | 'signup'>('login');

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-auto">
      {/* Background effects */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-violet-600/20 rounded-full blur-[120px] animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600/20 rounded-full blur-[120px] animate-pulse delay-700"></div>
      </div>

      <div className="relative z-10 w-full max-w-md">
        {mode === 'login' ? (
          <LoginForm 
            onLogin={onLogin} 
            onSwitchToSignUp={() => setMode('signup')} 
          />
        ) : (
          <SignUpForm 
            onLogin={onLogin} 
            onSwitchToLogin={() => setMode('login')} 
          />
        )}
      </div>
    </div>
  );
}