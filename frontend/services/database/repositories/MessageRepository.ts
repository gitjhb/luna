/**
 * Message Repository
 * 
 * Handles all message-related database operations.
 * Implements Repository pattern for clean data access.
 */

import { getDatabase } from '../index';

// ============================================================================
// Types
// ============================================================================

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  is_unlocked: boolean;
  unlock_cost: number;
  extra_data?: Record<string, any>;
}

export interface CreateMessageInput {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at?: string;
  is_unlocked?: boolean;
  unlock_cost?: number;
  extra_data?: Record<string, any>;
}

// ============================================================================
// Repository
// ============================================================================

export const MessageRepository = {
  /**
   * Get messages for a session with pagination
   */
  async getBySessionId(
    sessionId: string,
    options: { limit?: number; offset?: number; order?: 'asc' | 'desc' } = {}
  ): Promise<Message[]> {
    const db = getDatabase();
    const { limit = 50, offset = 0, order = 'asc' } = options;

    const rows = await db.getAllAsync<{
      id: string;
      session_id: string;
      role: string;
      content: string;
      created_at: string;
      is_unlocked: number;
      unlock_cost: number;
      extra_data: string | null;
    }>(
      `SELECT * FROM messages 
       WHERE session_id = ? 
       ORDER BY created_at ${order === 'desc' ? 'DESC' : 'ASC'}
       LIMIT ? OFFSET ?`,
      [sessionId, limit, offset]
    );

    return rows.map(row => ({
      id: row.id,
      session_id: row.session_id,
      role: row.role as Message['role'],
      content: row.content,
      created_at: row.created_at,
      is_unlocked: row.is_unlocked === 1,
      unlock_cost: row.unlock_cost,
      extra_data: row.extra_data ? JSON.parse(row.extra_data) : undefined,
    }));
  },

  /**
   * Get message count for a session
   */
  async getCountBySessionId(sessionId: string): Promise<number> {
    const db = getDatabase();
    const result = await db.getFirstAsync<{ count: number }>(
      'SELECT COUNT(*) as count FROM messages WHERE session_id = ?',
      [sessionId]
    );
    return result?.count ?? 0;
  },

  /**
   * Get a single message by ID
   */
  async getById(id: string): Promise<Message | null> {
    const db = getDatabase();
    const row = await db.getFirstAsync<any>(
      'SELECT * FROM messages WHERE id = ?',
      [id]
    );

    if (!row) return null;

    return {
      id: row.id,
      session_id: row.session_id,
      role: row.role,
      content: row.content,
      created_at: row.created_at,
      is_unlocked: row.is_unlocked === 1,
      unlock_cost: row.unlock_cost,
      extra_data: row.extra_data ? JSON.parse(row.extra_data) : undefined,
    };
  },

  /**
   * Create a new message
   */
  async create(input: CreateMessageInput): Promise<Message> {
    const db = getDatabase();
    const now = new Date().toISOString();

    await db.runAsync(
      `INSERT INTO messages (id, session_id, role, content, created_at, is_unlocked, unlock_cost, extra_data)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        input.id,
        input.session_id,
        input.role,
        input.content,
        input.created_at ?? now,
        input.is_unlocked !== false ? 1 : 0,
        input.unlock_cost ?? 0,
        input.extra_data ? JSON.stringify(input.extra_data) : null,
      ]
    );

    return {
      id: input.id,
      session_id: input.session_id,
      role: input.role,
      content: input.content,
      created_at: input.created_at ?? now,
      is_unlocked: input.is_unlocked !== false,
      unlock_cost: input.unlock_cost ?? 0,
      extra_data: input.extra_data,
    };
  },

  /**
   * Create multiple messages in a transaction
   */
  async createMany(inputs: CreateMessageInput[]): Promise<void> {
    const db = getDatabase();
    const now = new Date().toISOString();

    await db.withTransactionAsync(async () => {
      for (const input of inputs) {
        await db.runAsync(
          `INSERT OR REPLACE INTO messages (id, session_id, role, content, created_at, is_unlocked, unlock_cost, extra_data)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
          [
            input.id,
            input.session_id,
            input.role,
            input.content,
            input.created_at ?? now,
            input.is_unlocked !== false ? 1 : 0,
            input.unlock_cost ?? 0,
            input.extra_data ? JSON.stringify(input.extra_data) : null,
          ]
        );
      }
    });
  },

  /**
   * Update message (e.g., unlock)
   */
  async update(id: string, updates: Partial<Message>): Promise<void> {
    const db = getDatabase();
    const fields: string[] = [];
    const values: any[] = [];

    if (updates.content !== undefined) {
      fields.push('content = ?');
      values.push(updates.content);
    }
    if (updates.is_unlocked !== undefined) {
      fields.push('is_unlocked = ?');
      values.push(updates.is_unlocked ? 1 : 0);
    }
    if (updates.extra_data !== undefined) {
      fields.push('extra_data = ?');
      values.push(JSON.stringify(updates.extra_data));
    }

    if (fields.length === 0) return;

    values.push(id);
    await db.runAsync(
      `UPDATE messages SET ${fields.join(', ')} WHERE id = ?`,
      values
    );
  },

  /**
   * Delete a message
   */
  async delete(id: string): Promise<void> {
    const db = getDatabase();
    await db.runAsync('DELETE FROM messages WHERE id = ?', [id]);
  },

  /**
   * Delete all messages for a session
   */
  async deleteBySessionId(sessionId: string): Promise<void> {
    const db = getDatabase();
    await db.runAsync('DELETE FROM messages WHERE session_id = ?', [sessionId]);
  },

  /**
   * Search messages by content
   */
  async search(
    query: string,
    options: { sessionId?: string; limit?: number } = {}
  ): Promise<Message[]> {
    const db = getDatabase();
    const { sessionId, limit = 50 } = options;

    let sql = `SELECT * FROM messages WHERE content LIKE ?`;
    const params: any[] = [`%${query}%`];

    if (sessionId) {
      sql += ' AND session_id = ?';
      params.push(sessionId);
    }

    sql += ' ORDER BY created_at DESC LIMIT ?';
    params.push(limit);

    const rows = await db.getAllAsync<any>(sql, params);

    return rows.map(row => ({
      id: row.id,
      session_id: row.session_id,
      role: row.role,
      content: row.content,
      created_at: row.created_at,
      is_unlocked: row.is_unlocked === 1,
      unlock_cost: row.unlock_cost,
      extra_data: row.extra_data ? JSON.parse(row.extra_data) : undefined,
    }));
  },

  /**
   * Get latest messages across all sessions
   */
  async getLatest(limit: number = 20): Promise<Message[]> {
    const db = getDatabase();
    const rows = await db.getAllAsync<any>(
      `SELECT * FROM messages ORDER BY created_at DESC LIMIT ?`,
      [limit]
    );

    return rows.map(row => ({
      id: row.id,
      session_id: row.session_id,
      role: row.role,
      content: row.content,
      created_at: row.created_at,
      is_unlocked: row.is_unlocked === 1,
      unlock_cost: row.unlock_cost,
      extra_data: row.extra_data ? JSON.parse(row.extra_data) : undefined,
    }));
  },
};

export default MessageRepository;
