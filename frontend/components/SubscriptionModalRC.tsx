/**
 * Subscription Modal - RevenueCat Version
 * 
 * Modern subscription purchase UI using RevenueCat SDK.
 * Can be used standalone or with RevenueCat's pre-built paywall.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Modal,
  ScrollView,
  Alert,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { PurchasesPackage } from 'react-native-purchases';
import { useRevenueCat } from '../hooks/useRevenueCat';
import { revenueCatService, ENTITLEMENTS } from '../services/revenueCatService';
import { presentPaywall } from './RevenueCatPaywall';
import { useUserStore } from '../store/userStore';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// ============================================================================
// Types
// ============================================================================

interface SubscriptionModalRCProps {
  visible: boolean;
  onClose: () => void;
  onSubscribeSuccess?: () => void;
  /** Use RevenueCat's pre-built paywall instead of custom UI */
  useRevenueCatPaywall?: boolean;
}

// ============================================================================
// Plan Display Info
// ============================================================================

const PLAN_INFO = {
  monthly: {
    name: '月度订阅',
    badge: null,
    features: [
      '无限消息发送',
      '高级AI模型',
      '全部角色解锁',
      '专属会员角色',
      '优先客服支持',
    ],
  },
  yearly: {
    name: '年度订阅',
    badge: '省 40%',
    features: [
      '月度订阅全部权益',
      '额外 40% 优惠',
      '专属年度礼包',
    ],
  },
  lifetime: {
    name: '终身会员',
    badge: '最超值',
    features: [
      '一次购买，永久使用',
      '所有当前和未来功能',
      '永不涨价保障',
    ],
  },
};

// ============================================================================
// Component
// ============================================================================

