/**
 * Database Connection - Neon PostgreSQL via @vercel/postgres
 * Shared database with Luna iOS backend
 */

import { sql } from '@vercel/postgres';

/**
 * Initialize database tables (run once on first deploy)
 * These tables mirror Luna iOS backend schema
 */
export async function initDB() {
  try {
    // Users table (telegram-specific extension)
    await sql`
      CREATE TABLE IF NOT EXISTS telegram_users (
        telegram_id TEXT PRIMARY KEY,
        email TEXT,
        luna_user_id TEXT,
        username TEXT,
        first_name TEXT,
        is_pro BOOLEAN DEFAULT false,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
      )
    `;
    
    // Messages table for conversation history
    await sql`
      CREATE TABLE IF NOT EXISTS telegram_messages (
        id SERIAL PRIMARY KEY,
        telegram_id TEXT NOT NULL,
        character_id TEXT DEFAULT 'luna',
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp BIGINT,
        created_at TIMESTAMP DEFAULT NOW()
      )
    `;
    
    // Indexes
    await sql`CREATE INDEX IF NOT EXISTS idx_telegram_messages_user ON telegram_messages(telegram_id)`;
    await sql`CREATE INDEX IF NOT EXISTS idx_telegram_messages_time ON telegram_messages(timestamp DESC)`;
    await sql`CREATE INDEX IF NOT EXISTS idx_telegram_users_email ON telegram_users(email)`;
    
    return { success: true };
  } catch (error) {
    console.error('DB init error:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Get or create telegram user
 */
export async function getOrCreateUser(telegramId, userData = {}) {
  try {
    // Try to find existing user
    const existing = await sql`
      SELECT * FROM telegram_users WHERE telegram_id = ${String(telegramId)}
    `;
    
    if (existing.rows.length > 0) {
      return existing.rows[0];
    }
    
    // Create new user
    const result = await sql`
      INSERT INTO telegram_users (telegram_id, username, first_name)
      VALUES (${String(telegramId)}, ${userData.username || null}, ${userData.firstName || null})
      RETURNING *
    `;
    
    return result.rows[0];
  } catch (error) {
    console.error('getOrCreateUser error:', error);
    return null;
  }
}

/**
 * Link telegram user to Luna account via email
 */
export async function linkUserByEmail(telegramId, email) {
  try {
    // Check if email exists in Luna's users table
    const lunaUser = await sql`
      SELECT id, email, is_pro FROM users WHERE email = ${email}
    `;
    
    if (lunaUser.rows.length === 0) {
      return { success: false, message: 'Email not found' };
    }
    
    const luna = lunaUser.rows[0];
    
    // Update telegram user
    await sql`
      UPDATE telegram_users 
      SET email = ${email}, 
          luna_user_id = ${luna.id},
          is_pro = ${luna.is_pro || false},
          updated_at = NOW()
      WHERE telegram_id = ${String(telegramId)}
    `;
    
    return { success: true, isPro: luna.is_pro };
  } catch (error) {
    console.error('linkUserByEmail error:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Save a message to history
 */
export async function saveMessage(telegramId, role, content, characterId = 'luna') {
  try {
    await sql`
      INSERT INTO telegram_messages (telegram_id, character_id, role, content, timestamp)
      VALUES (${String(telegramId)}, ${characterId}, ${role}, ${content}, ${Date.now()})
    `;
    return { success: true };
  } catch (error) {
    console.error('saveMessage error:', error);
    return { success: false };
  }
}

/**
 * Get recent messages for context
 */
export async function getRecentMessages(telegramId, limit = 20, characterId = 'luna') {
  try {
    const result = await sql`
      SELECT role, content, timestamp 
      FROM telegram_messages 
      WHERE telegram_id = ${String(telegramId)} 
        AND character_id = ${characterId}
      ORDER BY timestamp DESC 
      LIMIT ${limit}
    `;
    
    // Return in chronological order (oldest first)
    return result.rows.reverse();
  } catch (error) {
    console.error('getRecentMessages error:', error);
    return [];
  }
}

/**
 * Clear conversation history
 */
export async function clearMessages(telegramId, characterId = 'luna') {
  try {
    await sql`
      DELETE FROM telegram_messages 
      WHERE telegram_id = ${String(telegramId)} 
        AND character_id = ${characterId}
    `;
    return { success: true };
  } catch (error) {
    console.error('clearMessages error:', error);
    return { success: false };
  }
}

/**
 * Check if user is Pro (via linked Luna account)
 */
export async function checkProStatus(telegramId) {
  try {
    const result = await sql`
      SELECT is_pro, luna_user_id FROM telegram_users 
      WHERE telegram_id = ${String(telegramId)}
    `;
    
    if (result.rows.length === 0) {
      return { isPro: false };
    }
    
    const user = result.rows[0];
    
    // If linked to Luna, check Luna's subscription status
    if (user.luna_user_id) {
      const lunaCheck = await sql`
        SELECT is_pro FROM users WHERE id = ${user.luna_user_id}
      `;
      if (lunaCheck.rows.length > 0) {
        return { isPro: lunaCheck.rows[0].is_pro || false };
      }
    }
    
    return { isPro: user.is_pro || false };
  } catch (error) {
    console.error('checkProStatus error:', error);
    return { isPro: false };
  }
}
