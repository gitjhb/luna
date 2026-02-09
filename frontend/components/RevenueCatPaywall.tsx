/**
 * RevenueCat Paywall Component
 * 
 * Uses RevenueCat's pre-built paywall UI for subscription purchases.
 * Configurable via RevenueCat dashboard without app updates.
 * 
 * @see https://www.revenuecat.com/docs/tools/paywalls/displaying-paywalls
 */

import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import Constants from 'expo-constants';
import RevenueCatUI, { PAYWALL_RESULT } from 'react-native-purchases-ui';
import { CustomerInfo } from 'react-native-purchases';
import { revenueCatService, ENTITLEMENTS } from '../services/revenueCatService';
import { useUserStore } from '../store/userStore';

// Check if running in Expo Go (no native modules available)
const isExpoGo = Constants.appOwnership === 'expo';

// ============================================================================
// Types
// ============================================================================

export interface PaywallResult {
  purchased: boolean;
  restored: boolean;
  cancelled: boolean;
  error: boolean;
  customerInfo?: CustomerInfo;
}

export interface RevenueCatPaywallProps {
  /** Callback when paywall closes (with result) */
  onComplete?: (result: PaywallResult) => void;
  /** Callback specifically for successful purchase */
  onPurchaseSuccess?: (customerInfo: CustomerInfo) => void;
  /** Callback when restore succeeds */
  onRestoreSuccess?: (customerInfo: CustomerInfo) => void;
  /** Callback when user dismisses without purchase */
  onDismiss?: () => void;
  /** Custom offering identifier (optional, uses default if not specified) */
  offeringIdentifier?: string;
  /** Whether to display as full screen modal or inline */
  displayAsModal?: boolean;
}

// ============================================================================
// Paywall Presentation Functions
// ============================================================================

/**
 * Present a mock paywall for Expo Go testing
 */
function presentMockPaywall(): Promise<PaywallResult> {
  return new Promise((resolve) => {
    Alert.alert(
      '🔮 Luna Pro',
      '测试模式 (Expo Go)\n\n月费 ¥28.00\n• 无限聊天\n• 解锁所有角色\n• NSFW内容',
      [
        {
          text: '取消',
          style: 'cancel',
          onPress: () => resolve({
            purchased: false,
            restored: false,
            cancelled: true,
            error: false,
          }),
        },
        {
          text: '模拟购买',
          onPress: () => resolve({
            purchased: true,
            restored: false,
            cancelled: false,
            error: false,
          }),
        },
      ]
    );
  });
}

/**
 * Present the paywall as a modal sheet
 * This is the simplest way to show the paywall
 */
export async function presentPaywall(options?: {
  offeringIdentifier?: string;
  onPurchaseSuccess?: (customerInfo: CustomerInfo) => void;
  onRestoreSuccess?: (customerInfo: CustomerInfo) => void;
}): Promise<PaywallResult> {
  // Use mock paywall in Expo Go (native modules unavailable)
  if (isExpoGo) {
    console.log('[Paywall] Using mock paywall (Expo Go)');
    return presentMockPaywall();
  }

  try {
    const result = await RevenueCatUI.presentPaywall({
      offering: options?.offeringIdentifier ? 
        await getOfferingByIdentifier(options.offeringIdentifier) : 
        undefined,
    });

    const paywallResult: PaywallResult = {
      purchased: result === PAYWALL_RESULT.PURCHASED,
      restored: result === PAYWALL_RESULT.RESTORED,
      cancelled: result === PAYWALL_RESULT.CANCELLED,
      error: result === PAYWALL_RESULT.ERROR,
    };

    // Fetch updated customer info after purchase/restore
    if (paywallResult.purchased || paywallResult.restored) {
      const customerInfo = await revenueCatService.getCustomerInfo();
      paywallResult.customerInfo = customerInfo ?? undefined;

      if (paywallResult.purchased && customerInfo && options?.onPurchaseSuccess) {
        options.onPurchaseSuccess(customerInfo);
      }
      if (paywallResult.restored && customerInfo && options?.onRestoreSuccess) {
        options.onRestoreSuccess(customerInfo);
      }
    }

    return paywallResult;
  } catch (error) {
    console.error('[Paywall] Present failed:', error);
    return {
      purchased: false,
      restored: false,
      cancelled: false,
      error: true,
    };
  }
}

