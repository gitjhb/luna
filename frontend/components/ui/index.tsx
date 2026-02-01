/**
 * Luna UI Components
 * 
 * 统一的 UI 组件库，确保全 App 风格一致
 * 基于 Luna Design System
 */

import React, { memo } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ViewStyle,
  TextStyle,
  ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, radius, typography, shadows, gradients } from '../../theme/designSystem';

// ============================================================================
// Button Component
// ============================================================================

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'gradient';
export type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: keyof typeof Ionicons.glyphMap;
  iconPosition?: 'left' | 'right';
  loading?: boolean;
  disabled?: boolean;
  fullWidth?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
  gradientColors?: readonly [string, string];
}

export const Button = memo(function Button({
  title,
  onPress,
  variant = 'primary',
  size = 'md',
  icon,
  iconPosition = 'left',
  loading = false,
  disabled = false,
  fullWidth = false,
  style,
  textStyle,
  gradientColors,
}: ButtonProps) {
  const sizeStyles = {
    sm: { paddingVertical: spacing.sm, paddingHorizontal: spacing.md, fontSize: typography.size.sm },
    md: { paddingVertical: spacing.md, paddingHorizontal: spacing.xl, fontSize: typography.size.base },
    lg: { paddingVertical: spacing.lg, paddingHorizontal: spacing['2xl'], fontSize: typography.size.md },
  };
  
  const variantStyles = {
    primary: {
      bg: colors.primary.main,
      text: colors.background.base,
      border: 'transparent',
    },
    secondary: {
      bg: 'transparent',
      text: colors.primary.main,
      border: colors.primary.main,
    },
    ghost: {
      bg: 'rgba(0, 240, 255, 0.1)',
      text: colors.primary.main,
      border: 'transparent',
    },
    danger: {
      bg: colors.error.main,
      text: '#fff',
      border: 'transparent',
    },
    gradient: {
      bg: 'transparent',
      text: '#fff',
      border: 'transparent',
    },
  };
  
  const currentVariant = variantStyles[variant];
  const currentSize = sizeStyles[size];
  const iconSize = size === 'sm' ? 16 : size === 'lg' ? 22 : 18;
  
  const content = (
    <View style={[
      buttonStyles.container,
      {
        paddingVertical: currentSize.paddingVertical,
        paddingHorizontal: currentSize.paddingHorizontal,
        backgroundColor: variant !== 'gradient' ? currentVariant.bg : undefined,
        borderColor: currentVariant.border,
        borderWidth: variant === 'secondary' ? 1 : 0,
        opacity: disabled ? 0.5 : 1,
      },
      fullWidth && { width: '100%' },
    ]}>
      {loading ? (
        <ActivityIndicator color={currentVariant.text} size="small" />
      ) : (
        <View style={buttonStyles.content}>
          {icon && iconPosition === 'left' && (
            <Ionicons name={icon} size={iconSize} color={currentVariant.text} style={{ marginRight: spacing.sm }} />
          )}
          <Text style={[
            buttonStyles.text,
            { color: currentVariant.text, fontSize: currentSize.fontSize },
            textStyle,
          ]}>
            {title}
          </Text>
          {icon && iconPosition === 'right' && (
            <Ionicons name={icon} size={iconSize} color={currentVariant.text} style={{ marginLeft: spacing.sm }} />
          )}
        </View>
      )}
    </View>
  );
  
  if (variant === 'gradient') {
    return (
      <TouchableOpacity onPress={onPress} disabled={disabled || loading} activeOpacity={0.8}>
        <LinearGradient
          colors={gradientColors || gradients.primary}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={[
            buttonStyles.gradient,
            {
              paddingVertical: currentSize.paddingVertical,
              paddingHorizontal: currentSize.paddingHorizontal,
              opacity: disabled ? 0.5 : 1,
            },
            fullWidth && { width: '100%' },
            style,
          ]}
        >
          {content.props.children}
        </LinearGradient>
      </TouchableOpacity>
    );
  }
  
  return (
    <TouchableOpacity onPress={onPress} disabled={disabled || loading} activeOpacity={0.8} style={style}>
      {content}
    </TouchableOpacity>
  );
});

const buttonStyles = StyleSheet.create({
  container: {
    borderRadius: radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  gradient: {
    borderRadius: radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    fontWeight: typography.weight.semibold,
  },
});

// ============================================================================
// Card Component
// ============================================================================

interface CardProps {
  children: React.ReactNode;
  variant?: 'base' | 'highlighted' | 'glass';
  style?: ViewStyle;
  onPress?: () => void;
}

export const Card = memo(function Card({
  children,
  variant = 'base',
  style,
  onPress,
}: CardProps) {
  const variantStyles = {
    base: cardStyles.base,
    highlighted: cardStyles.highlighted,
    glass: cardStyles.glass,
  };
  
  const Wrapper = onPress ? TouchableOpacity : View;
  
  return (
    <Wrapper
      style={[variantStyles[variant], style]}
      onPress={onPress}
      activeOpacity={onPress ? 0.8 : 1}
    >
      {children}
    </Wrapper>
  );
});

const cardStyles = StyleSheet.create({
  base: {
    backgroundColor: colors.background.elevated,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border.default,
    padding: spacing.lg,
  },
  highlighted: {
    backgroundColor: colors.background.elevated,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border.accent,
    padding: spacing.lg,
    shadowColor: colors.primary.main,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.2,
    shadowRadius: 12,
    elevation: 8,
  },
  glass: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.12)',
    padding: spacing.lg,
  },
});

