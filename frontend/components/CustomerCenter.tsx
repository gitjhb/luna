/**
 * Customer Center Component
 * 
 * RevenueCat's pre-built subscription management UI.
 * Allows users to view and manage their subscriptions.
 * 
 * @see https://www.revenuecat.com/docs/tools/customer-center
 */

import React, { useState, useCallback } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  ActivityIndicator,
  Alert,
  Linking,
  Platform,
} from 'react-native';
import Constants from 'expo-constants';
import RevenueCatUI from 'react-native-purchases-ui';
import { Ionicons } from '@expo/vector-icons';
import { revenueCatService, ENTITLEMENTS } from '../services/revenueCatService';
import { CustomerInfo } from 'react-native-purchases';

// Check if running in Expo Go
const isExpoGo = Constants.appOwnership === 'expo';

// ============================================================================
// Types
// ============================================================================

export interface CustomerCenterResult {
  action: 'cancelled' | 'refund_requested' | 'subscription_changed' | 'error';
  customerInfo?: CustomerInfo;
}

export interface CustomerCenterProps {
  /** Callback when customer center closes */
  onComplete?: (result: CustomerCenterResult) => void;
  /** Callback when subscription changes (upgrade/downgrade/cancel) */
  onSubscriptionChanged?: (customerInfo: CustomerInfo) => void;
}

// ============================================================================
// Customer Center Presentation
// ============================================================================

/**
 * Present the Customer Center as a modal
 */
export async function presentCustomerCenter(options?: {
  onSubscriptionChanged?: (customerInfo: CustomerInfo) => void;
}): Promise<CustomerCenterResult> {
  // Mock customer center in Expo Go
  if (isExpoGo) {
    console.log('[CustomerCenter] Using mock (Expo Go)');
    Alert.alert(
      '订阅管理',
      '测试模式 (Expo Go)\n\n当前状态: Luna Pro\n到期时间: 模拟数据\n自动续费: 已开启',
      [
        { text: '取消订阅 (模拟)', onPress: () => console.log('Mock cancel') },
        { text: '关闭' },
      ]
    );
    return { action: 'cancelled' };
  }

  try {
    // Check if user has active subscription
    const hasSubscription = await revenueCatService.hasLunaPro();
    
    if (!hasSubscription) {
      Alert.alert(
        '无活跃订阅',
        '您当前没有活跃的订阅，无法打开订阅管理',
        [{ text: '好的' }]
      );
      return { action: 'cancelled' };
    }

    await RevenueCatUI.presentCustomerCenter();
    
    // Refresh customer info after closing
    const customerInfo = await revenueCatService.getCustomerInfo();
    
    if (customerInfo) {
      options?.onSubscriptionChanged?.(customerInfo);
    }
    
    return { 
      action: 'subscription_changed',
      customerInfo: customerInfo ?? undefined,
    };
  } catch (error) {
    console.error('[CustomerCenter] Present failed:', error);
    
    // Fallback: Open system subscription management
    await openSystemSubscriptionManagement();
    
    return { action: 'error' };
  }
}

/**
 * Open the system's native subscription management
 * Fallback for when Customer Center isn't available
 */
export async function openSystemSubscriptionManagement(): Promise<void> {
  try {
    // First try to get the management URL from RevenueCat
    const managementURL = await revenueCatService.getManagementURL();
    
    if (managementURL) {
      await Linking.openURL(managementURL);
      return;
    }

    // Fallback to platform-specific URLs
    if (Platform.OS === 'ios') {
      // iOS: Open App Store subscription management
      await Linking.openURL('https://apps.apple.com/account/subscriptions');
    } else if (Platform.OS === 'android') {
      // Android: Open Play Store subscription management
      await Linking.openURL('https://play.google.com/store/account/subscriptions');
    }
  } catch (error) {
    console.error('[CustomerCenter] Failed to open subscription management:', error);
    Alert.alert(
      '无法打开',
      '请手动在系统设置中管理您的订阅',
      [{ text: '好的' }]
    );
  }
}

// ============================================================================
// Customer Center Button Component
// ============================================================================

/**
 * A pre-styled button to open the Customer Center
 */
export const CustomerCenterButton: React.FC<{
  style?: object;
  title?: string;
  onSubscriptionChanged?: (customerInfo: CustomerInfo) => void;
}> = ({ 
  style, 
  title = '管理订阅',
  onSubscriptionChanged,
}) => {
  const [loading, setLoading] = useState(false);

  const handlePress = useCallback(async () => {
    setLoading(true);
    try {
      await presentCustomerCenter({ onSubscriptionChanged });
    } finally {
      setLoading(false);
    }
  }, [onSubscriptionChanged]);

  return (
    <TouchableOpacity 
      style={[styles.button, style]}
      onPress={handlePress}
      disabled={loading}
    >
      {loading ? (
        <ActivityIndicator size="small" color="#FFFFFF" />
      ) : (
        <>
          <Ionicons name="settings-outline" size={20} color="#FFFFFF" />
          <Text style={styles.buttonText}>{title}</Text>
        </>
      )}
    </TouchableOpacity>
  );
};