/**
 * Present paywall only if user doesn't have the required entitlement
 */
export async function presentPaywallIfNeeded(
  requiredEntitlement: string = ENTITLEMENTS.LUNA_PRO,
  options?: {
    onPurchaseSuccess?: (customerInfo: CustomerInfo) => void;
    onRestoreSuccess?: (customerInfo: CustomerInfo) => void;
  }
): Promise<PaywallResult> {
  // Use mock paywall in Expo Go
  if (isExpoGo) {
    console.log('[Paywall] Using mock paywall if needed (Expo Go)');
    return presentMockPaywall();
  }

  try {
    const result = await RevenueCatUI.presentPaywallIfNeeded({
      requiredEntitlementIdentifier: requiredEntitlement,
    });

    const paywallResult: PaywallResult = {
      purchased: result === PAYWALL_RESULT.PURCHASED,
      restored: result === PAYWALL_RESULT.RESTORED,
      cancelled: result === PAYWALL_RESULT.CANCELLED,
      error: result === PAYWALL_RESULT.ERROR,
    };

    // Handle callbacks
    if (paywallResult.purchased || paywallResult.restored) {
      const customerInfo = await revenueCatService.getCustomerInfo();
      paywallResult.customerInfo = customerInfo ?? undefined;

      if (paywallResult.purchased && customerInfo && options?.onPurchaseSuccess) {
        options.onPurchaseSuccess(customerInfo);
      }
      if (paywallResult.restored && customerInfo && options?.onRestoreSuccess) {
        options.onRestoreSuccess(customerInfo);
      }
    }

    return paywallResult;
  } catch (error) {
    console.error('[Paywall] Present if needed failed:', error);
    return {
      purchased: false,
      restored: false,
      cancelled: false,
      error: true,
    };
  }
}

// Helper to get offering by identifier
async function getOfferingByIdentifier(identifier: string) {
  const offerings = await revenueCatService.getAllOfferings();
  return offerings[identifier];
}

// ============================================================================
// Paywall Footer Component (for custom paywalls)
// ============================================================================

/**
 * Paywall Footer - Shows purchase buttons that can be embedded in custom UI
 * Useful when you want custom paywall design but RevenueCat purchase handling
 */
export const PaywallFooter: React.FC<{
  onPurchaseSuccess?: (customerInfo: CustomerInfo) => void;
  onRestoreSuccess?: (customerInfo: CustomerInfo) => void;
}> = ({ onPurchaseSuccess, onRestoreSuccess }) => {
  const [loading, setLoading] = useState(false);

  const handlePurchaseStarted = useCallback(() => {
    console.log('[PaywallFooter] Purchase started');
    setLoading(true);
  }, []);

  const handlePurchaseCompleted = useCallback(async (info: CustomerInfo) => {
    console.log('[PaywallFooter] Purchase completed');
    setLoading(false);
    onPurchaseSuccess?.(info);
  }, [onPurchaseSuccess]);

  const handleRestoreCompleted = useCallback(async (info: CustomerInfo) => {
    console.log('[PaywallFooter] Restore completed');
    setLoading(false);
    onRestoreSuccess?.(info);
  }, [onRestoreSuccess]);

  return (
    <RevenueCatUI.PaywallFooterContainerView
      onPurchaseStarted={handlePurchaseStarted}
      onPurchaseCompleted={handlePurchaseCompleted}
      onRestoreCompleted={handleRestoreCompleted}
    >
      {loading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#8B5CF6" />
        </View>
      )}
    </RevenueCatUI.PaywallFooterContainerView>
  );
};

// ============================================================================
// Inline Paywall Component
// ============================================================================

