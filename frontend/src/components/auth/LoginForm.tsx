import { useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import type { User } from '../../App';

interface LoginFormProps {
  onLogin: (user: User) => void;
  onSwitchToSignUp: () => void;
}

export function LoginForm({ onLogin, onSwitchToSignUp }: LoginFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Simple auth - in real app would validate
    onLogin({
      name: email.split('@')[0],
      email,
    });
  };

  const handleGuestLogin = () => {
    onLogin({
      name: 'Guest User',
      email: 'guest@geosimulator.ai',
    });
  };

  const handleGoogleLogin = () => {
    onLogin({
      name: 'Demo User',
      email: 'demo@geosimulator.ai',
    });
  };

  return (
    <div className="space-y-8">
      {/* Logo/Header */}
      <div className="text-center space-y-3">
        <h1 className="text-3xl text-white">Welcome back</h1>
        <p className="text-gray-400">Sign in to continue to your dashboard</p>
      </div>

      {/* Login Form */}
      <div className="p-8 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-gray-300">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="bg-white/5 border-white/10 text-white placeholder:text-gray-500"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-gray-300">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="bg-white/5 border-white/10 text-white placeholder:text-gray-500"
              required
            />
          </div>

          <Button 
            type="submit"
            className="w-full h-11 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 text-white"
          >
            Login
          </Button>
        </form>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-white/10"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 text-gray-500">Or continue with</span>
          </div>
        </div>

        <div className="space-y-3">
          <Button
            type="button"
            variant="outline"
            onClick={handleGoogleLogin}
            className="w-full h-11 bg-blue-500 text-white hover:bg-blue-400"
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
              <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </Button>

          <Button
            type="button"
            variant="outline"
            onClick={handleGuestLogin}
            className="w-full h-11 bg-gray-200 text-gray-700 border-white/10 hover:bg-blue-400"
          >
            Guest Login
          </Button>
        </div>

        {/* Default Credentials */}
        <div className="p-4 rounded-lg bg-violet-500/10 border border-violet-500/20 space-y-2">
          <p className="text-xs text-violet-700">Demo Credentials:</p>
          <div className="space-y-1 text-xs font-mono">
            <div className="text-gray-400">
              Email: <span className="text-gray-700">guest@geosimulator.ai</span>
            </div>
            <div className="text-gray-400">
              Password: <span className="text-gray-700">guest123</span>
            </div>
          </div>
        </div>
      </div>

      {/* Sign Up Link */}
      <div className="text-center text-sm">
        <span className="text-gray-400">Don't have an account? </span>
        <button
          onClick={onSwitchToSignUp}
          className="text-violet-400 hover:text-violet-300 transition-colors"
        >
          Create an account
        </button>
      </div>
    </div>
  );
}