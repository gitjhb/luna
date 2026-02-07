/**
 * RevenueCat Service - Subscription Management
 * 
 * Handles all subscription-related functionality using RevenueCat SDK.
 * Replaces the previous react-native-iap implementation.
 * 
 * @see https://www.revenuecat.com/docs/getting-started/installation/expo
 */

import { Platform } from 'react-native';
import Purchases, {
  PurchasesOffering,
  PurchasesPackage,
  CustomerInfo,
  LOG_LEVEL,
  PURCHASES_ERROR_CODE,
  PurchasesError,
  PRODUCT_CATEGORY,
} from 'react-native-purchases';

// ============================================================================
// Configuration
// ============================================================================

const REVENUECAT_API_KEY = 'test_FBObZPlGuTyizNXjsTFNnnHSqNc';

// Entitlement IDs (configured in RevenueCat dashboard)
export const ENTITLEMENTS = {
  LUNA_PRO: 'Luna Pro',
} as const;

// Product identifiers
export const PRODUCT_IDS = {
  MONTHLY: 'monthly',
  YEARLY: 'yearly',
  LIFETIME: 'lifetime',
} as const;

// ============================================================================
// Types
// ============================================================================

export interface SubscriptionStatus {
  isSubscribed: boolean;
  isPro: boolean;
  activeEntitlements: string[];
  expirationDate: Date | null;
  willRenew: boolean;
  productIdentifier: string | null;
}

export interface SubscriptionProduct {
  identifier: string;
  title: string;
  description: string;
  priceString: string;
  price: number;
  currencyCode: string;
  packageType: string;
  isLifetime: boolean;
  introPrice?: {
    priceString: string;
    cycles: number;
    period: string;
  } | null;
}

export type PurchaseResult = {
  success: true;
  customerInfo: CustomerInfo;
} | {
  success: false;
  error: PurchasesError;
  userCancelled: boolean;
};

// ============================================================================
// Service State
// ============================================================================

let isInitialized = false;
let cachedCustomerInfo: CustomerInfo | null = null;

// Customer info update listeners
type CustomerInfoListener = (info: CustomerInfo) => void;
const customerInfoListeners: Set<CustomerInfoListener> = new Set();

// ============================================================================
// RevenueCat Service
// ============================================================================

