/**
 * Subscription Modal - Premium/VIP subscription purchase
 * 
 * Shows available plans and handles subscription flow
 */

import React, { useState, useEffect } from 'react';
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
import { pricingService, MembershipPlan } from '../services/pricingService';
import { paymentService } from '../services/paymentService';
import { useUserStore } from '../store/userStore';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface SubscriptionModalProps {
  visible: boolean;
  onClose: () => void;
  onSubscribeSuccess?: (tier: string) => void;
  highlightFeature?: string; // e.g., "spicy" to highlight that feature
}

export const SubscriptionModal: React.FC<SubscriptionModalProps> = ({
  visible,
  onClose,
  onSubscribeSuccess,
  highlightFeature,
}) => {
  const { user, updateUser, isSubscribed } = useUserStore();
  const [plans, setPlans] = useState<MembershipPlan[]>([]);
  const [loading, setLoading] = useState(false);
  const [subscribing, setSubscribing] = useState<string | null>(null);

  // Load plans when modal opens
  useEffect(() => {
    if (visible) {
      loadPlans();
    }
  }, [visible]);

  const loadPlans = async () => {
    try {
      setLoading(true);
      const membershipPlans = await pricingService.getMembershipPlans();
      // Filter out free plan, only show paid plans
      setPlans(membershipPlans.filter(p => p.tier !== 'free'));
    } catch (error) {
      console.error('Failed to load plans:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = (plan: MembershipPlan) => {
    Alert.alert(
      '确认订阅',
      `订阅 ${plan.name} 会员\n$${plan.price.toFixed(2)}/月\n\n功能包括：\n${plan.features.join('\n')}`,
      [
        { text: '取消', style: 'cancel' },
        {
          text: '订阅',
          onPress: async () => {
            try {
              setSubscribing(plan.id);
              
              const result = await paymentService.subscribe(
                plan.id,
                'monthly',
                'mock'
              );
              
              if (result.success) {
                // Update user subscription status
                updateUser({
                  subscriptionTier: plan.tier as 'free' | 'premium' | 'vip',
                  subscriptionExpiresAt: result.subscription.expires_at || undefined,
                });
                
                onSubscribeSuccess?.(plan.tier);
                onClose();
                
                Alert.alert(
                  '🎉 订阅成功！',
                  `欢迎成为 ${plan.name} 会员！\n现在可以享受所有高级功能了。`
                );
              }
            } catch (error: any) {
              Alert.alert('订阅失败', error.message || '请稍后重试');
            } finally {
              setSubscribing(null);
            }
          },
        },
      ]
    );
  };

  const getGradientColors = (tier: string): [string, string] => {
    switch (tier) {
      case 'premium':
        return ['#8B5CF6', '#EC4899'];
      case 'vip':
        return ['#F59E0B', '#EF4444'];
      default:
        return ['#6B7280', '#4B5563'];
    }
  };

  const renderPlanCard = (plan: MembershipPlan) => {
    const isCurrentPlan = user?.subscriptionTier === plan.tier;
    const isPurchasing = subscribing === plan.id;
    
    // Can upgrade: VIP is higher than Premium
    const tierRank: Record<string, number> = { free: 0, premium: 1, vip: 2 };
    const currentRank = tierRank[user?.subscriptionTier || 'free'] || 0;
    const planRank = tierRank[plan.tier] || 0;
    const canUpgrade = planRank > currentRank;
    const isDowngrade = planRank < currentRank;
    
    return (
      <TouchableOpacity
        key={plan.id}
        style={[styles.planCard, isCurrentPlan && styles.planCardCurrent]}
        onPress={() => (canUpgrade || !isSubscribed) && handleSubscribe(plan)}
        disabled={isCurrentPlan || isDowngrade || isPurchasing}
        activeOpacity={0.85}
      >
        <LinearGradient
          colors={getGradientColors(plan.tier)}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.planGradient}
        >
          {/* Header */}
          <View style={styles.planHeader}>
            <Text style={styles.planName}>{plan.name}</Text>
            {plan.highlighted && (
              <View style={styles.popularBadge}>
                <Text style={styles.popularBadgeText}>推荐</Text>
              </View>
            )}
            {isCurrentPlan && (
              <View style={styles.currentBadge}>
                <Text style={styles.currentBadgeText}>当前</Text>
              </View>
            )}
          </View>

          {/* Price */}
          <View style={styles.priceRow}>
            <Text style={styles.priceAmount}>${plan.price.toFixed(2)}</Text>
            <Text style={styles.pricePeriod}>/月</Text>
          </View>

          {/* Daily Credits */}
          <Text style={styles.dailyCredits}>
            🪙 每日 +{plan.dailyCredits} 金币
          </Text>

          {/* Features */}
          <View style={styles.featuresContainer}>
            {plan.features.map((feature, index) => {
              // Highlight the feature if it matches
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

          {/* Subscribe/Upgrade Button */}
          {!isCurrentPlan && !isDowngrade && (
            <TouchableOpacity
              style={styles.subscribeButton}
              onPress={() => handleSubscribe(plan)}
              disabled={isPurchasing}
            >
              {isPurchasing ? (
                <ActivityIndicator size="small" color="#8B5CF6" />
              ) : (
                <Text style={styles.subscribeButtonText}>
                  {canUpgrade ? '升级到 ' + plan.name : '立即订阅'}
                </Text>
              )}
            </TouchableOpacity>
          )}

          {/* Downgrade - disabled */}
          {isDowngrade && (
            <View style={[styles.subscribedBadge, { opacity: 0.5 }]}>
              <Text style={styles.subscribedText}>当前等级更高</Text>
            </View>
          )}

          {/* Already subscribed */}
          {isCurrentPlan && (
            <View style={styles.subscribedBadge}>
              <Ionicons name="checkmark-circle" size={18} color="#fff" />
              <Text style={styles.subscribedText}>已订阅</Text>
            </View>
          )}
        </LinearGradient>
      </TouchableOpacity>
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
              <View style={styles.titleRow}>
                <Text style={styles.title}>升级会员</Text>
                <View style={styles.testBadge}>
                  <Text style={styles.testBadgeText}>测试模式</Text>
                </View>
              </View>
              <Text style={styles.subtitle}>解锁全部高级功能</Text>
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
                  ? '订阅解锁成人内容，体验更亲密的对话 🔞'
                  : `订阅解锁 ${highlightFeature} 功能`
                }
              </Text>
            </View>
          )}

          {/* Plans */}
          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#EC4899" />
            </View>
          ) : (
            <ScrollView 
              style={styles.scroll} 
              showsVerticalScrollIndicator={false}
              contentContainerStyle={styles.scrollContent}
            >
              {plans.map(renderPlanCard)}
              
              {/* Terms */}
              <Text style={styles.termsText}>
                订阅将自动续费，可随时在设置中取消。{'\n'}
                价格可能因地区而异。
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
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#fff',
  },
  testBadge: {
    backgroundColor: 'rgba(255, 165, 0, 0.2)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
  },
  testBadgeText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#FFA500',
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
  dailyCredits: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFD700',
    marginBottom: 16,
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
  termsText: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.4)',
    textAlign: 'center',
    lineHeight: 18,
    marginTop: 8,
  },
});

export default SubscriptionModal;
