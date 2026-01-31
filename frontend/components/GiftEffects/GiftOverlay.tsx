/**
 * Gift Overlay Component
 * 
 * 全屏礼物特效覆盖层
 */

import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  Animated,
  Dimensions,
  TouchableWithoutFeedback,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { GiftOverlayProps, GIFT_CONFIGS } from './types';
import { GiftAnimation } from './GiftAnimation';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

/**
 * 礼物特效覆盖层
 */
export const GiftOverlay: React.FC<GiftOverlayProps> = ({
  visible,
  giftType,
  senderName = '你',
  receiverName = 'TA',
  onAnimationEnd,
  onClose,
}) => {
  const config = GIFT_CONFIGS[giftType];
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const textFadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible) {
      // 淡入
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
        Animated.timing(textFadeAnim, {
          toValue: 1,
          duration: 500,
          delay: 300,
          useNativeDriver: true,
        }),
      ]).start();

      // 自动关闭
      const timer = setTimeout(() => {
        handleClose();
      }, config.animationDuration);

      return () => clearTimeout(timer);
    } else {
      fadeAnim.setValue(0);
      textFadeAnim.setValue(0);
    }
  }, [visible]);

  const handleClose = () => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }),
      Animated.timing(textFadeAnim, {
        toValue: 0,
        duration: 200,
        useNativeDriver: true,
      }),
    ]).start(() => {
      onAnimationEnd?.();
      onClose?.();
    });
  };

  if (!visible) return null;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="none"
      statusBarTranslucent
      onRequestClose={handleClose}
    >
      <TouchableWithoutFeedback onPress={handleClose}>
        <View style={styles.container}>
          {/* 背景渐变 */}
          <Animated.View style={[styles.background, { opacity: fadeAnim }]}>
            <LinearGradient
              colors={['rgba(0,0,0,0.8)', 'rgba(30,0,50,0.9)', 'rgba(0,0,0,0.8)']}
              style={styles.gradient}
            />
          </Animated.View>

          {/* 粒子效果背景 */}
          <ParticleBackground giftType={giftType} />

          {/* 主动画 */}
          <View style={styles.animationContainer}>
            <GiftAnimation
              type={giftType}
              autoPlay
              onAnimationFinish={handleClose}
            />
          </View>

          {/* 文字说明 */}
          <Animated.View style={[styles.textContainer, { opacity: textFadeAnim }]}>
            <Text style={styles.senderText}>{senderName}</Text>
            <Text style={styles.actionText}>送出了</Text>
            <View style={styles.giftNameContainer}>
              <Text style={styles.giftEmoji}>{config.emoji}</Text>
              <Text style={styles.giftName}>{config.nameCn}</Text>
            </View>
            <Text style={styles.xpText}>+{config.xpReward} XP</Text>
          </Animated.View>

          {/* 点击提示 */}
          <Animated.Text style={[styles.tapHint, { opacity: textFadeAnim }]}>
            点击任意处关闭
          </Animated.Text>
        </View>
      </TouchableWithoutFeedback>
    </Modal>
  );
};

/**
 * 粒子效果背景 - 根据礼物等级调整粒子数量
 */
const ParticleBackground: React.FC<{ giftType: GiftType }> = ({ giftType }) => {
  // 大礼物粒子更多
  const particleCount = {
    rose: 15,
    chocolate: 18,
    bear: 22,
    diamond: 30,
    crown: 40,
    castle: 50,
  }[giftType] || 20;
  
  const particles = Array.from({ length: particleCount }, (_, i) => i);
  
  return (
    <View style={styles.particleContainer}>
      {particles.map((i) => (
        <Particle key={i} index={i} giftType={giftType} />
      ))}
    </View>
  );
};

/**
 * 单个粒子 - 根据礼物类型选择不同粒子样式
 */
const Particle: React.FC<{ index: number; giftType: GiftType }> = ({ index, giftType }) => {
  const translateY = useRef(new Animated.Value(SCREEN_HEIGHT + 50)).current;
  const translateX = useRef(new Animated.Value(Math.random() * SCREEN_WIDTH)).current;
  const opacity = useRef(new Animated.Value(0)).current;
  const scale = useRef(new Animated.Value(0.5 + Math.random() * 0.5)).current;

  // 不同礼物的粒子样式
  const particlesByGift: Record<string, string[]> = {
    rose: ['🌹', '💖', '💕', '✨', '🩷'],
    chocolate: ['🍫', '💝', '❤️', '✨', '🤎'],
    bear: ['🧸', '💛', '🌟', '✨', '💕'],
    diamond: ['💎', '✨', '💫', '⭐', '🌟', '💠'],
    crown: ['👑', '✨', '🌟', '💫', '⭐', '🏆', '💛'],
    castle: ['🏰', '🎆', '✨', '🌟', '💫', '🎇', '⭐', '👑', '💎'],
  };

  useEffect(() => {
    const delay = Math.random() * 2000;
    const duration = 3000 + Math.random() * 2000;

    Animated.loop(
      Animated.sequence([
        Animated.delay(delay),
        Animated.parallel([
          Animated.timing(translateY, {
            toValue: -50,
            duration,
            useNativeDriver: true,
          }),
          Animated.sequence([
            Animated.timing(opacity, {
              toValue: 0.9,
              duration: duration * 0.2,
              useNativeDriver: true,
            }),
            Animated.timing(opacity, {
              toValue: 0.9,
              duration: duration * 0.6,
              useNativeDriver: true,
            }),
            Animated.timing(opacity, {
              toValue: 0,
              duration: duration * 0.2,
              useNativeDriver: true,
            }),
          ]),
        ]),
        Animated.timing(translateY, {
          toValue: SCREEN_HEIGHT + 50,
          duration: 0,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, []);

  const particles = particlesByGift[giftType] || ['✨', '💫', '⭐', '💖', '💕'];
  const particle = particles[index % particles.length];
  
  // 大礼物粒子更大
  const baseSize = { rose: 20, chocolate: 20, bear: 22, diamond: 24, crown: 26, castle: 28 }[giftType] || 20;
  const fontSize = baseSize + Math.random() * 8;

  return (
    <Animated.Text
      style={[
        styles.particle,
        {
          fontSize,
          opacity,
          transform: [
            { translateX: translateX },
            { translateY },
            { scale },
          ],
        },
      ]}
    >
      {particle}
    </Animated.Text>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  background: {
    ...StyleSheet.absoluteFillObject,
  },
  gradient: {
    flex: 1,
  },
  particleContainer: {
    ...StyleSheet.absoluteFillObject,
    overflow: 'hidden',
  },
  particle: {
    position: 'absolute',
    fontSize: 20,
  },
  animationContainer: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  textContainer: {
    alignItems: 'center',
    marginTop: 20,
  },
  senderText: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.8)',
    marginBottom: 4,
  },
  actionText: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.6)',
    marginBottom: 8,
  },
  giftNameContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  giftEmoji: {
    fontSize: 28,
    marginRight: 8,
  },
  giftName: {
    fontSize: 28,
    fontWeight: '700',
    color: '#fff',
    textShadowColor: 'rgba(168, 85, 247, 0.8)',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 10,
  },
  xpText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#A855F7',
    textShadowColor: 'rgba(168, 85, 247, 0.5)',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 5,
  },
  tapHint: {
    position: 'absolute',
    bottom: 50,
    fontSize: 12,
    color: 'rgba(255,255,255,0.4)',
  },
});

export default GiftOverlay;
