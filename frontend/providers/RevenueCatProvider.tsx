/**
 * RevenueCat Provider
 * 
 * React Context Provider for RevenueCat state management.
 * Wraps the app to provide subscription state throughout the component tree.
 * 
 * @example
 * // In _layout.tsx
 * <RevenueCatProvider>
 *   <App />
 * </RevenueCatProvider>
 * 
 * // In any component
 * const { isPro, showPaywall } = useRevenueCatContext();
 */

import React, { 
  createContext, 
  useContext, 
  useEffect, 
  useState, 
  useCallback,
  useMemo,
  ReactNode,
} from 'react';
import { AppState, AppStateStatus } from 'react-native';
import { CustomerInfo, PurchasesPackage } from 'react-native-purchases';
import { 
  revenueCatService, 
  ENTITLEMENTS,
  SubscriptionProduct,
  PurchaseResult,
} from '../services/revenueCatService';
import { presentPaywall, presentPaywallIfNeeded } from '../components/RevenueCatPaywall';
import { presentCustomerCenter } from '../components/CustomerCenter';

// ============================================================================
// Context Types
// ============================================================================

interface RevenueCatContextValue {
  // State
  isReady: boolean;
  isLoading: boolean;
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
  purchase: (pkg: PurchasesPackage) => Promise<PurchaseResult>;
  restore: () => Promise<boolean>;
  refresh: () => Promise<void>;
  login: (userId: string) => Promise<void>;
  logout: () => Promise<void>;
  
  // UI Helpers
  showPaywall: () => Promise<boolean>;
  showPaywallIfNeeded: () => Promise<boolean>;
  showCustomerCenter: () => Promise<void>;
  
  // Utilities
  checkEntitlement: (entitlementId: string) => boolean;
}

const RevenueCatContext = createContext<RevenueCatContextValue | null>(null);

// ============================================================================
// Provider Props
// ============================================================================

interface RevenueCatProviderProps {
  children: ReactNode;
  /** Initial user ID for login */
  userId?: string;
  /** Callback when subscription status changes */
  onSubscriptionChange?: (isPro: boolean, customerInfo: CustomerInfo | null) => void;
}

// ============================================================================
// Provider Component
// ============================================================================

