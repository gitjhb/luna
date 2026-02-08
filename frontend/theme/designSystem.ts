/**
 * Luna Design System
 * 
 * 统一的设计规范，确保所有组件风格一致
 * 
 * 设计理念：赛博朋克 × 亲密感
 * - 深色背景 + 霓虹色高光
 * - 硬朗的边角 + 柔和的发光
 * - 科技感 + 温暖的交互
 */

import { Platform, ViewStyle, TextStyle } from 'react-native';

// ============================================================================
// 颜色系统
// ============================================================================

export const colors = {
  // 背景层级
  background: {
    base: '#0a0a0f',        // 最深层背景
    elevated: '#0d1117',    // 卡片/浮层背景
    surface: '#161b22',     // 表面元素
    overlay: 'rgba(10, 10, 15, 0.85)', // 遮罩层
  },
  
  // 主色调 - 霓虹青
  primary: {
    main: '#00F0FF',
    light: '#5CFFFF',
    dark: '#00B8C4',
    glow: 'rgba(0, 240, 255, 0.4)',
  },
  
  // 强调色 - 霓虹品红
  accent: {
    main: '#FF2A6D',
    light: '#FF5A8A',
    dark: '#D4205A',
    glow: 'rgba(255, 42, 109, 0.4)',
  },
  
  // 次要强调 - 霓虹紫
  secondary: {
    main: '#00D4FF',
    light: '#A78BFA',
    dark: '#7C3AED',
    glow: 'rgba(0, 212, 255, 0.4)',
  },
  
  // 警示色 - 赛博黄
  warning: {
    main: '#FCEE0A',
    dark: '#E5D800',
    glow: 'rgba(252, 238, 10, 0.4)',
  },
  
  // 成功色 - 霓虹绿
  success: {
    main: '#39FF14',
    dark: '#32E512',
    glow: 'rgba(57, 255, 20, 0.4)',
  },
  
  // 错误色
  error: {
    main: '#FF1744',
    dark: '#D50000',
    glow: 'rgba(255, 23, 68, 0.4)',
  },
  
  // 文字
  text: {
    primary: '#FFFFFF',
    secondary: 'rgba(255, 255, 255, 0.7)',
    tertiary: 'rgba(255, 255, 255, 0.4)',
    accent: '#00F0FF',
  },
  
  // 边框
  border: {
    default: 'rgba(255, 255, 255, 0.1)',
    accent: 'rgba(0, 240, 255, 0.3)',
    glow: 'rgba(0, 240, 255, 0.5)',
  },
} as const;

// ============================================================================
// 间距系统
// ============================================================================

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  '2xl': 24,
  '3xl': 32,
  '4xl': 48,
} as const;

// ============================================================================
// 圆角系统 (赛博朋克风格 - 更硬朗)
// ============================================================================

export const radius = {
  none: 0,
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  '2xl': 20,
  full: 9999,
} as const;

// ============================================================================
// 字体系统
// ============================================================================

export const typography = {
  // 尺寸
  size: {
    xs: 11,
    sm: 13,
    base: 15,
    md: 16,
    lg: 18,
    xl: 20,
    '2xl': 24,
    '3xl': 30,
    '4xl': 36,
  },
  
  // 行高
  lineHeight: {
    tight: 1.2,
    normal: 1.4,
    relaxed: 1.6,
  },
  
  // 字重
  weight: {
    normal: '400' as const,
    medium: '500' as const,
    semibold: '600' as const,
    bold: '700' as const,
    extrabold: '800' as const,
  },
} as const;

// ============================================================================
// 阴影系统
// ============================================================================

export const shadows = {
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 3,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  lg: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.35,
    shadowRadius: 16,
    elevation: 12,
  },
  // 发光阴影
  glow: (color: string, intensity: number = 0.5) => ({
    shadowColor: color,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: intensity,
    shadowRadius: 12,
    elevation: 8,
  }),
} as const;

// ============================================================================
// 预设样式 - 按钮
// ============================================================================

export const buttonStyles = {
  // 主按钮
  primary: {
    container: {
      backgroundColor: colors.primary.main,
      borderRadius: radius.md,
      paddingVertical: spacing.md,
      paddingHorizontal: spacing.xl,
    } as ViewStyle,
    text: {
      color: colors.background.base,
      fontSize: typography.size.base,
      fontWeight: typography.weight.semibold,
    } as TextStyle,
  },
  
  // 次要按钮 (描边)
  secondary: {
    container: {
      backgroundColor: 'transparent',
      borderRadius: radius.md,
      borderWidth: 1,
      borderColor: colors.primary.main,
      paddingVertical: spacing.md,
      paddingHorizontal: spacing.xl,
    } as ViewStyle,
    text: {
      color: colors.primary.main,
      fontSize: typography.size.base,
      fontWeight: typography.weight.semibold,
    } as TextStyle,
  },
  
  // 幽灵按钮 (透明)
  ghost: {
    container: {
      backgroundColor: 'rgba(0, 240, 255, 0.1)',
      borderRadius: radius.md,
      paddingVertical: spacing.md,
      paddingHorizontal: spacing.xl,
    } as ViewStyle,
    text: {
      color: colors.primary.main,
      fontSize: typography.size.base,
      fontWeight: typography.weight.medium,
    } as TextStyle,
  },
  
  // 危险按钮
  danger: {
    container: {
      backgroundColor: colors.error.main,
      borderRadius: radius.md,
      paddingVertical: spacing.md,
      paddingHorizontal: spacing.xl,
    } as ViewStyle,
    text: {
      color: '#fff',
      fontSize: typography.size.base,
      fontWeight: typography.weight.semibold,
    } as TextStyle,
  },
} as const;

