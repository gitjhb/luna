/**
 * Wallet & Payment Service
 * 
 * Handles credit balance, transactions, and purchases.
 */

import { api, mockApi, shouldUseMock } from './api';
import { Wallet } from '../store/userStore';
import { CreditPackage, SubscriptionPlan, Transaction } from '../types';

interface PurchaseCreditsRequest {
  sku: string;
  receipt: string; // Platform-specific receipt
}

interface SubscribeRequest {
  sku: string;
  receipt: string;
}

export const walletService = {
  /**
   * Get wallet balance
   */
  getBalance: async (): Promise<Wallet> => {
    if (shouldUseMock()) {
      await mockApi.delay(500);
      return mockApi.responses.login.wallet;
    }
    
    return api.get<Wallet>('/wallet/balance');
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
        {
          sku: 'credits_10',
          name: 'Starter Pack',
          credits: 10,
          priceUsd: 0.99,
          discountPercentage: 0,
        },
        {
          sku: 'credits_50',
          name: 'Popular Pack',
          credits: 50,
          priceUsd: 4.99,
          discountPercentage: 0,
          popular: true,
        },
        {
          sku: 'credits_100',
          name: 'Value Pack',
          credits: 110,
          priceUsd: 8.99,
          discountPercentage: 10,
        },
        {
          sku: 'credits_500',
          name: 'Best Value',
          credits: 600,
          priceUsd: 39.99,
          discountPercentage: 20,
        },
      ];
    }
    
    return api.get<CreditPackage[]>('/market/products?type=credits');
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
          features: [
            '100 daily free credits',
            'RAG memory system',
            'Spicy Mode access',
            '30% discount on credits',
          ],
          popular: true,
        },
        {
          sku: 'vip_monthly',
          name: 'VIP',
          tier: 'vip',
          priceUsd: 29.99,
          billingPeriod: 'monthly',
          bonusCredits: 1000,
          features: [
            '500 daily free credits',
            'Advanced RAG memory',
            'All Spicy characters',
            '50% discount on credits',
            'Priority support',
          ],
        },
      ];
    }
    
    return api.get<SubscriptionPlan[]>('/market/products?type=subscription');
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
    
    return api.post<Wallet>('/market/buy_credits', data);
  },
  
  /**
   * Subscribe to plan
   */
  subscribe: async (data: SubscribeRequest): Promise<{ success: boolean }> => {
    if (shouldUseMock()) {
      await mockApi.delay(1000);
      return { success: true };
    }
    
    return api.post<{ success: boolean }>('/market/subscribe', data);
  },
};
