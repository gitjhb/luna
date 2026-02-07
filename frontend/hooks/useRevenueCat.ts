/**
 * useRevenueCat Hook
 * 
 * React hook for easy access to RevenueCat subscription state.
 * Automatically syncs with RevenueCat and provides reactive updates.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { AppState, AppStateStatus } from 'react-native';
import { CustomerInfo, PurchasesPackage } from 'react-native-purchases';
import { 
  revenueCatService, 
  ENTITLEMENTS,
  SubscriptionStatus,
  SubscriptionProduct,
  PurchaseResult,
} from '../services/revenueCatService';
import { presentPaywall, presentPaywallIfNeeded } from '../components/RevenueCatPaywall';
import { presentCustomerCenter } from '../components/CustomerCenter';

// ============================================================================
// Types
// ============================================================================

export interface UseRevenueCatReturn {
  // State
  isLoading: boolean;
  isInitialized: boolean;
  customerInfo: CustomerInfo | null;
  
  // Subscription status
  isPro: boolean;
  isSubscribed: boolean;
  activeEntitlements: string[];
  expirationDate: Date | null;
  willRenew: boolean;
  
  // Products
  products: SubscriptionProduct[];
  packages: PurchasesPackage[];
  
  // Actions
  purchase: (packageOrProductId: PurchasesPackage | string) => Promise<PurchaseResult>;
  restore: () => Promise<boolean>;
  refresh: () => Promise<void>;
  
  // UI Helpers
  showPaywall: () => Promise<boolean>;
  showPaywallIfNeeded: () => Promise<boolean>;
  showCustomerCenter: () => Promise<void>;
  
  // Utilities
  checkEntitlement: (entitlementId: string) => boolean;
  getProduct: (productId: string) => SubscriptionProduct | undefined;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useRevenueCat(): UseRevenueCatReturn {
  const [isLoading, setIsLoading] = useState(true);
  const [customerInfo, setCustomerInfo] = useState<CustomerInfo | null>(null);
  const [packages, setPackages] = useState<PurchasesPackage[]>([]);
  const [products, setProducts] = useState<SubscriptionProduct[]>([]);

  // Initialize and fetch data
  useEffect(() => {
    let mounted = true;

    const initialize = async () => {
      try {
        // Wait for SDK initialization
        if (!revenueCatService.isInitialized()) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }

        // Fetch customer info and offerings in parallel
        const [info, offerings] = await Promise.all([
          revenueCatService.getCustomerInfo(),
          revenueCatService.getOfferings(),
        ]);

        if (!mounted) return;

        if (info) {
          setCustomerInfo(info);
        }

        if (offerings) {
          setPackages(offerings.availablePackages);
          setProducts(offerings.availablePackages.map(
            pkg => revenueCatService.packageToProduct(pkg)
          ));
        }
      } catch (error) {
        console.error('[useRevenueCat] Init error:', error);
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    initialize();

    // Subscribe to customer info updates
    const unsubscribe = revenueCatService.addCustomerInfoListener((info) => {
      if (mounted) {
        setCustomerInfo(info);
      }
    });

    return () => {
      mounted = false;
      unsubscribe();
    };
  }, []);

  // Refresh on app foreground
  useEffect(() => {
    const handleAppStateChange = async (nextAppState: AppStateStatus) => {
      if (nextAppState === 'active') {
        // Sync purchases when app comes to foreground
        await revenueCatService.syncPurchases();
        const info = await revenueCatService.getCustomerInfo();
        if (info) {
          setCustomerInfo(info);
        }
      }
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => subscription.remove();
  }, []);

  // Computed subscription status
  const subscriptionStatus = useMemo((): Omit<SubscriptionStatus, 'productIdentifier'> => {
    if (!customerInfo) {
      return {
        isSubscribed: false,
        isPro: false,
        activeEntitlements: [],
        expirationDate: null,
        willRenew: false,
      };
    }

    const proEntitlement = customerInfo.entitlements.active[ENTITLEMENTS.LUNA_PRO];
    const activeEntitlements = Object.keys(customerInfo.entitlements.active);

    return {
      isSubscribed: activeEntitlements.length > 0,
      isPro: !!proEntitlement?.isActive,
      activeEntitlements,
      expirationDate: proEntitlement?.expirationDate 
        ? new Date(proEntitlement.expirationDate) 
        : null,
      willRenew: proEntitlement?.willRenew ?? false,
    };
  }, [customerInfo]);

  // Purchase action
  const purchase = useCallback(async (
    packageOrProductId: PurchasesPackage | string
  ): Promise<PurchaseResult> => {
    if (typeof packageOrProductId === 'string') {
      return revenueCatService.purchaseProduct(packageOrProductId);
    }
    return revenueCatService.purchasePackage(packageOrProductId);
  }, []);

  // Restore action
  const restore = useCallback(async (): Promise<boolean> => {
    setIsLoading(true);
    try {
      const info = await revenueCatService.restorePurchases();
      if (info) {
        setCustomerInfo(info);
        return Object.keys(info.entitlements.active).length > 0;
      }
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Refresh action
  const refresh = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    try {
      const [info, offerings] = await Promise.all([
        revenueCatService.getCustomerInfo(),
        revenueCatService.getOfferings(),
      ]);

      if (info) setCustomerInfo(info);
      if (offerings) {
        setPackages(offerings.availablePackages);
        setProducts(offerings.availablePackages.map(
          pkg => revenueCatService.packageToProduct(pkg)
        ));
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Show paywall
  const showPaywall = useCallback(async (): Promise<boolean> => {
    const result = await presentPaywall({
      onPurchaseSuccess: (info) => setCustomerInfo(info),
      onRestoreSuccess: (info) => setCustomerInfo(info),
    });
    return result.purchased || result.restored;
  }, []);

  // Show paywall if needed
  const showPaywallIfNeeded = useCallback(async (): Promise<boolean> => {
    const result = await presentPaywallIfNeeded(ENTITLEMENTS.LUNA_PRO, {
      onPurchaseSuccess: (info) => setCustomerInfo(info),
      onRestoreSuccess: (info) => setCustomerInfo(info),
    });
    return result.purchased || result.restored;
  }, []);

  // Show customer center
  const showCustomerCenter = useCallback(async (): Promise<void> => {
    await presentCustomerCenter({
      onSubscriptionChanged: (info) => setCustomerInfo(info),
    });
  }, []);

  // Check specific entitlement
  const checkEntitlement = useCallback((entitlementId: string): boolean => {
    return !!customerInfo?.entitlements.active[entitlementId]?.isActive;
  }, [customerInfo]);

  // Get specific product
  const getProduct = useCallback((productId: string): SubscriptionProduct | undefined => {
    return products.find(p => p.identifier === productId);
  }, [products]);

  return {
    // State
    isLoading,
    isInitialized: revenueCatService.isInitialized(),
    customerInfo,
    
    // Subscription status
    ...subscriptionStatus,
    
    // Products
    products,
    packages,
    
    // Actions
    purchase,
    restore,
    refresh,
    
    // UI Helpers
    showPaywall,
    showPaywallIfNeeded,
    showCustomerCenter,
    
    // Utilities
    checkEntitlement,
    getProduct,
  };
}

// ============================================================================
// Utility Hook: Check Pro Access
// ============================================================================

/**
 * Simple hook to check if user has Luna Pro
 * Use this for quick access checks without full subscription data
 */
export function useIsPro(): boolean {
  const [isPro, setIsPro] = useState(revenueCatService.hasLunaProSync());

  useEffect(() => {
    // Initial check
    revenueCatService.hasLunaPro().then(setIsPro);

    // Subscribe to updates
    const unsubscribe = revenueCatService.addCustomerInfoListener((info) => {
      setIsPro(!!info.entitlements.active[ENTITLEMENTS.LUNA_PRO]?.isActive);
    });

    return unsubscribe;
  }, []);

  return isPro;
}

// ============================================================================
// Utility Hook: Require Pro Access
// ============================================================================

/**
 * Hook that shows paywall when Pro access is required
 * Returns whether user has access (after potential purchase)
 */
export function useRequirePro(): {
  isPro: boolean;
  requirePro: () => Promise<boolean>;
} {
  const isPro = useIsPro();

  const requirePro = useCallback(async (): Promise<boolean> => {
    if (isPro) return true;
    
    const result = await presentPaywallIfNeeded(ENTITLEMENTS.LUNA_PRO);
    return result.purchased || result.restored;
  }, [isPro]);

  return { isPro, requirePro };
}

export default useRevenueCat;
