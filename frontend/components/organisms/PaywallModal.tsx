/**
 * PaywallModal Component
 * 
 * High-conversion subscription paywall modal.
 * Shown when user tries to access premium features without subscription.
 * 
 * Features:
 * - Compelling value proposition
 * - Subscription plans with pricing
 * - "Restore Purchases" option
 * - Dismissible
 */

import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Modal,
  ScrollView,
  Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { theme, getShadow } from '../../theme/config';
import { Ionicons } from '@expo/vector-icons';
import { SubscriptionPlan } from '../../types';

const { height: SCREEN_HEIGHT } = Dimensions.get('window');

interface PaywallModalProps {
  visible: boolean;
  onClose: () => void;
  onSubscribe: (plan: SubscriptionPlan) => void;
  onRestore?: () => void;
  feature?: string; // e.g., "Spicy Mode"
}

export const PaywallModal: React.FC<PaywallModalProps> = ({
  visible,
  onClose,
  onSubscribe,
  onRestore,
  feature = "Premium Features",
}) => {
  // Mock subscription plans (replace with API data)
  const plans: SubscriptionPlan[] = [
    {
      sku: 'premium_monthly',
      name: 'Premium',
      tier: 'premium',
      priceUsd: 9.99,
      billingPeriod: 'monthly',
      bonusCredits: 200,
      features: [
        '100 daily free credits',
        'RAG memory system',
        'Spicy Mode access',
        '30% discount on credits',
        '30 requests/minute',
      ],
      popular: true,
    },
    {
      sku: 'vip_monthly',
      name: 'VIP',
      tier: 'vip',
      priceUsd: 29.99,
      billingPeriod: 'monthly',
      bonusCredits: 1000,
      features: [
        '500 daily free credits',
        'Advanced RAG memory',
        'All Spicy characters',
        '50% discount on credits',
        '100 requests/minute',
        'Priority support',
      ],
    },
  ];

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <BlurView intensity={80} style={styles.overlay}>
        <View style={styles.container}>
          {/* Close Button */}
          <TouchableOpacity style={styles.closeButton} onPress={onClose}>
            <Ionicons name="close" size={28} color={theme.colors.text.primary} />
          </TouchableOpacity>

          <ScrollView
            showsVerticalScrollIndicator={false}
            contentContainerStyle={styles.scrollContent}
          >
            {/* Header */}
            <View style={styles.header}>
              <LinearGradient
                colors={theme.colors.spicy.gradient}
                style={styles.iconContainer}
              >
                <Ionicons name="flame" size={40} color={theme.colors.text.inverse} />
              </LinearGradient>
              <Text style={styles.title}>Unlock {feature}</Text>
              <Text style={styles.subtitle}>
                Subscribe to access premium features and exclusive content
              </Text>
            </View>

            {/* Plans */}
            <View style={styles.plansContainer}>
              {plans.map((plan) => (
                <TouchableOpacity
                  key={plan.sku}
                  style={[
                    styles.planCard,
                    plan.popular && styles.popularPlanCard,
                  ]}
                  onPress={() => onSubscribe(plan)}
                  activeOpacity={0.8}
                >
                  {plan.popular && (
                    <View style={styles.popularBadge}>
                      <Text style={styles.popularBadgeText}>MOST POPULAR</Text>
                    </View>
                  )}

                  <View style={styles.planHeader}>
                    <Text style={styles.planName}>{plan.name}</Text>
                    <View style={styles.planPricing}>
                      <Text style={styles.planPrice}>${plan.priceUsd}</Text>
                      <Text style={styles.planPeriod}>/{plan.billingPeriod}</Text>
                    </View>
                  </View>

                  <View style={styles.bonusCredits}>
                    <Ionicons name="diamond" size={16} color={theme.colors.primary.main} />
                    <Text style={styles.bonusCreditsText}>
                      +{plan.bonusCredits} bonus credits
                    </Text>
                  </View>

                  <View style={styles.featuresContainer}>
                    {plan.features.map((feature, index) => (
                      <View key={index} style={styles.featureRow}>
                        <Ionicons
                          name="checkmark-circle"
                          size={18}
                          color={theme.colors.success}
                        />
                        <Text style={styles.featureText}>{feature}</Text>
                      </View>
                    ))}
                  </View>

                  <LinearGradient
                    colors={plan.popular ? theme.colors.spicy.gradient : theme.colors.primary.gradient}
                    style={styles.subscribeButton}
                  >
                    <Text style={styles.subscribeButtonText}>Subscribe Now</Text>
                  </LinearGradient>
                </TouchableOpacity>
              ))}
            </View>

            {/* Restore Purchases */}
            {onRestore && (
              <TouchableOpacity style={styles.restoreButton} onPress={onRestore}>
                <Text style={styles.restoreButtonText}>Restore Purchases</Text>
              </TouchableOpacity>
            )}

            {/* Terms */}
            <Text style={styles.terms}>
              Subscriptions auto-renew unless canceled 24 hours before the end of the
              current period. Manage in Account Settings.
            </Text>
          </ScrollView>
        </View>
      </BlurView>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  container: {
    backgroundColor: theme.colors.background.primary,
    borderTopLeftRadius: theme.borderRadius['2xl'],
    borderTopRightRadius: theme.borderRadius['2xl'],
    maxHeight: SCREEN_HEIGHT * 0.9,
    ...getShadow('xl'),
  },
  closeButton: {
    position: 'absolute',
    top: theme.spacing.md,
    right: theme.spacing.md,
    zIndex: 10,
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.background.secondary,
    borderRadius: theme.borderRadius.full,
  },
  scrollContent: {
    padding: theme.spacing.lg,
    paddingTop: theme.spacing['2xl'],
  },
  header: {
    alignItems: 'center',
    marginBottom: theme.spacing.xl,
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: theme.borderRadius.full,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  title: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize['2xl'],
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.xs,
  },
  subtitle: {
    fontFamily: theme.typography.fontFamily.regular,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
    textAlign: 'center',
    lineHeight: theme.typography.fontSize.base * theme.typography.lineHeight.normal,
  },
  plansContainer: {
    gap: theme.spacing.md,
    marginBottom: theme.spacing.lg,
  },
  planCard: {
    backgroundColor: theme.colors.background.secondary,
    borderRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  popularPlanCard: {
    borderColor: theme.colors.spicy.main,
  },
  popularBadge: {
    position: 'absolute',
    top: -12,
    alignSelf: 'center',
    backgroundColor: theme.colors.spicy.main,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.xs,
    borderRadius: theme.borderRadius.full,
  },
  popularBadgeText: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.text.inverse,
  },
  planHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  planName: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize.xl,
    color: theme.colors.text.primary,
  },
  planPricing: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  planPrice: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize['2xl'],
    color: theme.colors.primary.main,
  },
  planPeriod: {
    fontFamily: theme.typography.fontFamily.medium,
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.secondary,
  },
  bonusCredits: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.xs,
    marginBottom: theme.spacing.md,
  },
  bonusCreditsText: {
    fontFamily: theme.typography.fontFamily.medium,
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.primary.main,
  },
  featuresContainer: {
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.md,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
  },
  featureText: {
    fontFamily: theme.typography.fontFamily.regular,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
    flex: 1,
  },
  subscribeButton: {
    borderRadius: theme.borderRadius.lg,
    paddingVertical: theme.spacing.md,
    alignItems: 'center',
  },
  subscribeButtonText: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize.lg,
    color: theme.colors.text.inverse,
  },
  restoreButton: {
    paddingVertical: theme.spacing.md,
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  restoreButtonText: {
    fontFamily: theme.typography.fontFamily.medium,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
  },
  terms: {
    fontFamily: theme.typography.fontFamily.regular,
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.text.tertiary,
    textAlign: 'center',
    lineHeight: theme.typography.fontSize.xs * theme.typography.lineHeight.relaxed,
  },
});
