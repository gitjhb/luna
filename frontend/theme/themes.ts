/**
 * Theme Collection - Multiple Theme Support
 * 
 * 1. Purple Seduction (原版紫色诱惑)
 * 2. Cyberpunk 2077 (赛博朋克)
 */

export interface ThemeConfig {
  id: string;
  name: string;
  nameCn: string;
  
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
      cyan?: string;
      yellow?: string;
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
    
    // 特效颜色
    glow?: string;
    neon?: string;
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
  
  effects?: {
    glowIntensity?: number;
    borderGlow?: boolean;
    scanlines?: boolean;
  };
}

// ============================================================================
// Theme 1: Purple Seduction (紫色诱惑) - 原版
// ============================================================================
export const purpleSeduction: ThemeConfig = {
  id: 'purple-seduction',
  name: 'Purple Seduction',
  nameCn: '紫色诱惑',
  
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
    fontSize: { xs: 11, sm: 13, base: 15, lg: 17, xl: 20, '2xl': 24, '3xl': 30 },
    lineHeight: { tight: 1.2, normal: 1.5, relaxed: 1.7 },
  },
  
  spacing: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, '2xl': 48 },
  
  borderRadius: { sm: 6, md: 10, lg: 14, xl: 18, '2xl': 24, full: 9999 },
};

// ============================================================================
// Theme 2: Cyberpunk 2077 (赛博朋克)
// ============================================================================
export const cyberpunk2077: ThemeConfig = {
  id: 'cyberpunk-2077',
  name: 'Cyberpunk 2077',
  nameCn: '赛博朋克',
  
  colors: {
    background: {
      primary: "#0a0a0f",        // 深黑
      secondary: "#0d1117",      // 暗蓝黑
      tertiary: "#161b22",       // 稍亮的蓝黑
      gradient: ["#0a0a0f", "#0d1a1f", "#0a0a0f"] as const,
    },
    
    primary: {
      main: "#00F0FF",           // 霓虹青
      light: "#5CFFFF",
      dark: "#00B8C4",
      gradient: ["#00F0FF", "#FF2A6D"] as const,  // 青到品红
    },
    
    accent: {
      pink: "#FF2A6D",           // 霓虹品红
      purple: "#BD00FF",         // 霓虹紫
      cyan: "#00F0FF",           // 霓虹青
      yellow: "#FCEE0A",         // 赛博朋克黄
      gradient: ["#FCEE0A", "#00F0FF"] as const,  // 黄到青
    },
    
    text: {
      primary: "#FFFFFF",
      secondary: "rgba(0, 240, 255, 0.8)",   // 青色调文字
      tertiary: "rgba(255, 255, 255, 0.4)",
      inverse: "#0a0a0f",
    },
    
    success: "#39FF14",          // 霓虹绿
    warning: "#FCEE0A",          // 赛博朋克黄
    error: "#FF2A6D",            // 霓虹品红
    
    border: "rgba(0, 240, 255, 0.2)",     // 青色边框
    overlay: "rgba(10, 10, 15, 0.9)",
    
    glow: "#00F0FF",
    neon: "#FCEE0A",
  },
  
  typography: {
    fontSize: { xs: 11, sm: 13, base: 15, lg: 17, xl: 20, '2xl': 24, '3xl': 30 },
    lineHeight: { tight: 1.2, normal: 1.5, relaxed: 1.7 },
  },
  
  spacing: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, '2xl': 48 },
  
  // 赛博朋克风格：更硬朗的边角
  borderRadius: { sm: 2, md: 4, lg: 8, xl: 12, '2xl': 16, full: 9999 },
  
  effects: {
    glowIntensity: 0.8,
    borderGlow: true,
    scanlines: true,
  },
};

// ============================================================================
// Theme Registry
// ============================================================================
export const themes: Record<string, ThemeConfig> = {
  'purple-seduction': purpleSeduction,
  'cyberpunk-2077': cyberpunk2077,
};

export const themeList = [
  { id: 'purple-seduction', name: 'Purple Seduction', nameCn: '紫色诱惑', icon: '💜' },
  { id: 'cyberpunk-2077', name: 'Cyberpunk 2077', nameCn: '赛博朋克', icon: '🤖' },
];

export const defaultThemeId = 'purple-seduction';