export function RevenueCatProvider({ 
  children, 
  userId,
  onSubscriptionChange,
}: RevenueCatProviderProps) {
  const [isReady, setIsReady] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [customerInfo, setCustomerInfo] = useState<CustomerInfo | null>(null);
  const [packages, setPackages] = useState<PurchasesPackage[]>([]);
  const [products, setProducts] = useState<SubscriptionProduct[]>([]);

  // Initialize RevenueCat
  useEffect(() => {
    let mounted = true;

    const initialize = async () => {
      try {
        await revenueCatService.init(userId);
        
        if (!mounted) return;

        // Fetch initial data
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

        setIsReady(true);
      } catch (error) {
        console.error('[RevenueCatProvider] Init error:', error);
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
        const isPro = !!info.entitlements.active[ENTITLEMENTS.LUNA_PRO]?.isActive;
        onSubscriptionChange?.(isPro, info);
      }
    });

    return () => {
      mounted = false;
      unsubscribe();
    };
  }, [userId]);

  // Handle user ID changes (login/logout)
  useEffect(() => {
    if (!isReady) return;

    const handleUserChange = async () => {
      if (userId) {
        await revenueCatService.login(userId);
      } else {
        await revenueCatService.logout();
      }
      
      const info = await revenueCatService.getCustomerInfo();
      if (info) setCustomerInfo(info);
    };

    handleUserChange();
  }, [userId, isReady]);

  // Refresh on app foreground
  useEffect(() => {
    const handleAppStateChange = async (nextAppState: AppStateStatus) => {
      if (nextAppState === 'active' && isReady) {
        await revenueCatService.syncPurchases();
        const info = await revenueCatService.getCustomerInfo();
        if (info) setCustomerInfo(info);
      }
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => subscription.remove();
  }, [isReady]);

  // Computed values
  const subscriptionStatus = useMemo(() => {
    if (!customerInfo) {
      return {
        isSubscribed: false,
        isPro: false,
        activeEntitlements: [] as string[],
        expirationDate: null as Date | null,
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

  // Actions
  const purchase = useCallback(async (pkg: PurchasesPackage): Promise<PurchaseResult> => {
    setIsLoading(true);
    try {
      const result = await revenueCatService.purchasePackage(pkg);
      if (result.success) {
        setCustomerInfo(result.customerInfo);
      }
      return result;
    } finally {
      setIsLoading(false);
    }
  }, []);

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

  const login = useCallback(async (newUserId: string): Promise<void> => {
    const info = await revenueCatService.login(newUserId);
    if (info) setCustomerInfo(info);
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    await revenueCatService.logout();
    setCustomerInfo(null);
  }, []);

  const showPaywall = useCallback(async (): Promise<boolean> => {
    const result = await presentPaywall({
      onPurchaseSuccess: (info) => setCustomerInfo(info),
      onRestoreSuccess: (info) => setCustomerInfo(info),
    });
    return result.purchased || result.restored;
  }, []);

  const showPaywallIfNeeded = useCallback(async (): Promise<boolean> => {
    const result = await presentPaywallIfNeeded(ENTITLEMENTS.LUNA_PRO, {
      onPurchaseSuccess: (info) => setCustomerInfo(info),
      onRestoreSuccess: (info) => setCustomerInfo(info),
    });
    return result.purchased || result.restored;
  }, []);

  const showCustomerCenter = useCallback(async (): Promise<void> => {
    await presentCustomerCenter({
      onSubscriptionChanged: (info) => setCustomerInfo(info),
    });
  }, []);

  const checkEntitlement = useCallback((entitlementId: string): boolean => {
    return !!customerInfo?.entitlements.active[entitlementId]?.isActive;
  }, [customerInfo]);

  // Context value
  const value = useMemo<RevenueCatContextValue>(() => ({
    isReady,
    isLoading,
    customerInfo,
    ...subscriptionStatus,
    products,
    packages,
    purchase,
    restore,
    refresh,
    login,
    logout,
    showPaywall,
    showPaywallIfNeeded,
    showCustomerCenter,
    checkEntitlement,
  }), [
    isReady,
    isLoading,
    customerInfo,
    subscriptionStatus,
    products,
    packages,
    purchase,
    restore,
    refresh,
    login,
    logout,
    showPaywall,
    showPaywallIfNeeded,
    showCustomerCenter,
    checkEntitlement,
  ]);

  return (
    <RevenueCatContext.Provider value={value}>
      {children}
    </RevenueCatContext.Provider>
  );
}

// ============================================================================
// Hook
// ============================================================================

export function useRevenueCatContext(): RevenueCatContextValue {
  const context = useContext(RevenueCatContext);
  
  if (!context) {
    throw new Error(
      'useRevenueCatContext must be used within a RevenueCatProvider'
    );
  }
  
  return context;
}

// ============================================================================
// HOC for Pro-only screens
// ============================================================================

export function withProAccess<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  FallbackComponent?: React.ComponentType<P>
) {
  return function ProAccessWrapper(props: P) {
    const { isPro, showPaywallIfNeeded } = useRevenueCatContext();
    const [hasAccess, setHasAccess] = useState(isPro);

    useEffect(() => {
      if (!isPro) {
        showPaywallIfNeeded().then(setHasAccess);
      } else {
        setHasAccess(true);
      }
    }, [isPro]);

    if (!hasAccess) {
      return FallbackComponent ? <FallbackComponent {...props} /> : null;
    }

    return <WrappedComponent {...props} />;
  };
}

export default RevenueCatProvider;
