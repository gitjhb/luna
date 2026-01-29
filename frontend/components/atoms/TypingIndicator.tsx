/**
 * TypingIndicator Component
 * 
 * Simple animated dots showing typing status.
 */

import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { theme } from '../../theme/config';

interface TypingIndicatorProps {
  isSpicyMode?: boolean;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  isSpicyMode = false,
}) => {
  const [dots, setDots] = useState('.');

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? '.' : prev + '.'));
    }, 400);
    return () => clearInterval(interval);
  }, []);

  const accentColor = isSpicyMode
    ? theme.colors.spicy.main
    : theme.colors.primary.main;

  return (
    <View style={styles.container}>
      <View style={[styles.bubble, { backgroundColor: accentColor + '20' }]}>
        <Text style={[styles.dots, { color: accentColor }]}>{dots}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    alignItems: 'flex-start',
  },
  bubble: {
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.md,
    borderRadius: theme.borderRadius.lg,
    minWidth: 60,
    alignItems: 'center',
  },
  dots: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize.xl,
    letterSpacing: 2,
  },
});
