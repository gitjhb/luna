/**
 * Memory System - pgvector semantic search
 * Uses shared memory tables with Luna iOS backend
 */

import { sql } from '@vercel/postgres';
import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

const EMBEDDING_MODEL = 'text-embedding-3-small';
const EMBEDDING_DIMENSIONS = 1536;

/**
 * Initialize memory tables with pgvector
 */
export async function initMemoryTables() {
  try {
    // Enable pgvector extension
    await sql`CREATE EXTENSION IF NOT EXISTS vector`;
    
    // Semantic memories (user profile/preferences)
    await sql`
      CREATE TABLE IF NOT EXISTS telegram_semantic_memories (
        id SERIAL PRIMARY KEY,
        telegram_id TEXT NOT NULL,
        character_id TEXT DEFAULT 'luna',
        
        -- 基本信息
        user_name TEXT,
        user_nickname TEXT,
        birthday TEXT,
        occupation TEXT,
        location TEXT,
        
        -- 偏好 (JSONB)
        likes JSONB DEFAULT '[]',
        dislikes JSONB DEFAULT '[]',
        interests JSONB DEFAULT '[]',
        
        -- 关系
        pet_names JSONB DEFAULT '[]',
        important_dates JSONB DEFAULT '{}',
        
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        
        UNIQUE(telegram_id, character_id)
      )
    `;
    
    // Episodic memories (events with embeddings)
    await sql`
      CREATE TABLE IF NOT EXISTS telegram_episodic_memories (
        id SERIAL PRIMARY KEY,
        telegram_id TEXT NOT NULL,
        character_id TEXT DEFAULT 'luna',
        
        -- 事件内容
        event_type TEXT NOT NULL,
        summary TEXT NOT NULL,
        key_dialogue JSONB DEFAULT '[]',
        emotion_state TEXT,
        
        -- 向量嵌入
        embedding vector(1536),
        
        -- 元数据
        importance INTEGER DEFAULT 2,
        strength FLOAT DEFAULT 1.0,
        recall_count INTEGER DEFAULT 0,
        last_recalled TIMESTAMP,
        
        created_at TIMESTAMP DEFAULT NOW()
      )
    `;
    
    // Indexes
    await sql`CREATE INDEX IF NOT EXISTS idx_episodic_telegram_id ON telegram_episodic_memories(telegram_id)`;
    await sql`CREATE INDEX IF NOT EXISTS idx_episodic_embedding ON telegram_episodic_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)`;
    
    return { success: true };
  } catch (error) {
    console.error('Memory tables init error:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Generate embedding for text
 */
export async function generateEmbedding(text) {
  try {
    const response = await openai.embeddings.create({
      model: EMBEDDING_MODEL,
      input: text,
      dimensions: EMBEDDING_DIMENSIONS
    });
    return response.data[0].embedding;
  } catch (error) {
    console.error('Embedding error:', error);
    return null;
  }
}

/**
 * Search for relevant memories using cosine similarity
 */
export async function searchMemories(telegramId, query, limit = 5, characterId = 'luna') {
  try {
    const embedding = await generateEmbedding(query);
    if (!embedding) return [];
    
    // Convert embedding to string format for pgvector
    const embeddingStr = `[${embedding.join(',')}]`;
    
    const result = await sql`
      SELECT 
        id,
        event_type,
        summary,
        key_dialogue,
        emotion_state,
        importance,
        created_at,
        1 - (embedding <=> ${embeddingStr}::vector) as similarity
      FROM telegram_episodic_memories
      WHERE telegram_id = ${String(telegramId)}
        AND character_id = ${characterId}
        AND embedding IS NOT NULL
      ORDER BY embedding <=> ${embeddingStr}::vector
      LIMIT ${limit}
    `;
    
    // Filter by similarity threshold (> 0.5)
    return result.rows.filter(r => r.similarity > 0.5);
  } catch (error) {
    console.error('searchMemories error:', error);
    return [];
  }
}

/**
 * Store an episodic memory with embedding
 */
export async function storeEpisodicMemory(telegramId, memory, characterId = 'luna') {
  try {
    const { eventType, summary, keyDialogue = [], emotionState, importance = 2 } = memory;
    
    // Generate embedding for the memory
    const textToEmbed = `${eventType}: ${summary}. ${keyDialogue.join(' ')}`;
    const embedding = await generateEmbedding(textToEmbed);
    const embeddingStr = embedding ? `[${embedding.join(',')}]` : null;
    
    await sql`
      INSERT INTO telegram_episodic_memories 
        (telegram_id, character_id, event_type, summary, key_dialogue, emotion_state, importance, embedding)
      VALUES 
        (${String(telegramId)}, ${characterId}, ${eventType}, ${summary}, 
         ${JSON.stringify(keyDialogue)}, ${emotionState}, ${importance}, 
         ${embeddingStr}::vector)
    `;
    
    return { success: true };
  } catch (error) {
    console.error('storeEpisodicMemory error:', error);
    return { success: false };
  }
}

/**
 * Get semantic memory (user profile)
 */
export async function getSemanticMemory(telegramId, characterId = 'luna') {
  try {
    const result = await sql`
      SELECT * FROM telegram_semantic_memories
      WHERE telegram_id = ${String(telegramId)} AND character_id = ${characterId}
    `;
    
    if (result.rows.length === 0) return null;
    return result.rows[0];
  } catch (error) {
    console.error('getSemanticMemory error:', error);
    return null;
  }
}

/**
 * Update semantic memory (user profile)
 */
export async function updateSemanticMemory(telegramId, updates, characterId = 'luna') {
  try {
    // Build dynamic update - only update non-null fields
    const fields = ['user_name', 'user_nickname', 'birthday', 'occupation', 'location'];
    const jsonFields = ['likes', 'dislikes', 'interests', 'pet_names', 'important_dates'];
    
    // Check if record exists
    const existing = await getSemanticMemory(telegramId, characterId);
    
    if (!existing) {
      // Insert new record
      await sql`
        INSERT INTO telegram_semantic_memories (telegram_id, character_id, user_name, likes, dislikes, interests)
        VALUES (${String(telegramId)}, ${characterId}, ${updates.user_name || null},
                ${JSON.stringify(updates.likes || [])},
                ${JSON.stringify(updates.dislikes || [])},
                ${JSON.stringify(updates.interests || [])})
      `;
    } else {
      // Merge arrays for JSON fields
      const mergedLikes = [...new Set([...(existing.likes || []), ...(updates.likes || [])])];
      const mergedDislikes = [...new Set([...(existing.dislikes || []), ...(updates.dislikes || [])])];
      const mergedInterests = [...new Set([...(existing.interests || []), ...(updates.interests || [])])];
      
      await sql`
        UPDATE telegram_semantic_memories
        SET 
          user_name = COALESCE(${updates.user_name || null}, user_name),
          user_nickname = COALESCE(${updates.user_nickname || null}, user_nickname),
          birthday = COALESCE(${updates.birthday || null}, birthday),
          occupation = COALESCE(${updates.occupation || null}, occupation),
          location = COALESCE(${updates.location || null}, location),
          likes = ${JSON.stringify(mergedLikes)}::jsonb,
          dislikes = ${JSON.stringify(mergedDislikes)}::jsonb,
          interests = ${JSON.stringify(mergedInterests)}::jsonb,
          updated_at = NOW()
        WHERE telegram_id = ${String(telegramId)} AND character_id = ${characterId}
      `;
    }
    
    return { success: true };
  } catch (error) {
    console.error('updateSemanticMemory error:', error);
    return { success: false };
  }
}

/**
 * Get recent episodic memories
 */
export async function getRecentMemories(telegramId, limit = 5, characterId = 'luna') {
  try {
    const result = await sql`
      SELECT event_type, summary, key_dialogue, emotion_state, importance, created_at
      FROM telegram_episodic_memories
      WHERE telegram_id = ${String(telegramId)} AND character_id = ${characterId}
      ORDER BY created_at DESC
      LIMIT ${limit}
    `;
    return result.rows;
  } catch (error) {
    console.error('getRecentMemories error:', error);
    return [];
  }
}

/**
 * Build memory context for LLM prompt
 */
export async function buildMemoryContext(telegramId, userMessage, characterId = 'luna') {
  try {
    // Get semantic memory (user profile)
    const semantic = await getSemanticMemory(telegramId, characterId);
    
    // Search relevant episodic memories
    const relevantMemories = await searchMemories(telegramId, userMessage, 3, characterId);
    
    // Get recent memories for context
    const recentMemories = await getRecentMemories(telegramId, 3, characterId);
    
    let context = '';
    
    // Add user profile
    if (semantic) {
      context += '## 关于用户\n';
      if (semantic.user_name) context += `- 名字: ${semantic.user_name}\n`;
      if (semantic.user_nickname) context += `- 昵称: ${semantic.user_nickname}\n`;
      if (semantic.occupation) context += `- 职业: ${semantic.occupation}\n`;
      if (semantic.likes?.length) context += `- 喜欢: ${semantic.likes.slice(0, 5).join(', ')}\n`;
      if (semantic.interests?.length) context += `- 兴趣: ${semantic.interests.slice(0, 5).join(', ')}\n`;
      context += '\n';
    }
    
    // Add relevant memories
    if (relevantMemories.length > 0) {
      context += '## 相关记忆\n';
      for (const mem of relevantMemories) {
        context += `- [${mem.event_type}] ${mem.summary}\n`;
      }
      context += '\n';
    }
    
    // Add recent memories
    if (recentMemories.length > 0 && relevantMemories.length === 0) {
      context += '## 最近发生的事\n';
      for (const mem of recentMemories.slice(0, 2)) {
        context += `- [${mem.event_type}] ${mem.summary}\n`;
      }
      context += '\n';
    }
    
    return context || null;
  } catch (error) {
    console.error('buildMemoryContext error:', error);
    return null;
  }
}
