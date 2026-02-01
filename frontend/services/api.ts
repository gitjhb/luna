/**
 * API Service Layer
 * 
 * Centralized API client - NO MOCK, direct backend only
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useUserStore } from '../store/userStore';
import { ApiError } from '../types';

// API Configuration - MUST be set in .env
const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.1.125:8000/api/v1';
const API_TIMEOUT = 30000;

console.log('[API] Base URL:', API_BASE_URL);

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
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useUserStore.getState().accessToken;
    
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    console.log('[API] Request:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

/**
 * Response Interceptor
 */
apiClient.interceptors.response.use(
  (response) => {
    console.log('[API] Response:', response.status, response.config.url);
    return response;
  },
  async (error: AxiosError<ApiError>) => {
    console.error('[API] Error:', error.message, error.config?.url);
    
    const originalRequest = error.config;
    
    // Handle 401 Unauthorized
    if (error.response?.status === 401 && originalRequest) {
      useUserStore.getState().logout();
    }
    
    // Handle 402 Payment Required
    if (error.response?.status === 402) {
      const errData = error.response.data || {};
      return Promise.reject({
        ...errData,
        error: 'insufficient_credits',
        message: errData.message || 'Insufficient credits',
      });
    }
    
    // Handle 429 Rate Limit
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
        message: 'Unable to connect to server: ' + API_BASE_URL,
      });
    }
    
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
  get: async <T>(url: string, params?: any): Promise<T> => {
    const response = await apiClient.get<T>(url, { params });
    return response.data;
  },
  
  post: async <T>(url: string, data?: any): Promise<T> => {
    const response = await apiClient.post<T>(url, data);
    return response.data;
  },
  
  put: async <T>(url: string, data?: any): Promise<T> => {
    const response = await apiClient.put<T>(url, data);
    return response.data;
  },
  
  patch: async <T>(url: string, data?: any): Promise<T> => {
    const response = await apiClient.patch<T>(url, data);
    return response.data;
  },
  
  delete: async <T>(url: string): Promise<T> => {
    const response = await apiClient.delete<T>(url);
    return response.data;
  },
};
