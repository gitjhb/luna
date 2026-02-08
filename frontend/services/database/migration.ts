/**
 * AsyncStorage to SQLite Migration
 * 
 * One-time migration for existing users.
 * Safely moves data from AsyncStorage (Zustand) to SQLite.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { getDatabase } from './index';
import { MessageRepository } from './repositories/MessageRepository';
import { SessionRepository } from './repositories/SessionRepository';

const MIGRATION_KEY = 'sqlite_migration_completed';
const CHAT_STORAGE_KEY = 'chat-storage';

interface OldMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  isLocked?: boolean;
  unlockCost?: number;
  extraData?: any;
}

interface OldSession {
  sessionId: string;
  characterId: string;
  characterName: string;
  characterAvatar?: string;
  lastMessage?: string;
  lastMessageAt?: string;
  unreadCount?: number;
}

interface OldChatState {
  messagesBySession: Record<string, OldMessage[]>;
  sessions: OldSession[];
}

/**
 * Check if migration is needed
 */
export async function needsMigration(): Promise<boolean> {
  const migrationDone = await AsyncStorage.getItem(MIGRATION_KEY);
  if (migrationDone === 'true') {
    return false;
  }

  // Check if there's old data to migrate
  const oldData = await AsyncStorage.getItem(CHAT_STORAGE_KEY);
  return oldData !== null;
}

/**
 * Run migration from AsyncStorage to SQLite
 */
export async function migrateToSQLite(): Promise<{
  success: boolean;
  sessionsCount: number;
  messagesCount: number;
  error?: string;
}> {
  console.log('[Migration] Starting AsyncStorage → SQLite migration...');

  try {
    // Check if already migrated
    const migrationDone = await AsyncStorage.getItem(MIGRATION_KEY);
    if (migrationDone === 'true') {
      console.log('[Migration] Already completed, skipping');
      return { success: true, sessionsCount: 0, messagesCount: 0 };
    }

    // Load old data
    const oldDataStr = await AsyncStorage.getItem(CHAT_STORAGE_KEY);
    if (!oldDataStr) {
      console.log('[Migration] No old data found, marking as complete');
      await AsyncStorage.setItem(MIGRATION_KEY, 'true');
      return { success: true, sessionsCount: 0, messagesCount: 0 };
    }

    const oldData: { state: OldChatState } = JSON.parse(oldDataStr);
    const { sessions, messagesBySession } = oldData.state;

    console.log(`[Migration] Found ${sessions?.length || 0} sessions to migrate`);

    let sessionsCount = 0;
    let messagesCount = 0;

    const db = getDatabase();

    // Migrate in a transaction
    await db.withTransactionAsync(async () => {
      // Migrate sessions
      for (const oldSession of (sessions || [])) {
        await SessionRepository.create({
          id: oldSession.sessionId,
          character_id: oldSession.characterId,
          character_name: oldSession.characterName,
          character_avatar: oldSession.characterAvatar,
        });

        if (oldSession.lastMessage) {
          await SessionRepository.updateLastMessage(
            oldSession.sessionId,
            oldSession.lastMessage
          );
        }

        sessionsCount++;

        // Migrate messages for this session
        const oldMessages = messagesBySession[oldSession.sessionId] || [];
        if (oldMessages.length > 0) {
          await MessageRepository.createMany(
            oldMessages.map(msg => ({
              id: msg.id,
              session_id: oldSession.sessionId,
              role: msg.role,
              content: msg.content,
              created_at: msg.timestamp,
              is_unlocked: !msg.isLocked,
              unlock_cost: msg.unlockCost || 0,
              extra_data: msg.extraData,
            }))
          );
          messagesCount += oldMessages.length;
        }
      }
    });

    // Mark migration as complete
    await AsyncStorage.setItem(MIGRATION_KEY, 'true');

    // Optionally: Clear old AsyncStorage data (uncomment when confident)
    // await AsyncStorage.removeItem(CHAT_STORAGE_KEY);

    console.log(`[Migration] Complete: ${sessionsCount} sessions, ${messagesCount} messages`);

    return { success: true, sessionsCount, messagesCount };
  } catch (error) {
    console.error('[Migration] Failed:', error);
    return {
      success: false,
      sessionsCount: 0,
      messagesCount: 0,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Reset migration flag (for testing)
 */
export async function resetMigration(): Promise<void> {
  await AsyncStorage.removeItem(MIGRATION_KEY);
  console.log('[Migration] Reset complete');
}

export default {
  needsMigration,
  migrateToSQLite,
  resetMigration,
};
