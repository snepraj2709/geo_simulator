import { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { handleUrlSubmit } from '../lib/url-utils';

interface UrlInputFormProps {
  onSubmit: (url: string) => void;
  buttonText: string;
  placeholder?: string;
  subtext?: React.ReactNode;
  className?: string;
  buttonClassName?: string;
}

export function UrlInputForm({ 
  onSubmit, 
  buttonText, 
  placeholder = "Enter your website URL (e.g., acme.com)",
  subtext,
  className = "",
  buttonClassName = ""
}: UrlInputFormProps) {
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    handleUrlSubmit(e, url, setError, onSubmit);
  };

  return (
    <form onSubmit={handleSubmit} className={`max-w-xl mx-auto ${className}`}>
      <div className="flex flex-col sm:flex-row gap-3">
        <Input
          type="text"
          placeholder={placeholder}
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            setError('');
          }}
          className="flex-1 h-14 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-violet-500/50 focus:ring-violet-500/20"
          required
        />
        <Button 
          type="submit"
          className={`h-14 px-8 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 text-white shadow-lg shadow-violet-500/25 whitespace-nowrap ${buttonClassName}`}
        >
          {buttonText}
        </Button>
      </div>
      {error && (
        <p className="text-red-400 text-sm mt-2 text-left">{error}</p>
      )}
      {subtext && (
        <div className="text-xs text-gray-400 mt-3">{subtext}</div>
      )}
    </form>
  );
}
