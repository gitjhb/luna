/**
 * Wallet & Payment Service
 * 
 * Unified payment service with multiple providers:
 * - Stripe (Web)
 * - Apple IAP (iOS)
 * - Google Play (Android)
 * - Test Mode (Fallback/Development)
 * 
 * Set PAYMENT_TEST_MODE=true for testing without real charges.
 */

import { Platform } from 'react-native';
import { api } from './api';
import { Wallet } from '../store/userStore';
import { CreditPackage, SubscriptionPlan, Transaction } from '../types';
import { iapService, useIAP } from './iapService';
import { stripeService, useStripe } from './stripeService';

// TEST MODE for payments - set to false in production
// Can be controlled via environment variable
const PAYMENT_TEST_MODE = process.env.EXPO_PUBLIC_PAYMENT_TEST_MODE === 'true' || __DEV__;

// Determine which payment provider to use
const getPaymentProvider = (): 'stripe' | 'apple' | 'google' | 'test' => {
  if (PAYMENT_TEST_MODE) return 'test';
  if (Platform.OS === 'ios') return 'apple';
  if (Platform.OS === 'android') return 'google';
  return 'stripe'; // Web
};

// Map backend package to frontend format
const mapPackage = (data: any): CreditPackage => ({
  sku: data.package_id || data.sku,
  name: data.label || data.name || `${data.credits} Credits`,
  credits: data.credits,
  priceUsd: data.price_usd ?? data.priceUsd ?? 0,
  discountPercentage: data.discount_percent ?? data.discountPercentage ?? 0,
  popular: data.popular || data.credits === 500,
});

// Map backend plan to frontend format
const mapPlan = (data: any): SubscriptionPlan => ({
  sku: data.plan_id || data.sku,
  name: data.name,
  tier: data.tier || 'premium',
  priceUsd: data.price_usd ?? data.priceUsd ?? 0,
  billingPeriod: data.billing_period || data.billingPeriod || 'monthly',
  bonusCredits: data.bonus_credits ?? data.bonusCredits ?? 0,
  features: data.features || [],
  popular: data.popular || data.tier === 'premium',
});

// Map backend transaction to frontend format
const mapTransaction = (data: any): Transaction => ({
  transactionId: data.transaction_id || data.transactionId || data.id,
  transactionType: data.transaction_type || data.transactionType || 'deduction',
  amount: data.amount ?? data.credits ?? 0,
  balanceBefore: data.balance_before ?? data.balanceBefore ?? 0,
  balanceAfter: data.balance_after ?? data.balanceAfter ?? 0,
  description: data.description || '',
  createdAt: data.created_at || data.createdAt || new Date().toISOString(),
});

// Test mode mock data
const TEST_PACKAGES: CreditPackage[] = [
  { sku: 'credits_100', name: '100 积分', credits: 100, priceUsd: 1.99, discountPercentage: 0 },
  { sku: 'credits_500', name: '500 积分', credits: 500, priceUsd: 7.99, discountPercentage: 20, popular: true },
  { sku: 'credits_1500', name: '1500 积分', credits: 1500, priceUsd: 19.99, discountPercentage: 33 },
];

const TEST_PLANS: SubscriptionPlan[] = [
  {
    sku: 'premium_monthly',
    name: 'Premium',
    tier: 'premium',
    priceUsd: 9.99,
    billingPeriod: 'monthly',
    bonusCredits: 200,
    features: ['100 daily credits', 'Memory system', 'Spicy Mode'],
    popular: true,
  },
  {
    sku: 'vip_monthly',
    name: 'VIP',
    tier: 'vip',
    priceUsd: 29.99,
    billingPeriod: 'monthly',
    bonusCredits: 1000,
    features: ['500 daily credits', 'Advanced memory', 'All characters', 'Priority support'],
  },
];

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const walletService = {
  /**
   * Get wallet balance (real API)
   */
  getBalance: async (): Promise<Wallet> => {
    try {
      const data = await api.get<any>('/payment/wallet');
      return {
        totalCredits: data.total_credits ?? data.totalCredits ?? 0,
        dailyFreeCredits: data.daily_free_credits ?? data.dailyFreeCredits ?? 0,
        purchedCredits: data.purchased_credits ?? data.purchedCredits ?? 0,
        bonusCredits: data.bonus_credits ?? data.bonusCredits ?? 0,
        dailyCreditsLimit: data.daily_credits_limit ?? data.dailyCreditsLimit ?? 10,
      };
    } catch (e) {
      // Return default wallet if API fails
      return {
        totalCredits: 100,
        dailyFreeCredits: 10,
        purchedCredits: 0,
        bonusCredits: 0,
        dailyCreditsLimit: 50,
      };
    }
  },
  
  /**
   * Get transaction history (real API)
   */
  getTransactions: async (limit: number = 50, offset: number = 0): Promise<Transaction[]> => {
    try {
      const data = await api.get<any[]>('/wallet/transactions', { limit, offset });
      return data.map(mapTransaction);
    } catch (e) {
      return [];
    }
  },
  
  /**
   * Get available credit packages (TEST MODE)
   */
  getCreditPackages: async (): Promise<CreditPackage[]> => {
    if (PAYMENT_TEST_MODE) {
      await delay(300);
      return TEST_PACKAGES;
    }
    const data = await api.get<any[]>('/market/packages');
    return data.map(mapPackage);
  },
  
  /**
   * Get subscription plans (TEST MODE)
   */
  getSubscriptionPlans: async (): Promise<SubscriptionPlan[]> => {
    if (PAYMENT_TEST_MODE) {
      await delay(300);
      return TEST_PLANS;
    }
    const data = await api.get<any[]>('/market/plans');
    return data.map(mapPlan);
  },
  
  /**
   * Purchase credits (TEST MODE - no real charge)
   */
  purchaseCredits: async (sku: string): Promise<{ success: boolean; credits: number }> => {
    if (PAYMENT_TEST_MODE) {
      await delay(1000);
      const pkg = TEST_PACKAGES.find(p => p.sku === sku);
      console.log('[Payment] TEST MODE: Simulated purchase', sku, pkg?.credits, 'credits');
      return { success: true, credits: pkg?.credits || 0 };
    }
    return api.post<{ success: boolean; credits: number }>('/wallet/purchase', { sku });
  },
  
  /**
   * Subscribe to plan (TEST MODE - no real charge)
   */
  subscribe: async (sku: string): Promise<{ success: boolean; tier: string }> => {
    if (PAYMENT_TEST_MODE) {
      await delay(1000);
      const plan = TEST_PLANS.find(p => p.sku === sku);
      console.log('[Payment] TEST MODE: Simulated subscription', sku, plan?.tier);
      return { success: true, tier: plan?.tier || 'premium' };
    }
    return api.post<{ success: boolean; tier: string }>(`/wallet/subscribe/${sku}`, {});
  },
  
  /**
   * Check if payment is in test mode
   */
  isTestMode: () => PAYMENT_TEST_MODE,
};
