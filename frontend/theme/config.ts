/**
 * Theme Configuration - Purple Pink Intimate Style
 */

export interface ThemeConfig {
  appName: string;
  appTagline: string;
  
  colors: {
    background: {
      primary: string;
      secondary: string;
      tertiary: string;
      gradient: readonly [string, string, string];
    };
    
    primary: {
      main: string;
      light: string;
      dark: string;
      gradient: readonly [string, string];
    };
    
    accent: {
      pink: string;
      purple: string;
      gradient: readonly [string, string];
    };
    
    text: {
      primary: string;
      secondary: string;
      tertiary: string;
      inverse: string;
    };
    
    success: string;
    warning: string;
    error: string;
    
    border: string;
    overlay: string;
  };
  
  typography: {
    fontSize: {
      xs: number;
      sm: number;
      base: number;
      lg: number;
      xl: number;
      '2xl': number;
      '3xl': number;
    };
    
    lineHeight: {
      tight: number;
      normal: number;
      relaxed: number;
    };
  };
  
  spacing: {
    xs: number;
    sm: number;
    md: number;
    lg: number;
    xl: number;
    '2xl': number;
  };
  
  borderRadius: {
    sm: number;
    md: number;
    lg: number;
    xl: number;
    '2xl': number;
    full: number;
  };
}

export const theme: ThemeConfig = {
  appName: "Luna",
  appTagline: "Your AI Companion",
  
  colors: {
    background: {
      primary: "#1a1025",
      secondary: "#251832",
      tertiary: "#2d1f3d",
      gradient: ["#1a1025", "#2d1f3d", "#1a1025"] as const,
    },
    
    primary: {
      main: "#EC4899",
      light: "#F472B6",
      dark: "#DB2777",
      gradient: ["#EC4899", "#8B5CF6"] as const,
    },
    
    accent: {
      pink: "#EC4899",
      purple: "#8B5CF6",
      gradient: ["#EC4899", "#8B5CF6"] as const,
    },
    
    text: {
      primary: "#FFFFFF",
      secondary: "rgba(255, 255, 255, 0.7)",
      tertiary: "rgba(255, 255, 255, 0.4)",
      inverse: "#1a1025",
    },
    
    success: "#22C55E",
    warning: "#F59E0B",
    error: "#EF4444",
    
    border: "rgba(255, 255, 255, 0.1)",
    overlay: "rgba(26, 16, 37, 0.8)",
  },
  
  typography: {
    fontSize: {
      xs: 11,
      sm: 13,
      base: 15,
      lg: 17,
      xl: 20,
      '2xl': 24,
      '3xl': 30,
    },
    
    lineHeight: {
      tight: 1.2,
      normal: 1.5,
      relaxed: 1.7,
    },
  },
  
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    '2xl': 48,
  },
  
  borderRadius: {
    sm: 6,
    md: 10,
    lg: 14,
    xl: 18,
    '2xl': 24,
    full: 9999,
  },
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
