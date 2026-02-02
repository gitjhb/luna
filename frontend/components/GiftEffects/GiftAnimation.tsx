/**
 * Gift Animation Component
 * 
 * 简单有效的礼物特效：
 * - 有Lottie资源就用Lottie
 * - 没有就用Emoji + 粒子特效（同样好看）
 */

import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Animated, Easing, Dimensions } from 'react-native';
import { GiftAnimationProps, getGiftConfig } from './types';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

/**
 * Emoji 礼物动画 - 简单但效果好
 */
export const GiftAnimation: React.FC<GiftAnimationProps> = ({
  type,
  autoPlay = true,
  onAnimationFinish,
}) => {
  const config = getGiftConfig(type);
  
  // 主emoji动画
  const scaleAnim = useRef(new Animated.Value(0)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;
  const floatAnim = useRef(new Animated.Value(0)).current;
  const glowAnim = useRef(new Animated.Value(0)).current;
  
  // 粒子动画 (多个)
  const particles = useRef(
    Array.from({ length: 12 }, () => ({
      x: new Animated.Value(0),
      y: new Animated.Value(0),
      opacity: new Animated.Value(0),
      scale: new Animated.Value(0),
    }))
  ).current;

  useEffect(() => {
    if (!autoPlay) return;

    // 主emoji入场动画
    Animated.parallel([
      // 弹性缩放
      Animated.spring(scaleAnim, {
        toValue: 1,
        tension: 100,
        friction: 6,
        useNativeDriver: true,
      }),
      // 轻微旋转
      Animated.sequence([
        Animated.timing(rotateAnim, {
          toValue: -0.1,
          duration: 150,
          useNativeDriver: true,
        }),
        Animated.timing(rotateAnim, {
          toValue: 0.1,
          duration: 150,
          useNativeDriver: true,
        }),
        Animated.timing(rotateAnim, {
          toValue: 0,
          duration: 150,
          useNativeDriver: true,
        }),
      ]),
      // 发光效果
      Animated.loop(
        Animated.sequence([
          Animated.timing(glowAnim, {
            toValue: 1,
            duration: 800,
            useNativeDriver: true,
          }),
          Animated.timing(glowAnim, {
            toValue: 0.5,
            duration: 800,
            useNativeDriver: true,
          }),
        ])
      ),
    ]).start();

    // 漂浮动画
    Animated.loop(
      Animated.sequence([
        Animated.timing(floatAnim, {
          toValue: -15,
          duration: 1200,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(floatAnim, {
          toValue: 0,
          duration: 1200,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ])
    ).start();

    // 粒子爆发动画
    particles.forEach((particle, index) => {
      const angle = (index / particles.length) * Math.PI * 2;
      const distance = 80 + Math.random() * 60;
      const delay = index * 50;
      
      setTimeout(() => {
        Animated.parallel([
          Animated.timing(particle.opacity, {
            toValue: 1,
            duration: 200,
            useNativeDriver: true,
          }),
          Animated.timing(particle.scale, {
            toValue: 1,
            duration: 300,
            useNativeDriver: true,
          }),
          Animated.timing(particle.x, {
            toValue: Math.cos(angle) * distance,
            duration: 800,
            easing: Easing.out(Easing.cubic),
            useNativeDriver: true,
          }),
          Animated.timing(particle.y, {
            toValue: Math.sin(angle) * distance - 50,
            duration: 800,
            easing: Easing.out(Easing.cubic),
            useNativeDriver: true,
          }),
        ]).start();
        
        // 粒子淡出
        setTimeout(() => {
          Animated.timing(particle.opacity, {
            toValue: 0,
            duration: 500,
            useNativeDriver: true,
          }).start();
        }, 600);
      }, delay);
    });

    // 动画结束回调
    const timer = setTimeout(() => {
      onAnimationFinish?.();
    }, config.animationDuration);

    return () => clearTimeout(timer);
  }, [autoPlay]);

  const rotateInterpolate = rotateAnim.interpolate({
    inputRange: [-0.1, 0, 0.1],
    outputRange: ['-15deg', '0deg', '15deg'],
  });

  // 根据礼物价格决定大小
  const emojiSize = config.price >= 500 ? 140 : config.price >= 100 ? 120 : 100;

  return (
    <View style={styles.container}>
      {/* 粒子效果 */}
      {particles.map((particle, index) => (
        <Animated.Text
          key={index}
          style={[
            styles.particle,
            {
              opacity: particle.opacity,
              transform: [
                { translateX: particle.x },
                { translateY: particle.y },
                { scale: particle.scale },
              ],
            },
          ]}
        >
          {index % 3 === 0 ? '✨' : index % 3 === 1 ? '💫' : '⭐'}
        </Animated.Text>
      ))}
      
      {/* 发光背景 */}
      <Animated.View
        style={[
          styles.glow,
          {
            opacity: glowAnim,
            transform: [{ scale: scaleAnim }],
          },
        ]}
      />
      
      {/* 主Emoji */}
      <Animated.Text
        style={[
          styles.emoji,
          {
            fontSize: emojiSize,
            transform: [
              { scale: scaleAnim },
              { rotate: rotateInterpolate },
              { translateY: floatAnim },
            ],
          },
        ]}
      >
        {config.emoji}
      </Animated.Text>
      
      {/* 礼物名称 */}
      <Animated.Text
        style={[
          styles.giftName,
          {
            opacity: scaleAnim,
            transform: [{ translateY: floatAnim }],
          },
        ]}
      >
        {config.nameCn}
      </Animated.Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: 250,
    height: 250,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emoji: {
    textShadowColor: 'rgba(255, 255, 255, 0.8)',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 30,
  },
  glow: {
    position: 'absolute',
    width: 180,
    height: 180,
    borderRadius: 90,
    backgroundColor: 'rgba(255, 200, 100, 0.3)',
    shadowColor: '#FFD700',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 40,
  },
  particle: {
    position: 'absolute',
    fontSize: 24,
  },
  giftName: {
    marginTop: 10,
    fontSize: 18,
    fontWeight: '600',
    color: '#FFD700',
    textShadowColor: 'rgba(0, 0, 0, 0.5)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 3,
  },
});

export default GiftAnimation;
