/**
 * Interests Service - User interests/hobbies API
 */

import { api } from './api';

export interface InterestItem {
  id: number;
  name: string;
  displayName: string;
  icon?: string;
  category?: string;
}

export interface InterestListResponse {
  interests: InterestItem[];
  categories: string[];
}

export interface UserInterestsResponse {
  userId: string;
  interestIds: number[];
  interests: InterestItem[];
}

// Map backend response to frontend format
const mapInterest = (data: any): InterestItem => ({
  id: data.id,
  name: data.name,
  displayName: data.display_name || data.displayName,
  icon: data.icon,
  category: data.category,
});

const mapUserInterests = (data: any): UserInterestsResponse => ({
  userId: data.user_id || data.userId,
  interestIds: data.interest_ids || data.interestIds || [],
  interests: (data.interests || []).map(mapInterest),
});

export const interestsService = {
  /**
   * Get all available interests
   */
  getInterestList: async (): Promise<InterestListResponse> => {
    const data = await api.get<any>('/interests');
    return {
      interests: (data.interests || []).map(mapInterest),
      categories: data.categories || [],
    };
  },

  /**
   * Get current user's selected interests
   */
  getUserInterests: async (): Promise<UserInterestsResponse> => {
    const data = await api.get<any>('/interests/user');
    return mapUserInterests(data);
  },

  /**
   * Update user's selected interests
   */
  updateUserInterests: async (interestIds: number[]): Promise<UserInterestsResponse> => {
    const data = await api.put<any>('/interests/user', {
      interest_ids: interestIds,
    });
    return mapUserInterests(data);
  },

  /**
   * Toggle a single interest
   */
  toggleInterest: async (interestId: number, currentIds: number[]): Promise<UserInterestsResponse> => {
    const newIds = currentIds.includes(interestId)
      ? currentIds.filter(id => id !== interestId)
      : [...currentIds, interestId];
    return interestsService.updateUserInterests(newIds);
  },
};
