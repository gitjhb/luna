/**
 * Wallet & Payment Service
 */

import { api, mockApi, shouldUseMock } from './api';
import { Wallet } from '../store/userStore';
import { CreditPackage, SubscriptionPlan, Transaction } from '../types';

interface PurchaseCreditsRequest {
  sku: string;
  receipt: string;
}

interface SubscribeRequest {
  sku: string;
  receipt: string;
}

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

export const walletService = {
  /**
   * Get wallet balance
   */
  getBalance: async (): Promise<Wallet> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      return mockApi.responses.login.wallet;
    }
    
    const data = await api.get<any>('/wallet/balance');
    return {
      totalCredits: data.total_credits ?? data.totalCredits ?? 0,
      dailyFreeCredits: data.daily_free_credits ?? data.dailyFreeCredits ?? 0,
      purchedCredits: data.purchased_credits ?? data.purchedCredits ?? 0,
      bonusCredits: data.bonus_credits ?? data.bonusCredits ?? 0,
      dailyCreditsLimit: data.daily_credits_limit ?? data.dailyCreditsLimit ?? 10,
    };
  },
  
  /**
   * Get transaction history
   */
  getTransactions: async (limit: number = 50, offset: number = 0): Promise<Transaction[]> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      return [
        {
          transactionId: 'txn-1',
          transactionType: 'daily_refresh',
          amount: 10,
          balanceBefore: 0,
          balanceAfter: 10,
          description: 'Daily free credits',
          createdAt: new Date().toISOString(),
        },
      ];
    }
    
    return api.get<Transaction[]>('/wallet/transactions', { limit, offset });
  },
  
  /**
   * Get available credit packages
   */
  getCreditPackages: async (): Promise<CreditPackage[]> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      return [
        { sku: 'credits_100', name: '100 积分', credits: 100, priceUsd: 1.99, discountPercentage: 0 },
        { sku: 'credits_500', name: '500 积分', credits: 500, priceUsd: 7.99, discountPercentage: 20, popular: true },
        { sku: 'credits_1500', name: '1500 积分', credits: 1500, priceUsd: 19.99, discountPercentage: 33 },
      ];
    }
    
    const data = await api.get<any[]>('/market/packages');
    return data.map(mapPackage);
  },
  
  /**
   * Get subscription plans
   */
  getSubscriptionPlans: async (): Promise<SubscriptionPlan[]> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      return [
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
    }
    
    const data = await api.get<any[]>('/market/plans');
    return data.map(mapPlan);
  },
  
  /**
   * Purchase credits
   */
  purchaseCredits: async (data: PurchaseCreditsRequest): Promise<Wallet> => {
    if (shouldUseMock()) {
      await mockApi.delay(1000);
      return {
        ...mockApi.responses.login.wallet,
        totalCredits: mockApi.responses.login.wallet.totalCredits + 50,
        purchedCredits: mockApi.responses.login.wallet.purchedCredits + 50,
      };
    }
    
    return api.post<Wallet>('/wallet/purchase', data);
  },
  
  /**
   * Subscribe to plan
   */
  subscribe: async (data: SubscribeRequest): Promise<{ success: boolean }> => {
    if (shouldUseMock()) {
      await mockApi.delay(1000);
      return { success: true };
    }
    
    return api.post<{ success: boolean }>(`/wallet/subscribe/${data.sku}`, { receipt: data.receipt });
  },
};
