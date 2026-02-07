/**
 * IAP Service - In-App Purchases via react-native-iap
 * 
 * Handles StoreKit (iOS) and Play Billing (Android) subscriptions
 */

import { Platform, Alert } from 'react-native';
import Constants from 'expo-constants';

// 检测是否在 Expo Go 中运行
const isExpoGo = Constants.appOwnership === 'expo';

// 调试日志
console.log('[IAP] === Debug Info ===');
console.log('[IAP] appOwnership:', Constants.appOwnership);
console.log('[IAP] isExpoGo:', isExpoGo);
console.log('[IAP] executionEnvironment:', Constants.executionEnvironment);

// 动态导入 IAP（只在 dev build 中可用）
let iapModule: any = null;
if (!isExpoGo) {
  try {
    iapModule = require('react-native-iap');
    console.log('[IAP] react-native-iap loaded successfully');
  } catch (e) {
    console.warn('[IAP] react-native-iap not available:', e);
  }
} else {
  console.log('[IAP] Skipping IAP module load (Expo Go detected)');
}

// 临时调试弹窗（上线前删除）
setTimeout(() => {
  Alert.alert(
    '🔧 IAP Debug',
    `appOwnership: ${Constants.appOwnership || 'null'}\n` +
    `isExpoGo: ${isExpoGo}\n` +
    `iapModule: ${iapModule ? '✅ loaded' : '❌ null'}\n` +
    `Platform: ${Platform.OS}`
  );
}, 2000);

// 解构（如果可用）
const {
  initConnection,
  endConnection,
  getSubscriptions,
  requestSubscription,
  purchaseUpdatedListener,
  purchaseErrorListener,
  finishTransaction,
  getAvailablePurchases,
  clearTransactionIOS,
} = iapModule || {};

// ============================================================================
// Product IDs - Update these with your actual App Store Connect / Play Console IDs
// ============================================================================

export const SUBSCRIPTION_SKUS = Platform.select({
  ios: [
    'luna_premium_monthly',
    'luna_vip_monthly',
    // Add yearly if needed:
    // 'luna_premium_yearly',
    // 'luna_vip_yearly',
  ],
  android: [
    'luna_premium_monthly',
    'luna_vip_monthly',
  ],
  default: [],
}) as string[];

// Map product ID to tier
export const SKU_TO_TIER: Record<string, 'premium' | 'vip'> = {
  'luna_premium_monthly': 'premium',
  'luna_premium_yearly': 'premium',
  'luna_vip_monthly': 'vip',
  'luna_vip_yearly': 'vip',
};

// ============================================================================
// Types
// ============================================================================

export interface IAPProduct {
  productId: string;
  title: string;
  description: string;
  price: string;
  priceAmount: number;
  currency: string;
  tier: 'premium' | 'vip';
}

export interface IAPPurchaseResult {
  success: boolean;
  productId: string;
  transactionId: string;
  receipt: string;
  tier: 'premium' | 'vip';
}

// ============================================================================
// Service State
// ============================================================================

let isInitialized = false;
let purchaseUpdateSubscription: any = null;
let purchaseErrorSubscription: any = null;

// Callbacks for purchase events
let onPurchaseSuccess: ((result: IAPPurchaseResult) => void) | null = null;
let onPurchaseError: ((error: PurchaseError) => void) | null = null;

// ============================================================================
// Service
// ============================================================================

