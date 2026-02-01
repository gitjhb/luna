/**
 * Dynamic Theme Context
 * 
 * 提供基于情绪状态的动态主题切换，支持平滑过渡动画
 * 
 * 使用方法:
 * 1. 在 _layout.tsx 中包裹 <DynamicThemeProvider>
 * 2. 在组件中使用 useDynamicTheme() 获取当前主题
 * 3. 调用 setEmotionState() 更新情绪状态，主题会自动过渡
 */

import React, { createContext, useContext, useState, useEffect, useRef, useCallback, ReactNode } from 'react';
import { Animated, Easing } from 'react-native';
import { ThemeConfig } from './themes';
import {
  EmotionMode,
  EmotionState,
  getEmotionMode,
  getThemeForEmotion,
  interpolateTheme,
  angryTheme,
  happyTheme,
} from './dynamicTheme';
import { cyberpunk2077, purpleSeduction } from './themes';

// ============================================================================
// Context Types
// ============================================================================

interface DynamicThemeContextType {
  // 当前主题
  theme: ThemeConfig;
  
  // 当前情绪模式
  emotionMode: EmotionMode;
  
  // 动画过渡进度 (0-1)
  transitionProgress: Animated.Value;
  
  // 是否正在过渡中
  isTransitioning: boolean;
  
  // 更新情绪状态
  setEmotionState: (score: number, emotionalState: string, isSpicyMode: boolean) => void;
  
  // 直接设置模式（跳过计算）
  setMode: (mode: EmotionMode) => void;
  
  // 获取插值后的颜色（用于动画）
  getAnimatedColors: () => Partial<ThemeConfig['colors']>;
  
  // Glitch效果开关（愤怒状态时启用）
  glitchEnabled: boolean;
  
  // 光晕效果开关（开心状态时启用）
  glowEnabled: boolean;
}

const DynamicThemeContext = createContext<DynamicThemeContextType | undefined>(undefined);

// ============================================================================
// Provider Component
// ============================================================================

interface DynamicThemeProviderProps {
  children: ReactNode;
  initialMode?: EmotionMode;
  transitionDuration?: number;  // 过渡动画时长 (ms)
}

export function DynamicThemeProvider({
  children,
  initialMode = 'neutral',
  transitionDuration = 500,
}: DynamicThemeProviderProps) {
  // 当前和目标模式
  const [currentMode, setCurrentMode] = useState<EmotionMode>(initialMode);
  const [targetMode, setTargetMode] = useState<EmotionMode>(initialMode);
  const [isTransitioning, setIsTransitioning] = useState(false);
  
  // 动画值
  const transitionProgress = useRef(new Animated.Value(1)).current;
  
  // 主题引用
  const previousThemeRef = useRef<ThemeConfig>(getThemeForEmotion(initialMode));
  const currentThemeRef = useRef<ThemeConfig>(getThemeForEmotion(initialMode));
  
  // 特效状态
  const [glitchEnabled, setGlitchEnabled] = useState(false);
  const [glowEnabled, setGlowEnabled] = useState(false);

  // 更新情绪状态
  const setEmotionState = useCallback((
    score: number,
    emotionalState: string,
    isSpicyMode: boolean
  ) => {
    const newMode = getEmotionMode(score, emotionalState, isSpicyMode);
    
    if (newMode !== targetMode) {
      setTargetMode(newMode);
    }
  }, [targetMode]);

  // 直接设置模式
  const setMode = useCallback((mode: EmotionMode) => {
    if (mode !== targetMode) {
      setTargetMode(mode);
    }
  }, [targetMode]);

  // 当目标模式变化时，启动过渡动画
  useEffect(() => {
    if (targetMode !== currentMode) {
      // 保存当前主题作为过渡起点
      previousThemeRef.current = currentThemeRef.current;
      currentThemeRef.current = getThemeForEmotion(targetMode);
      
      // 重置动画值
      transitionProgress.setValue(0);
      setIsTransitioning(true);
      
      // 执行过渡动画
      Animated.timing(transitionProgress, {
        toValue: 1,
        duration: transitionDuration,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: false,  // 颜色动画不能用native driver
      }).start(() => {
        setCurrentMode(targetMode);
        setIsTransitioning(false);
        
        // 更新特效状态
        setGlitchEnabled(targetMode === 'angry');
        setGlowEnabled(targetMode === 'happy' || targetMode === 'spicy');
      });
    }
  }, [targetMode, currentMode, transitionDuration, transitionProgress]);

  // 获取插值后的颜色
  const getAnimatedColors = useCallback((): Partial<ThemeConfig['colors']> => {
    if (!isTransitioning) {
      return currentThemeRef.current.colors;
    }
    
    // 这里需要读取动画值，但由于是非native动画，
    // 实际使用时建议通过 Animated.interpolate 在组件内处理
    return currentThemeRef.current.colors;
  }, [isTransitioning]);

  // 当前使用的主题（过渡完成后的目标主题）
  const theme = currentThemeRef.current;

  return (
    <DynamicThemeContext.Provider
      value={{
        theme,
        emotionMode: currentMode,
        transitionProgress,
        isTransitioning,
        setEmotionState,
        setMode,
        getAnimatedColors,
        glitchEnabled,
        glowEnabled,
      }}
    >
      {children}
    </DynamicThemeContext.Provider>
  );
}

