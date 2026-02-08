/**
 * Session Repository
 * 
 * Handles all chat session-related database operations.
 */

import { getDatabase } from '../index';

// ============================================================================
// Types
// ============================================================================

export interface ChatSession {
  id: string;
  character_id: string;
  character_name: string | null;
  character_avatar: string | null;
  last_message: string | null;
  last_message_at: string | null;
  unread_count: number;
  created_at: string;
  updated_at: string;
}

export interface CreateSessionInput {
  id: string;
  character_id: string;
  character_name?: string;
  character_avatar?: string;
}

// ============================================================================
// Repository
// ============================================================================

export const SessionRepository = {
  /**
   * Get all sessions ordered by last message
   */
  async getAll(): Promise<ChatSession[]> {
    const db = getDatabase();
    const rows = await db.getAllAsync<ChatSession>(
      `SELECT * FROM sessions ORDER BY updated_at DESC`
    );
    return rows;
  },

  /**
   * Get session by ID
   */
  async getById(id: string): Promise<ChatSession | null> {
    const db = getDatabase();
    return await db.getFirstAsync<ChatSession>(
      'SELECT * FROM sessions WHERE id = ?',
      [id]
    );
  },

  /**
   * Get session by character ID
   */
  async getByCharacterId(characterId: string): Promise<ChatSession | null> {
    const db = getDatabase();
    return await db.getFirstAsync<ChatSession>(
      'SELECT * FROM sessions WHERE character_id = ?',
      [characterId]
    );
  },

  /**
   * Create a new session
   */
  async create(input: CreateSessionInput): Promise<ChatSession> {
    const db = getDatabase();
    const now = new Date().toISOString();

    await db.runAsync(
      `INSERT INTO sessions (id, character_id, character_name, character_avatar, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [
        input.id,
        input.character_id,
        input.character_name ?? null,
        input.character_avatar ?? null,
        now,
        now,
      ]
    );

    return {
      id: input.id,
      character_id: input.character_id,
      character_name: input.character_name ?? null,
      character_avatar: input.character_avatar ?? null,
      last_message: null,
      last_message_at: null,
      unread_count: 0,
      created_at: now,
      updated_at: now,
    };
  },

  /**
   * Create or get existing session for a character
   */
  async getOrCreate(input: CreateSessionInput): Promise<ChatSession> {
    const existing = await SessionRepository.getByCharacterId(input.character_id);
    if (existing) return existing;
    return await SessionRepository.create(input);
  },

  /**
   * Update session
   */
  async update(id: string, updates: Partial<ChatSession>): Promise<void> {
    const db = getDatabase();
    const fields: string[] = ['updated_at = ?'];
    const values: any[] = [new Date().toISOString()];

    if (updates.character_name !== undefined) {
      fields.push('character_name = ?');
      values.push(updates.character_name);
    }
    if (updates.character_avatar !== undefined) {
      fields.push('character_avatar = ?');
      values.push(updates.character_avatar);
    }
    if (updates.last_message !== undefined) {
      fields.push('last_message = ?');
      values.push(updates.last_message);
    }
    if (updates.last_message_at !== undefined) {
      fields.push('last_message_at = ?');
      values.push(updates.last_message_at);
    }
    if (updates.unread_count !== undefined) {
      fields.push('unread_count = ?');
      values.push(updates.unread_count);
    }

    values.push(id);
    await db.runAsync(
      `UPDATE sessions SET ${fields.join(', ')} WHERE id = ?`,
      values
    );
  },

  /**
   * Update last message info
   */
  async updateLastMessage(sessionId: string, message: string): Promise<void> {
    const db = getDatabase();
    const now = new Date().toISOString();
    await db.runAsync(
      `UPDATE sessions SET last_message = ?, last_message_at = ?, updated_at = ? WHERE id = ?`,
      [message, now, now, sessionId]
    );
  },

  /**
   * Increment unread count
   */
  async incrementUnread(sessionId: string): Promise<void> {
    const db = getDatabase();
    await db.runAsync(
      `UPDATE sessions SET unread_count = unread_count + 1, updated_at = ? WHERE id = ?`,
      [new Date().toISOString(), sessionId]
    );
  },

  /**
   * Clear unread count
   */
  async clearUnread(sessionId: string): Promise<void> {
    const db = getDatabase();
    await db.runAsync(
      `UPDATE sessions SET unread_count = 0, updated_at = ? WHERE id = ?`,
      [new Date().toISOString(), sessionId]
    );
  },

  /**
   * Delete session and all its messages (cascade)
   */
  async delete(id: string): Promise<void> {
    const db = getDatabase();
    await db.runAsync('DELETE FROM sessions WHERE id = ?', [id]);
  },

  /**
   * Delete session by character ID
   */
  async deleteByCharacterId(characterId: string): Promise<void> {
    const db = getDatabase();
    await db.runAsync('DELETE FROM sessions WHERE character_id = ?', [characterId]);
  },

  /**
   * Get total message count across all sessions
   */
  async getTotalMessageCount(): Promise<number> {
    const db = getDatabase();
    const result = await db.getFirstAsync<{ count: number }>(
      'SELECT COUNT(*) as count FROM messages'
    );
    return result?.count ?? 0;
  },
};

export default SessionRepository;
