/**
 * Character Service
 * 
 * Handles character-related API calls.
 */

import { api, mockApi, shouldUseMock } from './api';
import { Character } from '../types';

export const characterService = {
  /**
   * Get all available characters
   */
  getCharacters: async (): Promise<Character[]> => {
    if (shouldUseMock()) {
      await mockApi.delay(800);
      return mockApi.responses.characters;
    }
    
    return api.get<Character[]>('/config/characters');
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
    
    return api.get<Character>(`/config/characters/${characterId}`);
  },
};
