/**
 * useEmotionTheme - 独立的情绪主题 Hook
 * 
 * 不需要全局 Provider，可以直接在任何组件中使用
 * 根据情绪状态自动计算主题，支持平滑过渡
 * 
 * 使用示例:
 * ```tsx
 * const {
 *   theme,
 *   emotionMode,
 *   backgroundColors,
 *   overlayOpacity,
 *   glitchEnabled,
 *   glowEnabled,
 * } = useEmotionTheme(emotionScore, emotionState, isSpicyMode);
 * ```
 */

import { useState, useEffect, useRef, useMemo } from 'react';
import { Animated, Easing } from 'react-native';
import { ThemeConfig, cyberpunk2077, purpleSeduction } from '../theme/themes';

// ============================================================================
// 情绪主题定义
// ============================================================================

export type EmotionMode = 'neutral' | 'spicy' | 'angry' | 'happy';

/**
 * 愤怒主题 - 冷红色调
 */
const angryTheme: ThemeConfig = {
  id: 'angry',
  name: 'Angry',
  nameCn: '暴怒',
  
  colors: {
    background: {
      primary: "#0a0508",
      secondary: "#1a0a0f",
      tertiary: "#250a12",
      gradient: ["#0a0508", "#1a0a0f", "#0a0508"] as const,
    },
    primary: {
      main: "#FF1744",
      light: "#FF5252",
      dark: "#D50000",
      gradient: ["#FF1744", "#B71C1C"] as const,
    },
    accent: {
      pink: "#FF1744",
      purple: "#880E4F",
      cyan: "#37474F",
      yellow: "#FF6F00",
      gradient: ["#FF1744", "#880E4F"] as const,
    },
    text: {
      primary: "#FFFFFF",
      secondary: "rgba(255, 23, 68, 0.8)",
      tertiary: "rgba(255, 255, 255, 0.3)",
      inverse: "#0a0508",
    },
    success: "#4CAF50",
    warning: "#FF6F00",
    error: "#FF1744",
    border: "rgba(255, 23, 68, 0.3)",
    overlay: "rgba(10, 5, 8, 0.95)",
    glow: "#FF1744",
    neon: "#FF5252",
  },
  typography: {
    fontSize: { xs: 11, sm: 13, base: 15, lg: 17, xl: 20, '2xl': 24, '3xl': 30 },
    lineHeight: { tight: 1.2, normal: 1.5, relaxed: 1.7 },
  },
  spacing: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, '2xl': 48 },
  borderRadius: { sm: 2, md: 4, lg: 8, xl: 12, '2xl': 16, full: 9999 },
  effects: { glowIntensity: 1.0, borderGlow: true, scanlines: true },
};

/**
 * 开心主题 - 暖光粉色
 */
const happyTheme: ThemeConfig = {
  id: 'happy',
  name: 'Happy',
  nameCn: '开心',
  
  colors: {
    background: {
      primary: "#1a0f1f",
      secondary: "#2d1832",
      tertiary: "#3d2045",
      gradient: ["#1a0f1f", "#2d1832", "#1a0f1f"] as const,
    },
    primary: {
      main: "#FF69B4",
      light: "#FFB6C1",
      dark: "#FF1493",
      gradient: ["#FF69B4", "#FFD700"] as const,
    },
    accent: {
      pink: "#FF69B4",
      purple: "#DA70D6",
      cyan: "#87CEEB",
      yellow: "#FFD700",
      gradient: ["#FFD700", "#FF69B4"] as const,
    },
    text: {
      primary: "#FFFFFF",
      secondary: "rgba(255, 182, 193, 0.9)",
      tertiary: "rgba(255, 255, 255, 0.5)",
      inverse: "#1a0f1f",
    },
    success: "#98FB98",
    warning: "#FFD700",
    error: "#FF6B6B",
    border: "rgba(255, 105, 180, 0.3)",
    overlay: "rgba(26, 15, 31, 0.85)",
    glow: "#FF69B4",
    neon: "#FFD700",
  },
  typography: {
    fontSize: { xs: 11, sm: 13, base: 15, lg: 17, xl: 20, '2xl': 24, '3xl': 30 },
    lineHeight: { tight: 1.2, normal: 1.5, relaxed: 1.7 },
  },
  spacing: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, '2xl': 48 },
  borderRadius: { sm: 6, md: 10, lg: 14, xl: 18, '2xl': 24, full: 9999 },
  effects: { glowIntensity: 0.6, borderGlow: true, scanlines: false },
};

// ============================================================================
// 工具函数
// ============================================================================

