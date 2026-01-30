/**
 * Pricing Service
 * 
 * Fetches coin packs and membership plans from backend
 */

import { api } from './api';

export interface CoinPack {
  id: string;
  coins: number;
  price: number;        // USD
  bonusCoins?: number;  // Bonus coins (optional)
  discount?: number;    // Discount percentage (optional)
  popular?: boolean;    // Highlight as popular
}

export interface MembershipPlan {
  id: string;
  tier: 'free' | 'premium' | 'vip';
  name: string;
  price: number;              // USD per month (0 for free)
  dailyCredits: number;       // Credits added per day
  features: string[];         // Feature list
  highlighted?: boolean;      // Highlight this plan
}

export interface PricingConfig {
  coinPacks: CoinPack[];
  membershipPlans: MembershipPlan[];
}

// Default config (fallback if backend is unavailable)
const defaultPricingConfig: PricingConfig = {
  coinPacks: [
    { id: 'pack_60', coins: 60, price: 0.99 },
    { id: 'pack_300', coins: 300, price: 4.99, bonusCoins: 30 },
    { id: 'pack_980', coins: 980, price: 14.99, bonusCoins: 110, popular: true },
    { id: 'pack_1980', coins: 1980, price: 29.99, bonusCoins: 260 },
    { id: 'pack_3280', coins: 3280, price: 49.99, bonusCoins: 600 },
    { id: 'pack_6480', coins: 6480, price: 99.99, bonusCoins: 1600, discount: 20 },
  ],
  membershipPlans: [
    {
      id: 'free',
      tier: 'free',
      name: 'Free',
      price: 0,
      dailyCredits: 10,
      features: [
        '10 daily credits',
        'Basic characters',
        'Standard response speed',
      ],
    },
    {
      id: 'premium',
      tier: 'premium',
      name: 'Premium',
      price: 9.99,
      dailyCredits: 100,
      highlighted: true,
      features: [
        '100 daily credits',
        'All characters unlocked',
        'Fast response speed',
        'Long-term memory',
        'Spicy mode',
      ],
    },
    {
      id: 'vip',
      tier: 'vip',
      name: 'VIP',
      price: 19.99,
      dailyCredits: 300,
      features: [
        '300 daily credits',
        'All characters unlocked',
        'Priority response speed',
        'Extended memory (10x)',
        'Spicy mode',
        'Early access to new features',
      ],
    },
  ],
};

// Cache the pricing config
let cachedConfig: PricingConfig | null = null;
let cacheTimestamp: number = 0;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

export const pricingService = {
  /**
   * Get pricing configuration (coin packs + membership plans)
   */
  async getConfig(): Promise<PricingConfig> {
    // Return cached config if still valid
    if (cachedConfig && Date.now() - cacheTimestamp < CACHE_DURATION) {
      return cachedConfig;
    }

    try {
      const config = await api.get<PricingConfig>('/pricing/config');
      cachedConfig = config;
      cacheTimestamp = Date.now();
      return config;
    } catch (error) {
      console.log('Failed to fetch pricing config, using defaults:', error);
      return defaultPricingConfig;
    }
  },

  /**
   * Get coin packs only
   */
  async getCoinPacks(): Promise<CoinPack[]> {
    const config = await this.getConfig();
    return config.coinPacks;
  },

  /**
   * Get membership plans only
   */
  async getMembershipPlans(): Promise<MembershipPlan[]> {
    const config = await this.getConfig();
    return config.membershipPlans;
  },

  /**
   * Clear cached config (e.g., after purchase)
   */
  clearCache(): void {
    cachedConfig = null;
    cacheTimestamp = 0;
  },
};
