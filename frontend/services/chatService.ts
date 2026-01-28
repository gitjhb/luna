/**
 * Chat Service
 * 
 * Handles chat sessions and messages.
 */

import { api, mockApi, shouldUseMock } from './api';
import { Message, ChatSession } from '../store/chatStore';

interface CreateSessionRequest {
  characterId: string;
}

interface SendMessageRequest {
  sessionId: string;
  message: string;
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

export const chatService = {
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
    
    return api.post<ChatSession>('/chat/sessions', { characterId });
  },
  
  /**
   * Get user's chat sessions
   */
  getSessions: async (): Promise<ChatSession[]> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      return [mockApi.responses.chatSession];
    }
    
    return api.get<ChatSession[]>('/chat/sessions');
  },
  
  /**
   * Get session history
   */
  getSessionHistory: async (sessionId: string): Promise<Message[]> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      return [];
    }
    
    return api.get<Message[]>(`/chat/sessions/${sessionId}/messages`);
  },
  
  /**
   * Send message
   */
  sendMessage: async (data: SendMessageRequest): Promise<SendMessageResponse> => {
    if (shouldUseMock()) {
      await mockApi.delay(2000); // Simulate AI thinking
      return {
        ...mockApi.responses.chatResponse,
        content: `You said: "${data.message}". That's interesting! Tell me more.`,
      };
    }
    
    return api.post<SendMessageResponse>('/chat/completions', data);
  },
  
  /**
   * Unlock locked message
   */
  unlockMessage: async (sessionId: string, messageId: string): Promise<void> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      return;
    }
    
    return api.post<void>(`/chat/sessions/${sessionId}/messages/${messageId}/unlock`);
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
