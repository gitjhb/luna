/**
 * Character Service
 * 
 * Handles character-related API calls.
 */

import { api, mockApi, shouldUseMock } from './api';
import { Character } from '../types';

// Convert snake_case to camelCase
const snakeToCamel = (obj: any): any => {
  if (Array.isArray(obj)) {
    return obj.map(snakeToCamel);
  }
  if (obj !== null && typeof obj === 'object') {
    return Object.keys(obj).reduce((acc, key) => {
      const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
      acc[camelKey] = snakeToCamel(obj[key]);
      return acc;
    }, {} as any);
  }
  return obj;
};

// Map backend character to frontend Character type
const mapCharacter = (data: any): Character => ({
  characterId: data.character_id || data.characterId,
  name: data.name,
  avatarUrl: data.avatar_url || data.avatarUrl || 'https://i.pravatar.cc/300',
  backgroundUrl: data.background_url || data.backgroundUrl,
  description: data.description,
  personalityTraits: data.personality_traits || data.personalityTraits || [],
  tierRequired: data.tier_required || data.tierRequired || 'free',
  isSpicy: data.is_spicy || data.isSpicy || false,
  tags: data.tags || data.personality_traits || data.personalityTraits || [],
});

export const characterService = {
  /**
   * Get all available characters
   */
  getCharacters: async (): Promise<Character[]> => {
    if (shouldUseMock()) {
      await mockApi.delay(800);
      return mockApi.responses.characters;
    }
    
    const response = await api.get<{ characters: any[]; total: number }>('/characters');
    return response.characters.map(mapCharacter);
  },
  
  /**
   * Get character by ID
   */
  getCharacter: async (characterId: string): Promise<Character> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      const character = mockApi.responses.characters.find(
        (c) => c.characterId === characterId
      );
      if (!character) {
        throw new Error('Character not found');
      }
      return character;
    }
    
    const data = await api.get<any>(`/characters/${characterId}`);
    return mapCharacter(data);
  },
};
