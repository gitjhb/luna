/**
 * In-App Purchase Service
 * 
 * Handles iOS App Store and Google Play purchases using Expo IAP.
 * 
 * Setup requirements:
 * 1. Install: npx expo install expo-in-app-purchases
 * 2. Configure in app.json/app.config.js
 * 3. Create products in App Store Connect / Google Play Console
 * 
 * Product IDs must match those configured in:
 * - iOS: App Store Connect -> In-App Purchases
 * - Android: Google Play Console -> Products
 */

import { Platform } from 'react-native';
import { api } from './api';

// ============================================================================
// Types
// ============================================================================

export interface IAPProduct {
  productId: string;
  title: string;
  description: string;
  price: string;
  priceAmountMicros: number;
  priceCurrencyCode: string;
  type: 'consumable' | 'subscription';
  // Mapped from backend
  coins?: number;
  bonus?: number;
  tier?: string;
}

export interface IAPPurchase {
  productId: string;
  transactionId: string;
  transactionDate: number;
  transactionReceipt: string;
  purchaseToken?: string; // Android only
}

export interface VerifyResult {
  success: boolean;
  provider: 'apple' | 'google';
  fulfillments: Array<{
    type: 'credit_purchase' | 'subscription';
    status: string;
    credits_added?: number;
    tier?: string;
  }>;
}

// ============================================================================
// Product Configuration
// ============================================================================

// iOS Product IDs (must match App Store Connect)
const IOS_CREDIT_PRODUCTS = [
  'com.luna.credits.60',
  'com.luna.credits.300',
  'com.luna.credits.980',
  'com.luna.credits.1980',
  'com.luna.credits.3280',
  'com.luna.credits.6480',
];

const IOS_SUBSCRIPTION_PRODUCTS = [
  'com.luna.premium.monthly',
  'com.luna.premium.yearly',
  'com.luna.vip.monthly',
  'com.luna.vip.yearly',
];

// Android Product IDs (must match Google Play Console)
const ANDROID_CREDIT_PRODUCTS = [
  'credits_60',
  'credits_300',
  'credits_980',
  'credits_1980',
  'credits_3280',
  'credits_6480',
];

const ANDROID_SUBSCRIPTION_PRODUCTS = [
  'premium_monthly',
  'premium_yearly',
  'vip_monthly',
  'vip_yearly',
];

// ============================================================================
// IAP Service
// ============================================================================

class IAPService {
  private initialized = false;
  private iapModule: any = null;
  private purchaseUpdateSubscription: any = null;
  private purchaseErrorSubscription: any = null;
  
  // Callback for purchase completion
  private onPurchaseComplete?: (purchase: IAPPurchase) => void;
  private onPurchaseError?: (error: Error) => void;
  
  /**
   * Initialize IAP connection
   */
  async initialize(): Promise<boolean> {
    if (this.initialized) return true;
    
    try {
      // Dynamically import to avoid issues on web
      const IAP = await import('expo-in-app-purchases');
      this.iapModule = IAP;
      
      // Connect to store
      await IAP.connectAsync();
      
      // Set up purchase listeners
      IAP.setPurchaseListener(({ responseCode, results, errorCode }) => {
        if (responseCode === IAP.IAPResponseCode.OK) {
          // Purchase successful
          results?.forEach((purchase: any) => {
            this.handlePurchase(purchase);
          });
        } else if (responseCode === IAP.IAPResponseCode.USER_CANCELED) {
          console.log('[IAP] User cancelled purchase');
        } else {
          console.error('[IAP] Purchase error:', errorCode);
          this.onPurchaseError?.(new Error(`Purchase failed: ${errorCode}`));
        }
      });
      
      this.initialized = true;
      console.log('[IAP] Initialized successfully');
      return true;
      
    } catch (error) {
      console.error('[IAP] Initialization failed:', error);
      return false;
    }
  }
  
  /**
   * Disconnect from store
   */
  async disconnect(): Promise<void> {
    if (!this.iapModule || !this.initialized) return;
    
    try {
      await this.iapModule.disconnectAsync();
      this.initialized = false;
      console.log('[IAP] Disconnected');
    } catch (error) {
      console.error('[IAP] Disconnect error:', error);
    }
  }
  
  /**
   * Get available products from the store
   */
  async getProducts(): Promise<IAPProduct[]> {
    if (!await this.ensureInitialized()) return [];
    
    const productIds = Platform.OS === 'ios'
      ? [...IOS_CREDIT_PRODUCTS, ...IOS_SUBSCRIPTION_PRODUCTS]
      : [...ANDROID_CREDIT_PRODUCTS, ...ANDROID_SUBSCRIPTION_PRODUCTS];
    
    try {
      const { results } = await this.iapModule.getProductsAsync(productIds);
      
      return results.map((product: any) => ({
        productId: product.productId,
        title: product.title,
        description: product.description,
        price: product.price,
        priceAmountMicros: product.priceAmountMicros,
        priceCurrencyCode: product.priceCurrencyCode,
        type: this.isSubscription(product.productId) ? 'subscription' : 'consumable',
      }));
      
    } catch (error) {
      console.error('[IAP] Failed to get products:', error);
      return [];
    }
  }
  
  /**
   * Get credit packages (consumable products)
   */
  async getCreditPackages(): Promise<IAPProduct[]> {
    const products = await this.getProducts();
    return products.filter(p => p.type === 'consumable');
  }
  
  /**
   * Get subscription plans
   */
  async getSubscriptions(): Promise<IAPProduct[]> {
    const products = await this.getProducts();
    return products.filter(p => p.type === 'subscription');
  }
  
