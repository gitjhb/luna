/**
 * Theme Configuration
 * 
 * This file provides backward compatibility.
 * New code should use useTheme() from ThemeContext.
 * 
 * For dynamic emotion-based themes, use useDynamicTheme() from DynamicThemeContext.
 */

// Re-export everything from themes.ts
export type { ThemeConfig } from './themes';
export { purpleSeduction, cyberpunk2077, themes, themeList, defaultThemeId } from './themes';

// Re-export theme context (static)
export { ThemeProvider, useTheme } from './ThemeContext';

// Re-export dynamic theme context (emotion-based)
export { DynamicThemeProvider, useDynamicTheme, AnimatedThemeBackground } from './DynamicThemeContext';
export { angryTheme, happyTheme, getEmotionMode, getThemeForEmotion, interpolateColor } from './dynamicTheme';
export type { EmotionMode, EmotionState } from './dynamicTheme';

// Legacy: export default theme for backward compatibility
import { purpleSeduction } from './themes';
export const theme = {
  ...purpleSeduction,
  appName: "Luna",
  appTagline: "Your AI Companion",
};

export const getShadow = (level: 'sm' | 'md' | 'lg' | 'xl') => ({
  shadowColor: '#000',
  shadowOffset: {
    width: 0,
    height: level === 'sm' ? 2 : level === 'md' ? 4 : level === 'lg' ? 8 : 16,
  },
  shadowOpacity: level === 'sm' ? 0.2 : level === 'md' ? 0.25 : level === 'lg' ? 0.3 : 0.35,
  shadowRadius: level === 'sm' ? 4 : level === 'md' ? 8 : level === 'lg' ? 16 : 24,
  elevation: level === 'sm' ? 3 : level === 'md' ? 6 : level === 'lg' ? 12 : 20,
});

export type Theme = typeof theme;
