/**
 * Theme Context - Global Theme State Management
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { themes, defaultThemeId, ThemeConfig } from './themes';

const THEME_STORAGE_KEY = '@luna_theme';

interface ThemeContextType {
  theme: ThemeConfig;
  themeId: string;
  setTheme: (themeId: string) => void;
  isDark: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [themeId, setThemeId] = useState(defaultThemeId);
  
  // Load saved theme on mount
  useEffect(() => {
    loadTheme();
  }, []);
  
  const loadTheme = async () => {
    try {
      const saved = await AsyncStorage.getItem(THEME_STORAGE_KEY);
      if (saved && themes[saved]) {
        setThemeId(saved);
      }
    } catch (error) {
      console.log('Failed to load theme:', error);
    }
  };
  
  const setTheme = async (newThemeId: string) => {
    if (themes[newThemeId]) {
      setThemeId(newThemeId);
      try {
        await AsyncStorage.setItem(THEME_STORAGE_KEY, newThemeId);
      } catch (error) {
        console.log('Failed to save theme:', error);
      }
    }
  };
  
  const theme = themes[themeId] || themes[defaultThemeId];
  
  return (
    <ThemeContext.Provider value={{ 
      theme, 
      themeId, 
      setTheme,
      isDark: true, // All our themes are dark
    }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

// Legacy compatibility: export current theme as 'theme'
export { themes, defaultThemeId };
