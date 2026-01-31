/**
 * Payment Service
 * 
 * Handles all payment-related API calls:
 * - Wallet management
 * - Credit purchases
 * - Subscriptions
 * - Gift sending
 */

import { api } from './api';

// ============================================================================
// Types
// ============================================================================

export interface Wallet {
  user_id: string;
  total_credits: number;
  purchased_credits: number;
  bonus_credits: number;
  daily_free_credits: number;
  daily_credits_used?: number;
}

export interface Subscription {
  user_id: string;
  tier: 'free' | 'premium' | 'vip';
  started_at: string | null;
  expires_at: string | null;
  auto_renew: boolean;
  is_active: boolean;
}

export interface SubscriptionPlan {
  id: string;
  name: string;
  tier: 'free' | 'premium' | 'vip';
  price_monthly: number;
  price_yearly: number;
  daily_credits: number;
  features: string[];
  is_current?: boolean;
}

export interface CreditPackage {
  id: string;
  coins: number;
  price: number;
  bonus: number;
}

export interface Transaction {
  id: string;
  user_id: string;
  transaction_type: string;
  amount: number;
  credits: number;
  description: string;
  status: string;
  created_at: string;
}

export interface PurchaseResult {
  success: boolean;
  credits_added: number;
  wallet: Wallet;
  transaction: Transaction;
}

export interface SubscribeResult {
  success: boolean;
  subscription: Subscription;
  transaction: Transaction;
}

export interface GiftResult {
  success: boolean;
  credits_deducted: number;
  xp_awarded: number;
  wallet: Wallet;
  transaction: Transaction;
}

export interface PaymentConfig {
  mock_mode: boolean;
  credit_packages: CreditPackage[];
  subscription_plans: SubscriptionPlan[];
}

// ============================================================================
// Service
// ============================================================================

export const paymentService = {
  /**
   * Get payment configuration
   */
  getConfig: async (): Promise<PaymentConfig> => {
    return await api.get('/payment/config');
  },

  /**
   * Get available subscription plans for upgrade
   */
  getAvailablePlans: async (): Promise<{ plans: SubscriptionPlan[] }> => {
    return await api.get('/payment/plans');
  },

  // ========================================================================
  // Wallet
  // ========================================================================

  /**
   * Get current user's wallet
   */
  getWallet: async (): Promise<Wallet> => {
    return await api.get('/payment/wallet');
  },

  /**
   * Add credits to wallet (test/mock mode only)
   */
  addCredits: async (amount: number): Promise<{ success: boolean; wallet: Wallet }> => {
    return await api.post(`/payment/wallet/add-credits?amount=${amount}`);
  },

  // ========================================================================
  // Purchases
  // ========================================================================

  /**
   * Purchase a credit package
   */
  purchaseCredits: async (
    packageId: string,
    paymentProvider: string = 'mock',
    providerTransactionId?: string
  ): Promise<PurchaseResult> => {
    return await api.post('/payment/purchase', {
      package_id: packageId,
      payment_provider: paymentProvider,
      provider_transaction_id: providerTransactionId,
    });
  },

  // ========================================================================
  // Subscriptions
  // ========================================================================

  /**
   * Get current subscription status
   */
  getSubscription: async (): Promise<Subscription> => {
    return await api.get('/payment/subscription');
  },

  /**
   * Subscribe to a plan
   */
  subscribe: async (
    planId: string,
    billingPeriod: 'monthly' | 'yearly' = 'monthly',
    paymentProvider: string = 'mock',
    providerTransactionId?: string
  ): Promise<SubscribeResult> => {
    return await api.post('/payment/subscribe', {
      plan_id: planId,
      billing_period: billingPeriod,
      payment_provider: paymentProvider,
      provider_transaction_id: providerTransactionId,
    });
  },

  /**
   * Cancel subscription
   */
  cancelSubscription: async (): Promise<{ success: boolean; message: string }> => {
    return await api.post('/payment/subscription/cancel');
  },

  // ========================================================================
  // Gifts
  // ========================================================================

  /**
   * Send a gift to a character
   * Note: Uses /gifts/send API with idempotency support
   */
  sendGift: async (
    characterId: string,
    giftType: string,
    giftPrice: number,
    xpReward: number,
    sessionId?: string
  ): Promise<GiftResult> => {
    // Generate idempotency key for deduplication
    const idempotencyKey = `gift_${Date.now()}_${Math.random().toString(36).substring(7)}`;
    
    return await api.post('/gifts/send', {
      character_id: characterId,
      gift_type: giftType,
      idempotency_key: idempotencyKey,
      session_id: sessionId,
      trigger_ai_response: true,
    });
  },

  // ========================================================================
  // Transactions
  // ========================================================================

  /**
   * Get transaction history
   */
  getTransactions: async (
    limit: number = 20,
    offset: number = 0
  ): Promise<{ transactions: Transaction[]; total: number }> => {
    return await api.get('/payment/transactions', { limit, offset });
  },
};

export default paymentService;
