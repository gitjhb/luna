/**
 * ChatBubble Component
 * 
 * Flexible chat bubble supporting:
 * - Text and image messages
 * - Locked/blurred content with unlock overlay
 * - User vs Assistant styling
 * - Timestamps
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import { theme } from '../../theme/config';
import { Ionicons } from '@expo/vector-icons';
import { format } from 'date-fns';

interface ChatBubbleProps {
  message: {
    messageId: string;
    role: 'user' | 'assistant';
    content: string;
    type?: 'text' | 'image';
    isLocked?: boolean;
    imageUrl?: string;
    createdAt: string;
  };
  onUnlock?: (messageId: string) => void;
  isSpicyMode?: boolean;
}

export const ChatBubble: React.FC<ChatBubbleProps> = ({
  message,
  onUnlock,
  isSpicyMode = false,
}) => {
  const [imageLoading, setImageLoading] = useState(true);
  const [unlocking, setUnlocking] = useState(false);

  const isUser = message.role === 'user';
  const isImage = message.type === 'image';
  const isLocked = message.isLocked && isImage;

  const handleUnlock = async () => {
    if (!onUnlock || unlocking) return;
    
    setUnlocking(true);
    try {
      await onUnlock(message.messageId);
    } finally {
      setUnlocking(false);
    }
  };

  const bubbleColor = isUser
    ? isSpicyMode
      ? theme.colors.spicy.main
      : theme.colors.primary.main
    : theme.colors.background.secondary;

  const textColor = isUser
    ? theme.colors.text.inverse
    : theme.colors.text.primary;

  return (
    <View style={[styles.container, isUser && styles.userContainer]}>
      <View style={[styles.bubble, { backgroundColor: bubbleColor }]}>
        {/* Text Message */}
        {!isImage && (
          <Text style={[styles.text, { color: textColor }]}>
            {message.content}
          </Text>
        )}

        {/* Image Message */}
        {isImage && message.imageUrl && (
          <View style={styles.imageContainer}>
            <Image
              source={{ uri: message.imageUrl }}
              style={styles.image}
              resizeMode="cover"
              onLoadStart={() => setImageLoading(true)}
              onLoadEnd={() => setImageLoading(false)}
            />

            {/* Loading Indicator */}
            {imageLoading && (
              <View style={styles.imageLoading}>
                <ActivityIndicator size="large" color={theme.colors.primary.main} />
              </View>
            )}

            {/* Locked Overlay */}
            {isLocked && !imageLoading && (
              <BlurView intensity={80} style={styles.blurOverlay}>
                <TouchableOpacity
                  style={styles.unlockButton}
                  onPress={handleUnlock}
                  disabled={unlocking}
                  activeOpacity={0.8}
                >
                  <LinearGradient
                    colors={
                      isSpicyMode
                        ? theme.colors.spicy.gradient
                        : theme.colors.primary.gradient
                    }
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.unlockButtonGradient}
                  >
                    {unlocking ? (
                      <ActivityIndicator size="small" color={theme.colors.text.inverse} />
                    ) : (
                      <>
                        <Ionicons
                          name="lock-open"
                          size={24}
                          color={theme.colors.text.inverse}
                        />
                        <Text style={styles.unlockButtonText}>Tap to Unlock</Text>
                        <Text style={styles.unlockCostText}>5 credits</Text>
                      </>
                    )}
                  </LinearGradient>
                </TouchableOpacity>

                {/* Warning Text */}
                <Text style={styles.warningText}>
                  This content may be explicit
                </Text>
              </BlurView>
            )}
          </View>
        )}

        {/* Timestamp */}
        <Text style={[styles.timestamp, { color: isUser ? 'rgba(255,255,255,0.7)' : theme.colors.text.tertiary }]}>
          {format(new Date(message.createdAt), 'HH:mm')}
        </Text>
      </View>

      {/* Spicy Mode Indicator (for assistant messages) */}
      {!isUser && isSpicyMode && (
        <View style={styles.spicyIndicator}>
          <Ionicons name="flame" size={12} color={theme.colors.spicy.main} />
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    marginVertical: theme.spacing.xs,
    paddingHorizontal: theme.spacing.md,
    alignItems: 'flex-end',
  },
  userContainer: {
    justifyContent: 'flex-end',
  },
  bubble: {
    maxWidth: '75%',
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    shadowColor: theme.colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  text: {
    fontFamily: theme.typography.fontFamily.regular,
    fontSize: theme.typography.fontSize.base,
    lineHeight: theme.typography.fontSize.base * theme.typography.lineHeight.normal,
  },
  timestamp: {
    fontFamily: theme.typography.fontFamily.regular,
    fontSize: theme.typography.fontSize.xs,
    marginTop: theme.spacing.xs,
  },
  imageContainer: {
    width: 250,
    height: 250,
    borderRadius: theme.borderRadius.md,
    overflow: 'hidden',
    backgroundColor: theme.colors.background.tertiary,
  },
  image: {
    width: '100%',
    height: '100%',
  },
  imageLoading: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.background.tertiary,
  },
  blurOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    padding: theme.spacing.lg,
  },
  unlockButton: {
    borderRadius: theme.borderRadius.lg,
    overflow: 'hidden',
    marginBottom: theme.spacing.md,
  },
  unlockButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: theme.spacing.md,
    paddingHorizontal: theme.spacing.lg,
    gap: theme.spacing.sm,
  },
  unlockButtonText: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.inverse,
  },
  unlockCostText: {
    fontFamily: theme.typography.fontFamily.medium,
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.inverse,
    opacity: 0.8,
  },
  warningText: {
    fontFamily: theme.typography.fontFamily.medium,
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.text.secondary,
    textAlign: 'center',
  },
  spicyIndicator: {
    marginLeft: theme.spacing.xs,
    marginBottom: theme.spacing.xs,
  },
});
