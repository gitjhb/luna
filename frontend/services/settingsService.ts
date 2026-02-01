/**
 * Settings Service - User preferences API
 */

import { api } from './api';

export interface UserSettings {
  userId: string;
  nsfwEnabled: boolean;
  language: string;
  notificationsEnabled: boolean;
}

export interface UpdateSettingsRequest {
  nsfwEnabled?: boolean;
  language?: string;
  notificationsEnabled?: boolean;
}

// Map backend response to frontend format
const mapSettings = (data: any): UserSettings => ({
  userId: data.user_id || data.userId,
  nsfwEnabled: data.nsfw_enabled ?? data.nsfwEnabled ?? false,
  language: data.language || 'zh',
  notificationsEnabled: data.notifications_enabled ?? data.notificationsEnabled ?? true,
});

export const settingsService = {
  /**
   * Get current user settings
   */
  getSettings: async (): Promise<UserSettings> => {
    const data = await api.get<any>('/settings');
    return mapSettings(data);
  },

  /**
   * Update user settings
   */
  updateSettings: async (settings: UpdateSettingsRequest): Promise<UserSettings> => {
    const data = await api.patch<any>('/settings', {
      nsfw_enabled: settings.nsfwEnabled,
      language: settings.language,
      notifications_enabled: settings.notificationsEnabled,
    });
    return mapSettings(data);
  },

  /**
   * Toggle NSFW mode
   */
  toggleNsfw: async (enabled: boolean): Promise<UserSettings> => {
    return settingsService.updateSettings({ nsfwEnabled: enabled });
  },
};
