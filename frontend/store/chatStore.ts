/**
 * Chat Store (Zustand)
 * 
 * Manages chat sessions, messages, and spicy mode state.
 * Persisted to AsyncStorage for offline access.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface Message {
  messageId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  type?: 'text' | 'image';
  isLocked?: boolean;      // For locked/blurred content
  imageUrl?: string;
  tokensUsed?: number;
  creditsDeducted?: number;
  createdAt: string;
}

export interface ChatSession {
  sessionId: string;
  characterId: string;
  characterName: string;
  characterAvatar: string;
  title: string;
  totalMessages: number;
  totalCreditsSpent: number;
  lastMessageAt: string;
  createdAt: string;
}

interface ChatState {
  // Active session
  activeSessionId: string | null;
  activeCharacterId: string | null;
  
  // Messages by session
  messagesBySession: Record<string, Message[]>;
  
  // Sessions list
  sessions: ChatSession[];
  
  // Spicy mode
  isSpicyMode: boolean;
  
  // UI state
  isTyping: boolean;
  typingCharacterId: string | null;
  
  // Actions
  setActiveSession: (sessionId: string, characterId: string) => void;
  addMessage: (sessionId: string, message: Message) => void;
  addMessages: (sessionId: string, messages: Message[]) => void;
  setMessages: (sessionId: string, messages: Message[]) => void;
  clearMessages: (sessionId: string) => void;
  
  setSessions: (sessions: ChatSession[]) => void;
  addSession: (session: ChatSession) => void;
  updateSession: (sessionId: string, updates: Partial<ChatSession>) => void;
  deleteSession: (sessionId: string) => void;
  
  toggleSpicyMode: () => void;
  setSpicyMode: (enabled: boolean) => void;
  
  setTyping: (isTyping: boolean, characterId?: string) => void;
  
  unlockMessage: (sessionId: string, messageId: string) => void;
  
  // Find session by character ID
  getSessionByCharacterId: (characterId: string) => ChatSession | undefined;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
  // Initial state
  activeSessionId: null,
  activeCharacterId: null,
  messagesBySession: {},
  sessions: [],
  isSpicyMode: false,
  isTyping: false,
  typingCharacterId: null,
  
  // Actions
  setActiveSession: (sessionId, characterId) => {
    set({
      activeSessionId: sessionId,
      activeCharacterId: characterId,
    });
  },
  
  addMessage: (sessionId, message) => {
    const currentMessages = get().messagesBySession[sessionId] || [];
    set({
      messagesBySession: {
        ...get().messagesBySession,
        [sessionId]: [...currentMessages, message],
      },
    });
  },
  
  addMessages: (sessionId, messages) => {
    const currentMessages = get().messagesBySession[sessionId] || [];
    set({
      messagesBySession: {
        ...get().messagesBySession,
        [sessionId]: [...currentMessages, ...messages],
      },
    });
  },
  
  setMessages: (sessionId, messages) => {
    set({
      messagesBySession: {
        ...get().messagesBySession,
        [sessionId]: messages,
      },
    });
  },
  
  clearMessages: (sessionId) => {
    const { [sessionId]: _, ...rest } = get().messagesBySession;
    set({
      messagesBySession: rest,
    });
  },
  
  setSessions: (sessions) => {
    set({ sessions });
  },
  
  addSession: (session) => {
    set({
      sessions: [session, ...get().sessions],
    });
  },
  
  updateSession: (sessionId, updates) => {
    set({
      sessions: get().sessions.map((s) =>
        s.sessionId === sessionId ? { ...s, ...updates } : s
      ),
    });
  },
  
  deleteSession: (sessionId) => {
    set({
      sessions: get().sessions.filter((s) => s.sessionId !== sessionId),
    });
    
    // Clear messages for deleted session
    const { [sessionId]: _, ...rest } = get().messagesBySession;
    set({
      messagesBySession: rest,
    });
  },
  
  toggleSpicyMode: () => {
    set({ isSpicyMode: !get().isSpicyMode });
  },
  
  setSpicyMode: (enabled) => {
    set({ isSpicyMode: enabled });
  },
  
  setTyping: (isTyping, characterId) => {
    set({
      isTyping,
      typingCharacterId: characterId || null,
    });
  },
  
  unlockMessage: (sessionId, messageId) => {
    const messages = get().messagesBySession[sessionId];
    if (messages) {
      set({
        messagesBySession: {
          ...get().messagesBySession,
          [sessionId]: messages.map((msg) =>
            msg.messageId === messageId
              ? { ...msg, isLocked: false }
              : msg
          ),
        },
      });
    }
  },
  
  getSessionByCharacterId: (characterId) => {
    return get().sessions.find((s) => s.characterId === characterId);
  },
}),
    {
      name: 'chat-storage',
      storage: createJSONStorage(() => AsyncStorage),
      // Only persist sessions and messages, not UI state
      partialize: (state) => ({
        sessions: state.sessions,
        messagesBySession: state.messagesBySession,
      }),
    }
  )
);

/**
 * Selectors
 */
export const selectActiveMessages = (state: ChatState) => {
  const sessionId = state.activeSessionId;
  return sessionId ? state.messagesBySession[sessionId] || [] : [];
};

export const selectSessionByCharacterId = (characterId: string) => (state: ChatState) => {
  return state.sessions.find((s) => s.characterId === characterId);
};

export const selectIsSpicyMode = (state: ChatState) => state.isSpicyMode;
export const selectIsTyping = (state: ChatState) => state.isTyping;
