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
    // MVP: Force luna-2077 theme, ignore saved preferences
    // This ensures all users see the new Luna 2077 design
    setThemeId('luna-2077');
    try {
      // Clear any old saved theme
      await AsyncStorage.removeItem(THEME_STORAGE_KEY);
    } catch (error) {
      console.log('Failed to clear old theme:', error);
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
