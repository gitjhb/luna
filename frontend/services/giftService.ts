/**
 * Gift Service
 * 
 * Handles gift sending with idempotency:
 * - Get gift catalog (by tier)
 * - Send gifts with deduplication
 * - Get gift history
 * - Get active status effects
 * - Get gift summary for AI context
 * 
 * 货币单位: 月石 (Moon Stones)
 */

import { api } from './api';

// Simple UUID v4 generator (no external dependency)
const uuidv4 = (): string => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

// ============================================================================
// Types
// ============================================================================

// Tier 分类
export enum GiftTier {
  CONSUMABLE = 1,      // 日常消耗品
  STATE_TRIGGER = 2,   // 状态触发器 ⭐ MVP 重点
  SPEED_DATING = 3,    // 关系加速器
  WHALE_BAIT = 4,      // 榜一大哥尊享
}

export interface StatusEffect {
  type: string;               // tipsy, maid_mode, truth_mode
  duration_messages: number;  // 持续对话条数
  prompt_modifier: string;    // AI prompt 修改器
}

export interface GiftCatalogItem {
  gift_type: string;
  name: string;
  name_cn?: string;
  description?: string;
  description_cn?: string;
  price: number;              // 月石
  xp_reward: number;
  xp_multiplier?: number;     // XP 倍率
  icon?: string;
  tier: number;               // 1-4
  category?: string;
  emotion_boost?: number;
  status_effect?: StatusEffect;
  clears_cold_war?: boolean;
  force_emotion?: string;
  level_boost?: boolean;
  requires_subscription?: boolean;
  sort_order?: number;
}

export interface SendGiftRequest {
  character_id: string;
  gift_type: string;
  idempotency_key: string;
  session_id?: string;
  trigger_ai_response?: boolean;
}

export interface SendGiftResponse {
  success: boolean;
  is_duplicate: boolean;
  gift_id?: string;
  gift_type?: string;
  gift_name?: string;
  gift_name_cn?: string;
  icon?: string;
  tier?: number;
  credits_deducted?: number;
  new_balance?: number;
  xp_awarded?: number;
  level_up: boolean;
  new_level?: number;
  status_effect_applied?: {
    type: string;
    duration: number;
  };
  cold_war_unlocked?: boolean;
  bottleneck_unlocked?: boolean;
  bottleneck_unlock_message?: string;
  ai_response?: string;
  error?: string;
  message?: string;
}

export interface GiftHistoryItem {
  id: string;
  gift_type: string;
  gift_name: string;
  gift_name_cn?: string;
  icon?: string;
  gift_price: number;
  xp_reward: number;
  tier?: number;
  status: 'pending' | 'acknowledged' | 'failed';
  created_at: string;
  acknowledged_at?: string;
}

export interface GiftSummary {
  total_gifts: number;
  total_spent: number;
  total_xp_from_gifts: number;
  top_gifts: Array<{
    count: number;
    name: string;
    name_cn?: string;
    icon?: string;
  }>;
}

export interface ActiveEffect {
  type: string;
  name: string;
  icon: string;
  color: string;
  remaining: number;
  started_at?: string;
}

