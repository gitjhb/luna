/**
 * Chat Service - NO MOCK, direct backend only
 */

import { api } from './api';
import { Message, ChatSession } from '../store/chatStore';

interface SendMessageRequest {
  sessionId: string;
  message: string;
  requestType?: 'text' | 'photo' | 'video' | 'voice';
  spicyMode?: boolean;
  intimacyLevel?: number;
}

// Debug info from L1 perception + game engine
export interface GameDebugInfo {
  check_passed: boolean;
  refusal_reason: string | null;
  emotion: string;
  intimacy: number;
  events: string[];
  new_event: string | null;
  intent: string;
}

export interface ExtraData {
  game?: GameDebugInfo;
  l1?: {
    safety_flag: string;
    intent: string;
    difficulty_rating: number;
    sentiment: number;
    is_nsfw: boolean;
  };
}

interface SendMessageResponse {
  messageId: string;
  role: 'assistant';
  content: string;
  type?: 'text' | 'image';
  isLocked?: boolean;
  contentRating?: 'safe' | 'flirty' | 'spicy' | 'explicit';
  unlockPrompt?: string;
  imageUrl?: string;
  tokensUsed: number;
  creditsDeducted: number;
  createdAt: string;
  extraData?: ExtraData;  // Debug info
}

// Map backend session to frontend format
const mapSession = (data: any): ChatSession => ({
  sessionId: data.session_id || data.sessionId,
  characterId: data.character_id || data.characterId,
  characterName: data.character_name || data.characterName || 'Unknown',
  characterAvatar: data.character_avatar || data.characterAvatar || 'https://i.pravatar.cc/100',
  characterBackground: data.character_background || data.characterBackground,
  title: data.title || 'New Chat',
  totalMessages: data.total_messages || data.totalMessages || 0,
  totalCreditsSpent: data.total_credits_spent || data.totalCreditsSpent || 0,
  lastMessageAt: data.updated_at || data.updatedAt || data.last_message_at || data.lastMessageAt || data.created_at || data.createdAt,
  createdAt: data.created_at || data.createdAt,
});

// Map backend message to frontend format
const mapMessage = (data: any): Message => ({
  messageId: data.message_id || data.messageId || data.id,
  role: data.role,
  content: data.content,
  type: data.type || 'text',
  isLocked: data.is_locked || data.isLocked || false,
  imageUrl: data.image_url || data.imageUrl,
  tokensUsed: data.tokens_used || data.tokensUsed,
  creditsDeducted: data.credits_deducted || data.creditsDeducted,
  createdAt: data.created_at || data.createdAt,
});

export const chatService = {
  /**
   * Get or create session for a character
   */
  getOrCreateSession: async (characterId: string): Promise<ChatSession> => {
    // Try to get existing session first
    try {
      const sessions = await api.get<any[]>('/chat/sessions', { character_id: characterId });
      if (sessions && sessions.length > 0) {
        return mapSession(sessions[0]);
      }
    } catch (e) {
      // No existing session, will create new one
    }
    
    // Create new session
    const data = await api.post<any>('/chat/sessions', { character_id: characterId });
    return mapSession(data);
  },
  
  /**
   * Create new chat session
   */
  createSession: async (characterId: string): Promise<ChatSession> => {
    const data = await api.post<any>('/chat/sessions', { character_id: characterId });
    return mapSession(data);
  },
  
  /**
   * Get user's chat sessions
   */
  getSessions: async (): Promise<ChatSession[]> => {
    const data = await api.get<any[]>('/chat/sessions');
    return data.map(mapSession);
  },
  
  /**
   * Get session history
   */
  getSessionHistory: async (sessionId: string): Promise<Message[]> => {
    const data = await api.get<any[]>(`/chat/sessions/${sessionId}/messages`);
    return data.map(mapMessage);
  },
  
  /**
   * Send message
   */
  sendMessage: async (data: SendMessageRequest): Promise<SendMessageResponse> => {
    const response = await api.post<any>('/chat/completions', {
      session_id: data.sessionId,
      message: data.message,
      request_type: data.requestType || 'text',
      spicy_mode: data.spicyMode || false,
      intimacy_level: data.intimacyLevel || 1,
    });
    
    return {
      messageId: response.message_id || response.messageId || `msg-${Date.now()}`,
      role: 'assistant',
      content: response.content || response.message,
      type: response.type || 'text',
      isLocked: response.is_locked || response.isLocked || false,
      contentRating: response.content_rating || response.contentRating || 'safe',
      unlockPrompt: response.unlock_prompt || response.unlockPrompt,
      imageUrl: response.image_url,
      tokensUsed: response.tokens_used || 0,
      creditsDeducted: response.credits_deducted || 0,
      createdAt: response.created_at || new Date().toISOString(),
      extraData: response.extra_data || response.extraData,
    };
  },
  
  /**
   * Delete session
   */
  deleteSession: async (sessionId: string): Promise<void> => {
    return api.delete<void>(`/chat/sessions/${sessionId}`);
  },
};