export const SubscriptionModalRC: React.FC<SubscriptionModalRCProps> = ({
  visible,
  onClose,
  onSubscribeSuccess,
  useRevenueCatPaywall = false,
}) => {
  const { setSubscription } = useUserStore();
  const {
    isLoading,
    packages,
    isPro,
    purchase,
    restore,
    refresh,
  } = useRevenueCat();

  const [selectedPackage, setSelectedPackage] = useState<PurchasesPackage | null>(null);
  const [purchasing, setPurchasing] = useState(false);
  const [restoring, setRestoring] = useState(false);

  // Load products when modal opens
  useEffect(() => {
    if (visible) {
      refresh();
    }
  }, [visible, refresh]);

  // Auto-select yearly package as default
  useEffect(() => {
    if (packages.length > 0 && !selectedPackage) {
      const yearly = packages.find(p => 
        p.identifier.toLowerCase().includes('yearly') ||
        p.identifier.toLowerCase().includes('annual')
      );
      setSelectedPackage(yearly || packages[0]);
    }
  }, [packages, selectedPackage]);

  // Handle RevenueCat Paywall mode
  useEffect(() => {
    if (visible && useRevenueCatPaywall) {
      handleShowRevenueCatPaywall();
    }
  }, [visible, useRevenueCatPaywall]);

  const handleShowRevenueCatPaywall = async () => {
    const result = await presentPaywall({
      onPurchaseSuccess: (customerInfo) => {
        // Update local store
        const hasLunaPro = !!customerInfo.entitlements.active[ENTITLEMENTS.LUNA_PRO];
        if (hasLunaPro) {
          const expDate = customerInfo.entitlements.active[ENTITLEMENTS.LUNA_PRO]?.expirationDate;
          setSubscription('premium', expDate ?? undefined);
          onSubscribeSuccess?.();
        }
      },
    });

    // Close modal after paywall dismisses
    onClose();
  };

  const handlePurchase = async () => {
    if (!selectedPackage) return;

    setPurchasing(true);
    try {
      const result = await purchase(selectedPackage);

      if (result.success) {
        // Update local store
        const hasLunaPro = !!result.customerInfo.entitlements.active[ENTITLEMENTS.LUNA_PRO];
        if (hasLunaPro) {
          const expDate = result.customerInfo.entitlements.active[ENTITLEMENTS.LUNA_PRO]?.expirationDate;
          setSubscription('premium', expDate ?? undefined);
        }

        Alert.alert(
          '订阅成功 🎉',
          '欢迎成为 Luna Pro 会员！',
          [{ text: '开始体验', onPress: () => {
            onSubscribeSuccess?.();
            onClose();
          }}]
        );
      } else if (!result.userCancelled) {
        Alert.alert(
          '购买失败',
          revenueCatService.getErrorMessage(result.error),
          [{ text: '好的' }]
        );
      }
    } catch (error) {
      console.error('[SubscriptionModal] Purchase error:', error);
      Alert.alert('购买失败', '请稍后重试', [{ text: '好的' }]);
    } finally {
      setPurchasing(false);
    }
  };

  const handleRestore = async () => {
    setRestoring(true);
    try {
      const restored = await restore();
      
      if (restored && isPro) {
        Alert.alert(
          '恢复成功',
          'Luna Pro 会员已恢复',
          [{ text: '好的', onPress: onClose }]
        );
      } else {
        Alert.alert(
          '无可恢复的购买',
          '未找到之前的订阅记录',
          [{ text: '好的' }]
        );
      }
    } finally {
      setRestoring(false);
    }
  };

  const getPackageDisplayName = (pkg: PurchasesPackage): string => {
    const id = pkg.identifier.toLowerCase();
    if (id.includes('lifetime')) return PLAN_INFO.lifetime.name;
    if (id.includes('yearly') || id.includes('annual')) return PLAN_INFO.yearly.name;
    return PLAN_INFO.monthly.name;
  };

  const getPackageBadge = (pkg: PurchasesPackage): string | null => {
    const id = pkg.identifier.toLowerCase();
    if (id.includes('lifetime')) return PLAN_INFO.lifetime.badge;
    if (id.includes('yearly') || id.includes('annual')) return PLAN_INFO.yearly.badge;
    return null;
  };

  const getPackageFeatures = (pkg: PurchasesPackage): string[] => {
    const id = pkg.identifier.toLowerCase();
    if (id.includes('lifetime')) return PLAN_INFO.lifetime.features;
    if (id.includes('yearly') || id.includes('annual')) return PLAN_INFO.yearly.features;
    return PLAN_INFO.monthly.features;
  };

  // Don't render custom UI if using RevenueCat paywall
  if (useRevenueCatPaywall) {
    return null;
  }

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Ionicons name="close" size={28} color="#FFFFFF" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Luna Pro</Text>
          <View style={{ width: 40 }} />
        </View>

        <ScrollView 
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* Hero Section */}
          <LinearGradient
            colors={['#8B5CF6', '#6366F1']}
            style={styles.heroGradient}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
          >
            <Ionicons name="diamond" size={48} color="#FFFFFF" />
            <Text style={styles.heroTitle}>解锁全部功能</Text>
            <Text style={styles.heroSubtitle}>
              无限消息 · 高级模型 · 专属角色
            </Text>
          </LinearGradient>

          {/* Package Selection */}
          {isLoading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#8B5CF6" />
              <Text style={styles.loadingText}>加载中...</Text>
            </View>
          ) : (
            <View style={styles.packagesContainer}>
              {packages.map((pkg) => {
                const isSelected = selectedPackage?.identifier === pkg.identifier;
                const badge = getPackageBadge(pkg);

                return (
                  <TouchableOpacity
                    key={pkg.identifier}
                    style={[
                      styles.packageCard,
                      isSelected && styles.packageCardSelected,
                    ]}
                    onPress={() => setSelectedPackage(pkg)}
                    activeOpacity={0.7}
                  >
                    {badge && (
                      <View style={styles.packageBadge}>
                        <Text style={styles.packageBadgeText}>{badge}</Text>
                      </View>
                    )}
                    
                    <View style={styles.packageHeader}>
                      <View style={[
                        styles.radioButton,
                        isSelected && styles.radioButtonSelected,
                      ]}>
                        {isSelected && <View style={styles.radioButtonInner} />}
                      </View>
                      <Text style={[
                        styles.packageName,
                        isSelected && styles.packageNameSelected,
                      ]}>
                        {getPackageDisplayName(pkg)}
                      </Text>
                    </View>

                    <Text style={styles.packagePrice}>
                      {pkg.product.priceString}
                      {!pkg.identifier.toLowerCase().includes('lifetime') && (
                        <Text style={styles.packagePeriod}>
                          /{pkg.identifier.toLowerCase().includes('yearly') ? '年' : '月'}
                        </Text>
                      )}
                    </Text>

                    {pkg.product.introPrice && (
                      <Text style={styles.introPrice}>
                        首期优惠: {pkg.product.introPrice.priceString}
                      </Text>
                    )}
                  </TouchableOpacity>
                );
              })}
            </View>
          )}

          {/* Features List */}
          {selectedPackage && (
            <View style={styles.featuresContainer}>
              <Text style={styles.featuresTitle}>包含权益</Text>
              {getPackageFeatures(selectedPackage).map((feature, index) => (
                <View key={index} style={styles.featureRow}>
                  <Ionicons name="checkmark-circle" size={20} color="#10B981" />
                  <Text style={styles.featureText}>{feature}</Text>
                </View>
              ))}
            </View>
          )}

          {/* Terms */}
          <Text style={styles.termsText}>
            订阅将自动续费，您可以随时在系统设置中取消。
            购买即表示同意我们的服务条款和隐私政策。
          </Text>
        </ScrollView>

        {/* Bottom Actions */}
        <View style={styles.bottomActions}>
          <TouchableOpacity
            style={[
              styles.purchaseButton,
              (!selectedPackage || purchasing) && styles.purchaseButtonDisabled,
            ]}
            onPress={handlePurchase}
            disabled={!selectedPackage || purchasing}
          >
            {purchasing ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.purchaseButtonText}>
                立即订阅 {selectedPackage?.product.priceString || ''}
              </Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.restoreButton}
            onPress={handleRestore}
            disabled={restoring}
          >
            {restoring ? (
              <ActivityIndicator size="small" color="#8B5CF6" />
            ) : (
              <Text style={styles.restoreButtonText}>恢复购买</Text>
            )}
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
};