/**
 * Inline Paywall Component
 * 
 * Use this when you want to embed the paywall in your own screen/modal
 * rather than presenting it as a full-screen modal
 */
export const InlinePaywall: React.FC<RevenueCatPaywallProps> = ({
  onComplete,
  onPurchaseSuccess,
  onRestoreSuccess,
  onDismiss,
  offeringIdentifier,
}) => {
  const { setSubscription } = useUserStore();
  const [loading, setLoading] = useState(false);

  const handlePurchaseCompleted = useCallback(async (customerInfo: CustomerInfo) => {
    console.log('[InlinePaywall] Purchase completed');
    
    // Update local store
    const hasLunaPro = !!customerInfo.entitlements.active[ENTITLEMENTS.LUNA_PRO];
    if (hasLunaPro) {
      const expDate = customerInfo.entitlements.active[ENTITLEMENTS.LUNA_PRO]?.expirationDate;
      setSubscription('premium', expDate ?? undefined);
    }

    onPurchaseSuccess?.(customerInfo);
    onComplete?.({
      purchased: true,
      restored: false,
      cancelled: false,
      error: false,
      customerInfo,
    });
  }, [onPurchaseSuccess, onComplete, setSubscription]);

  const handleRestoreCompleted = useCallback(async (customerInfo: CustomerInfo) => {
    console.log('[InlinePaywall] Restore completed');
    
    // Update local store
    const hasLunaPro = !!customerInfo.entitlements.active[ENTITLEMENTS.LUNA_PRO];
    if (hasLunaPro) {
      const expDate = customerInfo.entitlements.active[ENTITLEMENTS.LUNA_PRO]?.expirationDate;
      setSubscription('premium', expDate ?? undefined);
      
      Alert.alert(
        '恢复成功',
        'Luna Pro 会员已恢复',
        [{ text: '好的' }]
      );
    } else {
      Alert.alert(
        '无可恢复的购买',
        '未找到之前的订阅记录',
        [{ text: '好的' }]
      );
    }

    onRestoreSuccess?.(customerInfo);
    onComplete?.({
      purchased: false,
      restored: true,
      cancelled: false,
      error: false,
      customerInfo,
    });
  }, [onRestoreSuccess, onComplete, setSubscription]);

  const handlePurchaseCancelled = useCallback(() => {
    console.log('[InlinePaywall] Purchase cancelled');
    onDismiss?.();
    onComplete?.({
      purchased: false,
      restored: false,
      cancelled: true,
      error: false,
    });
  }, [onDismiss, onComplete]);

  const handlePurchaseError = useCallback((error: any) => {
    console.error('[InlinePaywall] Purchase error:', error);
    onComplete?.({
      purchased: false,
      restored: false,
      cancelled: false,
      error: true,
    });
  }, [onComplete]);

  return (
    <View style={styles.container}>
      <RevenueCatUI.Paywall
        options={offeringIdentifier ? { offering: offeringIdentifier } : undefined}
        onPurchaseStarted={() => setLoading(true)}
        onPurchaseCompleted={({ customerInfo }) => {
          setLoading(false);
          handlePurchaseCompleted(customerInfo);
        }}
        onRestoreStarted={() => setLoading(true)}
        onRestoreCompleted={({ customerInfo }) => {
          setLoading(false);
          handleRestoreCompleted(customerInfo);
        }}
        onPurchaseCancelled={handlePurchaseCancelled}
        onPurchaseError={handlePurchaseError}
        onRestoreError={(error) => {
          setLoading(false);
          console.error('[InlinePaywall] Restore error:', error);
        }}
        onDismiss={onDismiss}
      />
      
      {loading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#8B5CF6" />
          <Text style={styles.loadingText}>处理中...</Text>
        </View>
      )}
    </View>
  );
};

// ============================================================================
// Styles
// ============================================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    color: '#FFFFFF',
    fontSize: 16,
  },
});

export default {
  presentPaywall,
  presentPaywallIfNeeded,
  InlinePaywall,
  PaywallFooter,
};
