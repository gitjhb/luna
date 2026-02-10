/**
 * SQLite Database Service
 * 
 * Centralized database connection and migration management.
 * Uses expo-sqlite (Next API) with async/await support.
 */

import * as SQLite from 'expo-sqlite';

// Database instance (singleton)
let db: SQLite.SQLiteDatabase | null = null;
let initPromise: Promise<SQLite.SQLiteDatabase> | null = null;

// Current schema version
const SCHEMA_VERSION = 1;

/**
 * Initialize database connection
 */
export async function initDatabase(): Promise<SQLite.SQLiteDatabase> {
  if (db) return db;
  
  // 防止并发初始化
  if (initPromise) return initPromise;

  initPromise = (async () => {
    console.log('[DB] Opening database...');
    db = await SQLite.openDatabaseAsync('luna.db');
    
    // Enable WAL mode for better performance
    await db.execAsync('PRAGMA journal_mode = WAL;');
    
    // Run migrations
    await runMigrations(db);
    
    console.log('[DB] Database initialized');
    return db;
  })();
  
  return initPromise;
}

/**
 * Get database instance (waits for init if needed)
 */
export function getDatabase(): SQLite.SQLiteDatabase {
  if (!db) {
    throw new Error('Database not initialized. Call initDatabase() first.');
  }
  return db;
}

/**
 * Get database instance async (auto-initializes if needed)
 */
export async function getDatabaseAsync(): Promise<SQLite.SQLiteDatabase> {
  if (db) return db;
  return initDatabase();
}

/**
 * Close database connection
 */
export async function closeDatabase(): Promise<void> {
  if (db) {
    await db.closeAsync();
    db = null;
    console.log('[DB] Database closed');
  }
}

/**
 * Run database migrations
 */
async function runMigrations(database: SQLite.SQLiteDatabase): Promise<void> {
  // Create migrations table if not exists
  await database.execAsync(`
    CREATE TABLE IF NOT EXISTS migrations (
      version INTEGER PRIMARY KEY,
      applied_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
  `);

  // Get current version
  const result = await database.getFirstAsync<{ version: number }>(
    'SELECT MAX(version) as version FROM migrations'
  );
  const currentVersion = result?.version ?? 0;

  console.log(`[DB] Current schema version: ${currentVersion}, target: ${SCHEMA_VERSION}`);

  // Run pending migrations
  if (currentVersion < 1) {
    await migration_v1(database);
    await database.runAsync('INSERT INTO migrations (version) VALUES (?)', 1);
  }

  // Add more migrations here as needed:
  // if (currentVersion < 2) { await migration_v2(database); ... }
}

/**
 * Migration v1: Initial schema
 */
async function migration_v1(database: SQLite.SQLiteDatabase): Promise<void> {
  console.log('[DB] Running migration v1...');

  await database.execAsync(`
    -- Chat sessions table
    CREATE TABLE IF NOT EXISTS sessions (
      id TEXT PRIMARY KEY,
      character_id TEXT NOT NULL,
      character_name TEXT,
      character_avatar TEXT,
      last_message TEXT,
      last_message_at TEXT,
      unread_count INTEGER DEFAULT 0,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- Messages table
    CREATE TABLE IF NOT EXISTS messages (
      id TEXT PRIMARY KEY,
      session_id TEXT NOT NULL,
      role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
      content TEXT NOT NULL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      is_unlocked INTEGER DEFAULT 1,
      unlock_cost INTEGER DEFAULT 0,
      extra_data TEXT,
      FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    );

    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
    CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
    CREATE INDEX IF NOT EXISTS idx_sessions_character_id ON sessions(character_id);
    CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at);

    -- Intimacy cache table
    CREATE TABLE IF NOT EXISTS intimacy_cache (
      character_id TEXT PRIMARY KEY,
      level INTEGER DEFAULT 1,
      current_xp INTEGER DEFAULT 0,
      max_xp INTEGER DEFAULT 100,
      stage TEXT DEFAULT 'stranger',
      stage_cn TEXT DEFAULT '陌生人',
      emotion INTEGER DEFAULT 50,
      emotion_state TEXT DEFAULT 'neutral',
      streak_days INTEGER DEFAULT 0,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- User preferences (key-value store for misc settings)
    CREATE TABLE IF NOT EXISTS preferences (
      key TEXT PRIMARY KEY,
      value TEXT,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
  `);

  console.log('[DB] Migration v1 complete');
}

export default {
  initDatabase,
  getDatabase,
  getDatabaseAsync,
  closeDatabase,
};