// ============================================================================
// Subscription Info Card Component
// ============================================================================

/**
 * A card showing current subscription status with manage button
 */
export const SubscriptionInfoCard: React.FC<{
  onManagePress?: () => void;
  onUpgradePress?: () => void;
}> = ({ onManagePress, onUpgradePress }) => {
  const [loading, setLoading] = useState(false);
  const [subscriptionInfo, setSubscriptionInfo] = useState<{
    isPro: boolean;
    expirationDate: Date | null;
    productIdentifier: string | null;
    willRenew: boolean;
  } | null>(null);

  // Fetch subscription status on mount
  React.useEffect(() => {
    const fetchStatus = async () => {
      setLoading(true);
      try {
        const status = await revenueCatService.getSubscriptionStatus();
        setSubscriptionInfo({
          isPro: status.isPro,
          expirationDate: status.expirationDate,
          productIdentifier: status.productIdentifier,
          willRenew: status.willRenew,
        });
      } finally {
        setLoading(false);
      }
    };
    fetchStatus();
  }, []);

  const handleManagePress = useCallback(async () => {
    if (onManagePress) {
      onManagePress();
    } else {
      await presentCustomerCenter();
    }
  }, [onManagePress]);

  if (loading) {
    return (
      <View style={styles.card}>
        <ActivityIndicator size="small" color="#8B5CF6" />
      </View>
    );
  }

  if (!subscriptionInfo?.isPro) {
    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Ionicons name="star-outline" size={24} color="#9CA3AF" />
          <Text style={styles.cardTitle}>免费用户</Text>
        </View>
        <Text style={styles.cardDescription}>
          升级到 Luna Pro 解锁全部功能
        </Text>
        <TouchableOpacity 
          style={styles.upgradeButton}
          onPress={onUpgradePress}
        >
          <Text style={styles.upgradeButtonText}>升级到 Pro</Text>
        </TouchableOpacity>
      </View>
    );
  }

  // Format expiration date
  const formatDate = (date: Date | null) => {
    if (!date) return '永久';
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // Get plan name
  const getPlanName = (productId: string | null) => {
    if (!productId) return 'Luna Pro';
    if (productId.includes('lifetime')) return 'Luna Pro 终身版';
    if (productId.includes('yearly')) return 'Luna Pro 年度版';
    if (productId.includes('monthly')) return 'Luna Pro 月度版';
    return 'Luna Pro';
  };

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Ionicons name="star" size={24} color="#8B5CF6" />
        <Text style={styles.cardTitleActive}>
          {getPlanName(subscriptionInfo.productIdentifier)}
        </Text>
      </View>
      
      <View style={styles.cardInfo}>
        <Text style={styles.cardLabel}>到期时间</Text>
        <Text style={styles.cardValue}>
          {formatDate(subscriptionInfo.expirationDate)}
        </Text>
      </View>
      
      {subscriptionInfo.expirationDate && (
        <View style={styles.cardInfo}>
          <Text style={styles.cardLabel}>自动续费</Text>
          <Text style={[
            styles.cardValue,
            { color: subscriptionInfo.willRenew ? '#10B981' : '#EF4444' }
          ]}>
            {subscriptionInfo.willRenew ? '已开启' : '已关闭'}
          </Text>
        </View>
      )}
      
      <TouchableOpacity 
        style={styles.manageButton}
        onPress={handleManagePress}
      >
        <Ionicons name="settings-outline" size={18} color="#8B5CF6" />
        <Text style={styles.manageButtonText}>管理订阅</Text>
      </TouchableOpacity>
    </View>
  );
};

// ============================================================================
// Styles
// ============================================================================

const styles = StyleSheet.create({
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#8B5CF6',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 12,
    gap: 8,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  card: {
    backgroundColor: '#1F2937',
    borderRadius: 16,
    padding: 20,
    margin: 16,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#9CA3AF',
  },
  cardTitleActive: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  cardDescription: {
    fontSize: 14,
    color: '#9CA3AF',
    marginBottom: 16,
  },
  cardInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: '#374151',
  },
  cardLabel: {
    fontSize: 14,
    color: '#9CA3AF',
  },
  cardValue: {
    fontSize: 14,
    fontWeight: '500',
    color: '#FFFFFF',
  },
  upgradeButton: {
    backgroundColor: '#8B5CF6',
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  upgradeButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  manageButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 16,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: '#8B5CF6',
    borderRadius: 10,
  },
  manageButtonText: {
    color: '#8B5CF6',
    fontSize: 14,
    fontWeight: '500',
  },
});

export default {
  presentCustomerCenter,
  openSystemSubscriptionManagement,
  CustomerCenterButton,
  SubscriptionInfoCard,
};