// ============================================================================
// Badge Component
// ============================================================================

interface BadgeProps {
  text: string;
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'error';
  size?: 'sm' | 'md';
  icon?: string;  // emoji
  style?: ViewStyle;
}

export const Badge = memo(function Badge({
  text,
  variant = 'primary',
  size = 'sm',
  icon,
  style,
}: BadgeProps) {
  const variantStyles = {
    primary: { bg: colors.primary.main, text: colors.background.base },
    secondary: { bg: 'rgba(139, 92, 246, 0.2)', text: colors.secondary.light },
    success: { bg: 'rgba(57, 255, 20, 0.2)', text: colors.success.main },
    warning: { bg: 'rgba(252, 238, 10, 0.15)', text: colors.warning.main },
    error: { bg: 'rgba(255, 23, 68, 0.2)', text: colors.error.main },
  };
  
  const current = variantStyles[variant];
  const sizeStyle = size === 'sm' 
    ? { paddingHorizontal: spacing.sm, paddingVertical: 3, fontSize: typography.size.xs }
    : { paddingHorizontal: spacing.md, paddingVertical: spacing.xs, fontSize: typography.size.sm };
  
  return (
    <View style={[
      badgeStyles.container,
      { backgroundColor: current.bg, paddingHorizontal: sizeStyle.paddingHorizontal, paddingVertical: sizeStyle.paddingVertical },
      style,
    ]}>
      {icon && <Text style={badgeStyles.icon}>{icon}</Text>}
      <Text style={[badgeStyles.text, { color: current.text, fontSize: sizeStyle.fontSize }]}>
        {text}
      </Text>
    </View>
  );
});

const badgeStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: radius.full,
    gap: spacing.xs,
  },
  icon: {
    fontSize: 12,
  },
  text: {
    fontWeight: typography.weight.bold,
  },
});

// ============================================================================
// IconButton Component
// ============================================================================

interface IconButtonProps {
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'primary' | 'ghost';
  disabled?: boolean;
  style?: ViewStyle;
}

export const IconButton = memo(function IconButton({
  icon,
  onPress,
  size = 'md',
  variant = 'default',
  disabled = false,
  style,
}: IconButtonProps) {
  const sizeConfig = {
    sm: { container: 36, icon: 18 },
    md: { container: 44, icon: 22 },
    lg: { container: 52, icon: 26 },
  };
  
  const variantConfig = {
    default: { bg: 'rgba(255, 255, 255, 0.08)', color: colors.text.primary },
    primary: { bg: colors.primary.main, color: colors.background.base },
    ghost: { bg: 'transparent', color: colors.text.secondary },
  };
  
  const current = variantConfig[variant];
  const currentSize = sizeConfig[size];
  
  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled}
      activeOpacity={0.7}
      style={[
        iconButtonStyles.container,
        {
          width: currentSize.container,
          height: currentSize.container,
          backgroundColor: current.bg,
          opacity: disabled ? 0.5 : 1,
        },
        style,
      ]}
    >
      <Ionicons name={icon} size={currentSize.icon} color={current.color} />
    </TouchableOpacity>
  );
});

const iconButtonStyles = StyleSheet.create({
  container: {
    borderRadius: radius.md,
    justifyContent: 'center',
    alignItems: 'center',
  },
});

// ============================================================================
// Divider Component
// ============================================================================

interface DividerProps {
  style?: ViewStyle;
  color?: string;
}

export const Divider = memo(function Divider({ style, color }: DividerProps) {
  return (
    <View style={[
      dividerStyles.line,
      { backgroundColor: color || colors.border.default },
      style,
    ]} />
  );
});

const dividerStyles = StyleSheet.create({
  line: {
    height: 1,
    width: '100%',
    marginVertical: spacing.md,
  },
});

// ============================================================================
// SectionHeader Component
// ============================================================================

interface SectionHeaderProps {
  title: string;
  action?: {
    text: string;
    onPress: () => void;
  };
  style?: ViewStyle;
}

export const SectionHeader = memo(function SectionHeader({
  title,
  action,
  style,
}: SectionHeaderProps) {
  return (
    <View style={[sectionStyles.container, style]}>
      <Text style={sectionStyles.title}>{title}</Text>
      {action && (
        <TouchableOpacity onPress={action.onPress}>
          <Text style={sectionStyles.action}>{action.text}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
});

const sectionStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  title: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.bold,
    color: colors.primary.main,
  },
  action: {
    fontSize: typography.size.sm,
    color: colors.text.secondary,
  },
});

// ============================================================================
// ProgressBar Component
// ============================================================================

interface ProgressBarProps {
  progress: number;  // 0-100
  color?: string;
  backgroundColor?: string;
  height?: number;
  style?: ViewStyle;
}

export const ProgressBar = memo(function ProgressBar({
  progress,
  color = colors.secondary.main,
  backgroundColor = 'rgba(139, 92, 246, 0.2)',
  height = 6,
  style,
}: ProgressBarProps) {
  const clampedProgress = Math.max(0, Math.min(100, progress));
  
  return (
    <View style={[progressStyles.container, { height, backgroundColor }, style]}>
      <View style={[progressStyles.fill, { width: `${clampedProgress}%`, backgroundColor: color }]} />
    </View>
  );
});

const progressStyles = StyleSheet.create({
  container: {
    borderRadius: radius.full,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: radius.full,
  },
});

// ============================================================================
// 导出 Design System 常量供直接使用
// ============================================================================

export { colors, spacing, radius, typography, shadows, gradients };
