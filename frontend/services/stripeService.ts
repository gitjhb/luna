/**
 * Stripe Payment Service (Web)
 * 
 * Handles Stripe payments for web platform.
 * Uses Stripe Checkout for secure, hosted payment flow.
 * 
 * Setup:
 * 1. Get publishable key from Stripe Dashboard
 * 2. Set EXPO_PUBLIC_STRIPE_PUBLISHABLE_KEY in .env
 */

import { Platform } from 'react-native';
import * as Linking from 'expo-linking';
import { api } from './api';

// ============================================================================
// Types
// ============================================================================

export interface StripeConfig {
  enabled: boolean;
  publishable_key: string | null;
}

export interface CheckoutSession {
  checkout_url: string;
  session_id: string;
  package_id?: string;
  plan_id?: string;
  coins?: number;
  bonus?: number;
  tier?: string;
}

export interface CreditPackage {
  id: string;
  name: string;
  coins: number;
  bonus: number;
  price: number;
  priceDisplay: string;
}

export interface SubscriptionPlan {
  id: string;
  name: string;
  tier: string;
  price_monthly: number;
  price_yearly: number;
  daily_credits: number;
  features: string[];
}

// ============================================================================
// Stripe Payment Links (pre-built links from Stripe Dashboard)
// ============================================================================

const STRIPE_PAYMENT_LINKS = {
  // Test mode payment link
  test_subscription: 'https://buy.stripe.com/test_aFa6oGcuLf0Z92gc9c2Fa02',
  // TODO: Add production payment links
  // prod_subscription: 'https://buy.stripe.com/...',
};

// ============================================================================
// Credit Packages (matching backend)
// ============================================================================

const CREDIT_PACKAGES: CreditPackage[] = [
  { id: 'pack_60', name: '60 积分', coins: 60, bonus: 0, price: 0.99, priceDisplay: '$0.99' },
  { id: 'pack_300', name: '300 积分', coins: 300, bonus: 30, price: 4.99, priceDisplay: '$4.99' },
  { id: 'pack_980', name: '980 积分', coins: 980, bonus: 110, price: 14.99, priceDisplay: '$14.99' },
  { id: 'pack_1980', name: '1980 积分', coins: 1980, bonus: 260, price: 29.99, priceDisplay: '$29.99' },
  { id: 'pack_3280', name: '3280 积分', coins: 3280, bonus: 600, price: 49.99, priceDisplay: '$49.99' },
  { id: 'pack_6480', name: '6480 积分', coins: 6480, bonus: 1600, price: 99.99, priceDisplay: '$99.99' },
];

const SUBSCRIPTION_PLANS = [
  {
    id: 'premium_monthly',
    name: 'Premium',
    tier: 'premium',
    price: 9.99,
    period: 'monthly',
    daily_credits: 100,
    features: ['100 daily credits', 'All characters unlocked', 'Long-term memory', '成人内容 (NSFW)'],
  },
  {
    id: 'premium_yearly',
    name: 'Premium (年付)',
    tier: 'premium',
    price: 79.99,
    period: 'yearly',
    daily_credits: 100,
    features: ['100 daily credits', 'All characters unlocked', 'Long-term memory', '成人内容 (NSFW)', '2个月免费'],
  },
  {
    id: 'vip_monthly',
    name: 'VIP',
    tier: 'vip',
    price: 19.99,
    period: 'monthly',
    daily_credits: 300,
    features: ['300 daily credits', 'All characters unlocked', 'Extended memory (10x)', 'Priority response', 'Early access'],
  },
  {
    id: 'vip_yearly',
    name: 'VIP (年付)',
    tier: 'vip',
    price: 149.99,
    period: 'yearly',
    daily_credits: 300,
    features: ['300 daily credits', 'All characters unlocked', 'Extended memory (10x)', 'Priority response', 'Early access', '2个月免费'],
  },
];

// ============================================================================
// Stripe Service
// ============================================================================

class StripeService {
  private config: StripeConfig | null = null;
  
  /**
   * Get Stripe configuration from backend
   */
  async getConfig(): Promise<StripeConfig> {
    if (this.config) return this.config;
    
    try {
      this.config = await api.get<StripeConfig>('/payment/stripe/config');
      return this.config;
    } catch (error) {
      console.error('[Stripe] Failed to get config:', error);
      return { enabled: false, publishable_key: null };
    }
  }
  
  /**
   * Check if Stripe is available
   */
  async isEnabled(): Promise<boolean> {
    const config = await this.getConfig();
    return config.enabled;
  }
  
  /**
   * Check if Stripe should be used (web only)
   */
  isAvailable(): boolean {
    return Platform.OS === 'web';
  }
  
  /**
   * Get credit packages
   */
  getCreditPackages(): CreditPackage[] {
    return CREDIT_PACKAGES;
  }
  
