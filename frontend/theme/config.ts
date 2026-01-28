/**
 * White-Label Theme Configuration
 * 
 * This is the SINGLE SOURCE OF TRUTH for all visual branding.
 * Change colors, fonts, and assets here to completely reskin the app.
 * 
 * Design Philosophy: "Dark Luxury" - Seductive, not flashy
 * Target Audience: Men 40+ (readable fonts, intuitive UI)
 */

export interface ThemeConfig {
  // Brand Identity
  appName: string;
  appTagline: string;
  
  // Color Palette
  colors: {
    // Background colors
    background: {
      primary: string;      // Main app background
      secondary: string;    // Card backgrounds
      tertiary: string;     // Input fields, subtle elements
      gradient: string[];   // Gradient overlay for premium feel
    };
    
    // Primary action colors (buttons, CTAs)
    primary: {
      main: string;         // Primary button color
      light: string;        // Hover/pressed state
      dark: string;         // Disabled state
      gradient: string[];   // Gradient for premium buttons
    };
    
    // Spicy mode colors (premium feature)
    spicy: {
      main: string;         // Hot pink/red for spicy mode
      light: string;        // Lighter variant
      gradient: string[];   // Seductive gradient
      glow: string;         // Glow effect color
    };
    
    // Text colors
    text: {
      primary: string;      // Main text (high contrast)
      secondary: string;    // Subtle text
      tertiary: string;     // Disabled/placeholder text
      inverse: string;      // Text on colored backgrounds
      accent: string;       // Highlighted text (gold)
    };
    
    // Semantic colors
    success: string;
    warning: string;
    error: string;
    info: string;
    
    // UI element colors
    border: string;
    divider: string;
    shadow: string;
    overlay: string;        // Modal/blur overlay
  };
  
  // Typography
  typography: {
    fontFamily: {
      regular: string;
      medium: string;
      semibold: string;
      bold: string;
    };
    
    fontSize: {
      xs: number;   // 12px - Captions
      sm: number;   // 14px - Small text
      base: number; // 16px - Body text (readable for 40+)
      lg: number;   // 18px - Subheadings
      xl: number;   // 20px - Headings
      '2xl': number; // 24px - Large headings
      '3xl': number; // 30px - Hero text
    };
    
    lineHeight: {
      tight: number;
      normal: number;
      relaxed: number;
    };
  };
  
  // Spacing (8px base grid)
  spacing: {
    xs: number;   // 4px
    sm: number;   // 8px
    md: number;   // 16px
    lg: number;   // 24px
    xl: number;   // 32px
    '2xl': number; // 48px
    '3xl': number; // 64px
  };
  
  // Border radius
  borderRadius: {
    none: number;
    sm: number;   // 4px
    md: number;   // 8px
    lg: number;   // 12px
    xl: number;   // 16px
    '2xl': number; // 24px
    full: number; // 9999px (pill shape)
  };
  
