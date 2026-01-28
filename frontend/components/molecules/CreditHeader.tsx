/**
 * CreditHeader Component
 * 
 * Sticky header displaying user's credit balance with buy button.
 * Features:
 * - Animated credit counter
 * - Low balance warning
 * - Quick buy CTA
 */

import React, { useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Platform,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withSequence,
} from 'react-native-reanimated';
import { theme, getShadow } from '../../theme/config';
import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';

interface CreditHeaderProps {
  credits: number;
  onBuyCredits: () => void;
  isSpicyMode?: boolean;
}

export const CreditHeader: React.FC<CreditHeaderProps> = ({
  credits,
  onBuyCredits,
  isSpicyMode = false,
}) => {
  const scale = useSharedValue(1);
  const isLowBalance = credits < 10;

  // Animate when credits change
  useEffect(() => {
    scale.value = withSequence(
      withSpring(1.2, { damping: 10 }),
      withSpring(1, { damping: 10 })
    );
  }, [credits]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const accentColor = isSpicyMode
    ? theme.colors.spicy.main
    : theme.colors.primary.main;

  return (
    <BlurView intensity={80} style={styles.container}>
      <View style={styles.content}>
        {/* Credit Balance */}
        <View style={styles.balanceContainer}>
          <Ionicons name="diamond" size={20} color={accentColor} />
          <Animated.View style={animatedStyle}>
            <Text style={[styles.credits, { color: isLowBalance ? theme.colors.warning : theme.colors.text.primary }]}>
              {credits.toFixed(2)}
            </Text>
          </Animated.View>
          <Text style={styles.creditsLabel}>credits</Text>
        </View>

        {/* Low Balance Warning */}
        {isLowBalance && (
          <View style={styles.warningContainer}>
            <Ionicons name="warning" size={14} color={theme.colors.warning} />
            <Text style={styles.warningText}>Low balance</Text>
          </View>
        )}

        {/* Buy Button */}
        <TouchableOpacity
          style={styles.buyButton}
          onPress={onBuyCredits}
          activeOpacity={0.8}
        >
          <LinearGradient
            colors={isSpicyMode ? theme.colors.spicy.gradient : theme.colors.primary.gradient}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.buyButtonGradient}
          >
            <Ionicons name="add-circle" size={20} color={theme.colors.text.inverse} />
            <Text style={styles.buyButtonText}>Buy</Text>
          </LinearGradient>
        </TouchableOpacity>
      </View>
    </BlurView>
  );
};

const styles = StyleSheet.create({
  container: {
    paddingTop: Platform.OS === 'ios' ? 50 : 10,
    paddingBottom: theme.spacing.sm,
    paddingHorizontal: theme.spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
    ...getShadow('sm'),
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  balanceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.xs,
  },
  credits: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize.xl,
  },
  creditsLabel: {
    fontFamily: theme.typography.fontFamily.medium,
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.secondary,
  },
  warningContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
    borderRadius: theme.borderRadius.full,
  },
  warningText: {
    fontFamily: theme.typography.fontFamily.medium,
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.warning,
  },
  buyButton: {
    borderRadius: theme.borderRadius.lg,
    overflow: 'hidden',
  },
  buyButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: theme.spacing.sm,
    paddingHorizontal: theme.spacing.md,
    gap: theme.spacing.xs,
  },
  buyButtonText: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.inverse,
  },
});
