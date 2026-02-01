/**
 * Emotion Effects Components
 * 
 * 情绪视觉特效组件:
 * - GlitchOverlay: 故障风效果 (愤怒状态)
 * - GlowOverlay: 光晕效果 (开心/Spicy状态)
 * - EmotionIndicator: 情绪指示器
 */

import React, { useEffect, useState, useRef, memo } from 'react';
import { View, Text, StyleSheet, Animated, Easing } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { EmotionMode } from '../hooks/useEmotionTheme';

// ============================================================================
// Glitch Overlay - 故障风效果
// ============================================================================

interface GlitchOverlayProps {
  enabled: boolean;
  intensity?: number;  // 0-1, 默认 0.3
}

export const GlitchOverlay = memo(function GlitchOverlay({ 
  enabled, 
  intensity = 0.3 
}: GlitchOverlayProps) {
  const [visible, setVisible] = useState(true);
  const [offset, setOffset] = useState(0);
  
  useEffect(() => {
    if (!enabled) return;
    
    // 随机闪烁和偏移
    const interval = setInterval(() => {
      const shouldShow = Math.random() > 0.15;  // 85%概率显示
      setVisible(shouldShow);
      
      if (shouldShow) {
        // 随机水平偏移 (模拟glitch)
        setOffset((Math.random() - 0.5) * 4);
      }
    }, 80);
    
    return () => clearInterval(interval);
  }, [enabled]);
  
  if (!enabled || !visible) return null;
  
  return (
    <View 
      style={[
        styles.glitchOverlay, 
        { opacity: intensity, transform: [{ translateX: offset }] }
      ]} 
      pointerEvents="none"
    >
      {/* 扫描线 */}
      {Array.from({ length: 15 }).map((_, i) => (
        <View
          key={i}
          style={[
            styles.scanline,
            { 
              top: `${(i * 7) + Math.random() * 2}%`,
              opacity: 0.15 + Math.random() * 0.2,
              backgroundColor: i % 3 === 0 ? 'rgba(255,0,0,0.3)' : 'rgba(0,255,255,0.15)',
            },
          ]}
        />
      ))}
      
      {/* 顶部红色条纹 (愤怒提示) */}
      <View style={styles.angryStripe} />
    </View>
  );
});

// ============================================================================
// Glow Overlay - 光晕效果
// ============================================================================

interface GlowOverlayProps {
  enabled: boolean;
  color?: string;
  mode?: 'happy' | 'spicy';
}

export const GlowOverlay = memo(function GlowOverlay({ 
  enabled, 
  color = '#FF69B4',
  mode = 'happy',
}: GlowOverlayProps) {
  const pulseAnim = useRef(new Animated.Value(0.2)).current;
  
  useEffect(() => {
    if (!enabled) return;
    
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: mode === 'spicy' ? 0.45 : 0.35,
          duration: 2500,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: false,
        }),
        Animated.timing(pulseAnim, {
          toValue: 0.2,
          duration: 2500,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: false,
        }),
      ])
    );
    
    animation.start();
    return () => animation.stop();
  }, [enabled, mode, pulseAnim]);
  
  if (!enabled) return null;
  
  const glowColor = mode === 'spicy' ? '#8B5CF6' : color;
  
  return (
    <Animated.View
      style={[styles.glowOverlay, { opacity: pulseAnim }]}
      pointerEvents="none"
    >
      {/* 顶部光晕 */}
      <LinearGradient
        colors={[`${glowColor}50`, 'transparent']}
        style={styles.glowTop}
        start={{ x: 0.5, y: 0 }}
        end={{ x: 0.5, y: 1 }}
      />
      
      {/* 底部光晕 */}
      <LinearGradient
        colors={['transparent', `${glowColor}30`]}
        style={styles.glowBottom}
        start={{ x: 0.5, y: 0 }}
        end={{ x: 0.5, y: 1 }}
      />
      
      {/* 边缘光晕 (Spicy模式更强) */}
      {mode === 'spicy' && (
        <>
          <LinearGradient
            colors={[`${glowColor}40`, 'transparent']}
            style={styles.glowLeft}
            start={{ x: 0, y: 0.5 }}
            end={{ x: 1, y: 0.5 }}
          />
          <LinearGradient
            colors={['transparent', `${glowColor}40`]}
            style={styles.glowRight}
            start={{ x: 0, y: 0.5 }}
            end={{ x: 1, y: 0.5 }}
          />
        </>
      )}
    </Animated.View>
  );
});

// ============================================================================
// Emotion Indicator - 情绪指示条
// ============================================================================

interface EmotionIndicatorProps {
  mode: EmotionMode;
  score: number;
  visible?: boolean;
  style?: object;
}

export const EmotionIndicator = memo(function EmotionIndicator({
  mode,
  score,
  visible = true,
  style,
}: EmotionIndicatorProps) {
  const slideAnim = useRef(new Animated.Value(visible ? 0 : -50)).current;
  
  useEffect(() => {
    Animated.timing(slideAnim, {
      toValue: visible ? 0 : -50,
      duration: 300,
      useNativeDriver: true,
    }).start();
  }, [visible]);
  
  if (mode === 'neutral') return null;
  
  const config = {
    angry: { emoji: '😠', text: '她有点生气了', color: '#FF1744', bg: 'rgba(255,23,68,0.2)' },
    happy: { emoji: '😊', text: '她很开心', color: '#FF69B4', bg: 'rgba(255,105,180,0.2)' },
    spicy: { emoji: '🔥', text: 'Spicy Mode', color: '#8B5CF6', bg: 'rgba(139,92,246,0.2)' },
    neutral: { emoji: '😌', text: '', color: '#00F0FF', bg: 'transparent' },
  }[mode];
  
  return (
    <Animated.View 
      style={[
        styles.indicatorContainer, 
        { backgroundColor: config.bg, transform: [{ translateY: slideAnim }] },
        style,
      ]}
    >
      <Text style={styles.indicatorEmoji}>{config.emoji}</Text>
      <Text style={[styles.indicatorText, { color: config.color }]}>{config.text}</Text>
    </Animated.View>
  );
});

// ============================================================================
// Combined Effects Layer - 组合特效层
// ============================================================================

interface EmotionEffectsLayerProps {
  emotionMode: EmotionMode;
  glitchEnabled: boolean;
  glowEnabled: boolean;
  glowColor?: string;
}

export const EmotionEffectsLayer = memo(function EmotionEffectsLayer({
  emotionMode,
  glitchEnabled,
  glowEnabled,
  glowColor,
}: EmotionEffectsLayerProps) {
  return (
    <>
      <GlitchOverlay enabled={glitchEnabled} intensity={0.25} />
      <GlowOverlay 
        enabled={glowEnabled} 
        color={glowColor}
        mode={emotionMode === 'spicy' ? 'spicy' : 'happy'}
      />
    </>
  );
});

// ============================================================================
// Styles
// ============================================================================

const styles = StyleSheet.create({
  glitchOverlay: {
    ...StyleSheet.absoluteFillObject,
    overflow: 'hidden',
  },
  scanline: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 1,
  },
  angryStripe: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: 'rgba(255, 23, 68, 0.6)',
  },
  
  glowOverlay: {
    ...StyleSheet.absoluteFillObject,
  },
  glowTop: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: '20%',
  },
  glowBottom: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: '15%',
  },
  glowLeft: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    width: '8%',
  },
  glowRight: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    right: 0,
    width: '8%',
  },
  
  indicatorContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    gap: 6,
  },
  indicatorEmoji: {
    fontSize: 14,
  },
  indicatorText: {
    fontSize: 12,
    fontWeight: '600',
  },
});
