/**
 * useChatDatabase Hook
 * 
 * React hook for chat database operations.
 * Provides a clean interface to SQLite repositories.
 */

import { useState, useEffect, useCallback } from 'react';
import { initDatabase } from '../services/database';
import { 
  MessageRepository, 
  SessionRepository,
  Message,
  ChatSession,
} from '../services/database/repositories';
import { migrateToSQLite, needsMigration } from '../services/database/migration';

// ============================================================================
// Types
// ============================================================================

interface UseChatDatabaseReturn {
  // State
  isReady: boolean;
  isLoading: boolean;
  error: string | null;

  // Sessions
  sessions: ChatSession[];
  loadSessions: () => Promise<void>;
  createSession: (characterId: string, characterName: string, characterAvatar?: string) => Promise<ChatSession>;
  getSessionByCharacterId: (characterId: string) => Promise<ChatSession | null>;
  deleteSession: (sessionId: string) => Promise<void>;

  // Messages
  loadMessages: (sessionId: string, options?: { limit?: number; offset?: number }) => Promise<Message[]>;
  addMessage: (sessionId: string, message: Omit<Message, 'session_id'>) => Promise<Message>;
  addMessages: (sessionId: string, messages: Omit<Message, 'session_id'>[]) => Promise<void>;
  getMessageCount: (sessionId: string) => Promise<number>;
  searchMessages: (query: string, sessionId?: string) => Promise<Message[]>;
  unlockMessage: (messageId: string) => Promise<void>;
  clearMessages: (sessionId: string) => Promise<void>;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useChatDatabase(): UseChatDatabaseReturn {
  const [isReady, setIsReady] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  // Initialize database
  useEffect(() => {
    let mounted = true;

    const init = async () => {
      try {
        // Initialize SQLite
        await initDatabase();

        // Run migration if needed
        if (await needsMigration()) {
          console.log('[useChatDatabase] Running migration...');
          const result = await migrateToSQLite();
          if (!result.success) {
            console.error('[useChatDatabase] Migration failed:', result.error);
          }
        }

        // Load initial sessions
        const allSessions = await SessionRepository.getAll();
        
        if (mounted) {
          setSessions(allSessions);
          setIsReady(true);
          setIsLoading(false);
        }
      } catch (err) {
        console.error('[useChatDatabase] Init failed:', err);
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Database init failed');
          setIsLoading(false);
        }
      }
    };

    init();

    return () => {
      mounted = false;
    };
  }, []);

  // Load sessions
  const loadSessions = useCallback(async () => {
    const allSessions = await SessionRepository.getAll();
    setSessions(allSessions);
  }, []);

  // Create session
  const createSession = useCallback(async (
    characterId: string,
    characterName: string,
    characterAvatar?: string
  ): Promise<ChatSession> => {
    const id = `session_${characterId}_${Date.now()}`;
    const session = await SessionRepository.create({
      id,
      character_id: characterId,
      character_name: characterName,
      character_avatar: characterAvatar,
    });
    setSessions(prev => [session, ...prev]);
    return session;
  }, []);

  // Get session by character ID
  const getSessionByCharacterId = useCallback(async (
    characterId: string
  ): Promise<ChatSession | null> => {
    return await SessionRepository.getByCharacterId(characterId);
  }, []);

  // Delete session
  const deleteSession = useCallback(async (sessionId: string) => {
    await SessionRepository.delete(sessionId);
    setSessions(prev => prev.filter(s => s.id !== sessionId));
  }, []);

  // Load messages
  const loadMessages = useCallback(async (
    sessionId: string,
    options?: { limit?: number; offset?: number }
  ): Promise<Message[]> => {
    return await MessageRepository.getBySessionId(sessionId, options);
  }, []);

  // Add message
  const addMessage = useCallback(async (
    sessionId: string,
    message: Omit<Message, 'session_id'>
  ): Promise<Message> => {
    const newMessage = await MessageRepository.create({
      ...message,
      session_id: sessionId,
    });

    // Update session's last message
    await SessionRepository.updateLastMessage(
      sessionId,
      message.content.substring(0, 100)
    );

    // Update local sessions state
    setSessions(prev => {
      const updated = prev.map(s => 
        s.id === sessionId 
          ? { ...s, last_message: message.content.substring(0, 100), last_message_at: new Date().toISOString() }
          : s
      );
      // Move updated session to top
      const session = updated.find(s => s.id === sessionId);
      if (session) {
        return [session, ...updated.filter(s => s.id !== sessionId)];
      }
      return updated;
    });

    return newMessage;
  }, []);

  // Add multiple messages
  const addMessages = useCallback(async (
    sessionId: string,
    messages: Omit<Message, 'session_id'>[]
  ) => {
    await MessageRepository.createMany(
      messages.map(m => ({ ...m, session_id: sessionId }))
    );

    if (messages.length > 0) {
      const lastMsg = messages[messages.length - 1];
      await SessionRepository.updateLastMessage(
        sessionId,
        lastMsg.content.substring(0, 100)
      );
    }
  }, []);

  // Get message count
  const getMessageCount = useCallback(async (sessionId: string): Promise<number> => {
    return await MessageRepository.getCountBySessionId(sessionId);
  }, []);

  // Search messages
  const searchMessages = useCallback(async (
    query: string,
    sessionId?: string
  ): Promise<Message[]> => {
    return await MessageRepository.search(query, { sessionId });
  }, []);

  // Unlock message
  const unlockMessage = useCallback(async (messageId: string) => {
    await MessageRepository.update(messageId, { is_unlocked: true });
  }, []);

  // Clear messages
  const clearMessages = useCallback(async (sessionId: string) => {
    await MessageRepository.deleteBySessionId(sessionId);
  }, []);

  return {
    isReady,
    isLoading,
    error,
    sessions,
    loadSessions,
    createSession,
    getSessionByCharacterId,
    deleteSession,
    loadMessages,
    addMessage,
    addMessages,
    getMessageCount,
    searchMessages,
    unlockMessage,
    clearMessages,
  };
}

export default useChatDatabase;
