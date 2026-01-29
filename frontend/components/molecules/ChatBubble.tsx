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
import { Ionicons } from '@expo/vector-icons';
import { theme, getShadow } from '../../theme/config';

interface Message {
  messageId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  type?: 'text' | 'image';
  isLocked?: boolean;
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
  const accentColor = isSpicyMode ? theme.colors.spicy.main : theme.colors.primary.main;

  if (message.isLocked) {
    return (
      <View style={[styles.container, styles.containerAssistant]}>
        <TouchableOpacity
          style={styles.lockedBubble}
          onPress={() => onUnlock?.(message.messageId)}
          activeOpacity={0.8}
        >
          <LinearGradient
            colors={['rgba(255,255,255,0.05)', 'rgba(255,255,255,0.02)']}
            style={styles.lockedContent}
          >
            <View style={styles.lockedIcon}>
              <Ionicons name="lock-closed" size={24} color={accentColor} />
            </View>
            <Text style={styles.lockedText}>Unlock this content</Text>
            <Text style={styles.lockedSubtext}>Tap to reveal • 5 credits</Text>
          </LinearGradient>
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
  lockedBubble: {
    maxWidth: '80%',
    borderRadius: theme.borderRadius.xl,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderStyle: 'dashed',
  },
  lockedContent: {
    paddingHorizontal: theme.spacing.xl,
    paddingVertical: theme.spacing.lg,
    alignItems: 'center',
  },
  lockedIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: `${theme.colors.primary.main}15`,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  lockedText: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.primary,
    fontWeight: '600',
  },
  lockedSubtext: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.tertiary,
    marginTop: theme.spacing.xs,
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