// ============================================================================
// Styles
// ============================================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#111827',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 12,
  },
  closeButton: {
    padding: 8,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 24,
  },
  heroGradient: {
    margin: 16,
    padding: 32,
    borderRadius: 20,
    alignItems: 'center',
  },
  heroTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#FFFFFF',
    marginTop: 16,
  },
  heroSubtitle: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.8)',
    marginTop: 8,
  },
  loadingContainer: {
    padding: 40,
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    color: '#9CA3AF',
    fontSize: 14,
  },
  packagesContainer: {
    paddingHorizontal: 16,
    gap: 12,
  },
  packageCard: {
    backgroundColor: '#1F2937',
    borderRadius: 16,
    padding: 20,
    borderWidth: 2,
    borderColor: 'transparent',
    position: 'relative',
  },
  packageCardSelected: {
    borderColor: '#8B5CF6',
    backgroundColor: 'rgba(139, 92, 246, 0.1)',
  },
  packageBadge: {
    position: 'absolute',
    top: -10,
    right: 16,
    backgroundColor: '#F59E0B',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  packageBadgeText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '600',
  },
  packageHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  radioButton: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#4B5563',
    justifyContent: 'center',
    alignItems: 'center',
  },
  radioButtonSelected: {
    borderColor: '#8B5CF6',
  },
  radioButtonInner: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#8B5CF6',
  },
  packageName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  packageNameSelected: {
    color: '#8B5CF6',
  },
  packagePrice: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
    marginTop: 12,
  },
  packagePeriod: {
    fontSize: 16,
    fontWeight: '400',
    color: '#9CA3AF',
  },
  introPrice: {
    fontSize: 14,
    color: '#10B981',
    marginTop: 4,
  },
  featuresContainer: {
    marginTop: 24,
    paddingHorizontal: 16,
  },
  featuresTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 16,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 8,
  },
  featureText: {
    fontSize: 16,
    color: '#D1D5DB',
  },
  termsText: {
    marginTop: 24,
    marginHorizontal: 16,
    fontSize: 12,
    color: '#6B7280',
    textAlign: 'center',
    lineHeight: 18,
  },
  bottomActions: {
    padding: 16,
    paddingBottom: 32,
    backgroundColor: '#111827',
    borderTopWidth: 1,
    borderTopColor: '#1F2937',
  },
  purchaseButton: {
    backgroundColor: '#8B5CF6',
    borderRadius: 14,
    paddingVertical: 18,
    alignItems: 'center',
  },
  purchaseButtonDisabled: {
    backgroundColor: '#4B5563',
  },
  purchaseButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '600',
  },
  restoreButton: {
    marginTop: 12,
    paddingVertical: 12,
    alignItems: 'center',
  },
  restoreButtonText: {
    color: '#8B5CF6',
    fontSize: 14,
    fontWeight: '500',
  },
});

export default SubscriptionModalRC;
