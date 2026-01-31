/**
 * API Service Layer
 * 
 * Centralized API client with:
 * - Axios instance configuration
 * - Request/response interceptors
 * - Error handling
 * - Token management
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useUserStore } from '../store/userStore';
import { ApiError } from '../types';

// API Configuration
const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.1.125:8000/api/v1';
const API_TIMEOUT = 30000; // 30 seconds

/**
 * Create Axios instance
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request Interceptor
 * Adds authentication token to requests
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useUserStore.getState().accessToken;
    
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

/**
 * Response Interceptor
 * Handles common error scenarios
 */
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config;
    
    // Handle 401 Unauthorized (token expired)
    if (error.response?.status === 401 && originalRequest) {
      // Logout user
      useUserStore.getState().logout();
      // Redirect to login (handled by navigation guard)
    }
    
    // Handle 402 Payment Required (insufficient credits)
    if (error.response?.status === 402) {
      // Return structured error for UI handling
      const errData = error.response.data || {};
      return Promise.reject({
        ...errData,
        error: 'insufficient_credits',
        message: errData.message || 'Insufficient credits',
      });
    }
    
    // Handle 429 Rate Limit Exceeded
    if (error.response?.status === 429) {
      return Promise.reject({
        error: 'rate_limit_exceeded',
        message: error.response.data.message,
        retryAfter: error.response.headers['retry-after'] || 60,
      });
    }
    
    // Handle network errors
    if (!error.response) {
      return Promise.reject({
        error: 'network_error',
        message: 'Unable to connect to server. Please check your internet connection.',
      });
    }
    
    // Return API error
    return Promise.reject(error.response?.data || {
      error: 'unknown_error',
      message: 'An unexpected error occurred',
    });
  }
);

/**
 * API Helper Functions
 */

export const api = {
  // GET request
  get: async <T>(url: string, params?: any): Promise<T> => {
    const response = await apiClient.get<T>(url, { params });
    return response.data;
  },
  
  // POST request
  post: async <T>(url: string, data?: any): Promise<T> => {
    const response = await apiClient.post<T>(url, data);
    return response.data;
  },
  
  // PUT request
  put: async <T>(url: string, data?: any): Promise<T> => {
    const response = await apiClient.put<T>(url, data);
    return response.data;
  },
  
  // PATCH request
  patch: async <T>(url: string, data?: any): Promise<T> => {
    const response = await apiClient.patch<T>(url, data);
    return response.data;
  },
  
  // DELETE request
  delete: async <T>(url: string): Promise<T> => {
    const response = await apiClient.delete<T>(url);
    return response.data;
  },
};

/**
 * Mock API for development
 * Replace with real API calls in production
 */
export const mockApi = {
  enabled: false, // Set to false to use real API
  
  delay: (ms: number = 1000) => new Promise((resolve) => setTimeout(resolve, ms)),
  
  // Mock responses
  responses: {
    login: {
      user: {
        userId: 'mock-user-id',
        email: 'user@example.com',
        displayName: 'John Doe',
        subscriptionTier: 'free' as const,
        createdAt: new Date().toISOString(),
      },
      wallet: {
        totalCredits: 10,
        dailyFreeCredits: 10,
        purchedCredits: 0,
        bonusCredits: 0,
        dailyCreditsLimit: 10,
      },
      accessToken: 'mock-token',
    },
    
    characters: [
      {
        characterId: 'char-1',
        name: 'Sophia',
        avatarUrl: 'https://i.pravatar.cc/300?img=1',
        description: 'A sophisticated and intelligent companion who loves deep conversations.',
        personalityTraits: ['Intelligent', 'Empathetic', 'Sophisticated'],
        tierRequired: 'free' as const,
        isSpicy: false,
        tags: ['Conversation', 'Advice', 'Philosophy'],
      },
      {
        characterId: 'char-2',
        name: 'Isabella',
        avatarUrl: 'https://i.pravatar.cc/300?img=5',
        description: 'A playful and flirtatious companion with a seductive charm.',
        personalityTraits: ['Playful', 'Seductive', 'Confident'],
        tierRequired: 'premium' as const,
        isSpicy: true,
        tags: ['Flirty', 'Romantic', 'Spicy'],
      },
      {
        characterId: 'char-3',
        name: 'Victoria',
        avatarUrl: 'https://i.pravatar.cc/300?img=9',
        description: 'An elegant and mysterious companion who enjoys roleplay.',
        personalityTraits: ['Mysterious', 'Elegant', 'Creative'],
        tierRequired: 'vip' as const,
        isSpicy: true,
        tags: ['Roleplay', 'Fantasy', 'Exclusive'],
      },
    ],
    
    chatSession: {
      sessionId: 'session-123',
      characterId: 'char-1',
      characterName: 'Sophia',
      characterAvatar: 'https://i.pravatar.cc/300?img=1',
      title: 'Chat with Sophia',
      totalMessages: 0,
      totalCreditsSpent: 0,
      lastMessageAt: new Date().toISOString(),
      createdAt: new Date().toISOString(),
    },
    
    chatSessions: [
      {
        sessionId: 'session-123',
        characterId: 'char-1',
        characterName: 'Sophia',
        characterAvatar: 'https://i.pravatar.cc/300?img=1',
        title: 'Deep conversation about life...',
        totalMessages: 24,
        totalCreditsSpent: 3.6,
        lastMessageAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 min ago
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
      },
      {
        sessionId: 'session-456',
        characterId: 'char-2',
        characterName: 'Isabella',
        characterAvatar: 'https://i.pravatar.cc/300?img=5',
        title: 'Playful banter and flirting',
        totalMessages: 56,
        totalCreditsSpent: 8.4,
        lastMessageAt: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(), // 3 hours ago
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
      },
    ],
    
    chatResponse: {
      messageId: `msg-${Date.now()}`,
      role: 'assistant' as const,
      content: 'Hello! How can I help you today?',
      type: 'text' as const,
      tokensUsed: 15,
      creditsDeducted: 0.15,
      createdAt: new Date().toISOString(),
    },
  },
};

/**
 * Check if mock API should be used
 */
export const shouldUseMock = () => {
  return mockApi.enabled || !process.env.EXPO_PUBLIC_API_URL;
};