  // Shadows
  shadows: {
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
  
  // Animation durations (ms)
  animation: {
    fast: number;
    normal: number;
    slow: number;
  };
  
  // Asset paths
  assets: {
    logo: string;
    logoLight: string;
    defaultAvatar: string;
    placeholderImage: string;
  };
}

/**
 * Default Theme: "Dark Luxury"
 * Can be exported and replaced with custom themes
 */
export const defaultTheme: ThemeConfig = {
  appName: "LuxeCompanion",
  appTagline: "Your Premium AI Experience",
  
  colors: {
    background: {
      primary: "#0A0A0F",       // Deep black with slight blue tint
      secondary: "#1A1A24",     // Elevated surfaces
      tertiary: "#252530",      // Input fields
      gradient: ["#0A0A0F", "#1A1520", "#0A0A0F"], // Subtle gradient
    },
    
    primary: {
      main: "#FFD700",          // Luxe gold
      light: "#FFE55C",         // Lighter gold
      dark: "#B8960A",          // Darker gold
      gradient: ["#FFD700", "#FFA500"], // Gold to orange
    },
    
    spicy: {
      main: "#FF69B4",          // Hot pink
      light: "#FF8DC7",         // Lighter pink
      gradient: ["#FF1493", "#FF69B4", "#FF8DC7"], // Deep pink to light
      glow: "rgba(255, 105, 180, 0.4)", // Pink glow
    },
    
    text: {
      primary: "#FFFFFF",       // Pure white
      secondary: "#A0A0B0",     // Muted gray
      tertiary: "#606070",      // Subtle gray
      inverse: "#0A0A0F",       // Dark text on light bg
      accent: "#FFD700",        // Gold accent
    },
    
    success: "#10B981",         // Green
    warning: "#F59E0B",         // Amber
    error: "#EF4444",           // Red
    info: "#3B82F6",            // Blue
    
    border: "#2A2A35",
    divider: "#1F1F28",
    shadow: "rgba(0, 0, 0, 0.5)",
    overlay: "rgba(0, 0, 0, 0.7)",
  },
  
  typography: {
    fontFamily: {
      regular: "Inter-Regular",
      medium: "Inter-Medium",
      semibold: "Inter-SemiBold",
      bold: "Inter-Bold",
    },
    
    fontSize: {
      xs: 12,
      sm: 14,
      base: 16,   // Optimized for 40+ readability
      lg: 18,
      xl: 20,
      '2xl': 24,
      '3xl': 30,
    },
    
    lineHeight: {
      tight: 1.2,
      normal: 1.5,
      relaxed: 1.75,
    },
  },
  
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    '2xl': 48,
    '3xl': 64,
  },
  
  borderRadius: {
    none: 0,
    sm: 4,
    md: 8,
    lg: 12,
    xl: 16,
    '2xl': 24,
    full: 9999,
  },
  
  shadows: {
    sm: "0px 1px 2px rgba(0, 0, 0, 0.3)",
    md: "0px 4px 6px rgba(0, 0, 0, 0.4)",
    lg: "0px 10px 15px rgba(0, 0, 0, 0.5)",
    xl: "0px 20px 25px rgba(0, 0, 0, 0.6)",
  },
  
  animation: {
    fast: 150,
    normal: 300,
    slow: 500,
  },
  
  assets: {
    logo: require("../assets/images/logo.png"),
    logoLight: require("../assets/images/logo-light.png"),
    defaultAvatar: require("../assets/images/default-avatar.png"),
    placeholderImage: require("../assets/images/placeholder.png"),
  },
};

/**
 * Active theme instance
 * Replace this with your custom theme to reskin the entire app
 */
export const theme = defaultTheme;

/**
 * Helper function to get gradient string for React Native
 */
export const getGradient = (colors: string[]) => ({
  colors,
  start: { x: 0, y: 0 },
  end: { x: 1, y: 1 },
});

/**
 * Helper to get shadow style for React Native
 */
export const getShadow = (level: 'sm' | 'md' | 'lg' | 'xl') => ({
  shadowColor: theme.colors.shadow,
  shadowOffset: {
    width: 0,
    height: level === 'sm' ? 1 : level === 'md' ? 4 : level === 'lg' ? 10 : 20,
  },
  shadowOpacity: level === 'sm' ? 0.3 : level === 'md' ? 0.4 : level === 'lg' ? 0.5 : 0.6,
  shadowRadius: level === 'sm' ? 2 : level === 'md' ? 6 : level === 'lg' ? 15 : 25,
  elevation: level === 'sm' ? 2 : level === 'md' ? 4 : level === 'lg' ? 8 : 12,
});

/**
 * Spicy mode theme variant
 * Dynamically applies when spicy mode is enabled
 */
export const getSpicyTheme = (): Partial<ThemeConfig> => ({
  colors: {
    ...theme.colors,
    primary: {
      main: theme.colors.spicy.main,
      light: theme.colors.spicy.light,
      dark: "#C71585", // Medium violet red
      gradient: theme.colors.spicy.gradient,
    },
    background: {
      ...theme.colors.background,
      gradient: ["#1A0A14", "#2D1428", "#1A0A14"], // Dark purple gradient
    },
  },
});

/**
 * Export type for theme context
 */
export type Theme = typeof theme;
