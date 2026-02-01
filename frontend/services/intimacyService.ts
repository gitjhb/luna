/**
 * Intimacy Service
 *
 * Handles all intimacy/gamification related API calls:
 * - Get intimacy status
 * - Daily check-in
 * - Get available actions
 * - Get XP history
 * - Get stages & features info
 */

import { api } from './api';
import {
  IntimacyStatus,
  DailyCheckinResponse,
  ActionAvailability,
  IntimacyHistoryResponse,
  AllStagesResponse,
  AllFeaturesResponse,
  XPAwardResponse,
  ActionType,
} from '../types';

// Transform snake_case API response to camelCase
const transformIntimacyStatus = (data: any): IntimacyStatus => ({
  characterId: data.character_id,
  characterName: data.character_name,
  currentLevel: data.current_level,
  totalXp: data.total_xp,
  xpForCurrentLevel: data.xp_for_current_level,
  xpForNextLevel: data.xp_for_next_level,
  xpProgressInLevel: data.xp_progress_in_level,
  progressPercent: data.progress_percent,
  intimacyStage: data.intimacy_stage,
  stageNameCn: data.stage_name_cn,
  streakDays: data.streak_days,
  lastInteractionDate: data.last_interaction_date,
  dailyXpEarned: data.daily_xp_earned,
  dailyXpLimit: data.daily_xp_limit,
  dailyXpRemaining: data.daily_xp_remaining,
  availableActions: (data.available_actions || []).map((a: any) => ({
    actionType: a.action_type,
    actionName: a.action_name,
    xpReward: a.xp_reward,
    dailyLimit: a.daily_limit,
    usedToday: a.used_today,
    available: a.available,
    cooldownSeconds: a.cooldown_seconds,
  })),
  unlockedFeatures: data.unlocked_features || [],
  // 统计数据
  totalMessages: data.total_messages || 0,
  giftsCount: data.gifts_count || 0,
  specialEvents: data.special_events || 0,
});

const transformCheckinResponse = (data: any): DailyCheckinResponse => ({
  success: data.success,
  message: data.message,
  xpAwarded: data.xp_awarded,
  streakDays: data.streak_days,
  streakBonus: data.streak_bonus,
  totalXpAwarded: data.total_xp_awarded,
  newTotalXp: data.new_total_xp,
  newLevel: data.new_level,
  levelUp: data.level_up,
});

const transformXPAwardResponse = (data: any): XPAwardResponse => ({
  success: data.success,
  actionType: data.action_type,
  xpAwarded: data.xp_awarded,
  xpBefore: data.xp_before,
  newTotalXp: data.new_total_xp,
  levelBefore: data.level_before,
  newLevel: data.new_level,
  levelUp: data.level_up,
  levelsGained: data.levels_gained,
  stageBefore: data.stage_before,
  newStage: data.new_stage,
  stageChanged: data.stage_changed,
  dailyXpEarned: data.daily_xp_earned,
  dailyXpRemaining: data.daily_xp_remaining,
  streakDays: data.streak_days,
  celebrationMessage: data.celebration_message,
  unlockedFeatures: data.unlocked_features,
});

const transformHistoryResponse = (data: any): IntimacyHistoryResponse => ({
  characterId: data.character_id,
  entries: data.entries.map((e: any) => ({
    actionType: e.action_type,
    actionName: e.action_name,
    xpAwarded: e.xp_awarded,
    createdAt: e.created_at,
  })),
  total: data.total,
  limit: data.limit,
  offset: data.offset,
  hasMore: data.has_more,
});

const transformStagesResponse = (data: any): AllStagesResponse => ({
  stages: data.stages.map((s: any) => ({
    stageId: s.stage_id,
    stageName: s.stage_name,
    stageNameCn: s.stage_name_cn,
    levelRange: s.level_range,
    minLevel: s.min_level,
    maxLevel: s.max_level,
    description: s.description,
    aiAttitude: s.ai_attitude,
    keyUnlocks: s.key_unlocks,
  })),
  currentStage: data.current_stage,
  currentLevel: data.current_level,
});

const transformFeaturesResponse = (data: any): AllFeaturesResponse => ({
  features: data.features.map((f: any) => ({
    level: f.level,
    featureId: f.feature_id,
    featureName: f.feature_name,
    featureNameCn: f.feature_name_cn,
    description: f.description,
    isUnlocked: f.is_unlocked,
  })),
  currentLevel: data.current_level,
  totalUnlocked: data.total_unlocked,
  totalFeatures: data.total_features,
});

export const intimacyService = {
  /**
   * Get current intimacy status with a character
   */
  getStatus: async (characterId: string): Promise<IntimacyStatus> => {
    const data = await api.get(`/intimacy/${characterId}`);
    return transformIntimacyStatus(data);
  },

  /**
   * Perform daily check-in with a character
   */
  dailyCheckin: async (characterId: string): Promise<DailyCheckinResponse> => {
    const data = await api.post(`/intimacy/${characterId}/checkin`);
    return transformCheckinResponse(data);
  },

  /**
   * Get available XP actions and their status
   */
  getAvailableActions: async (characterId: string): Promise<ActionAvailability[]> => {
    const data = await api.get<any[]>(`/intimacy/${characterId}/actions`);
    return data.map((a) => ({
      actionType: a.action_type,
      actionName: a.action_name,
      xpReward: a.xp_reward,
      dailyLimit: a.daily_limit,
      usedToday: a.used_today,
      available: a.available,
      cooldownSeconds: a.cooldown_seconds,
    }));
  },

  /**
   * Get XP earning history
   */
  getHistory: async (
    characterId: string,
    limit: number = 20,
    offset: number = 0
  ): Promise<IntimacyHistoryResponse> => {
    const data = await api.get(`/intimacy/${characterId}/history`, { limit, offset });
    return transformHistoryResponse(data);
  },

  /**
   * Get all intimacy stages info
   */
  getAllStages: async (characterId?: string): Promise<AllStagesResponse> => {
    const params = characterId ? { character_id: characterId } : undefined;
    const data = await api.get('/intimacy/stages/all', params);
    return transformStagesResponse(data);
  },

  /**
   * Get all unlockable features
   */
  getAllFeatures: async (characterId?: string): Promise<AllFeaturesResponse> => {
    const params = characterId ? { character_id: characterId } : undefined;
    const data = await api.get('/intimacy/features/all', params);
    return transformFeaturesResponse(data);
  },

  /**
   * Manually award XP for an action (testing/special cases)
   */
  awardXP: async (characterId: string, actionType: ActionType): Promise<XPAwardResponse> => {
    const data = await api.post(`/intimacy/${characterId}/award/${actionType}`);
    return transformXPAwardResponse(data);
  },
};

export default intimacyService;
