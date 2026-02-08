/**
 * Database Module - Unified Export
 * 
 * Usage:
 * import { initDatabase, MessageRepository, SessionRepository } from '@/services/database';
 */

// Core database functions
export { initDatabase, getDatabase, closeDatabase } from './index';

// Repositories
export { 
  MessageRepository,
  SessionRepository,
} from './repositories';

// Types
export type { 
  Message, 
  CreateMessageInput,
  ChatSession,
  CreateSessionInput,
} from './repositories';

// Migration
export { 
  migrateToSQLite, 
  needsMigration, 
  resetMigration,
} from './migration';
