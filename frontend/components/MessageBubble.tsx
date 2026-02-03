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
  Share,
  ActivityIndicator,
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
  interpolate,
} from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useTheme } from '../theme/config';
import { colors, radius, spacing, typography, shadows } from '../theme/designSystem';

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
  messageReaction?: string | null; // Persisted reaction from chat history
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
  messageReaction,
}: MessageBubbleProps) {
  const { theme } = useTheme();
  const isCyberpunk = theme.id === 'cyberpunk-2077';
  const [showMenu, setShowMenu] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ x: 0, y: 0 });
  const [selectedReaction, setSelectedReaction] = useState<string | null>(messageReaction || null);
  const [isLoading, setIsLoading] = useState(false);
  const [pressedEmoji, setPressedEmoji] = useState<string | null>(null);
  
  // Animation values
  const scale = useSharedValue(1);
  const reactionScale = useSharedValue(0);
  const reactionOpacity = useSharedValue(0);
  const menuOpacity = useSharedValue(0);
  const menuScale = useSharedValue(0.9);
  
  // Bubble press animation style
  const bubbleAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));
  
  // Floating reaction animation style
  const floatingReactionStyle = useAnimatedStyle(() => ({
    transform: [{ scale: reactionScale.value }],
    opacity: reactionOpacity.value,
  }));
  
  // Menu animation style - elegant fade + subtle scale, no bouncing
  const menuAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: menuScale.value }],
    opacity: menuOpacity.value,
  }));
  
  // Open menu with elegant animation (no bouncing)
  const openMenu = useCallback(() => {
    setIsLoading(true);
    setShowMenu(true);
    menuScale.value = 0.9;
    menuOpacity.value = 0;
    
    // Small delay for loading effect
    setTimeout(() => {
      setIsLoading(false);
      menuScale.value = withTiming(1, { duration: 200, easing: Easing.out(Easing.cubic) });
      menuOpacity.value = withTiming(1, { duration: 180, easing: Easing.out(Easing.cubic) });
    }, 150);
  }, [menuScale, menuOpacity]);
  
  // Close menu with elegant fade out
  const closeMenu = useCallback(() => {
    menuOpacity.value = withTiming(0, { duration: 120, easing: Easing.in(Easing.cubic) });
    menuScale.value = withTiming(0.95, { duration: 120, easing: Easing.in(Easing.cubic) }, () => {
      runOnJS(setShowMenu)(false);
    });
  }, [menuScale, menuOpacity]);
  
  // Handle copy text
  const handleCopy = useCallback(async () => {
    try {
      await Clipboard.setStringAsync(content);
      showToast?.('已复制到剪贴板 ✓');
      closeMenu();
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  }, [content, showToast, closeMenu]);
  
  // Handle reaction selection with visual feedback
  const handleReaction = useCallback((reaction: typeof REACTIONS[0]) => {
    // Visual feedback - mark as pressed
    setPressedEmoji(reaction.emoji);
    
    // Short delay to show press state
    setTimeout(() => {
      setSelectedReaction(reaction.emoji);
      closeMenu();
      
      // Animate floating reaction
      reactionScale.value = 0;
      reactionOpacity.value = 1;
      reactionScale.value = withSequence(
        withTiming(1.3, { duration: 150, easing: Easing.out(Easing.cubic) }),
        withTiming(1, { duration: 100 })
      );
      
      // Callback for XP bonus - this should update chat history
      onReaction?.(reaction.name, reaction.xpBonus);
      
      setPressedEmoji(null);
    }, 100);
  }, [onReaction, reactionScale, reactionOpacity, closeMenu]);
  
  // Handle reply
  const handleReply = useCallback(() => {
    closeMenu();
    onReply?.(content);
  }, [content, onReply, closeMenu]);
  
  // Handle share to social media
  const handleShare = useCallback(async () => {
    try {
      const result = await Share.share({
        message: content,
        // For X/Twitter sharing on iOS
      });
      
      if (result.action === Share.sharedAction) {
        showToast?.('已分享 ✓');
      }
      closeMenu();
    } catch (error) {
      console.error('Share failed:', error);
      showToast?.('分享失败');
    }
  }, [content, showToast, closeMenu]);
  
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
            
            {/* Persisted reaction indicator (shows permanently) */}
            {selectedReaction && (
              <View style={[
                styles.reactionBadge,
                { borderColor: theme.colors.background.primary }
              ]}>
                <Animated.Text style={[styles.reactionBadgeText, floatingReactionStyle]}>
                  {selectedReaction}
                </Animated.Text>
              </View>
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
            {/* Loading indicator */}
            {isLoading && (
              <View style={styles.loadingContainer}>
                <ActivityIndicator size="small" color={theme.colors.primary.main} />
              </View>
            )}
            
            {/* Reaction Bar */}
            {!isLoading && (
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
                      },
                      // Press feedback - scale and glow effect
                      pressedEmoji === reaction.emoji && {
                        transform: [{ scale: 1.2 }],
                        backgroundColor: 'rgba(0, 240, 255, 0.25)',
                        borderColor: theme.colors.primary.main,
                      },
                      // Currently selected reaction
                      selectedReaction === reaction.emoji && {
                        backgroundColor: 'rgba(255, 42, 109, 0.2)',
                        borderColor: theme.colors.accent.pink,
                      }
                    ]}
                    onPress={() => handleReaction(reaction)}
                    activeOpacity={0.7}
                  >
                    <Text style={[
                      styles.reactionEmoji,
                      pressedEmoji === reaction.emoji && { transform: [{ scale: 1.1 }] }
                    ]}>{reaction.emoji}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            )}
            
            {/* Menu Actions */}
            {!isLoading && (
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
                
                {/* Share button */}
                <TouchableOpacity style={[
                  styles.menuItem,
                  isCyberpunk && { backgroundColor: 'rgba(0, 240, 255, 0.08)' }
                ]} onPress={handleShare}>
                  <Ionicons name="share-social-outline" size={20} color={isCyberpunk ? theme.colors.primary.main : '#fff'} />
                  <Text style={[styles.menuItemText, isCyberpunk && { color: theme.colors.primary.main }]}>分享</Text>
                </TouchableOpacity>
                
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
            )}
            
            {/* Preview of message */}
            {!isLoading && (
              <View style={[styles.previewContainer, { borderTopColor: theme.colors.border }]}>
                <Text style={[styles.previewText, { color: theme.colors.text.tertiary }]} numberOfLines={2}>
                  {content}
                </Text>
              </View>
            )}
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
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radius.xl,
    position: 'relative',
  },
  bubbleUser: {
    backgroundColor: 'rgba(0, 240, 255, 0.12)',
    borderBottomRightRadius: radius.sm,
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.2)',
  },
  bubbleAI: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderBottomLeftRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border.default,
  },
  messageText: {
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.relaxed,
    color: colors.text.primary,
  },
  messageTextUser: {
    color: colors.text.primary,
  },
  messageTextAI: {
    color: 'rgba(255, 255, 255, 0.92)',
  },
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
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: radius.xl,
  },
  unlockBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(139, 92, 246, 0.3)',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.full,
    borderWidth: 1,
    borderColor: colors.secondary.glow,
    gap: spacing.sm,
  },
  unlockText: {
    color: colors.text.primary,
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  // Reaction badge
  reactionBadge: {
    position: 'absolute',
    bottom: -8,
    right: -8,
    backgroundColor: colors.background.elevated,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderWidth: 2,
    borderColor: colors.border.accent,
  },
  reactionBadgeText: {
    fontSize: 14,
  },
  // Menu overlay
  menuOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  // Loading container
  loadingContainer: {
    paddingVertical: spacing.xl,
    alignItems: 'center',
    justifyContent: 'center',
  },
  menuContainer: {
    padding: spacing.lg,
    width: SCREEN_WIDTH * 0.85,
    maxWidth: 360,
    backgroundColor: colors.background.elevated,
    borderRadius: radius.xl,
    borderWidth: 1,
    borderColor: colors.border.default,
    ...shadows.lg,
  },
  // Reaction bar
  reactionBar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.default,
    marginBottom: spacing.md,
  },
  reactionButton: {
    width: 46,
    height: 46,
    borderRadius: radius.lg,
    backgroundColor: 'rgba(0, 240, 255, 0.08)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'transparent',
  },
  reactionEmoji: {
    fontSize: 24,
  },
  // Menu actions
  menuActions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },
  menuItem: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.sm,
    backgroundColor: 'rgba(0, 240, 255, 0.06)',
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border.default,
    gap: spacing.sm,
  },
  menuItemText: {
    color: colors.text.secondary,
    fontSize: typography.size.xs,
    fontWeight: typography.weight.medium,
  },
  // Preview
  previewContainer: {
    marginTop: spacing.md,
    paddingTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border.default,
  },
  previewText: {
    fontSize: typography.size.sm,
    fontStyle: 'italic',
    color: colors.text.tertiary,
  },
});
