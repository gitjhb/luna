/**
 * MessageBubble Component
 * 
 * Interactive chat bubble with:
 * - Long press to show context menu
 * - Copy text functionality
 * - Emoji reactions with animations
 * - Press feedback animation
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  Pressable,
  Dimensions,
  Platform,
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
import { LinearGradient } from 'expo-linear-gradient';
import { useTheme } from '../theme/config';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Emoji reactions configuration
const REACTIONS = [
  { emoji: '❤️', name: 'love', xpBonus: 2 },
  { emoji: '😂', name: 'haha', xpBonus: 1 },
  { emoji: '😍', name: 'wow', xpBonus: 2 },
  { emoji: '😢', name: 'sad', xpBonus: 1 },
  { emoji: '👍', name: 'like', xpBonus: 1 },
  { emoji: '🔥', name: 'fire', xpBonus: 3 },
];

interface MessageBubbleProps {
  content: string;
  isUser: boolean;
  isLocked?: boolean;
  contentRating?: 'safe' | 'flirty' | 'spicy' | 'explicit';
  onUnlock?: () => void;
  onReaction?: (reaction: string, xpBonus: number) => void;
  onReply?: (content: string) => void;
  showToast?: (message: string) => void;
}

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export default function MessageBubble({
  content,
  isUser,
  isLocked = false,
  contentRating,
  onUnlock,
  onReaction,
  onReply,
  showToast,
}: MessageBubbleProps) {
  const { theme } = useTheme();
  const isCyberpunk = theme.id === 'cyberpunk-2077';
  const [showMenu, setShowMenu] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ x: 0, y: 0 });
  const [selectedReaction, setSelectedReaction] = useState<string | null>(null);
  
  // Animation values
  const scale = useSharedValue(1);
  const reactionScale = useSharedValue(0);
  const reactionOpacity = useSharedValue(0);
  const menuScale = useSharedValue(0);
  
  // Bubble press animation style
  const bubbleAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));
  
  // Floating reaction animation style
  const floatingReactionStyle = useAnimatedStyle(() => ({
    transform: [{ scale: reactionScale.value }],
    opacity: reactionOpacity.value,
  }));
  
  // Menu animation style
  const menuAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: menuScale.value }],
    opacity: menuScale.value,
  }));
  
  // Handle copy text
  const handleCopy = useCallback(async () => {
    try {
      await Clipboard.setStringAsync(content);
      showToast?.('已复制到剪贴板 ✓');
      setShowMenu(false);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  }, [content, showToast]);
  
  // Handle reaction selection
  const handleReaction = useCallback((reaction: typeof REACTIONS[0]) => {
    setSelectedReaction(reaction.emoji);
    setShowMenu(false);
    
    // Animate floating reaction
    reactionScale.value = 0;
    reactionOpacity.value = 1;
    reactionScale.value = withSequence(
      withSpring(1.5, { damping: 8, stiffness: 200 }),
      withTiming(1, { duration: 200 })
    );
    
    // Float up and fade out
    setTimeout(() => {
      reactionOpacity.value = withTiming(0, { duration: 500 });
    }, 800);
    
    // Clear reaction after animation
    setTimeout(() => {
      setSelectedReaction(null);
    }, 1500);
    
    // Callback for XP bonus
    onReaction?.(reaction.name, reaction.xpBonus);
  }, [onReaction, reactionScale, reactionOpacity]);
  
  // Handle reply
  const handleReply = useCallback(() => {
    setShowMenu(false);
    onReply?.(content);
  }, [content, onReply]);
  
  // Open menu with animation
  const openMenu = useCallback(() => {
    setShowMenu(true);
    menuScale.value = 0;
    menuScale.value = withSpring(1, { damping: 12, stiffness: 200 });
  }, [menuScale]);
  
  // Close menu
  const closeMenu = useCallback(() => {
    menuScale.value = withTiming(0, { duration: 150 }, () => {
      runOnJS(setShowMenu)(false);
    });
  }, [menuScale]);
  
  // Long press gesture for menu
  const longPressGesture = Gesture.LongPress()
    .minDuration(400)
    .onStart(() => {
      // Scale down slightly
      scale.value = withSpring(0.95, { damping: 15 });
    })
    .onEnd((_, success) => {
      scale.value = withSpring(1, { damping: 10 });
      if (success) {
        runOnJS(openMenu)();
      }
    });
  
  // Tap gesture for press feedback
  const tapGesture = Gesture.Tap()
    .onBegin(() => {
      scale.value = withSpring(0.97, { damping: 15 });
    })
    .onFinalize(() => {
      scale.value = withSpring(1, { damping: 10 });
    });
  
  // Combine gestures
  const composedGestures = Gesture.Simultaneous(longPressGesture, tapGesture);
  
  // Locked content render
  if (isLocked) {
    return (
      <TouchableOpacity 
        style={[styles.bubble, styles.bubbleAI, styles.lockedBubble]}
        onPress={onUnlock}
        activeOpacity={0.9}
      >
        <View style={styles.blurredContent}>
          <Text style={[styles.messageText, styles.messageTextAI, styles.blurredText]}>
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
  
  // Dynamic bubble styles based on theme
  const bubbleUserStyle = isCyberpunk ? {
    backgroundColor: 'rgba(0, 240, 255, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.3)',
    borderRadius: theme.borderRadius.md,
    shadowColor: '#00F0FF',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
  } : {
    backgroundColor: 'rgba(255, 255, 255, 0.18)',
  };

  const bubbleAIStyle = isCyberpunk ? {
    backgroundColor: 'rgba(255, 42, 109, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(255, 42, 109, 0.25)',
    borderRadius: theme.borderRadius.md,
    shadowColor: '#FF2A6D',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
  } : {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
  };

  const textUserStyle = isCyberpunk ? {
    color: '#00F0FF',
    textShadowColor: 'rgba(0, 240, 255, 0.5)',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 4,
  } : {
    color: '#fff',
  };

  const textAIStyle = isCyberpunk ? {
    color: 'rgba(255, 255, 255, 0.95)',
  } : {
    color: 'rgba(255, 255, 255, 0.92)',
  };

  return (
    <>
      <GestureDetector gesture={composedGestures}>
        <Animated.View style={[bubbleAnimatedStyle, styles.bubbleContainer]}>
          <View style={[
            styles.bubble, 
            isUser ? [styles.bubbleUser, bubbleUserStyle] : [styles.bubbleAI, bubbleAIStyle]
          ]}>
            <Text style={[
              styles.messageText, 
              isUser ? [styles.messageTextUser, textUserStyle] : [styles.messageTextAI, textAIStyle]
            ]}>
              {content}
            </Text>
            
            {/* Selected reaction indicator */}
            {selectedReaction && (
              <Animated.View style={[
                styles.reactionBadge, 
                floatingReactionStyle,
                { borderColor: theme.colors.background.primary }
              ]}>
                <Text style={styles.reactionBadgeText}>{selectedReaction}</Text>
              </Animated.View>
            )}
          </View>
        </Animated.View>
      </GestureDetector>
      
      {/* Context Menu Modal */}
      <Modal
        visible={showMenu}
        transparent
        animationType="none"
        onRequestClose={closeMenu}
      >
        <Pressable style={styles.menuOverlay} onPress={closeMenu}>
          <Animated.View style={[
            styles.menuContainer, 
            menuAnimatedStyle,
            { 
              backgroundColor: theme.colors.background.secondary,
              borderRadius: theme.borderRadius.xl,
              ...(isCyberpunk && {
                borderWidth: 1,
                borderColor: theme.colors.border,
                shadowColor: theme.colors.glow,
                shadowOpacity: 0.4,
                shadowRadius: 15,
              })
            }
          ]}>
            {/* Reaction Bar */}
            <View style={[styles.reactionBar, { borderBottomColor: theme.colors.border }]}>
              {REACTIONS.map((reaction) => (
                <TouchableOpacity
                  key={reaction.name}
                  style={[
                    styles.reactionButton,
                    isCyberpunk && {
                      backgroundColor: 'rgba(0, 240, 255, 0.1)',
                      borderWidth: 1,
                      borderColor: 'rgba(0, 240, 255, 0.2)',
                    }
                  ]}
                  onPress={() => handleReaction(reaction)}
                  activeOpacity={0.7}
                >
                  <Text style={styles.reactionEmoji}>{reaction.emoji}</Text>
                </TouchableOpacity>
              ))}
            </View>
            
            {/* Menu Actions */}
            <View style={styles.menuActions}>
              <TouchableOpacity style={[
                styles.menuItem,
                isCyberpunk && { backgroundColor: 'rgba(0, 240, 255, 0.08)' }
              ]} onPress={handleCopy}>
                <Ionicons name="copy-outline" size={20} color={isCyberpunk ? theme.colors.primary.main : '#fff'} />
                <Text style={[styles.menuItemText, isCyberpunk && { color: theme.colors.primary.main }]}>复制</Text>
              </TouchableOpacity>
              
              {!isUser && onReply && (
                <TouchableOpacity style={[
                  styles.menuItem,
                  isCyberpunk && { backgroundColor: 'rgba(0, 240, 255, 0.08)' }
                ]} onPress={handleReply}>
                  <Ionicons name="arrow-undo-outline" size={20} color={isCyberpunk ? theme.colors.primary.main : '#fff'} />
                  <Text style={[styles.menuItemText, isCyberpunk && { color: theme.colors.primary.main }]}>回复</Text>
                </TouchableOpacity>
              )}
              
              {!isUser && (
                <TouchableOpacity 
                  style={[
                    styles.menuItem,
                    isCyberpunk && { backgroundColor: 'rgba(255, 42, 109, 0.12)' }
                  ]} 
                  onPress={() => {
                    handleReaction({ emoji: '❤️', name: 'love', xpBonus: 2 });
                  }}
                >
                  <Ionicons name="heart-outline" size={20} color={theme.colors.accent.pink} />
                  <Text style={[styles.menuItemText, { color: theme.colors.accent.pink }]}>喜欢</Text>
                </TouchableOpacity>
              )}
            </View>
            
            {/* Preview of message */}
            <View style={[styles.previewContainer, { borderTopColor: theme.colors.border }]}>
              <Text style={[styles.previewText, { color: theme.colors.text.tertiary }]} numberOfLines={2}>
                {content}
              </Text>
            </View>
          </Animated.View>
        </Pressable>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  bubbleContainer: {
    maxWidth: SCREEN_WIDTH * 0.72,
  },
  bubble: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 18,
    position: 'relative',
  },
  bubbleUser: {
    borderBottomRightRadius: 4,
  },
  bubbleAI: {
    borderBottomLeftRadius: 4,
  },
  messageText: {
    fontSize: 15,
    lineHeight: 21,
  },
  messageTextUser: {},
  messageTextAI: {},
  // Locked styles
  lockedBubble: {
    position: 'relative',
    overflow: 'hidden',
    maxWidth: SCREEN_WIDTH * 0.72,
  },
  blurredContent: {
    opacity: 0.3,
  },
  blurredText: {},
  unlockOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 16,
  },
  unlockBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.15)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
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
    right: -8,
    backgroundColor: 'rgba(0,0,0,0.6)',
    borderRadius: 12,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderWidth: 2,
  },
  reactionBadgeText: {
    fontSize: 14,
  },
  // Menu overlay
  menuOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  menuContainer: {
    padding: 16,
    width: SCREEN_WIDTH * 0.85,
    maxWidth: 360,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.5,
    shadowRadius: 20,
    elevation: 20,
  },
  // Reaction bar
  reactionBar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 12,
    borderBottomWidth: 1,
    marginBottom: 12,
  },
  reactionButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255,255,255,0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  reactionEmoji: {
    fontSize: 24,
  },
  // Menu actions
  menuActions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 8,
    gap: 8,
  },
  menuItem: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 8,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 12,
    gap: 6,
  },
  menuItemText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '500',
  },
  // Preview
  previewContainer: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
  },
  previewText: {
    fontSize: 13,
    fontStyle: 'italic',
  },
});
