/**
 * Dynamic Theme System
 * 
 * 根据AI情绪状态动态调整UI主题
 * 
 * 情绪状态映射:
 * - 默认/平静 (neutral): 赛博朋克蓝
 * - Spicy Mode: 紫色诱惑渐变
 * - 暴怒 (angry, emotionScore < -60): 冷红/故障风
 * - 开心 (happy, emotionScore > 80): 暖光/粉色光晕
 */

import { ThemeConfig, cyberpunk2077, purpleSeduction } from './themes';

// ============================================================================
// 情绪主题变体
// ============================================================================

/**
 * 愤怒主题 - 冷红色调 + 故障风效果
 */
export const angryTheme: ThemeConfig = {
  id: 'angry',
  name: 'Angry',
  nameCn: '暴怒',
  
  colors: {
    background: {
      primary: "#0a0508",          // 深红黑
      secondary: "#1a0a0f",        // 暗红
      tertiary: "#250a12",         // 血红黑
      gradient: ["#0a0508", "#1a0a0f", "#0a0508"] as const,
    },
    
    primary: {
      main: "#FF1744",             // 愤怒红
      light: "#FF5252",
      dark: "#D50000",
      gradient: ["#FF1744", "#B71C1C"] as const,
    },
    
    accent: {
      pink: "#FF1744",
      purple: "#880E4F",
      cyan: "#37474F",             // 冷灰蓝
      yellow: "#FF6F00",           // 暗橙
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
  
  effects: {
    glowIntensity: 1.0,
    borderGlow: true,
    scanlines: true,
  },
};

/**
 * 开心主题 - 暖光 + 粉色光晕
 */
export const happyTheme: ThemeConfig = {
  id: 'happy',
  name: 'Happy',
  nameCn: '开心',
  
  colors: {
    background: {
      primary: "#1a0f1f",          // 温暖紫黑
      secondary: "#2d1832",        // 暖粉紫
      tertiary: "#3d2045",         // 浅暖紫
      gradient: ["#1a0f1f", "#2d1832", "#1a0f1f"] as const,
    },
    
    primary: {
      main: "#FF69B4",             // 粉色
      light: "#FFB6C1",            // 浅粉
      dark: "#FF1493",             // 深粉
      gradient: ["#FF69B4", "#FFD700"] as const,  // 粉到金
    },
    
    accent: {
      pink: "#FF69B4",
      purple: "#DA70D6",           // 兰花紫
      cyan: "#87CEEB",             // 天蓝
      yellow: "#FFD700",           // 金色
      gradient: ["#FFD700", "#FF69B4"] as const,
    },
    
    text: {
      primary: "#FFFFFF",
      secondary: "rgba(255, 182, 193, 0.9)",
      tertiary: "rgba(255, 255, 255, 0.5)",
      inverse: "#1a0f1f",
    },
    
    success: "#98FB98",            // 淡绿
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
  
  effects: {
    glowIntensity: 0.6,
    borderGlow: true,
    scanlines: false,
  },
};

// ============================================================================
// 情绪状态类型
// ============================================================================

export type EmotionMode = 'neutral' | 'spicy' | 'angry' | 'happy';

export interface EmotionState {
  mode: EmotionMode;
  score: number;           // -100 to 100
  emotionalState: string;  // 原始情绪状态字符串
  isSpicyMode: boolean;
}

// ============================================================================
// 情绪 -> 主题映射
// ============================================================================

/**
 * 根据情绪状态计算应该使用的主题模式
 */
export function getEmotionMode(emotionScore: number, emotionalState: string, isSpicyMode: boolean): EmotionMode {
  // Spicy mode 优先级最高
  if (isSpicyMode) {
    return 'spicy';
  }
  
  // 极端情绪判断
  if (emotionScore <= -60) {
    return 'angry';
  }
  
  if (emotionScore >= 80) {
    return 'happy';
  }
  
  // 默认平静状态
  return 'neutral';
}

/**
 * 根据情绪模式获取主题配置
 */
export function getThemeForEmotion(mode: EmotionMode): ThemeConfig {
  switch (mode) {
    case 'spicy':
      return purpleSeduction;
    case 'angry':
      return angryTheme;
    case 'happy':
      return happyTheme;
    case 'neutral':
    default:
      return cyberpunk2077;
  }
}

// ============================================================================
// 颜色插值工具
// ============================================================================

/**
 * 解析hex颜色为RGB
 */
function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : null;
}

/**
 * RGB转hex
 */
function rgbToHex(r: number, g: number, b: number): string {
  return '#' + [r, g, b].map(x => {
    const hex = Math.round(Math.max(0, Math.min(255, x))).toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  }).join('');
}

/**
 * 在两个颜色之间插值
 * @param color1 起始颜色 (hex)
 * @param color2 结束颜色 (hex)
 * @param t 插值因子 (0-1)
 */
export function interpolateColor(color1: string, color2: string, t: number): string {
  const rgb1 = hexToRgb(color1);
  const rgb2 = hexToRgb(color2);
  
  if (!rgb1 || !rgb2) {
    return color1;
  }
  
  const r = rgb1.r + (rgb2.r - rgb1.r) * t;
  const g = rgb1.g + (rgb2.g - rgb1.g) * t;
  const b = rgb1.b + (rgb2.b - rgb1.b) * t;
  
  return rgbToHex(r, g, b);
}

/**
 * 在两个主题之间插值（用于平滑过渡）
 */
export function interpolateTheme(
  theme1: ThemeConfig,
  theme2: ThemeConfig,
  t: number
): Partial<ThemeConfig['colors']> {
  return {
    background: {
      primary: interpolateColor(theme1.colors.background.primary, theme2.colors.background.primary, t),
      secondary: interpolateColor(theme1.colors.background.secondary, theme2.colors.background.secondary, t),
      tertiary: interpolateColor(theme1.colors.background.tertiary, theme2.colors.background.tertiary, t),
      gradient: [
        interpolateColor(theme1.colors.background.gradient[0], theme2.colors.background.gradient[0], t),
        interpolateColor(theme1.colors.background.gradient[1], theme2.colors.background.gradient[1], t),
        interpolateColor(theme1.colors.background.gradient[2], theme2.colors.background.gradient[2], t),
      ] as const,
    },
    primary: {
      main: interpolateColor(theme1.colors.primary.main, theme2.colors.primary.main, t),
      light: interpolateColor(theme1.colors.primary.light, theme2.colors.primary.light, t),
      dark: interpolateColor(theme1.colors.primary.dark, theme2.colors.primary.dark, t),
      gradient: [
        interpolateColor(theme1.colors.primary.gradient[0], theme2.colors.primary.gradient[0], t),
        interpolateColor(theme1.colors.primary.gradient[1], theme2.colors.primary.gradient[1], t),
      ] as const,
    },
    accent: {
      pink: interpolateColor(theme1.colors.accent.pink, theme2.colors.accent.pink, t),
      purple: interpolateColor(theme1.colors.accent.purple, theme2.colors.accent.purple, t),
      gradient: [
        interpolateColor(theme1.colors.accent.gradient[0], theme2.colors.accent.gradient[0], t),
        interpolateColor(theme1.colors.accent.gradient[1], theme2.colors.accent.gradient[1], t),
      ] as const,
    },
    border: interpolateColor(
      theme1.colors.border.replace(/rgba?\([^)]+\)/, '#333'),
      theme2.colors.border.replace(/rgba?\([^)]+\)/, '#333'),
      t
    ),
  };
}