export const revenueCatService = {
  /**
   * Initialize RevenueCat SDK
   * Call this once on app startup (in _layout.tsx)
   */
  init: async (userId?: string): Promise<boolean> => {
    if (isInitialized) {
      console.log('[RevenueCat] Already initialized');
      return true;
    }

    try {
      // Enable debug logs in development
      if (__DEV__) {
        Purchases.setLogLevel(LOG_LEVEL.DEBUG);
      }

      // Configure the SDK
      Purchases.configure({
        apiKey: REVENUECAT_API_KEY,
        appUserID: userId || null, // null = anonymous user
      });

      // Set up customer info update listener
      Purchases.addCustomerInfoUpdateListener((info) => {
        console.log('[RevenueCat] Customer info updated');
        cachedCustomerInfo = info;
        customerInfoListeners.forEach((listener) => listener(info));
      });

      isInitialized = true;
      console.log('[RevenueCat] Initialized successfully');

      // Pre-fetch customer info
      await revenueCatService.getCustomerInfo();

      return true;
    } catch (error) {
      console.error('[RevenueCat] Initialization failed:', error);
      return false;
    }
  },

  /**
   * Check if SDK is initialized
   */
  isInitialized: (): boolean => isInitialized,

  /**
   * Login user (associate purchases with user ID)
   * Call this after user authentication
   */
  login: async (userId: string): Promise<CustomerInfo | null> => {
    try {
      const { customerInfo } = await Purchases.logIn(userId);
      cachedCustomerInfo = customerInfo;
      console.log('[RevenueCat] User logged in:', userId);
      return customerInfo;
    } catch (error) {
      console.error('[RevenueCat] Login failed:', error);
      return null;
    }
  },

  /**
   * Logout user (reset to anonymous)
   * Call this when user logs out
   */
  logout: async (): Promise<void> => {
    try {
      await Purchases.logOut();
      cachedCustomerInfo = null;
      console.log('[RevenueCat] User logged out');
    } catch (error) {
      console.error('[RevenueCat] Logout failed:', error);
    }
  },

  /**
   * Get current customer info
   */
  getCustomerInfo: async (): Promise<CustomerInfo | null> => {
    try {
      const info = await Purchases.getCustomerInfo();
      cachedCustomerInfo = info;
      return info;
    } catch (error) {
      console.error('[RevenueCat] Failed to get customer info:', error);
      return cachedCustomerInfo;
    }
  },

  /**
   * Get cached customer info (sync, no network call)
   */
  getCachedCustomerInfo: (): CustomerInfo | null => cachedCustomerInfo,

  /**
   * Add listener for customer info updates
   */
  addCustomerInfoListener: (listener: CustomerInfoListener): (() => void) => {
    customerInfoListeners.add(listener);
    return () => customerInfoListeners.delete(listener);
  },

  /**
   * Check subscription status
   */
  getSubscriptionStatus: async (): Promise<SubscriptionStatus> => {
    const info = await revenueCatService.getCustomerInfo();
    
    if (!info) {
      return {
        isSubscribed: false,
        isPro: false,
        activeEntitlements: [],
        expirationDate: null,
        willRenew: false,
        productIdentifier: null,
      };
    }

    const proEntitlement = info.entitlements.active[ENTITLEMENTS.LUNA_PRO];
    const activeEntitlements = Object.keys(info.entitlements.active);

    return {
      isSubscribed: activeEntitlements.length > 0,
      isPro: !!proEntitlement?.isActive,
      activeEntitlements,
      expirationDate: proEntitlement?.expirationDate 
        ? new Date(proEntitlement.expirationDate) 
        : null,
      willRenew: proEntitlement?.willRenew ?? false,
      productIdentifier: proEntitlement?.productIdentifier ?? null,
    };
  },

  /**
   * Quick check if user has Luna Pro entitlement
   */
  hasLunaPro: async (): Promise<boolean> => {
    const info = await revenueCatService.getCustomerInfo();
    return !!info?.entitlements.active[ENTITLEMENTS.LUNA_PRO]?.isActive;
  },

  /**
   * Sync check using cached info (no network call)
   */
  hasLunaProSync: (): boolean => {
    return !!cachedCustomerInfo?.entitlements.active[ENTITLEMENTS.LUNA_PRO]?.isActive;
  },

  /**
   * Get available offerings (products)
   */
  getOfferings: async (): Promise<PurchasesOffering | null> => {
    try {
      const offerings = await Purchases.getOfferings();
      
      if (!offerings.current) {
        console.warn('[RevenueCat] No current offering configured');
        return null;
      }

      console.log('[RevenueCat] Current offering:', offerings.current.identifier);
      console.log('[RevenueCat] Available packages:', 
        offerings.current.availablePackages.map(p => p.identifier)
      );

      return offerings.current;
    } catch (error) {
      console.error('[RevenueCat] Failed to get offerings:', error);
      return null;
    }
  },

  /**
   * Get all offerings (including non-current)
   */
  getAllOfferings: async (): Promise<{ [key: string]: PurchasesOffering }> => {
    try {
      const offerings = await Purchases.getOfferings();
      return offerings.all;
    } catch (error) {
      console.error('[RevenueCat] Failed to get all offerings:', error);
      return {};
    }
  },

  /**
   * Convert package to our product type
   */
  packageToProduct: (pkg: PurchasesPackage): SubscriptionProduct => {
    const product = pkg.product;
    
    return {
      identifier: pkg.identifier,
      title: product.title,
      description: product.description,
      priceString: product.priceString,
      price: product.price,
      currencyCode: product.currencyCode,
      packageType: pkg.packageType,
      isLifetime: pkg.packageType === 'LIFETIME',
      introPrice: product.introPrice ? {
        priceString: product.introPrice.priceString,
        cycles: product.introPrice.cycles,
        period: product.introPrice.periodUnit,
      } : null,
    };
  },

  /**
   * Purchase a package
   */
  purchasePackage: async (pkg: PurchasesPackage): Promise<PurchaseResult> => {
    try {
      console.log('[RevenueCat] Purchasing package:', pkg.identifier);
      
      const { customerInfo } = await Purchases.purchasePackage(pkg);
      cachedCustomerInfo = customerInfo;

      console.log('[RevenueCat] Purchase successful');
      return { success: true, customerInfo };
    } catch (error) {
      const purchaseError = error as PurchasesError;
      
      // Check if user cancelled
      const userCancelled = purchaseError.code === PURCHASES_ERROR_CODE.PURCHASE_CANCELLED_ERROR;
      
      if (userCancelled) {
        console.log('[RevenueCat] Purchase cancelled by user');
      } else {
        console.error('[RevenueCat] Purchase failed:', purchaseError.message);
      }

      return {
        success: false,
        error: purchaseError,
        userCancelled,
      };
    }
  },

  /**
   * Purchase a specific product by ID
   */
  purchaseProduct: async (productId: string): Promise<PurchaseResult> => {
    try {
      const offerings = await revenueCatService.getOfferings();
      
      if (!offerings) {
        throw new Error('No offerings available');
      }

      const pkg = offerings.availablePackages.find(
        p => p.product.identifier === productId || p.identifier === productId
      );

      if (!pkg) {
        throw new Error(`Product not found: ${productId}`);
      }

      return revenueCatService.purchasePackage(pkg);
    } catch (error) {
      console.error('[RevenueCat] Purchase product failed:', error);
      return {
        success: false,
        error: error as PurchasesError,
        userCancelled: false,
      };
    }
  },

  /**
   * Restore previous purchases
   */
  restorePurchases: async (): Promise<CustomerInfo | null> => {
    try {
      console.log('[RevenueCat] Restoring purchases...');
      const info = await Purchases.restorePurchases();
      cachedCustomerInfo = info;
      
      const activeEntitlements = Object.keys(info.entitlements.active);
      console.log('[RevenueCat] Restored entitlements:', activeEntitlements);
      
      return info;
    } catch (error) {
      console.error('[RevenueCat] Restore failed:', error);
      return null;
    }
  },

  /**
   * Check if eligible for intro pricing
   */
  checkIntroEligibility: async (productIds: string[]): Promise<{ [key: string]: boolean }> => {
    try {
      // Note: This is iOS only. Android always returns UNKNOWN
      if (Platform.OS !== 'ios') {
        return productIds.reduce((acc, id) => ({ ...acc, [id]: true }), {});
      }

      const eligibility = await Purchases.checkTrialOrIntroDiscountEligibility(productIds);
      
      return Object.entries(eligibility).reduce((acc, [key, value]) => ({
        ...acc,
        [key]: value === 'INTRO_ELIGIBILITY_STATUS_ELIGIBLE',
      }), {});
    } catch (error) {
      console.error('[RevenueCat] Intro eligibility check failed:', error);
      return productIds.reduce((acc, id) => ({ ...acc, [id]: true }), {});
    }
  },

  /**
   * Get the management URL for subscriptions
   */
  getManagementURL: async (): Promise<string | null> => {
    try {
      const info = await revenueCatService.getCustomerInfo();
      return info?.managementURL ?? null;
    } catch (error) {
      console.error('[RevenueCat] Failed to get management URL:', error);
      return null;
    }
  },

  /**
   * Sync purchases with RevenueCat server
   * Use after app comes to foreground
   */
  syncPurchases: async (): Promise<void> => {
    try {
      await Purchases.syncPurchases();
      console.log('[RevenueCat] Purchases synced');
    } catch (error) {
      console.error('[RevenueCat] Sync failed:', error);
    }
  },

  /**
   * Set user attributes (for analytics)
   */
  setUserAttributes: async (attributes: {
    email?: string;
    displayName?: string;
    phoneNumber?: string;
    [key: string]: string | undefined;
  }): Promise<void> => {
    try {
      if (attributes.email) await Purchases.setEmail(attributes.email);
      if (attributes.displayName) await Purchases.setDisplayName(attributes.displayName);
      if (attributes.phoneNumber) await Purchases.setPhoneNumber(attributes.phoneNumber);
      
      // Set custom attributes
      for (const [key, value] of Object.entries(attributes)) {
        if (value && !['email', 'displayName', 'phoneNumber'].includes(key)) {
          await Purchases.setAttributes({ [key]: value });
        }
      }
      
      console.log('[RevenueCat] User attributes set');
    } catch (error) {
      console.error('[RevenueCat] Failed to set attributes:', error);
    }
  },

  /**
   * Get error message for display
   */
  getErrorMessage: (error: PurchasesError): string => {
    switch (error.code) {
      case PURCHASES_ERROR_CODE.PURCHASE_CANCELLED_ERROR:
        return '购买已取消';
      case PURCHASES_ERROR_CODE.PURCHASE_NOT_ALLOWED_ERROR:
        return '此设备不允许购买';
      case PURCHASES_ERROR_CODE.PURCHASE_INVALID_ERROR:
        return '购买无效，请重试';
      case PURCHASES_ERROR_CODE.PRODUCT_NOT_AVAILABLE_FOR_PURCHASE_ERROR:
        return '该产品当前不可购买';
      case PURCHASES_ERROR_CODE.PRODUCT_ALREADY_PURCHASED_ERROR:
        return '您已购买此产品';
      case PURCHASES_ERROR_CODE.RECEIPT_ALREADY_IN_USE_ERROR:
        return '此购买已被其他账户使用';
      case PURCHASES_ERROR_CODE.INVALID_RECEIPT_ERROR:
        return '收据验证失败';
      case PURCHASES_ERROR_CODE.MISSING_RECEIPT_FILE_ERROR:
        return '找不到收据文件';
      case PURCHASES_ERROR_CODE.NETWORK_ERROR:
        return '网络错误，请检查网络连接';
      case PURCHASES_ERROR_CODE.INVALID_CREDENTIALS_ERROR:
        return '认证失败';
      case PURCHASES_ERROR_CODE.UNEXPECTED_BACKEND_RESPONSE_ERROR:
        return '服务器响应异常';
      case PURCHASES_ERROR_CODE.STORE_PROBLEM_ERROR:
        return '应用商店出现问题，请稍后重试';
      default:
        return error.message || '购买失败，请重试';
    }
  },
};

export default revenueCatService;
