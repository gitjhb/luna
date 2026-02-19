/**
 * ChatLoadingSkeleton - 聊天界面加载骨架屏
 * 
 * Luna 2077 风格的加载动画，模拟消息气泡加载中
 */

import React, { useEffect, useRef } from 'react';
import { View, StyleSheet, Animated, Dimensions } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// 单个骨架气泡
const SkeletonBubble = ({ 
  isUser, 
  width, 
  delay = 0 
}: { 
  isUser: boolean; 
  width: number; 
  delay?: number;
}) => {
  const shimmerAnim = useRef(new Animated.Value(0)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // 淡入动画
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 300,
      delay,
      useNativeDriver: true,
    }).start();

    // 闪烁动画
    Animated.loop(
      Animated.sequence([
        Animated.timing(shimmerAnim, {
          toValue: 1,
          duration: 1000,
          delay: delay + 300,
          useNativeDriver: true,
        }),
        Animated.timing(shimmerAnim, {
          toValue: 0,
          duration: 1000,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, []);

  const opacity = shimmerAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.3, 0.6],
  });

  return (
    <Animated.View 
      style={[
        styles.messageRow,
        isUser ? styles.messageRowUser : styles.messageRowAI,
        { opacity: fadeAnim },
      ]}
    >
      {/* AI 头像占位 */}
      {!isUser && (
        <Animated.View style={[styles.avatarSkeleton, { opacity }]} />
      )}
      
      {/* 气泡占位 */}
      <Animated.View 
        style={[
          styles.bubbleSkeleton,
          isUser ? styles.bubbleSkeletonUser : styles.bubbleSkeletonAI,
          { width, opacity },
        ]}
      >
        {/* 内部发光效果 */}
        <View style={styles.innerGlow} />
      </Animated.View>
    </Animated.View>
  );
};

// 完整的骨架屏
export default function ChatLoadingSkeleton() {
  return (
    <View style={styles.container}>
      {/* 模拟对话的骨架气泡 */}
      <SkeletonBubble isUser={false} width={SCREEN_WIDTH * 0.65} delay={0} />
      <SkeletonBubble isUser={true} width={SCREEN_WIDTH * 0.45} delay={100} />
      <SkeletonBubble isUser={false} width={SCREEN_WIDTH * 0.55} delay={200} />
      <SkeletonBubble isUser={false} width={SCREEN_WIDTH * 0.4} delay={250} />
      <SkeletonBubble isUser={true} width={SCREEN_WIDTH * 0.5} delay={350} />
      <SkeletonBubble isUser={false} width={SCREEN_WIDTH * 0.6} delay={450} />
    </View>
  );
}

// 简化版 - 只有几个气泡
export function ChatLoadingSimple() {
  const pulseAnim = useRef(new Animated.Value(0.4)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 0.7,
          duration: 800,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 0.4,
          duration: 800,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, []);

  return (
    <View style={styles.simpleContainer}>
      <Animated.View 
        style={[
          styles.messageRow,
          styles.messageRowAI,
          { opacity: pulseAnim },
        ]}
      >
        <View style={styles.avatarSkeleton} />
        <View style={[styles.bubbleSkeleton, styles.bubbleSkeletonAI, { width: SCREEN_WIDTH * 0.5 }]} />
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 16,
    paddingTop: 20,
    justifyContent: 'flex-end',  // 从底部开始（配合 inverted list）
    paddingBottom: 20,
  },
  simpleContainer: {
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  messageRow: {
    flexDirection: 'row',
    marginBottom: 16,
    alignItems: 'flex-end',
  },
  messageRowUser: {
    justifyContent: 'flex-end',
  },
  messageRowAI: {
    justifyContent: 'flex-start',
  },
  avatarSkeleton: {
    width: 34,
    height: 34,
    borderRadius: 12,
    backgroundColor: 'rgba(0, 212, 255, 0.15)',
    marginRight: 10,
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.2)',
  },
  bubbleSkeleton: {
    height: 44,
    borderRadius: 16,
    overflow: 'hidden',
  },
  bubbleSkeletonUser: {
    backgroundColor: 'rgba(0, 212, 255, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.2)',
    borderBottomRightRadius: 4,
  },
  bubbleSkeletonAI: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderBottomLeftRadius: 4,
  },
  innerGlow: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    width: 60,
    height: 60,
    marginLeft: -30,
    marginTop: -30,
    borderRadius: 30,
    backgroundColor: 'rgba(0, 212, 255, 0.1)',
  },
});
