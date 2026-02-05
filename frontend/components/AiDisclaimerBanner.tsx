/**
 * AI Disclaimer Banner
 * 
 * 首次进入聊天界面时显示一次性横幅提示：
 * "所有角色均为AI虚拟角色，非真实人物"
 * 
 * 5秒后自动消失，AsyncStorage 记录已读。
 */

import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withDelay,
  Easing,
  runOnJS,
} from 'react-native-reanimated';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';

const STORAGE_KEY = '@luna_ai_disclaimer_seen';
const DISPLAY_DURATION = 4500; // ms before fade-out starts

export default function AiDisclaimerBanner() {
  const [shouldShow, setShouldShow] = useState(false);
  const opacity = useSharedValue(0);
  const translateY = useSharedValue(-40);

  useEffect(() => {
    checkIfSeen();
  }, []);

  useEffect(() => {
    if (!shouldShow) return;

    // Animate in
    opacity.value = withTiming(1, { duration: 300, easing: Easing.out(Easing.ease) });
    translateY.value = withTiming(0, { duration: 300, easing: Easing.out(Easing.ease) });

    // Animate out after delay
    opacity.value = withDelay(
      DISPLAY_DURATION,
      withTiming(0, { duration: 400 }, (finished) => {
        if (finished) runOnJS(setShouldShow)(false);
      })
    );
    translateY.value = withDelay(
      DISPLAY_DURATION,
      withTiming(-30, { duration: 400 })
    );
  }, [shouldShow]);

  const checkIfSeen = async () => {
    try {
      const seen = await AsyncStorage.getItem(STORAGE_KEY);
      if (seen !== 'true') {
        setShouldShow(true);
        await AsyncStorage.setItem(STORAGE_KEY, 'true');
      }
    } catch {
      // Silently fail
    }
  };

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: opacity.value,
    transform: [{ translateY: translateY.value }],
  }));

  if (!shouldShow) return null;

  return (
    <Animated.View style={[styles.container, animatedStyle]}>
      <View style={styles.inner}>
        <Ionicons name="information-circle" size={16} color="#8B5CF6" style={{ marginRight: 6 }} />
        <Text style={styles.text}>所有角色均为 AI 虚拟角色，非真实人物</Text>
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 56,
    left: 16,
    right: 16,
    zIndex: 100,
    alignItems: 'center',
  },
  inner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(26, 16, 37, 0.92)',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.3)',
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.2,
    shadowRadius: 12,
    elevation: 8,
  },
  text: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 13,
    fontWeight: '500',
  },
});
