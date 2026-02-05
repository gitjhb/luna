/**
 * MessageBubble Component
 * 
 * Interactive chat bubble with:
 * - Long press → elegant inline popup with Copy & Share
 * - Emoji reactions (persisted)
 * - Press feedback animation
 */

import React, { useState, useCallback, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Pressable,
  Dimensions,
  Share,
} from 'react-native';
import * as Clipboard from 'expo-clipboard';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withSequence,
  withTiming,
  runOnJS,
  Easing,
} from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { colors, radius, spacing, typography } from '../theme/designSystem';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface MessageBubbleProps {
  content: string;
  isUser: boolean;
  isLocked?: boolean;
  contentRating?: 'safe' | 'flirty' | 'spicy' | 'explicit';
  onUnlock?: () => void;
  onReaction?: (reaction: string, xpBonus: number) => void;
  onReply?: (content: string) => void;
  showToast?: (message: string) => void;
  messageReaction?: string | null;
}

export default function MessageBubble({
  content,
  isUser,
  isLocked = false,
  contentRating,
  onUnlock,
  onReaction,
  onReply,
  showToast,
  messageReaction,
}: MessageBubbleProps) {
  const [showPopup, setShowPopup] = useState(false);
  const [selectedReaction, setSelectedReaction] = useState<string | null>(messageReaction || null);
  
  // Animation values
  const scale = useSharedValue(1);
  const popupScale = useSharedValue(0);
  const popupOpacity = useSharedValue(0);
  const reactionScale = useSharedValue(1);
  
  // Bubble press animation
  const bubbleAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));
  
  // Popup animation
  const popupAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: popupScale.value }],
    opacity: popupOpacity.value,
  }));
  
  // Reaction badge animation
  const reactionAnimStyle = useAnimatedStyle(() => ({
    transform: [{ scale: reactionScale.value }],
  }));
  
  const openPopup = useCallback(() => {
    setShowPopup(true);
    popupScale.value = withSpring(1, { damping: 18, stiffness: 300 });
    popupOpacity.value = withTiming(1, { duration: 150 });
  }, []);
  
  const closePopup = useCallback(() => {
    popupOpacity.value = withTiming(0, { duration: 100, easing: Easing.in(Easing.cubic) });
    popupScale.value = withTiming(0.8, { duration: 100 }, () => {
      runOnJS(setShowPopup)(false);
    });
  }, []);
  
  // Copy
  const handleCopy = useCallback(async () => {
    try {
      await Clipboard.setStringAsync(content);
      showToast?.('已复制 ✓');
    } catch (e) {
      console.error('Copy failed:', e);
    }
    closePopup();
  }, [content, showToast, closePopup]);
  
  // Share
  const handleShare = useCallback(async () => {
    try {
      await Share.share({ message: content });
    } catch (e) {
      console.error('Share failed:', e);
    }
    closePopup();
  }, [content, closePopup]);
  
  // Long press gesture
  const longPressGesture = Gesture.LongPress()
    .minDuration(350)
    .onStart(() => {
      scale.value = withSpring(0.95, { damping: 15 });
    })
    .onEnd((_, success) => {
      scale.value = withSpring(1, { damping: 12 });
      if (success) {
        runOnJS(openPopup)();
      }
    });
  
  // Tap gesture
  const tapGesture = Gesture.Tap()
    .onBegin(() => {
      scale.value = withSpring(0.97, { damping: 15 });
    })
    .onFinalize(() => {
      scale.value = withSpring(1, { damping: 10 });
    });
  
  const composedGestures = Gesture.Simultaneous(longPressGesture, tapGesture);
  
  // Locked content
  if (isLocked) {
    return (
      <TouchableOpacity 
        style={[styles.bubble, styles.bubbleAI, styles.lockedBubble]}
        onPress={onUnlock}
        activeOpacity={0.9}
      >
        <View style={styles.blurredContent}>
          <Text style={[styles.messageText, styles.messageTextAI, { opacity: 0.3 }]}>
            {content}
          </Text>
        </View>
        <View style={styles.unlockOverlay}>
          <View style={styles.unlockBadge}>
            <Ionicons name="lock-closed" size={16} color="#fff" />
            <Text style={styles.unlockText}>
              {contentRating === 'explicit' ? '🔥' : '💕'} 升级解锁
            </Text>
          </View>
        </View>
      </TouchableOpacity>
    );
  }

  return (
    <View style={styles.wrapper}>
      <GestureDetector gesture={composedGestures}>
        <Animated.View style={[bubbleAnimatedStyle, styles.bubbleContainer]}>
          <View style={[
            styles.bubble, 
            isUser ? styles.bubbleUser : styles.bubbleAI,
          ]}>
            <Text style={[
              styles.messageText, 
              isUser ? styles.messageTextUser : styles.messageTextAI,
            ]}>
              {content}
            </Text>
            
            {/* Reaction badge */}
            {selectedReaction && (
              <Animated.View style={[styles.reactionBadge, reactionAnimStyle]}>
                <Text style={styles.reactionBadgeText}>{selectedReaction}</Text>
              </Animated.View>
            )}
          </View>
        </Animated.View>
      </GestureDetector>
      
      {/* Inline popup - 两个精致气泡 */}
      {showPopup && (
        <>
          {/* 轻触关闭 */}
          <Pressable style={styles.popupBackdrop} onPress={closePopup} />
          
          <Animated.View style={[
            styles.popupContainer,
            isUser ? styles.popupRight : styles.popupLeft,
            popupAnimatedStyle,
          ]}>
            <View style={styles.popupPill}>
              {/* 复制 */}
              <TouchableOpacity 
                style={styles.popupButton} 
                onPress={handleCopy}
                activeOpacity={0.7}
              >
                <View style={styles.popupIconCircle}>
                  <Ionicons name="copy-outline" size={18} color="#fff" />
                </View>
                <Text style={styles.popupLabel}>复制</Text>
              </TouchableOpacity>
              
              {/* 分隔线 */}
              <View style={styles.popupDivider} />
              
              {/* 分享 */}
              <TouchableOpacity 
                style={styles.popupButton} 
                onPress={handleShare}
                activeOpacity={0.7}
              >
                <View style={styles.popupIconCircle}>
                  <Ionicons name="share-outline" size={18} color="#fff" />
                </View>
                <Text style={styles.popupLabel}>分享</Text>
              </TouchableOpacity>
            </View>
            
            {/* 小三角箭头 */}
            <View style={[
              styles.popupArrow,
              isUser ? styles.popupArrowRight : styles.popupArrowLeft,
            ]} />
          </Animated.View>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    position: 'relative',
    maxWidth: SCREEN_WIDTH * 0.72,
  },
  bubbleContainer: {},
  bubble: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 18,
    position: 'relative',
  },
  bubbleUser: {
    backgroundColor: 'rgba(139, 92, 246, 0.85)',
    borderBottomRightRadius: 4,
  },
  bubbleAI: {
    backgroundColor: 'rgba(30, 20, 50, 0.85)',
    borderBottomLeftRadius: 4,
  },
  messageText: {
    fontSize: 15,
    lineHeight: 21,
  },
  messageTextUser: {
    color: '#fff',
  },
  messageTextAI: {
    color: 'rgba(255, 255, 255, 0.92)',
  },
  
  // Locked
  lockedBubble: {
    position: 'relative',
    overflow: 'hidden',
    maxWidth: SCREEN_WIDTH * 0.72,
  },
  blurredContent: {
    opacity: 0.3,
  },
  unlockOverlay: {
    position: 'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 18,
  },
  unlockBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(139, 92, 246, 0.3)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.5)',
    gap: 6,
  },
  unlockText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '600',
  },
  
  // Reaction badge
  reactionBadge: {
    position: 'absolute',
    bottom: -8,
    right: -4,
    backgroundColor: 'rgba(30, 20, 50, 0.9)',
    borderRadius: 12,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderWidth: 1.5,
    borderColor: 'rgba(139, 92, 246, 0.4)',
  },
  reactionBadgeText: {
    fontSize: 14,
  },
  
  // Popup backdrop (invisible, just for catching taps)
  popupBackdrop: {
    position: 'absolute',
    top: -500,
    left: -500,
    right: -500,
    bottom: -500,
    zIndex: 98,
  },
  
  // Popup container
  popupContainer: {
    position: 'absolute',
    top: -60,
    zIndex: 99,
  },
  popupLeft: {
    left: 0,
  },
  popupRight: {
    right: 0,
  },
  
  // Pill shape
  popupPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(60, 40, 80, 0.95)',
    borderRadius: 28,
    paddingHorizontal: 6,
    paddingVertical: 6,
    gap: 0,
    // Shadow
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 10,
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.3)',
  },
  
  // Button inside pill
  popupButton: {
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 4,
    gap: 3,
  },
  popupIconCircle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(139, 92, 246, 0.4)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  popupLabel: {
    fontSize: 10,
    fontWeight: '600',
    color: 'rgba(255, 255, 255, 0.8)',
  },
  
  // Divider
  popupDivider: {
    width: 1,
    height: 28,
    backgroundColor: 'rgba(255, 255, 255, 0.12)',
  },
  
  // Arrow pointing down to bubble
  popupArrow: {
    width: 12,
    height: 12,
    backgroundColor: 'rgba(60, 40, 80, 0.95)',
    transform: [{ rotate: '45deg' }],
    marginTop: -6,
    borderRightWidth: 1,
    borderBottomWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.3)',
  },
  popupArrowLeft: {
    marginLeft: 20,
  },
  popupArrowRight: {
    alignSelf: 'flex-end',
    marginRight: 20,
  },
});