export const iapService = {
  /**
   * Initialize IAP connection - call once on app start
   */
  init: async (): Promise<boolean> => {
    // Expo Go 中跳过 IAP
    if (isExpoGo || !iapModule) {
      console.log('[IAP] Skipping init (Expo Go or module unavailable)');
      return false;
    }
    
    if (isInitialized) return true;

    try {
      const result = await initConnection();
      console.log('[IAP] Connection initialized:', result);

      // iOS: Clear any pending transactions from previous sessions
      if (Platform.OS === 'ios') {
        await clearTransactionIOS();
      }

      // Set up purchase listeners
      purchaseUpdateSubscription = purchaseUpdatedListener(
        async (purchase: Purchase | SubscriptionPurchase) => {
          console.log('[IAP] Purchase updated:', purchase.productId);

          const receipt = Platform.OS === 'ios'
            ? purchase.transactionReceipt
            : (purchase as any).purchaseToken;

          if (receipt) {
            // Finish the transaction
            try {
              await finishTransaction({ purchase, isConsumable: false });
              console.log('[IAP] Transaction finished');

              // Call success callback
              if (onPurchaseSuccess) {
                onPurchaseSuccess({
                  success: true,
                  productId: purchase.productId,
                  transactionId: purchase.transactionId || '',
                  receipt: receipt,
                  tier: SKU_TO_TIER[purchase.productId] || 'premium',
                });
              }
            } catch (err) {
              console.error('[IAP] Failed to finish transaction:', err);
            }
          }
        }
      );

      purchaseErrorSubscription = purchaseErrorListener((error: PurchaseError) => {
        console.warn('[IAP] Purchase error:', error);
        if (onPurchaseError) {
          onPurchaseError(error);
        }
      });

      isInitialized = true;
      return true;
    } catch (err) {
      console.error('[IAP] Failed to initialize:', err);
      return false;
    }
  },

  /**
   * Clean up IAP connection - call on app unmount
   */
  cleanup: async (): Promise<void> => {
    if (isExpoGo || !iapModule) return;
    
    if (purchaseUpdateSubscription) {
      purchaseUpdateSubscription.remove();
      purchaseUpdateSubscription = null;
    }
    if (purchaseErrorSubscription) {
      purchaseErrorSubscription.remove();
      purchaseErrorSubscription = null;
    }

    await endConnection();
    isInitialized = false;
    console.log('[IAP] Connection ended');
  },

  /**
   * Set purchase callbacks
   */
  setCallbacks: (
    onSuccess: (result: IAPPurchaseResult) => void,
    onError: (error: PurchaseError) => void
  ) => {
    onPurchaseSuccess = onSuccess;
    onPurchaseError = onError;
  },

  /**
   * Get available subscription products
   */
  getProducts: async (): Promise<IAPProduct[]> => {
    if (isExpoGo || !iapModule) {
      console.log('[IAP] Returning empty products (Expo Go)');
      return [];
    }
    
    if (!isInitialized) {
      await iapService.init();
    }

    console.log('[IAP] Fetching subscriptions for SKUs:', SUBSCRIPTION_SKUS);
    
    try {
      const subscriptions = await getSubscriptions({ skus: SUBSCRIPTION_SKUS });
      console.log('[IAP] Fetched subscriptions:', subscriptions.length);
      console.log('[IAP] Subscriptions data:', JSON.stringify(subscriptions, null, 2));

      return subscriptions.map((sub: any) => ({
        productId: sub.productId,
        title: sub.title || sub.productId,
        description: sub.description || '',
        price: sub.localizedPrice || `$${sub.price}`,
        priceAmount: parseFloat(sub.price || '0'),
        currency: sub.currency || 'USD',
        tier: SKU_TO_TIER[sub.productId] || 'premium',
      }));
    } catch (err) {
      console.error('[IAP] Failed to get products:', err);
      return [];
    }
  },

  /**
   * Purchase a subscription
   */
  purchaseSubscription: async (productId: string): Promise<void> => {
    if (isExpoGo || !iapModule) {
      throw new Error('IAP 在 Expo Go 中不可用，请使用 dev build');
    }
    
    if (!isInitialized) {
      await iapService.init();
    }

    console.log('[IAP] Requesting subscription:', productId);

    try {
      if (Platform.OS === 'ios') {
        await requestSubscription({ sku: productId });
      } else {
        // Android requires offer token for subscriptions
        const subscriptions = await getSubscriptions({ skus: [productId] });
        const sub = subscriptions[0];
        
        if (sub && (sub as any).subscriptionOfferDetails?.length > 0) {
          const offerToken = (sub as any).subscriptionOfferDetails[0].offerToken;
          await requestSubscription({
            sku: productId,
            subscriptionOffers: [{ sku: productId, offerToken }],
          });
        } else {
          await requestSubscription({ sku: productId });
        }
      }
    } catch (err: any) {
      console.error('[IAP] Purchase request failed:', err);
      throw err;
    }
  },

  /**
   * Restore previous purchases
   */
  restorePurchases: async (): Promise<IAPPurchaseResult[]> => {
    if (isExpoGo || !iapModule) {
      console.log('[IAP] Cannot restore (Expo Go)');
      return [];
    }
    
    if (!isInitialized) {
      await iapService.init();
    }

    try {
      const purchases = await getAvailablePurchases();
      console.log('[IAP] Restored purchases:', purchases.length);

      return purchases
        .filter((p: any) => SUBSCRIPTION_SKUS.includes(p.productId))
        .map((p: any) => ({
          success: true,
          productId: p.productId,
          transactionId: p.transactionId || '',
          receipt: Platform.OS === 'ios' 
            ? p.transactionReceipt || ''
            : (p as any).purchaseToken || '',
          tier: SKU_TO_TIER[p.productId] || 'premium',
        }));
    } catch (err) {
      console.error('[IAP] Failed to restore purchases:', err);
      return [];
    }
  },

  /**
   * Check if IAP is available on this device
   */
  isAvailable: (): boolean => {
    return !isExpoGo && !!iapModule && isInitialized;
  },
  
  /**
   * Check if running in Expo Go
   */
  isExpoGo: (): boolean => {
    return isExpoGo;
  },
};

export default iapService;
