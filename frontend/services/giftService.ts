/**
 * Gift Service
 * 
 * Handles gift sending with idempotency:
 * - Get gift catalog
 * - Send gifts with deduplication
 * - Get gift history
 * - Get gift summary for AI context
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

export interface GiftCatalogItem {
  gift_type: string;
  name: string;
  name_cn?: string;
  description?: string;
  description_cn?: string;
  price: number;
  xp_reward: number;
  icon?: string;
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
  credits_deducted?: number;
  new_balance?: number;
  xp_awarded?: number;
  level_up: boolean;
  new_level?: number;
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

// ============================================================================
// API Functions
// ============================================================================

/**
 * Get gift catalog
 */
export const getGiftCatalog = async (): Promise<GiftCatalogItem[]> => {
  return api.get<GiftCatalogItem[]>('/gifts/catalog');
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
  return gift.gift_name || (gift as GiftCatalogItem).name || 'Gift';
};

/**
 * Format gift price for display
 */
export const formatGiftPrice = (price: number): string => {
  return `${price} 💎`;
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

// ============================================================================
// Export
// ============================================================================

export const giftService = {
  getGiftCatalog,
  sendGift,
  getGiftHistory,
  getGiftSummary,
  getGift,
  acknowledgeGift,
  getGiftName,
  formatGiftPrice,
  sortGiftsByPrice,
};

export default giftService;
