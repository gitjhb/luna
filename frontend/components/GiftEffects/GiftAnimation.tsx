/**
 * Gift Animation Component
 * 
 * 使用 Lottie 播放礼物动画，带降级方案
 */

import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Animated, Easing } from 'react-native';
import { GiftAnimationProps, getGiftConfig } from './types';

// 尝试导入 Lottie（可选依赖）
let LottieView: any = null;
try {
  LottieView = require('lottie-react-native').default;
} catch (e) {
  // Lottie 未安装，使用降级方案
  console.log('Lottie not installed, using fallback animation');
}

// Lottie 动画资源映射 - 匹配后端 gift_type
// 注意：如果动画文件不存在会使用 fallback emoji 动画
let ANIMATION_SOURCES: Record<string, any> = {};
try {
  ANIMATION_SOURCES = {
    rose: require('./assets/animations/rose.json'),
    chocolate: require('./assets/animations/chocolate.json'),
    teddy_bear: require('./assets/animations/teddy_bear.json'),
    premium_rose: require('./assets/animations/premium_rose.json'),
    diamond_ring: require('./assets/animations/diamond_ring.json'),
    crown: require('./assets/animations/crown.json'),
  };
} catch (e) {
  console.log('Some animation files not found, using fallback');
}

/**
 * 降级动画组件 - 当 Lottie 不可用时使用
 */
const FallbackAnimation: React.FC<GiftAnimationProps> = ({
  type,
  autoPlay = true,
  onAnimationFinish,
}) => {
  const config = getGiftConfig(type);
  const scaleAnim = useRef(new Animated.Value(0)).current;
  const opacityAnim = useRef(new Animated.Value(0)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;
  const floatAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!autoPlay) return;

    // 组合动画
    Animated.parallel([
      // 缩放：从小到大再到正常
      Animated.sequence([
        Animated.timing(scaleAnim, {
          toValue: 1.3,
          duration: 300,
          easing: Easing.out(Easing.back(2)),
          useNativeDriver: true,
        }),
        Animated.timing(scaleAnim, {
          toValue: 1,
          duration: 200,
          useNativeDriver: true,
        }),
      ]),
      // 透明度
      Animated.timing(opacityAnim, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }),
      // 旋转
      Animated.timing(rotateAnim, {
        toValue: 1,
        duration: 500,
        easing: Easing.elastic(1),
        useNativeDriver: true,
      }),
    ]).start();

    // 漂浮动画
    Animated.loop(
      Animated.sequence([
        Animated.timing(floatAnim, {
          toValue: -10,
          duration: 1000,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(floatAnim, {
          toValue: 0,
          duration: 1000,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ])
    ).start();

    // 动画结束回调
    const timer = setTimeout(() => {
      Animated.timing(opacityAnim, {
        toValue: 0,
        duration: 500,
        useNativeDriver: true,
      }).start(() => {
        onAnimationFinish?.();
      });
    }, config.animationDuration - 500);

    return () => clearTimeout(timer);
  }, [autoPlay]);

  const rotateInterpolate = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['-20deg', '0deg'],
  });

  return (
    <Animated.View
      style={[
        styles.fallbackContainer,
        {
          opacity: opacityAnim,
          transform: [
            { scale: scaleAnim },
            { rotate: rotateInterpolate },
            { translateY: floatAnim },
          ],
        },
      ]}
    >
      <Text style={styles.fallbackEmoji}>{config.emoji}</Text>
      <View style={styles.sparkles}>
        <Text style={styles.sparkle}>✨</Text>
        <Text style={[styles.sparkle, styles.sparkle2]}>✨</Text>
        <Text style={[styles.sparkle, styles.sparkle3]}>✨</Text>
      </View>
    </Animated.View>
  );
};

// 根据礼物等级返回动画大小（匹配后端 gift_type）
const getAnimationSize = (type: string): number => {
  switch (type) {
    case 'crown': return 300;        // 最大最贵
    case 'diamond_ring': return 280;
    case 'premium_rose': return 260;
    case 'teddy_bear': return 240;
    default: return 200;
  }
};

// 根据礼物等级返回播放速度（大礼物慢一点更有仪式感）
const getAnimationSpeed = (type: string): number => {
  switch (type) {
    case 'crown': return 0.8;
    case 'diamond_ring': return 0.85;
    case 'premium_rose': return 0.9;
    default: return 1;
  }
};

/**
 * 礼物动画组件
 */
export const GiftAnimation: React.FC<GiftAnimationProps> = (props) => {
  const { type, autoPlay = true, loop = false, speed, style, onAnimationFinish } = props;
  const lottieRef = useRef<any>(null);

  // 检查是否有对应的 Lottie 动画
  const hasLottieAnimation = LottieView && ANIMATION_SOURCES[type];
  
  // 动画大小和速度
  const size = getAnimationSize(type);
  const animSpeed = speed ?? getAnimationSpeed(type);

  useEffect(() => {
    if (hasLottieAnimation && autoPlay && lottieRef.current) {
      lottieRef.current.play();
    }
  }, [hasLottieAnimation, autoPlay]);

  // 如果没有 Lottie 或没有对应动画，使用降级方案
  if (!hasLottieAnimation) {
    return <FallbackAnimation {...props} />;
  }

  // 使用 Lottie 动画
  return (
    <LottieView
      ref={lottieRef}
      source={ANIMATION_SOURCES[type]}
      autoPlay={autoPlay}
      loop={loop}
      speed={animSpeed}
      style={[styles.lottie, { width: size, height: size }, style]}
      onAnimationFinish={onAnimationFinish}
    />
  );
};

const styles = StyleSheet.create({
  lottie: {
    width: 200,
    height: 200,
  },
  fallbackContainer: {
    width: 200,
    height: 200,
    justifyContent: 'center',
    alignItems: 'center',
  },
  fallbackEmoji: {
    fontSize: 100,
    textShadowColor: 'rgba(255, 255, 255, 0.5)',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 20,
  },
  sparkles: {
    position: 'absolute',
    width: '100%',
    height: '100%',
  },
  sparkle: {
    position: 'absolute',
    fontSize: 24,
    top: 20,
    right: 30,
  },
  sparkle2: {
    top: 40,
    left: 20,
    fontSize: 20,
  },
  sparkle3: {
    bottom: 30,
    right: 20,
    fontSize: 28,
  },
});

export default GiftAnimation;
