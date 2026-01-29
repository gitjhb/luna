/**
 * Chat Service
 * 
 * Handles chat sessions and messages.
 */

import { api, mockApi, shouldUseMock } from './api';
import { Message, ChatSession } from '../store/chatStore';

interface SendMessageRequest {
  sessionId: string;
  message: string;
  requestType?: 'text' | 'photo' | 'video' | 'voice';
}

interface SendMessageResponse {
  messageId: string;
  role: 'assistant';
  content: string;
  type?: 'text' | 'image';
  isLocked?: boolean;
  imageUrl?: string;
  tokensUsed: number;
  creditsDeducted: number;
  createdAt: string;
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
  lastMessageAt: data.last_message_at || data.lastMessageAt || data.created_at || data.createdAt,
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
   * Returns existing session if one exists, creates new one if not
   */
  getOrCreateSession: async (characterId: string): Promise<ChatSession> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      return {
        ...mockApi.responses.chatSession,
        characterId,
      };
    }
    
    // Try to get existing session first
    try {
      const sessions = await api.get<any[]>('/chat/sessions', { character_id: characterId });
      if (sessions && sessions.length > 0) {
        return mapSession(sessions[0]);
      }
    } catch (e) {
      // No existing session, create new one
    }
    
    // Create new session
    const data = await api.post<any>('/chat/sessions', { character_id: characterId });
    return mapSession(data);
  },
  
  /**
   * Create new chat session
   */
  createSession: async (characterId: string): Promise<ChatSession> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      return {
        ...mockApi.responses.chatSession,
        characterId,
      };
    }
    
    const data = await api.post<any>('/chat/sessions', { character_id: characterId });
    return mapSession(data);
  },
  
  /**
   * Get user's chat sessions
   */
  getSessions: async (): Promise<ChatSession[]> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      return mockApi.responses.chatSessions || [mockApi.responses.chatSession];
    }
    
    const data = await api.get<any[]>('/chat/sessions');
    return data.map(mapSession);
  },
  
  /**
   * Get session history
   */
  getSessionHistory: async (sessionId: string): Promise<Message[]> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      return [];
    }
    
    const data = await api.get<any[]>(`/chat/sessions/${sessionId}/messages`);
    return data.map(mapMessage);
  },
  
  /**
   * Send message
   */
  sendMessage: async (data: SendMessageRequest): Promise<SendMessageResponse> => {
    if (shouldUseMock()) {
      await mockApi.delay(2000);
      return {
        ...mockApi.responses.chatResponse,
        content: `You said: "${data.message}". That's interesting! Tell me more.`,
      };
    }
    
    const response = await api.post<any>('/chat/completions', {
      session_id: data.sessionId,
      message: data.message,
      request_type: data.requestType || 'text',
    });
    
    return {
      messageId: response.message_id || response.messageId || `msg-${Date.now()}`,
      role: 'assistant',
      content: response.content || response.message,
      type: response.type || 'text',
      isLocked: response.is_locked || false,
      imageUrl: response.image_url,
      tokensUsed: response.tokens_used || 0,
      creditsDeducted: response.credits_deducted || 0,
      createdAt: response.created_at || new Date().toISOString(),
    };
  },
  
  /**
   * Delete session
   */
  deleteSession: async (sessionId: string): Promise<void> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      return;
    }
    
    return api.delete<void>(`/chat/sessions/${sessionId}`);
  },
};
