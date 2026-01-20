import { useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import type { User } from '../../App';

interface SignUpFormProps {
  onLogin: (user: User) => void;
  onSwitchToLogin: () => void;
}

export function SignUpForm({ onLogin, onSwitchToLogin }: SignUpFormProps) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onLogin({ name, email });
  };

  const handleGoogleSignUp = () => {
    onLogin({
      name: 'Demo User',
      email: 'demo@geosimulator.ai',
    });
  };

  return (
    <div className="space-y-5 bg-gradient-to-br from-violet-50/90 to-blue-50/90 border border-white/50 backdrop-blur-xl shadow-xl rounded-xl py-8">
      {/* Logo/Header */}
      <div className="text-center">
        <h1 className="text-3xl text-black">Create your account</h1>
        <p className="text-gray-700">Start optimizing for AI visibility today</p>
      </div>

      {/* Sign Up Form */}
      <div className="pt-8 px-8 space-y-4">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name" className="text-gray-700">Full Name</Label>
            <Input
              id="name"
              type="text"
              placeholder="Enter your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="bg-white/50 border-gray-200 text-gray-900 placeholder:text-gray-500 focus:bg-white transition-all"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email" className="text-gray-700">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="bg-white/50 border-gray-200 text-gray-900 placeholder:text-gray-500 focus:bg-white transition-all"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-gray-700">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="Create a password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="bg-white/50 border-gray-200 text-gray-900 placeholder:text-gray-500 focus:bg-white transition-all"
              required
            />
          </div>

          <Button 
            type="submit"
            variant="gradient" size="lg" className="w-full"
          >
            Create account
          </Button>
        </form>

        <div className="pt-10 space-y-2">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-transparent text-gray-500 text-xs uppercase tracking-wider font-medium">Or sign up with</span>
            </div>
          </div>

          <Button
            type="button"
            variant="outline"
            onClick={handleGoogleSignUp}
            className="w-full h-11 bg-white text-gray-700 border-gray-200 hover:bg-gray-50 hover:text-gray-900 hover:border-gray-300 transition-all duration-200"
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
              <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Sign up with Google
          </Button>
        </div>

        {/* Login Link */}
        <div className="text-center text-sm">
          <span className="text-gray-400">Already have an account? </span>
          <button
            onClick={onSwitchToLogin}
            className="text-violet-400 hover:text-violet-500 transition-colors"
          >
            Sign in
          </button>
        </div>
      </div>
    </div>
  );
}