/**
 * GlassCard - Luna 2077 风格玻璃拟态卡片
 * 
 * 特点：
 * - 半透明黑色背景
 * - 1px 发光边框 (HUD 风格)
 * - 可选的背景模糊
 */

import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { BlurView } from 'expo-blur';
import { theme } from '../theme/config';

interface GlassCardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  glowColor?: string;
  intensity?: number;  // blur intensity
  noBorder?: boolean;
}

export function GlassCard({ 
  children, 
  style, 
  glowColor = theme.colors.primary.main,
  intensity = 20,
  noBorder = false,
}: GlassCardProps) {
  return (
    <View style={[
      styles.container, 
      !noBorder && { 
        borderColor: `${glowColor}30`,
        shadowColor: glowColor,
      },
      style
    ]}>
      <View style={styles.innerContent}>
        {children}
      </View>
    </View>
  );
}

// Simpler version without blur for better performance
export function GlassCardSimple({ 
  children, 
  style, 
  glowColor = theme.colors.primary.main,
  noBorder = false,
}: Omit<GlassCardProps, 'intensity'>) {
  return (
    <View style={[
      styles.simpleContainer, 
      !noBorder && { 
        borderColor: `${glowColor}25`,
        shadowColor: glowColor,
      },
      style
    ]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.2)',
    backgroundColor: 'rgba(10, 15, 20, 0.8)',
    overflow: 'hidden',
    // Glow effect
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  innerContent: {
    // Content wrapper
  },
  simpleContainer: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.15)',
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    // Subtle glow
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.2,
    shadowRadius: 6,
    elevation: 3,
  },
});

export default GlassCard;
