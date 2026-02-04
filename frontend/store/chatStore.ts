/**
 * Chat Store (Zustand)
 * 
 * Manages chat sessions, messages, and spicy mode state.
 * Persisted to AsyncStorage for offline access.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Power 计算明细
export interface PowerBreakdown {
  intimacy: number;    // Intimacy × 0.5
  emotion: number;     // Emotion × 0.5
  chaos: number;       // Chaos 值
  pure: number;        // Pure 值
  buff: number;        // 环境加成
  effect: number;      // 道具效果 (Tier 2 礼物)
}

// Debug info from L1 perception + game engine
export interface GameDebugInfo {
  check_passed: boolean;
  refusal_reason: string | null;
  emotion: number;
  emotion_before?: number;
  emotion_delta?: number;
  emotion_state?: string;
  emotion_locked?: boolean;
  intimacy: number;        // intimacy_x (0-100 mapped value)
  level?: number;          // display level (1-50)
  events: string[];
  new_event: string | null;
  intent: string;
  // v3.0 新增
  power?: number;
  stage?: string;
  archetype?: string;
  adjusted_difficulty?: number;
  difficulty_modifier?: number;
  is_nsfw?: boolean;
  power_breakdown?: PowerBreakdown;
}

// 激活的道具效果
export interface ActiveEffect {
  type: string;
  name: string;
  icon: string;
  color: string;
  remaining: number;  // 剩余消息数
}

// 约会状态
export interface DateInfo {
  is_active: boolean;
  scenario_name?: string;
  scenario_icon?: string;
  message_count?: number;
  required_messages?: number;
  status?: string;
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
  active_effects?: ActiveEffect[];  // Tier 2 礼物激活效果
  date?: DateInfo;  // 约会状态
}

export interface Message {
  messageId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  type?: 'text' | 'image' | 'gift' | 'video';  // video = 视频消息
  isLocked?: boolean;      // For locked/blurred content
  contentRating?: 'safe' | 'flirty' | 'spicy' | 'explicit';
  unlockPrompt?: string;
  imageUrl?: string;
  videoUrl?: string;       // 视频 URL 或本地资源 ID
  videoThumbnail?: string; // 视频封面图
  tokensUsed?: number;
  creditsDeducted?: number;
  createdAt: string;
  extraData?: ExtraData;   // Debug info from backend
  reaction?: string;       // User's emoji reaction to this message
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
  deleteSessionByCharacterId: (characterId: string) => void;
  
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
  
  deleteSessionByCharacterId: (characterId) => {
    const session = get().sessions.find((s) => s.characterId === characterId);
    if (session) {
      set({
        sessions: get().sessions.filter((s) => s.characterId !== characterId),
      });
      
      // Clear messages for deleted session
      const { [session.sessionId]: _, ...rest } = get().messagesBySession;
      set({
        messagesBySession: rest,
      });
    }
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