function getEmotionMode(emotionScore: number, isSpicyMode: boolean): EmotionMode {
  if (isSpicyMode) return 'spicy';
  if (emotionScore <= -60) return 'angry';
  if (emotionScore >= 80) return 'happy';
  return 'neutral';
}

function getThemeForMode(mode: EmotionMode): ThemeConfig {
  switch (mode) {
    case 'spicy': return purpleSeduction;
    case 'angry': return angryTheme;
    case 'happy': return happyTheme;
    default: return cyberpunk2077;
  }
}

// ============================================================================
// Hook
// ============================================================================

interface UseEmotionThemeReturn {
  // 当前主题
  theme: ThemeConfig;
  
  // 情绪模式
  emotionMode: EmotionMode;
  
  // 是否正在过渡
  isTransitioning: boolean;
  
  // 过渡动画进度 (Animated.Value 0-1)
  transitionProgress: Animated.Value;
  
  // 便捷颜色数组
  backgroundColors: readonly [string, string, string];
  primaryGradient: readonly [string, string];
  accentGradient: readonly [string, string];
  
  // 背景叠加层透明度（基于情绪调整）
  overlayColors: readonly [string, string, string];
  
  // 特效开关
  glitchEnabled: boolean;
  glowEnabled: boolean;
  
  // 情绪指示
  emotionEmoji: string;
  emotionHint: string;
}

export function useEmotionTheme(
  emotionScore: number,
  emotionState: string,
  isSpicyMode: boolean,
  transitionDuration: number = 600
): UseEmotionThemeReturn {
  // 计算目标模式
  const targetMode = useMemo(
    () => getEmotionMode(emotionScore, isSpicyMode),
    [emotionScore, isSpicyMode]
  );
  
  // 当前激活的模式
  const [currentMode, setCurrentMode] = useState<EmotionMode>(targetMode);
  const [isTransitioning, setIsTransitioning] = useState(false);
  
  // 动画值
  const transitionProgress = useRef(new Animated.Value(1)).current;
  
  // 主题引用
  const themeRef = useRef<ThemeConfig>(getThemeForMode(targetMode));

  // 当目标模式变化时执行过渡
  useEffect(() => {
    if (targetMode !== currentMode) {
      // 更新主题引用
      themeRef.current = getThemeForMode(targetMode);
      
      // 重置并执行动画
      transitionProgress.setValue(0);
      setIsTransitioning(true);
      
      Animated.timing(transitionProgress, {
        toValue: 1,
        duration: transitionDuration,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: false,
      }).start(() => {
        setCurrentMode(targetMode);
        setIsTransitioning(false);
      });
    }
  }, [targetMode, currentMode, transitionDuration]);

  // 当前主题
  const theme = themeRef.current;

  // 便捷颜色
  const backgroundColors = theme.colors.background.gradient;
  const primaryGradient = theme.colors.primary.gradient;
  const accentGradient = theme.colors.accent.gradient;

  // 叠加层颜色（根据情绪调整透明度）
  const overlayColors = useMemo((): readonly [string, string, string] => {
    const baseOpacity = currentMode === 'angry' ? 0.85 : 
                        currentMode === 'happy' ? 0.7 : 
                        currentMode === 'spicy' ? 0.75 : 0.8;
    const color = theme.colors.background.primary;
    return [
      `rgba(26,16,37,0.3)`,
      `rgba(26,16,37,${baseOpacity * 0.8})`,
      `rgba(26,16,37,${baseOpacity})`,
    ] as const;
  }, [currentMode, theme]);

  // 特效
  const glitchEnabled = currentMode === 'angry';
  const glowEnabled = currentMode === 'happy' || currentMode === 'spicy';

  // 情绪指示
  const emotionEmoji = useMemo(() => {
    switch (currentMode) {
      case 'angry': return '😠';
      case 'happy': return '😊';
      case 'spicy': return '🔥';
      default: return '😌';
    }
  }, [currentMode]);

  const emotionHint = useMemo(() => {
    switch (currentMode) {
      case 'angry': return '她有点生气了...';
      case 'happy': return '她很开心！';
      case 'spicy': return 'Spicy Mode 已开启';
      default: return '';
    }
  }, [currentMode]);

  return {
    theme,
    emotionMode: currentMode,
    isTransitioning,
    transitionProgress,
    backgroundColors,
    primaryGradient,
    accentGradient,
    overlayColors,
    glitchEnabled,
    glowEnabled,
    emotionEmoji,
    emotionHint,
  };
}

// ============================================================================
// 导出主题常量（供外部使用）
// ============================================================================

export { angryTheme, happyTheme };
export { cyberpunk2077 as neutralTheme, purpleSeduction as spicyTheme };