// ============================================================================
// Hook
// ============================================================================

export function useDynamicTheme(): DynamicThemeContextType {
  const context = useContext(DynamicThemeContext);
  if (!context) {
    throw new Error('useDynamicTheme must be used within a DynamicThemeProvider');
  }
  return context;
}

// ============================================================================
// Animated Background Component
// ============================================================================

import { StyleSheet, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';

interface AnimatedThemeBackgroundProps {
  children: ReactNode;
  style?: object;
}

/**
 * 带动态主题背景的容器组件
 * 会根据情绪状态自动切换背景颜色和渐变
 */
export function AnimatedThemeBackground({ children, style }: AnimatedThemeBackgroundProps) {
  const { theme, emotionMode, transitionProgress, isTransitioning, glitchEnabled, glowEnabled } = useDynamicTheme();
  
  // 使用动画透明度实现过渡
  const overlayOpacity = transitionProgress.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 1],
  });
  
  return (
    <View style={[styles.container, style]}>
      {/* 基础背景 */}
      <LinearGradient
        colors={theme.colors.background.gradient as unknown as string[]}
        style={StyleSheet.absoluteFill}
      />
      
      {/* 过渡叠加层（可选，用于更平滑的过渡） */}
      {isTransitioning && (
        <Animated.View
          style={[
            StyleSheet.absoluteFill,
            { opacity: overlayOpacity },
          ]}
        >
          <LinearGradient
            colors={theme.colors.background.gradient as unknown as string[]}
            style={StyleSheet.absoluteFill}
          />
        </Animated.View>
      )}
      
      {/* Glitch效果叠加层 (愤怒状态) */}
      {glitchEnabled && (
        <GlitchOverlay intensity={0.3} />
      )}
      
      {/* 光晕效果叠加层 (开心/Spicy状态) */}
      {glowEnabled && (
        <GlowOverlay color={theme.colors.glow || theme.colors.primary.main} />
      )}
      
      {/* 内容 */}
      {children}
    </View>
  );
}

// ============================================================================
// Effect Components
// ============================================================================

interface GlitchOverlayProps {
  intensity: number;  // 0-1
}

/**
 * 故障风效果叠加层
 * 简化版：使用条纹和轻微偏移模拟
 */
function GlitchOverlay({ intensity }: GlitchOverlayProps) {
  const [visible, setVisible] = useState(true);
  
  // 随机闪烁
  useEffect(() => {
    const interval = setInterval(() => {
      setVisible(Math.random() > 0.7);  // 30%概率隐藏
    }, 100);
    
    return () => clearInterval(interval);
  }, []);
  
  if (!visible) return null;
  
  return (
    <View style={[styles.glitchOverlay, { opacity: intensity * 0.5 }]} pointerEvents="none">
      {/* 扫描线效果 */}
      {Array.from({ length: 20 }).map((_, i) => (
        <View
          key={i}
          style={[
            styles.scanline,
            { top: `${i * 5}%`, opacity: Math.random() * 0.3 },
          ]}
        />
      ))}
    </View>
  );
}

interface GlowOverlayProps {
  color: string;
}

/**
 * 光晕效果叠加层
 * 在屏幕边缘添加柔和的发光效果
 */
function GlowOverlay({ color }: GlowOverlayProps) {
  const pulseAnim = useRef(new Animated.Value(0.3)).current;
  
  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 0.6,
          duration: 2000,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: false,
        }),
        Animated.timing(pulseAnim, {
          toValue: 0.3,
          duration: 2000,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: false,
        }),
      ])
    ).start();
  }, [pulseAnim]);
  
  return (
    <Animated.View
      style={[styles.glowOverlay, { opacity: pulseAnim }]}
      pointerEvents="none"
    >
      <LinearGradient
        colors={[
          `${color}40`,  // 25% opacity
          'transparent',
          'transparent',
          `${color}20`,  // 12% opacity
        ]}
        locations={[0, 0.3, 0.7, 1]}
        start={{ x: 0.5, y: 0 }}
        end={{ x: 0.5, y: 1 }}
        style={StyleSheet.absoluteFill}
      />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  glitchOverlay: {
    ...StyleSheet.absoluteFillObject,
    overflow: 'hidden',
  },
  scanline: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: 'rgba(255, 0, 0, 0.1)',
  },
  glowOverlay: {
    ...StyleSheet.absoluteFillObject,
  },
});
