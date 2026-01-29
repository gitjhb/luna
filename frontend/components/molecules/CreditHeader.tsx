/**
 * CreditHeader Component
 * 
 * Header displaying user's credit balance with buy button.
 */

import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { theme, getShadow } from '../../theme/config';
import { Ionicons } from '@expo/vector-icons';

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
  const isLowBalance = credits < 10;
  const accentColor = isSpicyMode
    ? theme.colors.spicy.main
    : theme.colors.primary.main;

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        {/* Credit Balance */}
        <View style={styles.balanceContainer}>
          <Ionicons name="diamond" size={20} color={accentColor} />
          <Text style={[styles.credits, { color: isLowBalance ? theme.colors.warning : theme.colors.text.primary }]}>
            {credits.toFixed(1)}
          </Text>
          <Text style={styles.creditsLabel}>credits</Text>
        </View>

        {/* Low Balance Warning */}
        {isLowBalance && (
          <View style={styles.warningContainer}>
            <Ionicons name="warning" size={14} color={theme.colors.warning} />
            <Text style={styles.warningText}>Low</Text>
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
            <Ionicons name="add-circle" size={18} color={theme.colors.text.inverse} />
            <Text style={styles.buyButtonText}>Buy</Text>
          </LinearGradient>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: theme.colors.background.secondary,
    paddingVertical: theme.spacing.sm,
    paddingHorizontal: theme.spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
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
