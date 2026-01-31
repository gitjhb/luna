/**
 * ChatBubble Component
 * 
 * Message bubble for chat interface
 */

import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Image,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { Ionicons } from '@expo/vector-icons';
import { theme, getShadow } from '../../theme/config';

interface Message {
  messageId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  type?: 'text' | 'image';
  isLocked?: boolean;
  contentRating?: 'safe' | 'flirty' | 'spicy' | 'explicit';
  unlockPrompt?: string;
  imageUrl?: string;
  createdAt: string;
}

interface ChatBubbleProps {
  message: Message;
  onUnlock?: (messageId: string) => void;
  isSpicyMode?: boolean;
}

export const ChatBubble: React.FC<ChatBubbleProps> = ({
  message,
  onUnlock,
  isSpicyMode = false,
}) => {
  const isUser = message.role === 'user';
  const accentColor = isSpicyMode ? theme.colors.accent.pink : theme.colors.primary.main;

  // Locked content - show blurred message with unlock overlay
  if (message.isLocked) {
    const rating = message.contentRating || 'spicy';
    const ratingEmoji = rating === 'explicit' ? '🔥' : rating === 'spicy' ? '💕' : '💬';
    
    return (
      <View style={[styles.container, styles.containerAssistant]}>
        <TouchableOpacity
          style={styles.lockedWrapper}
          onPress={() => onUnlock?.(message.messageId)}
          activeOpacity={0.9}
        >
          {/* Blurred content underneath */}
          <View style={[styles.bubble, styles.bubbleAssistant, styles.blurredBubble]}>
            <Text style={[styles.textAssistant, styles.blurredText]}>
              {message.content}
            </Text>
          </View>
          
          {/* Blur overlay */}
          <BlurView intensity={25} tint="dark" style={styles.blurOverlay}>
            <View style={styles.unlockContent}>
              <View style={[styles.lockedIcon, { backgroundColor: `${accentColor}20` }]}>
                <Ionicons name="lock-closed" size={20} color={accentColor} />
              </View>
              <Text style={styles.unlockText}>
                {ratingEmoji} {message.unlockPrompt || '升级订阅解锁'}
              </Text>
            </View>
          </BlurView>
        </TouchableOpacity>
      </View>
    );
  }

  if (message.type === 'image' && message.imageUrl) {
    return (
      <View style={[styles.container, styles.containerAssistant]}>
        <View style={styles.imageBubble}>
          <Image
            source={{ uri: message.imageUrl }}
            style={styles.messageImage}
            resizeMode="cover"
          />
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, isUser ? styles.containerUser : styles.containerAssistant]}>
      {isUser ? (
        <LinearGradient
          colors={theme.colors.primary.gradient}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.bubble, styles.bubbleUser]}
        >
          <Text style={styles.textUser}>{message.content}</Text>
        </LinearGradient>
      ) : (
        <View style={[styles.bubble, styles.bubbleAssistant]}>
          <Text style={styles.textAssistant}>{message.content}</Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.xs,
  },
  containerUser: {
    alignItems: 'flex-end',
  },
  containerAssistant: {
    alignItems: 'flex-start',
  },
  bubble: {
    maxWidth: '80%',
    borderRadius: theme.borderRadius.xl,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm + 2,
  },
  bubbleUser: {
    borderBottomRightRadius: theme.borderRadius.sm,
    ...getShadow('sm'),
  },
  bubbleAssistant: {
    backgroundColor: theme.colors.background.secondary,
    borderBottomLeftRadius: theme.borderRadius.sm,
  },
  textUser: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.inverse,
    lineHeight: theme.typography.fontSize.base * theme.typography.lineHeight.normal,
  },
  textAssistant: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.primary,
    lineHeight: theme.typography.fontSize.base * theme.typography.lineHeight.normal,
  },
  // Locked/blurred content styles
  lockedWrapper: {
    maxWidth: '80%',
    position: 'relative',
  },
  blurredBubble: {
    // Content is visible but will be covered by blur
  },
  blurredText: {
    // Text that will be blurred
    opacity: 0.9,
  },
  blurOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderRadius: theme.borderRadius.xl,
    overflow: 'hidden',
    justifyContent: 'center',
    alignItems: 'center',
  },
  unlockContent: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    backgroundColor: 'rgba(0,0,0,0.4)',
    borderRadius: theme.borderRadius.lg,
  },
  lockedIcon: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: theme.spacing.sm,
  },
  unlockText: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.inverse,
    fontWeight: '600',
  },
  imageBubble: {
    maxWidth: '75%',
    borderRadius: theme.borderRadius.xl,
    overflow: 'hidden',
    ...getShadow('md'),
  },
  messageImage: {
    width: 240,
    height: 240,
  },
});