// ============================================================================
// 预设样式 - 卡片
// ============================================================================

export const cardStyles = {
  // 基础卡片
  base: {
    backgroundColor: colors.background.elevated,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border.default,
    padding: spacing.lg,
  } as ViewStyle,
  
  // 高亮卡片 (带发光边框)
  highlighted: {
    backgroundColor: colors.background.elevated,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border.accent,
    padding: spacing.lg,
    ...shadows.glow(colors.primary.main, 0.2),
  } as ViewStyle,
  
  // 玻璃态卡片
  glass: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.12)',
    padding: spacing.lg,
  } as ViewStyle,
} as const;

// ============================================================================
// 预设样式 - 输入框
// ============================================================================

export const inputStyles = {
  // 基础输入框
  base: {
    container: {
      backgroundColor: 'rgba(255, 255, 255, 0.08)',
      borderRadius: radius.lg,
      borderWidth: 1,
      borderColor: colors.border.default,
      paddingHorizontal: spacing.lg,
      paddingVertical: Platform.OS === 'ios' ? spacing.md : spacing.sm,
    } as ViewStyle,
    text: {
      color: colors.text.primary,
      fontSize: typography.size.base,
    } as TextStyle,
    placeholder: colors.text.tertiary,
  },
  
  // 聚焦状态
  focused: {
    borderColor: colors.primary.main,
    ...shadows.glow(colors.primary.main, 0.15),
  } as ViewStyle,
} as const;

// ============================================================================
// 预设样式 - 消息气泡
// ============================================================================

export const bubbleStyles = {
  // 用户消息
  user: {
    backgroundColor: 'rgba(0, 240, 255, 0.15)',
    borderRadius: radius.xl,
    borderBottomRightRadius: radius.sm,
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.25)',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  } as ViewStyle,
  
  // AI消息
  ai: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: radius.xl,
    borderBottomLeftRadius: radius.sm,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  } as ViewStyle,
  
  // 文字样式
  text: {
    color: colors.text.primary,
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.relaxed,
  } as TextStyle,
} as const;

// ============================================================================
// 预设样式 - 徽章/标签
// ============================================================================

export const badgeStyles = {
  // 主色徽章
  primary: {
    container: {
      backgroundColor: colors.primary.main,
      borderRadius: radius.full,
      paddingHorizontal: spacing.sm,
      paddingVertical: spacing.xs,
    } as ViewStyle,
    text: {
      color: colors.background.base,
      fontSize: typography.size.xs,
      fontWeight: typography.weight.bold,
    } as TextStyle,
  },
  
  // 次要徽章
  secondary: {
    container: {
      backgroundColor: 'rgba(0, 212, 255, 0.2)',
      borderRadius: radius.full,
      paddingHorizontal: spacing.sm,
      paddingVertical: spacing.xs,
    } as ViewStyle,
    text: {
      color: colors.secondary.light,
      fontSize: typography.size.xs,
      fontWeight: typography.weight.semibold,
    } as TextStyle,
  },
  
  // 金币徽章
  coin: {
    container: {
      backgroundColor: 'rgba(252, 238, 10, 0.15)',
      borderRadius: radius.full,
      paddingHorizontal: spacing.md,
      paddingVertical: spacing.xs,
      flexDirection: 'row',
      alignItems: 'center',
      gap: spacing.xs,
    } as ViewStyle,
    text: {
      color: colors.warning.main,
      fontSize: typography.size.sm,
      fontWeight: typography.weight.bold,
    } as TextStyle,
  },
  
  // 等级徽章
  level: {
    container: {
      backgroundColor: 'rgba(0, 212, 255, 0.2)',
      borderRadius: radius.md,
      paddingHorizontal: spacing.md,
      paddingVertical: spacing.xs,
      borderWidth: 1,
      borderColor: 'rgba(0, 212, 255, 0.3)',
    } as ViewStyle,
    text: {
      color: colors.secondary.light,
      fontSize: typography.size.sm,
      fontWeight: typography.weight.bold,
    } as TextStyle,
  },
} as const;

// ============================================================================
// 预设渐变色
// ============================================================================

export const gradients = {
  // 主渐变 (青 → 品红)
  primary: ['#00F0FF', '#FF2A6D'] as const,
  
  // 强调渐变 (品红 → 紫)
  accent: ['#FF2A6D', '#00D4FF'] as const,
  
  // 紫色渐变 (Spicy Mode)
  purple: ['#00D4FF', '#00D4FF'] as const,
  
  // 金色渐变
  gold: ['#FFD700', '#FFA500'] as const,
  
  // 背景渐变
  background: ['#0a0a0f', '#0d1a1f', '#0a0a0f'] as const,
  
  // 叠加层渐变
  overlay: ['rgba(10,10,15,0.2)', 'rgba(10,10,15,0.7)', 'rgba(10,10,15,0.95)'] as const,
} as const;

// ============================================================================
// 动画配置
// ============================================================================

export const animation = {
  // 弹性动画
  spring: {
    damping: 15,
    stiffness: 150,
  },
  
  // 时长
  duration: {
    fast: 150,
    normal: 300,
    slow: 500,
  },
} as const;

// ============================================================================
// 图标尺寸
// ============================================================================

export const iconSize = {
  xs: 14,
  sm: 18,
  md: 22,
  lg: 26,
  xl: 32,
} as const;