  /**
   * Purchase a product
   */
  async purchase(
    productId: string,
    onComplete?: (purchase: IAPPurchase) => void,
    onError?: (error: Error) => void,
  ): Promise<void> {
    if (!await this.ensureInitialized()) {
      onError?.(new Error('IAP not initialized'));
      return;
    }
    
    this.onPurchaseComplete = onComplete;
    this.onPurchaseError = onError;
    
    try {
      await this.iapModule.purchaseItemAsync(productId);
      // Result will come through purchase listener
    } catch (error) {
      console.error('[IAP] Purchase initiation failed:', error);
      onError?.(error as Error);
    }
  }
  
  /**
   * Restore purchases (required for App Store)
   */
  async restorePurchases(): Promise<IAPPurchase[]> {
    if (!await this.ensureInitialized()) return [];
    
    try {
      const history = await this.iapModule.getPurchaseHistoryAsync();
      
      // Verify and restore each purchase with backend
      const restored: IAPPurchase[] = [];
      
      for (const purchase of history.results || []) {
        const iapPurchase = this.mapToPurchase(purchase);
        
        try {
          await this.verifyWithBackend(iapPurchase);
          restored.push(iapPurchase);
        } catch (error) {
          console.warn('[IAP] Failed to restore purchase:', purchase.productId);
        }
      }
      
      return restored;
      
    } catch (error) {
      console.error('[IAP] Restore failed:', error);
      return [];
    }
  }
  
  /**
   * Check if product is a subscription
   */
  private isSubscription(productId: string): boolean {
    const subscriptionIds = Platform.OS === 'ios'
      ? IOS_SUBSCRIPTION_PRODUCTS
      : ANDROID_SUBSCRIPTION_PRODUCTS;
    return subscriptionIds.includes(productId);
  }
  
  /**
   * Handle successful purchase
   */
  private async handlePurchase(purchase: any): Promise<void> {
    const iapPurchase = this.mapToPurchase(purchase);
    
    try {
      // Verify with backend and fulfill
      const result = await this.verifyWithBackend(iapPurchase);
      
      // Acknowledge/finish the purchase
      await this.finishPurchase(purchase);
      
      console.log('[IAP] Purchase completed:', iapPurchase.productId, result);
      this.onPurchaseComplete?.(iapPurchase);
      
    } catch (error) {
      console.error('[IAP] Purchase verification failed:', error);
      this.onPurchaseError?.(error as Error);
    }
  }
  
  /**
   * Map store purchase to our format
   */
  private mapToPurchase(purchase: any): IAPPurchase {
    return {
      productId: purchase.productId,
      transactionId: purchase.orderId || purchase.transactionId,
      transactionDate: purchase.purchaseTime || purchase.transactionDate,
      transactionReceipt: purchase.purchaseToken || purchase.transactionReceipt,
      purchaseToken: purchase.purchaseToken,
    };
  }
  
  /**
   * Verify purchase with backend
   */
  private async verifyWithBackend(purchase: IAPPurchase): Promise<VerifyResult> {
    const provider = Platform.OS === 'ios' ? 'apple' : 'google';
    
    const response = await api.post<VerifyResult>('/payment/iap/verify', {
      provider,
      receipt_data: purchase.transactionReceipt,
      product_id: purchase.productId,
      purchase_token: purchase.purchaseToken,
    });
    
    if (!response.success) {
      throw new Error('Verification failed');
    }
    
    return response;
  }
  
  /**
   * Finish/acknowledge purchase (required by stores)
   */
  private async finishPurchase(purchase: any): Promise<void> {
    try {
      await this.iapModule.finishTransactionAsync(purchase, !this.isSubscription(purchase.productId));
    } catch (error) {
      console.error('[IAP] Failed to finish transaction:', error);
    }
  }
  
  /**
   * Ensure IAP is initialized
   */
  private async ensureInitialized(): Promise<boolean> {
    if (this.initialized) return true;
    return await this.initialize();
  }
  
  /**
   * Check if IAP is available on this platform
   */
  isAvailable(): boolean {
    return Platform.OS === 'ios' || Platform.OS === 'android';
  }
  
  /**
   * Get the provider name for current platform
   */
  getProvider(): 'apple' | 'google' {
    return Platform.OS === 'ios' ? 'apple' : 'google';
  }
}

// Singleton export
export const iapService = new IAPService();

// ============================================================================
// Hook for React components
// ============================================================================

import { useState, useEffect, useCallback } from 'react';

export function useIAP() {
  const [products, setProducts] = useState<IAPProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    let mounted = true;
    
    const init = async () => {
      if (!iapService.isAvailable()) {
        setLoading(false);
        return;
      }
      
      const success = await iapService.initialize();
      if (!success || !mounted) {
        setLoading(false);
        return;
      }
      
      const products = await iapService.getProducts();
      if (mounted) {
        setProducts(products);
        setLoading(false);
      }
    };
    
    init();
    
    return () => {
      mounted = false;
    };
  }, []);
  
  const purchase = useCallback(async (productId: string): Promise<boolean> => {
    setError(null);
    setPurchasing(true);
    
    return new Promise((resolve) => {
      iapService.purchase(
        productId,
        () => {
          setPurchasing(false);
          resolve(true);
        },
        (err) => {
          setError(err.message);
          setPurchasing(false);
          resolve(false);
        },
      );
    });
  }, []);
  
  const restore = useCallback(async () => {
    setError(null);
    setLoading(true);
    
    try {
      const restored = await iapService.restorePurchases();
      return restored;
    } catch (err: any) {
      setError(err.message);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);
  
  return {
    products,
    creditPackages: products.filter(p => p.type === 'consumable'),
    subscriptions: products.filter(p => p.type === 'subscription'),
    loading,
    purchasing,
    error,
    purchase,
    restore,
    isAvailable: iapService.isAvailable(),
  };
}

export default iapService;
