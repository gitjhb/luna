/**
 * Subscription Modal - Premium/VIP subscription purchase
 * 
 * Uses react-native-iap for real App Store / Google Play subscriptions
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
  Platform,
  Image,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { iapService, IAPProduct, IAPPurchaseResult, SUBSCRIPTION_SKUS } from '../services/iapService';
import { paymentService } from '../services/paymentService';
import { useUserStore } from '../store/userStore';
import { useLocale } from '../i18n';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Get fallback display info when products aren't loaded from store yet
const getPlanDisplayInfo = (t: any): Record<string, { name: string; features: string[]; dailyCredits: number }> => ({
  'luna_premium_monthly': {
    name: 'Premium',
    dailyCredits: 100,
    features: [
      t.subscription.dailyCredits.replace('{amount}', '100'),
      t.subscription.fasterResponse,
      t.subscription.premiumCharacters,
      t.subscription.adultContent,
      t.subscription.prioritySupport,
    ],
  },
});

interface SubscriptionModalProps {
  visible: boolean;
  onClose: () => void;
  onSubscribeSuccess?: (tier: string) => void;
  highlightFeature?: string;
}

export const SubscriptionModal: React.FC<SubscriptionModalProps> = ({
  visible,
  onClose,
  onSubscribeSuccess,
  highlightFeature,
}) => {
  const { t } = useLocale();
  const { user, updateUser, isSubscribed } = useUserStore();
  const [products, setProducts] = useState<IAPProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [purchasing, setPurchasing] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(false);

  // Load products when modal opens
  useEffect(() => {
    if (visible) {
      loadProducts();
      setupPurchaseCallbacks();
    }
  }, [visible]);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const iapProducts = await iapService.getProducts();
      console.log('[SubscriptionModal] Loaded products:', iapProducts);
      setProducts(iapProducts);
    } catch (error) {
      console.error('[SubscriptionModal] Failed to load products:', error);
      // Show fallback UI with mock data for testing
    } finally {
      setLoading(false);
    }
  };

  const setupPurchaseCallbacks = useCallback(() => {
    iapService.setCallbacks(
      // On success
      async (result: IAPPurchaseResult) => {
        console.log('[SubscriptionModal] Purchase success:', result);
        setPurchasing(null);

        try {
          // Verify receipt with backend
          const verification = await paymentService.verifyReceipt(
            result.receipt,
            result.productId,
            Platform.OS
          );

          if (verification.success) {
            // Update local user state
            updateUser({
              subscriptionTier: result.tier,
              subscriptionExpiresAt: verification.expiresAt,
            });

            onSubscribeSuccess?.(result.tier);
            onClose();

            const PLAN_DISPLAY_INFO = getPlanDisplayInfo(t);
            const planName = PLAN_DISPLAY_INFO[result.productId]?.name || result.tier.toUpperCase();
            
            Alert.alert(
              t.subscription.subscribeSuccessTitle,
              t.subscription.subscribeSuccessMessage.replace('{planName}', planName)
            );
          } else {
            Alert.alert(t.subscription.verificationFailed, verification.message || t.subscription.contactSupport);
          }
        } catch (err: any) {
          console.error('[SubscriptionModal] Receipt verification failed:', err);
          Alert.alert(t.subscription.verificationFailed, t.subscription.subscriptionMightSucceed);
        }
      },
      // On error
      (error) => {
        console.warn('[SubscriptionModal] Purchase error:', error);
        setPurchasing(null);

        // User cancelled - don't show error
        if (error.code === 'E_USER_CANCELLED') {
          return;
        }

        Alert.alert(
          t.subscription.purchaseFailed,
          error.message || t.gift.retryLater
        );
      }
    );
  }, [onSubscribeSuccess, onClose, updateUser]);

  const handlePurchase = async (productId: string) => {
    setPurchasing(productId);

    try {
      await iapService.purchaseSubscription(productId);
      // Result handled in callback
    } catch (err: any) {
      console.error('[SubscriptionModal] Purchase error:', err);
      setPurchasing(null);
      
      if (err.code !== 'E_USER_CANCELLED') {
        Alert.alert(t.subscription.purchaseFailed, err.message || t.gift.retryLater);
      }
    }
  };

  const handleRestore = async () => {
    setRestoring(true);

    try {
      const restored = await iapService.restorePurchases();
      
      if (restored.length > 0) {
        // Find highest tier
        const tier = 'premium';

        // Verify with backend
        const latest = restored[restored.length - 1];
        const verification = await paymentService.verifyReceipt(
          latest.receipt,
          latest.productId,
          Platform.OS
        );

        if (verification.success) {
          updateUser({
            subscriptionTier: tier,
            subscriptionExpiresAt: verification.expiresAt,
          });

          Alert.alert(t.subscription.restoreSuccess, t.subscription.restoreSuccessMessage.replace('{tier}', tier.toUpperCase()));
          onClose();
        } else {
          Alert.alert(t.subscription.restoreFailed, t.subscription.noValidSubscription);
        }
      } else {
        Alert.alert(t.subscription.noSubscriptionFound, t.subscription.noPurchaseHistory);
      }
    } catch (err: any) {
      console.error('[SubscriptionModal] Restore error:', err);
      Alert.alert(t.subscription.restoreFailed, err.message || t.gift.retryLater);
    } finally {
      setRestoring(false);
    }
  };

  const getGradientColors = (tier: string): [string, string] => {
    switch (tier) {
      case 'premium':
        return ['#8B5CF6', '#00D4FF'];
      default:
        return ['#6B7280', '#4B5563'];
    }
  };

  const renderProductCard = (product: IAPProduct) => {
    const PLAN_DISPLAY_INFO = getPlanDisplayInfo(t);
    const displayInfo = PLAN_DISPLAY_INFO[product.productId];
    const isCurrentPlan = user?.subscriptionTier === product.tier;
    const isPurchasing = purchasing === product.productId;
    
    const tierRank: Record<string, number> = { free: 0, premium: 1 };
    const currentRank = tierRank[user?.subscriptionTier || 'free'] || 0;
    const planRank = tierRank[product.tier] || 0;
    const canUpgrade = planRank > currentRank;
    const isDowngrade = planRank < currentRank;
    
    return (
      <TouchableOpacity
        key={product.productId}
        style={[styles.planCard, isCurrentPlan && styles.planCardCurrent]}
        onPress={() => (canUpgrade || !isSubscribed) && handlePurchase(product.productId)}
        disabled={isCurrentPlan || isDowngrade || isPurchasing}
        activeOpacity={0.85}
      >
        <LinearGradient
          colors={getGradientColors(product.tier)}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.planGradient}
        >
          {/* Header */}
          <View style={styles.planHeader}>
            <Text style={styles.planName}>{displayInfo?.name || product.title}</Text>
            {isCurrentPlan && (
              <View style={styles.currentBadge}>
                <Text style={styles.currentBadgeText}>{t.subscription.current}</Text>
              </View>
            )}
          </View>

          {/* Price - from App Store */}
          <View style={styles.priceRow}>
            <Text style={styles.priceAmount}>{product.price}</Text>
            <Text style={styles.pricePeriod}>{t.subscription.perMonth}</Text>
          </View>

          {/* Daily Credits */}
          <View style={styles.dailyCreditsRow}>
            <Image source={require('../assets/icons/moon-shard.png')} style={styles.shardIcon} />
            <Text style={styles.dailyCredits}>
              {t.subscription.dailyBonus.replace('{amount}', (displayInfo?.dailyCredits || 100).toString())}
            </Text>
          </View>

          {/* Features */}
          <View style={styles.featuresContainer}>
            {(displayInfo?.features || []).map((feature, index) => {
              const isHighlighted = highlightFeature && 
                feature.toLowerCase().includes(highlightFeature.toLowerCase());
              
              return (
                <View key={index} style={styles.featureRow}>
                  <Ionicons 
                    name="checkmark-circle" 
                    size={16} 
                    color={isHighlighted ? '#FFD700' : 'rgba(255,255,255,0.9)'} 
                  />
                  <Text style={[
                    styles.featureText,
                    isHighlighted && styles.featureTextHighlighted,
                  ]}>
                    {feature}
                  </Text>
                </View>
              );
            })}
          </View>

          {/* Subscribe Button */}
          {!isCurrentPlan && !isDowngrade && (
            <TouchableOpacity
              style={styles.subscribeButton}
              onPress={() => handlePurchase(product.productId)}
              disabled={isPurchasing}
            >
              {isPurchasing ? (
                <ActivityIndicator size="small" color="#8B5CF6" />
              ) : (
                <Text style={styles.subscribeButtonText}>
                  {canUpgrade ? t.subscription.upgrade : t.subscription.subscribe}
                </Text>
              )}
            </TouchableOpacity>
          )}

          {isDowngrade && (
            <View style={[styles.subscribedBadge, { opacity: 0.5 }]}>
              <Text style={styles.subscribedText}>{t.subscription.higherTier}</Text>
            </View>
          )}

          {isCurrentPlan && (
            <View style={styles.subscribedBadge}>
              <Ionicons name="checkmark-circle" size={18} color="#fff" />
              <Text style={styles.subscribedText}>{t.subscription.subscribed}</Text>
            </View>
          )}
        </LinearGradient>
      </TouchableOpacity>
    );
  };

  // Fallback UI when no products available from App Store
  const renderFallbackProducts = () => {
    return (
      <View style={styles.fallbackContainer}>
        <Ionicons name="alert-circle-outline" size={48} color="rgba(255,255,255,0.4)" />
        <Text style={styles.fallbackTitle}>{t.subscription.productsLoading}</Text>
        <Text style={styles.fallbackText}>
          {t.subscription.checkConfiguration}
        </Text>
        <Text style={styles.fallbackSkus}>
          {t.subscription.requiresConfiguration}{SUBSCRIPTION_SKUS.join(', ')}
        </Text>
      </View>
    );
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <View style={styles.content}>
          {/* Header */}
          <View style={styles.header}>
            <View>
              <Text style={styles.title}>{t.subscription.title}</Text>
              <Text style={styles.subtitle}>{t.subscription.subtitle}</Text>
            </View>
            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>
          </View>

          {/* Feature Highlight */}
          {highlightFeature && (
            <View style={styles.highlightBanner}>
              <Ionicons name="sparkles" size={18} color="#FFD700" />
              <Text style={styles.highlightText}>
                {highlightFeature === 'nsfw' 
                  ? t.subscription.unlockAdultContent
                  : t.subscription.unlockFeature.replace('{feature}', highlightFeature)
                }
              </Text>
            </View>
          )}

          {/* Plans */}
          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#00D4FF" />
              <Text style={styles.loadingText}>{t.subscription.loading}</Text>
            </View>
          ) : (
            <ScrollView 
              style={styles.scroll} 
              showsVerticalScrollIndicator={false}
              contentContainerStyle={styles.scrollContent}
            >
              {products.length > 0 
                ? products.map(renderProductCard)
                : renderFallbackProducts()
              }
              
              {/* Restore Purchases */}
              <TouchableOpacity 
                style={styles.restoreButton}
                onPress={handleRestore}
                disabled={restoring}
              >
                {restoring ? (
                  <ActivityIndicator size="small" color="rgba(255,255,255,0.6)" />
                ) : (
                  <Text style={styles.restoreText}>{t.subscription.restorePurchases}</Text>
                )}
              </TouchableOpacity>
              
              {/* Terms */}
              <Text style={styles.termsText}>
                {t.subscription.autoRenewTerms.replace(
                  '{platform}', 
                  Platform.OS === 'ios' ? t.subscription.appleId : t.subscription.googlePlay
                )}
              </Text>
            </ScrollView>
          )}
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'flex-end',
  },
  content: {
    backgroundColor: '#1A1A2E',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '85%',
    paddingBottom: 34,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: 20,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#fff',
  },
  subtitle: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.6)',
    marginTop: 4,
  },
  closeButton: {
    padding: 4,
  },
  highlightBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 215, 0, 0.15)',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 8,
  },
  highlightText: {
    fontSize: 14,
    color: '#FFD700',
    fontWeight: '500',
    flex: 1,
  },
  loadingContainer: {
    height: 300,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.6)',
  },
  scroll: {
    maxHeight: 500,
  },
  scrollContent: {
    padding: 16,
    gap: 16,
  },
  planCard: {
    borderRadius: 16,
    overflow: 'hidden',
  },
  planCardCurrent: {
    opacity: 0.8,
  },
  planGradient: {
    padding: 20,
  },
  planHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 12,
  },
  planName: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
  },
  popularBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.25)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 10,
  },
  popularBadgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#fff',
  },
  currentBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 10,
  },
  currentBadgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#fff',
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: 8,
  },
  priceAmount: {
    fontSize: 36,
    fontWeight: '800',
    color: '#fff',
  },
  pricePeriod: {
    fontSize: 16,
    fontWeight: '500',
    color: 'rgba(255, 255, 255, 0.7)',
    marginLeft: 4,
  },
  dailyCreditsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    marginBottom: 16,
  },
  shardIcon: {
    width: 22,
    height: 22,
    borderRadius: 11,
  },
  dailyCredits: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFD700',
  },
  featuresContainer: {
    gap: 8,
    marginBottom: 16,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  featureText: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.9)',
  },
  featureTextHighlighted: {
    color: '#FFD700',
    fontWeight: '600',
  },
  subscribeButton: {
    backgroundColor: '#fff',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
  },
  subscribeButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#8B5CF6',
  },
  subscribedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
  },
  subscribedText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  restoreButton: {
    alignItems: 'center',
    paddingVertical: 12,
  },
  restoreText: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.6)',
    textDecorationLine: 'underline',
  },
  fallbackContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40,
    paddingHorizontal: 20,
  },
  fallbackTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: 'rgba(255, 255, 255, 0.7)',
    marginTop: 16,
    marginBottom: 8,
  },
  fallbackText: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.5)',
    textAlign: 'center',
    marginBottom: 12,
  },
  fallbackSkus: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.3)',
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  termsText: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.4)',
    textAlign: 'center',
    lineHeight: 18,
    marginTop: 8,
  },
});

export default SubscriptionModal;