  /**
   * Get subscription plans
   */
  getSubscriptionPlans() {
    return SUBSCRIPTION_PLANS;
  }
  
  /**
   * Create checkout session for credit purchase
   */
  async createCheckoutSession(
    packageId: string,
    successUrl?: string,
    cancelUrl?: string,
  ): Promise<CheckoutSession> {
    // Default URLs using Expo Linking
    const baseUrl = Platform.OS === 'web' 
      ? window.location.origin 
      : Linking.createURL('/');
    
    const response = await api.post<CheckoutSession>('/payment/stripe/checkout', {
      package_id: packageId,
      success_url: successUrl || `${baseUrl}/payment/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: cancelUrl || `${baseUrl}/payment/cancel`,
    });
    
    return response;
  }
  
  /**
   * Create subscription checkout session
   */
  async createSubscriptionCheckout(
    planId: string,
    successUrl?: string,
    cancelUrl?: string,
  ): Promise<CheckoutSession> {
    const baseUrl = Platform.OS === 'web' 
      ? window.location.origin 
      : Linking.createURL('/');
    
    const response = await api.post<CheckoutSession>('/payment/stripe/subscribe', {
      plan_id: planId,
      success_url: successUrl || `${baseUrl}/subscription/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: cancelUrl || `${baseUrl}/subscription/cancel`,
    });
    
    return response;
  }
  
  /**
   * Purchase credits (redirect to Stripe Checkout)
   */
  async purchaseCredits(packageId: string): Promise<void> {
    const session = await this.createCheckoutSession(packageId);
    
    if (Platform.OS === 'web') {
      // Redirect to Stripe Checkout
      window.location.href = session.checkout_url;
    } else {
      // Open in browser for mobile (fallback)
      await Linking.openURL(session.checkout_url);
    }
  }
  
  /**
   * Subscribe to a plan (redirect to Stripe Checkout)
   */
  async subscribe(planId: string): Promise<void> {
    const session = await this.createSubscriptionCheckout(planId);
    
    if (Platform.OS === 'web') {
      window.location.href = session.checkout_url;
    } else {
      await Linking.openURL(session.checkout_url);
    }
  }
  
  /**
   * Open pre-built payment link (for quick purchase without backend)
   */
  async openPaymentLink(linkKey: keyof typeof STRIPE_PAYMENT_LINKS = 'test_subscription'): Promise<void> {
    const url = STRIPE_PAYMENT_LINKS[linkKey];
    if (!url) {
      throw new Error(`Payment link not found: ${linkKey}`);
    }
    
    if (Platform.OS === 'web') {
      window.location.href = url;
    } else {
      await Linking.openURL(url);
    }
  }
  
  /**
   * Get available payment links
   */
  getPaymentLinks() {
    return STRIPE_PAYMENT_LINKS;
  }
  
  /**
   * Open customer portal for subscription management
   */
  async openCustomerPortal(returnUrl?: string): Promise<void> {
    const baseUrl = Platform.OS === 'web' 
      ? window.location.origin 
      : Linking.createURL('/');
    
    const response = await api.post<{ portal_url: string }>(
      '/payment/stripe/portal',
      {},
      { params: { return_url: returnUrl || `${baseUrl}/profile` } }
    );
    
    if (Platform.OS === 'web') {
      window.location.href = response.portal_url;
    } else {
      await Linking.openURL(response.portal_url);
    }
  }
}

// Singleton export
export const stripeService = new StripeService();

// ============================================================================
// Hook for React components
// ============================================================================

import { useState, useEffect, useCallback } from 'react';

export function useStripe() {
  const [enabled, setEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    const init = async () => {
      const isEnabled = await stripeService.isEnabled();
      setEnabled(isEnabled);
      setLoading(false);
    };
    init();
  }, []);
  
  const purchaseCredits = useCallback(async (packageId: string) => {
    setError(null);
    setPurchasing(true);
    
    try {
      await stripeService.purchaseCredits(packageId);
      // User will be redirected, this won't return
    } catch (err: any) {
      setError(err.message);
      setPurchasing(false);
    }
  }, []);
  
  const subscribe = useCallback(async (planId: string) => {
    setError(null);
    setPurchasing(true);
    
    try {
      await stripeService.subscribe(planId);
    } catch (err: any) {
      setError(err.message);
      setPurchasing(false);
    }
  }, []);
  
  return {
    enabled,
    loading,
    purchasing,
    error,
    creditPackages: stripeService.getCreditPackages(),
    subscriptionPlans: stripeService.getSubscriptionPlans(),
    paymentLinks: stripeService.getPaymentLinks(),
    purchaseCredits,
    subscribe,
    openPaymentLink: stripeService.openPaymentLink.bind(stripeService),
    openPortal: stripeService.openCustomerPortal.bind(stripeService),
    isAvailable: stripeService.isAvailable(),
  };
}

export default stripeService;
