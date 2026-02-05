/**
 * Character Service - NO MOCK, direct backend only
 */

import { api } from './api';
import { Character } from '../types';

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
  isRomanceable: data.is_romanceable ?? data.isRomanceable ?? true,
  characterType: data.character_type || data.characterType || 'romantic',
  tags: data.tags || data.personality_traits || data.personalityTraits || [],
  greeting: data.greeting,
  // Extended profile fields
  age: data.age,
  zodiac: data.zodiac,
  occupation: data.occupation,
  hobbies: data.hobbies || [],
  mbti: data.mbti,
  birthday: data.birthday,
  height: data.height,
  location: data.location,
});

export const characterService = {
  /**
   * Get all available characters
   */
  getCharacters: async (): Promise<Character[]> => {
    const response = await api.get<{ characters: any[]; total: number }>('/characters');
    return response.characters.map(mapCharacter);
  },
  
  /**
   * Get character by ID
   */
  getCharacter: async (characterId: string): Promise<Character> => {
    const data = await api.get<any>(`/characters/${characterId}`);
    return mapCharacter(data);
  },
};
