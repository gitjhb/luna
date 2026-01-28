/**
 * TypingIndicator Component
 * 
 * Subtle animation showing the AI is "thinking".
 * Three animated dots with sequential timing.
 */

import React, { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withSequence,
  withTiming,
  withDelay,
} from 'react-native-reanimated';
import { theme } from '../../theme/config';

interface TypingIndicatorProps {
  isSpicyMode?: boolean;
}

const Dot: React.FC<{ delay: number; isSpicyMode?: boolean }> = ({ delay, isSpicyMode }) => {
  const opacity = useSharedValue(0.3);
  const scale = useSharedValue(1);

  useEffect(() => {
    opacity.value = withDelay(
      delay,
      withRepeat(
        withSequence(
          withTiming(1, { duration: 400 }),
          withTiming(0.3, { duration: 400 })
        ),
        -1,
        false
      )
    );

    scale.value = withDelay(
      delay,
      withRepeat(
        withSequence(
          withTiming(1.2, { duration: 400 }),
          withTiming(1, { duration: 400 })
        ),
        -1,
        false
      )
    );
  }, []);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: opacity.value,
    transform: [{ scale: scale.value }],
  }));

  const dotColor = isSpicyMode
    ? theme.colors.spicy.main
    : theme.colors.text.secondary;

  return (
    <Animated.View
      style={[
        styles.dot,
        { backgroundColor: dotColor },
        animatedStyle,
      ]}
    />
  );
};

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({ isSpicyMode = false }) => {
  return (
    <View style={styles.container}>
      <View style={styles.bubble}>
        <View style={styles.dotsContainer}>
          <Dot delay={0} isSpicyMode={isSpicyMode} />
          <Dot delay={150} isSpicyMode={isSpicyMode} />
          <Dot delay={300} isSpicyMode={isSpicyMode} />
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    marginVertical: theme.spacing.xs,
    paddingHorizontal: theme.spacing.md,
    alignItems: 'flex-end',
  },
  bubble: {
    backgroundColor: theme.colors.background.secondary,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    shadowColor: theme.colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  dotsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.xs,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
});
