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
  characterBackground?: string;
  title: string;
  totalMessages: number;
  totalCreditsSpent: number;
  lastMessageAt: string;
  createdAt: string;
}

export interface IntimacyCache {
  currentLevel: number;
  xpProgressInLevel: number;
  xpForNextLevel: number;
  xpForCurrentLevel: number;
  updatedAt: string;
}

interface ChatState {
  // Active session
  activeSessionId: string | null;
  activeCharacterId: string | null;
  
  // Messages by session
  messagesBySession: Record<string, Message[]>;
  
  // Sessions list
  sessions: ChatSession[];
  
  // Intimacy cache by characterId
  intimacyByCharacter: Record<string, IntimacyCache>;
  
  // Hydration status
  _hasHydrated: boolean;
  
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
  
  // Intimacy cache actions
  setIntimacy: (characterId: string, intimacy: Omit<IntimacyCache, 'updatedAt'>) => void;
  getIntimacy: (characterId: string) => IntimacyCache | undefined;
  
  // Hydration
  setHasHydrated: (state: boolean) => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
  // Initial state
  activeSessionId: null,
  activeCharacterId: null,
  messagesBySession: {},
  sessions: [],
  intimacyByCharacter: {},
  _hasHydrated: false,
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
    // Deduplicate by sessionId (keep first occurrence)
    const seen = new Set<string>();
    const uniqueSessions = sessions.filter((s) => {
      if (seen.has(s.sessionId)) return false;
      seen.add(s.sessionId);
      return true;
    });
    set({ sessions: uniqueSessions });
  },
  
  addSession: (session) => {
    // Don't add if session already exists
    const existing = get().sessions.find((s) => s.sessionId === session.sessionId);
    if (existing) return;
    
    // Also check by characterId - only one session per character
    const existingByChar = get().sessions.find((s) => s.characterId === session.characterId);
    if (existingByChar) {
      // Update existing instead of adding new
      set({
        sessions: get().sessions.map((s) =>
          s.characterId === session.characterId ? { ...s, ...session } : s
        ),
      });
      return;
    }
    
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
  
  setIntimacy: (characterId, intimacy) => {
    set({
      intimacyByCharacter: {
        ...get().intimacyByCharacter,
        [characterId]: {
          ...intimacy,
          updatedAt: new Date().toISOString(),
        },
      },
    });
  },
  
  getIntimacy: (characterId) => {
    return get().intimacyByCharacter[characterId];
  },
  
  setHasHydrated: (state) => {
    set({ _hasHydrated: state });
  },
}),
    {
      name: 'chat-storage',
      storage: createJSONStorage(() => AsyncStorage),
      // Only persist sessions, messages, and intimacy - not UI state
      partialize: (state) => ({
        sessions: state.sessions,
        messagesBySession: state.messagesBySession,
        intimacyByCharacter: state.intimacyByCharacter,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
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
