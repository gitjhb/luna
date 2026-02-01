/**
 * Backend Connection Status Hook
 * 
 * Checks if the backend is reachable and provides status for UI indicators.
 */

import { useState, useEffect } from 'react';
import axios from 'axios';

// Health endpoint is at root, not under /api/v1
const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.1.125:8000/api/v1';
const HEALTH_URL = API_BASE_URL.replace('/api/v1', '') + '/health';

interface BackendStatus {
  isConnected: boolean;
  lastChecked: Date | null;
  error: string | null;
}

let globalStatus: BackendStatus = {
  isConnected: false,
  lastChecked: null,
  error: null,
};

let listeners: Set<() => void> = new Set();

const notifyListeners = () => {
  listeners.forEach(listener => listener());
};

/**
 * Check backend health
 */
export const checkBackendHealth = async (): Promise<boolean> => {
  console.log('[Backend] Checking health at:', HEALTH_URL);
  try {
    const response = await axios.get(HEALTH_URL, { timeout: 5000 });
    console.log('[Backend] Health check passed:', response.data);
    globalStatus = {
      isConnected: true,
      lastChecked: new Date(),
      error: null,
    };
    notifyListeners();
    return true;
  } catch (error: any) {
    console.error('[Backend] Health check failed:', error.message);
    globalStatus = {
      isConnected: false,
      lastChecked: new Date(),
      error: error.message || 'Backend unreachable',
    };
    notifyListeners();
    return false;
  }
};

/**
 * Hook to get backend status
 */
export const useBackendStatus = () => {
  const [status, setStatus] = useState<BackendStatus>(globalStatus);

  useEffect(() => {
    const listener = () => setStatus({ ...globalStatus });
    listeners.add(listener);

    // Check on mount if not checked recently
    if (!globalStatus.lastChecked || 
        Date.now() - globalStatus.lastChecked.getTime() > 30000) {
      checkBackendHealth();
    }

    return () => {
      listeners.delete(listener);
    };
  }, []);

  return {
    ...status,
    refresh: checkBackendHealth,
  };
};

/**
 * Get current status synchronously
 */
export const getBackendStatus = () => globalStatus;