export interface EffectStatus {
  has_effects: boolean;
  count: number;
  effects: ActiveEffect[];
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Get gift catalog
 * 
 * @param tier - Optional tier filter (1-4)
 */
export const getGiftCatalog = async (tier?: number): Promise<GiftCatalogItem[]> => {
  const params = tier ? { tier } : undefined;
  return api.get<GiftCatalogItem[]>('/gifts/catalog', params);
};

/**
 * Get gift catalog organized by tier
 * 
 * Returns: { "1": [...], "2": [...], "3": [...], "4": [...] }
 */
export const getGiftCatalogByTier = async (): Promise<Record<string, GiftCatalogItem[]>> => {
  return api.get<Record<string, GiftCatalogItem[]>>('/gifts/catalog/by-tier');
};

/**
 * Get active status effects for a character
 */
export const getActiveEffects = async (characterId: string): Promise<EffectStatus> => {
  return api.get<EffectStatus>(`/gifts/effects/${characterId}`);
};

/**
 * Send a gift to a character
 * 
 * @param characterId - Target character ID
 * @param giftType - Gift type from catalog
 * @param sessionId - Optional chat session ID
 * @param triggerAIResponse - Whether to auto-generate AI response (default: true)
 */
export const sendGift = async (
  characterId: string,
  giftType: string,
  sessionId?: string,
  triggerAIResponse: boolean = true,
): Promise<SendGiftResponse> => {
  // Generate idempotency key for this request
  const idempotencyKey = uuidv4();
  
  const request: SendGiftRequest = {
    character_id: characterId,
    gift_type: giftType,
    idempotency_key: idempotencyKey,
    session_id: sessionId,
    trigger_ai_response: triggerAIResponse,
  };
  
  return api.post<SendGiftResponse>('/gifts/send', request);
};

/**
 * Get gift history
 * 
 * @param characterId - Optional filter by character
 * @param limit - Max results
 * @param offset - Pagination offset
 */
export const getGiftHistory = async (
  characterId?: string,
  limit: number = 20,
  offset: number = 0,
): Promise<GiftHistoryItem[]> => {
  const params: Record<string, any> = { limit, offset };
  if (characterId) {
    params.character_id = characterId;
  }
  return api.get<GiftHistoryItem[]>('/gifts/history', params);
};

/**
 * Get gift summary for a character
 * 
 * Returns aggregated stats useful for display and AI context.
 */
export const getGiftSummary = async (characterId: string): Promise<GiftSummary> => {
  return api.get<GiftSummary>(`/gifts/summary/${characterId}`);
};

/**
 * Get gift details by ID
 */
export const getGift = async (giftId: string): Promise<GiftHistoryItem> => {
  return api.get<GiftHistoryItem>(`/gifts/${giftId}`);
};

/**
 * Manually acknowledge a gift
 * (Usually automatic after AI responds)
 */
export const acknowledgeGift = async (giftId: string): Promise<{ success: boolean; status: string }> => {
  return api.post(`/gifts/${giftId}/acknowledge`);
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get localized gift name
 */
export const getGiftName = (gift: GiftCatalogItem | GiftHistoryItem, locale: string = 'zh'): string => {
  if (locale === 'zh' && gift.name_cn) {
    return gift.name_cn;
  }
  return (gift as any).gift_name || (gift as GiftCatalogItem).name || 'Gift';
};

/**
 * Format gift price for display (月石)
 */
export const formatGiftPrice = (price: number): string => {
  return `💎 ${price}`;
};

/**
 * Sort gifts by price (ascending or descending)
 */
export const sortGiftsByPrice = (
  gifts: GiftCatalogItem[],
  ascending: boolean = true,
): GiftCatalogItem[] => {
  return [...gifts].sort((a, b) => 
    ascending ? a.price - b.price : b.price - a.price
  );
};

/**
 * Get tier display name
 */
export const getTierName = (tier: number): string => {
  const names: Record<number, string> = {
    1: '日常',
    2: '状态',
    3: '加速',
    4: '尊享',
  };
  return names[tier] || '其他';
};

/**
 * Get tier description
 */
export const getTierDescription = (tier: number): string => {
  const descriptions: Record<number, string> = {
    1: '日常小礼物，维持好感，修补小摩擦',
    2: '状态触发器，改变她的行为模式 ⭐',
    3: '关系加速器，快速提升亲密度',
    4: '榜一大哥专属，解锁终极特权',
  };
  return descriptions[tier] || '';
};

/**
 * Get effect description
 */
export const getEffectDescription = (effectType: string): string => {
  const descriptions: Record<string, string> = {
    tipsy: '她会变得微醺，说话更加柔软放松，防御心降低，更容易说出心里话...',
    maid_mode: '她会进入女仆模式，称呼你为"主人"，语气变得恭敬服务导向~',
    truth_mode: '她必须诚实回答所有问题，包括那些平时会回避的隐私问题...',
  };
  return descriptions[effectType] || '特殊效果';
};

/**
 * Check if gift has status effect (Tier 2)
 */
export const hasStatusEffect = (gift: GiftCatalogItem): boolean => {
  return gift.tier === GiftTier.STATE_TRIGGER && !!gift.status_effect;
};

/**
 * Check if gift can clear cold war
 */
export const canClearColdWar = (gift: GiftCatalogItem): boolean => {
  return !!gift.clears_cold_war;
};

// ============================================================================
// Export
// ============================================================================

export const giftService = {
  getGiftCatalog,
  getGiftCatalogByTier,
  getActiveEffects,
  sendGift,
  getGiftHistory,
  getGiftSummary,
  getGift,
  acknowledgeGift,
  getGiftName,
  formatGiftPrice,
  sortGiftsByPrice,
  getTierName,
  getTierDescription,
  getEffectDescription,
  hasStatusEffect,
  canClearColdWar,
};

export default giftService;
