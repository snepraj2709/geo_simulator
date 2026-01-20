import React from 'react';

export const normalizeUrl = (input: string): string => {
  let normalized = input.trim();
  
  // Remove protocol if present
  normalized = normalized.replace(/^(https?:\/\/)?(www\.)?/, '');
  
  // Remove trailing slashes
  normalized = normalized.replace(/\/+$/, '');
  
  return normalized;
};

export const isValidDomain = (domain: string): boolean => {
  // Basic domain validation: at least one dot and valid characters
  const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-_.]*\.[a-zA-Z]{2,}$/;
  return domainRegex.test(domain);
};

export const handleUrlSubmit = (
  e: React.FormEvent,
  url: string,
  setError: (error: string) => void,
  onSuccess: (normalizedUrl: string) => void
) => {
  e.preventDefault();
  setError('');
  
  const normalized = normalizeUrl(url);
  
  if (!normalized) {
    setError('Please enter a website URL');
    return;
  }
  
  if (!isValidDomain(normalized)) {
    setError('Please enter a valid domain (e.g., example.com)');
    return;
  }
  
  onSuccess(normalized);
};
