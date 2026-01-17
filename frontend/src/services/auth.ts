import api from './api';
import { AuthResponse, LoginRequest, RegisterRequest } from '@/types';

export const authService = {
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/login', credentials);
    
    // Store tokens
    if (response.data.token) {
      localStorage.setItem('auth_token', response.data.token);
    }
    if (response.data.refresh_token) {
      localStorage.setItem('refresh_token', response.data.refresh_token);
    }
    
    return response.data;
  },

  async register(userData: RegisterRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/register', userData);
    
    // Store tokens
    if (response.data.token) {
      localStorage.setItem('auth_token', response.data.token);
    }
    if (response.data.refresh_token) {
      localStorage.setItem('refresh_token', response.data.refresh_token);
    }
    
    return response.data;
  },

  async logout(): Promise<void> {
    try {
      await api.post('/auth/logout');
    } finally {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');
    }
  },

  async refreshToken(): Promise<{ token: string; expires_in: number }> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await api.post<{ token: string; expires_in: number }>(
      '/auth/refresh',
      { refresh_token: refreshToken }
    );

    if (response.data.token) {
      localStorage.setItem('auth_token', response.data.token);
    }

    return response.data;
  },

  getToken(): string | null {
    return localStorage.getItem('auth_token');
  },

  isAuthenticated(): boolean {
    return !!this.getToken();
  },
};
