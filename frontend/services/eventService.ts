/**
 * Event Story Service
 * 
 * API calls for event memories and story generation
 */

import { api } from './api';

// Event types that support story generation
export const STORY_EVENT_TYPES = [
  'first_date',
  'first_confession', 
  'first_kiss',
  'first_nsfw',
  'anniversary',
  'reconciliation',
] as const;

export type StoryEventType = typeof STORY_EVENT_TYPES[number];

// Event type info for display
export const EVENT_TYPE_INFO: Record<string, { name_cn: string; icon: string; description: string }> = {
  first_chat: { name_cn: '初次相遇', icon: '👋', description: '你们的第一次对话' },
  first_compliment: { name_cn: '第一次夸赞', icon: '😊', description: '第一次收到夸奖' },
  first_gift: { name_cn: '第一份礼物', icon: '🎁', description: '收到第一份礼物' },
  first_date: { name_cn: '第一次约会', icon: '💕', description: '浪漫的第一次约会' },
  first_kiss: { name_cn: '初吻', icon: '💋', description: '难忘的初吻时刻' },
  first_confession: { name_cn: '表白', icon: '💝', description: '心跳加速的表白' },
  first_nsfw: { name_cn: '亲密时刻', icon: '🔥', description: '最亲密的时刻' },
  anniversary: { name_cn: '纪念日', icon: '🎂', description: '值得庆祝的日子' },
  reconciliation: { name_cn: '和好', icon: '🤗', description: '冷战后的和解' },
};

// Event memory from backend
export interface EventMemory {
  id: string;
  user_id: string;
  character_id: string;
  event_type: string;
  story_content: string;
  context_summary?: string;
  intimacy_level?: string;
  emotion_state?: string;
  generated_at?: string;
}

// Event story placeholder in chat
export interface EventStoryPlaceholder {
  type: 'event_story';
  event_type: string;
  character_id: string;
  status: 'pending' | 'generated';
  story_id?: string;
}

// Story generation response
export interface StoryGenerationResponse {
  success: boolean;
  event_type: string;
  story_content?: string;
  event_memory_id?: string;
  error?: string;
}

export const eventService = {
  /**
   * Get all event memories for a character
   */
  getEventMemories: async (characterId: string): Promise<EventMemory[]> => {
    try {
      const response = await api.get<{ success: boolean; count: number; memories: EventMemory[] }>(
        `/events/me/${characterId}`
      );
      return response.memories || [];
    } catch (error) {
      console.error('Failed to get event memories:', error);
      return [];
    }
  },
  
  /**
   * Get a specific event memory
   */
  getEventMemory: async (characterId: string, eventType: string): Promise<EventMemory | null> => {
    try {
      const response = await api.get<EventMemory>(
        `/events/me/${characterId}/${eventType}`
      );
      return response;
    } catch (error) {
      // 404 is expected if memory doesn't exist
      return null;
    }
  },
  
  /**
   * Generate story for an event
   */
  generateStory: async (
    characterId: string, 
    eventType: string,
    chatHistory: { role: string; content: string }[] = [],
    memoryContext: string = '',
    relationshipState?: Record<string, any>
  ): Promise<StoryGenerationResponse> => {
    try {
      const response = await api.post<StoryGenerationResponse>(
        `/events/me/${characterId}/generate`,
        {
          event_type: eventType,
          chat_history: chatHistory,
          memory_context: memoryContext,
          relationship_state: relationshipState,
        }
      );
      return response;
    } catch (error: any) {
      console.error('Failed to generate story:', error);
      return {
        success: false,
        event_type: eventType,
        error: error.message || 'Failed to generate story',
      };
    }
  },
  
  /**
   * Check if an event type supports story generation
   */
  isStoryEvent: (eventType: string): boolean => {
    return STORY_EVENT_TYPES.includes(eventType as StoryEventType);
  },
  
  /**
   * Get event type display info
   */
  getEventInfo: (eventType: string) => {
    return EVENT_TYPE_INFO[eventType] || { 
      name_cn: eventType, 
      icon: '📖', 
      description: '特别的时刻' 
    };
  },
  
  /**
   * Parse event story placeholder from message content
   */
  parseEventStoryPlaceholder: (content: string): EventStoryPlaceholder | null => {
    try {
      const parsed = JSON.parse(content);
      if (parsed.type === 'event_story') {
        return parsed as EventStoryPlaceholder;
      }
    } catch {
      // Not a JSON message
    }
    return null;
  },
  
  /**
   * Check if message content is an event story placeholder
   */
  isEventStoryMessage: (content: string): boolean => {
    return eventService.parseEventStoryPlaceholder(content) !== null;
  },
};
