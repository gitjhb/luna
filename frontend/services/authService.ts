/**
 * Authentication Service - NO MOCK, direct backend only
 */

import { api } from './api';
import { User, Wallet } from '../store/userStore';

interface LoginResponse {
  user: User;
  wallet: Wallet;
  accessToken: string;
}

interface LoginRequest {
  provider: 'google' | 'apple' | 'guest';
  idToken?: string;
}

export const authService = {
  /**
   * Login - guest mode for now (TODO: implement Firebase auth)
   */
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    // Use guest login endpoint
    const response = await api.post<any>('/auth/guest');
    
    return {
      user: {
        userId: response.user_id,
        email: 'guest@luna.app',
        displayName: 'Guest',
        subscriptionTier: response.subscription_tier || 'free',
        createdAt: new Date().toISOString(),
      },
      wallet: {
        totalCredits: response.wallet?.total_credits || 100,
        dailyFreeCredits: response.wallet?.daily_free_credits || 10,
        purchedCredits: response.wallet?.purchased_credits || 0,
        bonusCredits: response.wallet?.bonus_credits || 0,
        dailyCreditsLimit: response.wallet?.daily_credits_limit || 50,
      },
      accessToken: response.access_token,
    };
  },
  
  /**
   * Get current user profile
   */
  getProfile: async (): Promise<User> => {
    const response = await api.get<any>('/auth/me');
    return {
      userId: response.user_id,
      email: response.email || 'guest@luna.app',
      displayName: response.display_name || 'Guest',
      subscriptionTier: response.subscription_tier || 'free',
      createdAt: response.created_at || new Date().toISOString(),
    };
  },
  
  /**
   * Refresh access token
   */
  refreshToken: async (): Promise<{ accessToken: string }> => {
    const response = await api.post<any>('/auth/refresh');
    return { accessToken: response.access_token };
  },
};
