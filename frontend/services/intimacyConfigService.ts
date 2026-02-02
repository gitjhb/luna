/**
 * Intimacy Config Service
 * 
 * 获取亲密度系统配置（阶段、功能解锁等）
 * App启动时只需要拿一次
 */

import { API_BASE_URL } from './api';

export interface StageInfo {
  stage_id: string;
  stage_name: string;
  stage_name_cn: string;
  level_range: string;
  min_level: number;
  max_level: number;
  description: string;
  ai_attitude: string;
  key_unlocks: string[];
}

export interface IntimacyConfig {
  stages: StageInfo[];
  current_stage?: string;
  current_level?: number;
}

// 阶段对应的emoji (v3.0)
const STAGE_EMOJIS: Record<string, string> = {
  strangers: '👋',     // S0 陌生人 Lv1-5
  friends: '😊',       // S1 朋友 Lv6-10
  ambiguous: '💕',     // S2 暧昧 Lv11-15
  lovers: '❤️',        // S3 恋人 Lv16-25
  soulmates: '💍',     // S4 挚爱 Lv26-40
};

// 缓存配置
let cachedConfig: IntimacyConfig | null = null;

/**
 * 获取亲密度配置（带缓存）
 */
export async function getIntimacyConfig(characterId?: string): Promise<IntimacyConfig | null> {
  // 如果没有characterId且有缓存，直接返回缓存
  if (!characterId && cachedConfig) {
    return cachedConfig;
  }
  
  try {
    const url = characterId 
      ? `${API_BASE_URL}/intimacy/stages/all?character_id=${characterId}`
      : `${API_BASE_URL}/intimacy/stages/all`;
      
    const response = await fetch(url);
    
    if (!response.ok) {
      console.warn('Failed to fetch intimacy config:', response.status);
      return cachedConfig;  // 返回缓存作为降级
    }
    
    const data = await response.json();
    
    // 更新缓存
    cachedConfig = data;
    
    return data;
  } catch (error) {
    console.error('Error fetching intimacy config:', error);
    return cachedConfig;  // 返回缓存作为降级
  }
}

/**
 * 获取阶段emoji
 */
export function getStageEmoji(stageId: string): string {
  return STAGE_EMOJIS[stageId] || '💫';
}

/**
 * 清除缓存（用于调试或强制刷新）
 */
export function clearIntimacyConfigCache() {
  cachedConfig = null;
}

/**
 * 预加载配置（App启动时调用）
 */
export async function preloadIntimacyConfig(): Promise<void> {
  await getIntimacyConfig();
}
