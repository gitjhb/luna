/**
 * useChatTheme - 聊天页面动态主题 Hook
 * 
 * 自动根据 emotionScore + isSpicyMode 计算并切换主题
 * 
 * 使用示例:
 * ```tsx
 * const { theme, emotionMode, backgroundColors, primaryGradient } = useChatTheme({
 *   emotionScore,
 *   emotionState,
 *   isSpicyMode,
 * });
 * 
 * // 在 LinearGradient 中使用
 * <LinearGradient colors={backgroundColors} ... />
 * ```
 */

import { useEffect, useMemo } from 'react';
import { useDynamicTheme } from '../theme/DynamicThemeContext';
import { ThemeConfig } from '../theme/themes';
import { EmotionMode } from '../theme/dynamicTheme';

interface UseChatThemeOptions {
  emotionScore: number;
  emotionState: string;
  isSpicyMode: boolean;
}

interface UseChatThemeReturn {
  // 当前主题配置
  theme: ThemeConfig;
  
  // 当前情绪模式
  emotionMode: EmotionMode;
  
  // 是否正在过渡
  isTransitioning: boolean;
  
  // 便捷的颜色数组（可直接用于 LinearGradient）
  backgroundColors: [string, string, string];
  primaryGradient: [string, string];
  accentGradient: [string, string];
  
  // 特效开关
  glitchEnabled: boolean;
  glowEnabled: boolean;
  
  // 情绪提示文字
  emotionHint: string;
}

export function useChatTheme({
  emotionScore,
  emotionState,
  isSpicyMode,
}: UseChatThemeOptions): UseChatThemeReturn {
  const {
    theme,
    emotionMode,
    isTransitioning,
    setEmotionState,
    glitchEnabled,
    glowEnabled,
  } = useDynamicTheme();

  // 当情绪状态变化时更新主题
  useEffect(() => {
    setEmotionState(emotionScore, emotionState, isSpicyMode);
  }, [emotionScore, emotionState, isSpicyMode, setEmotionState]);

  // 便捷的颜色数组
  const backgroundColors = useMemo(
    () => [...theme.colors.background.gradient] as [string, string, string],
    [theme]
  );

  const primaryGradient = useMemo(
    () => [...theme.colors.primary.gradient] as [string, string],
    [theme]
  );

  const accentGradient = useMemo(
    () => [...theme.colors.accent.gradient] as [string, string],
    [theme]
  );

  // 情绪提示文字
  const emotionHint = useMemo(() => {
    switch (emotionMode) {
      case 'angry':
        return '💢 她有点生气了...';
      case 'happy':
        return '💕 她很开心！';
      case 'spicy':
        return '🔥 Spicy Mode';
      case 'neutral':
      default:
        return '';
    }
  }, [emotionMode]);

  return {
    theme,
    emotionMode,
    isTransitioning,
    backgroundColors,
    primaryGradient,
    accentGradient,
    glitchEnabled,
    glowEnabled,
    emotionHint,
  };
}

/**
 * 获取情绪对应的表情符号
 */
export function getEmotionEmoji(emotionMode: EmotionMode): string {
  switch (emotionMode) {
    case 'angry':
      return '😠';
    case 'happy':
      return '😊';
    case 'spicy':
      return '🔥';
    case 'neutral':
    default:
      return '😌';
  }
}

/**
 * 获取情绪对应的背景叠加层透明度
 * 用于在背景图上添加主题色调
 */
export function getEmotionOverlayOpacity(emotionMode: EmotionMode): number {
  switch (emotionMode) {
    case 'angry':
      return 0.4;  // 更强的红色覆盖
    case 'happy':
      return 0.25; // 轻微的粉色光晕
    case 'spicy':
      return 0.35; // 紫色诱惑
    case 'neutral':
    default:
      return 0.3;  // 默认赛博蓝
  }
}
