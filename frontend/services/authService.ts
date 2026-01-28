/**
 * Authentication Service
 * 
 * Handles user authentication with Firebase tokens.
 */

import { api, mockApi, shouldUseMock } from './api';
import { User, Wallet } from '../store/userStore';

interface LoginResponse {
  user: User;
  wallet: Wallet;
  accessToken: string;
}

interface LoginRequest {
  provider: 'google' | 'apple';
  idToken: string;
}

export const authService = {
  /**
   * Login with Firebase token
   */
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    if (shouldUseMock()) {
      await mockApi.delay(1000);
      return mockApi.responses.login;
    }
    
    return api.post<LoginResponse>('/auth/login', data);
  },
  
  /**
   * Get current user profile
   */
  getProfile: async (): Promise<User> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      return mockApi.responses.login.user;
    }
    
    return api.get<User>('/auth/me');
  },
  
  /**
   * Refresh access token
   */
  refreshToken: async (): Promise<{ accessToken: string }> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      return { accessToken: 'mock-refreshed-token' };
    }
    
    return api.post<{ accessToken: string }>('/auth/refresh');
  },
};
