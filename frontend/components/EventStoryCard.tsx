/**
 * EventStoryCard Component
 * 
 * Renders an event story placeholder in the chat as a clickable card.
 * When clicked, opens EventStoryModal to view/generate the story.
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withSequence,
  withTiming,
  withSpring,
  Easing,
} from 'react-native-reanimated';
import { eventService, EventStoryPlaceholder } from '../services/eventService';

interface EventStoryCardProps {
  placeholder: EventStoryPlaceholder;
  characterName: string;
  onPress: () => void;
  isRead?: boolean;
}

const AnimatedTouchable = Animated.createAnimatedComponent(TouchableOpacity);

export default function EventStoryCard({
  placeholder,
  characterName,
  onPress,
  isRead = false,
}: EventStoryCardProps) {
  const eventInfo = eventService.getEventInfo(placeholder.event_type);
  const isGenerated = placeholder.status === 'generated';
  
  // Glow animation for pending/unread cards
  const glowOpacity = useSharedValue(0.5);
  const scale = useSharedValue(1);
  
  React.useEffect(() => {
    if (!isRead) {
      glowOpacity.value = withRepeat(
        withSequence(
          withTiming(1, { duration: 1000, easing: Easing.inOut(Easing.ease) }),
          withTiming(0.5, { duration: 1000, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        true
      );
    }
  }, [isRead]);
  
  const glowStyle = useAnimatedStyle(() => ({
    opacity: glowOpacity.value,
  }));
  
  const cardStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));
  
  const handlePressIn = () => {
    scale.value = withSpring(0.96, { damping: 15 });
  };
  
  const handlePressOut = () => {
    scale.value = withSpring(1, { damping: 10 });
  };
  
  // Gradient colors based on event type
  const getGradientColors = (): [string, string] => {
    switch (placeholder.event_type) {
      case 'first_date':
        return ['rgba(236, 72, 153, 0.3)', 'rgba(168, 85, 247, 0.3)'];
      case 'first_kiss':
        return ['rgba(244, 63, 94, 0.3)', 'rgba(251, 113, 133, 0.3)'];
      case 'first_confession':
        return ['rgba(249, 115, 22, 0.3)', 'rgba(251, 146, 60, 0.3)'];
      case 'first_nsfw':
        return ['rgba(239, 68, 68, 0.4)', 'rgba(185, 28, 28, 0.4)'];
      case 'anniversary':
        return ['rgba(234, 179, 8, 0.3)', 'rgba(250, 204, 21, 0.3)'];
      case 'reconciliation':
        return ['rgba(34, 197, 94, 0.3)', 'rgba(74, 222, 128, 0.3)'];
      default:
        return ['rgba(139, 92, 246, 0.3)', 'rgba(168, 85, 247, 0.3)'];
    }
  };
  
  const getBorderColor = () => {
    if (isRead) return 'rgba(255, 255, 255, 0.2)';
    switch (placeholder.event_type) {
      case 'first_date': return '#00D4FF';
      case 'first_kiss': return '#F43F5E';
      case 'first_confession': return '#F97316';
      case 'first_nsfw': return '#EF4444';
      case 'anniversary': return '#EAB308';
      case 'reconciliation': return '#22C55E';
      default: return '#8B5CF6';
    }
  };
  
  return (
    <View style={styles.container}>
      <AnimatedTouchable
        style={[styles.cardWrapper, cardStyle]}
        onPress={onPress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        activeOpacity={0.9}
      >
        {/* Glow effect */}
        {!isRead && (
          <Animated.View style={[styles.glowEffect, glowStyle, { borderColor: getBorderColor() }]} />
        )}
        
        <LinearGradient
          colors={getGradientColors()}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.card, { borderColor: getBorderColor() }]}
        >
          {/* Icon */}
          <View style={styles.iconContainer}>
            <Text style={styles.icon}>{eventInfo.icon}</Text>
          </View>
          
          {/* Content */}
          <View style={styles.content}>
            <Text style={styles.title}>{eventInfo.name_cn}</Text>
            <Text style={styles.subtitle}>
              {isRead ? '点击重温回忆' : (isGenerated ? '点击查看剧情' : '点击生成专属剧情')}
            </Text>
          </View>
          
          {/* Arrow / Status */}
          <View style={styles.statusContainer}>
            {isRead ? (
              <Ionicons name="checkmark-circle" size={20} color="rgba(255,255,255,0.5)" />
            ) : (
              <View style={styles.newBadge}>
                <Text style={styles.newBadgeText}>NEW</Text>
              </View>
            )}
            <Ionicons name="chevron-forward" size={20} color="rgba(255,255,255,0.7)" />
          </View>
        </LinearGradient>
      </AnimatedTouchable>
      
      {/* Description */}
      <Text style={styles.description}>
        ✨ 与{characterName}的{eventInfo.description}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    marginVertical: 16,
    paddingHorizontal: 16,
  },
  cardWrapper: {
    width: '100%',
    position: 'relative',
  },
  glowEffect: {
    position: 'absolute',
    top: -2,
    left: -2,
    right: -2,
    bottom: -2,
    borderRadius: 18,
    borderWidth: 2,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 16,
    borderRadius: 16,
    borderWidth: 1.5,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  icon: {
    fontSize: 24,
  },
  content: {
    flex: 1,
    marginLeft: 12,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 2,
  },
  subtitle: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.7)',
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  newBadge: {
    backgroundColor: '#F43F5E',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
  },
  newBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#fff',
  },
  description: {
    marginTop: 8,
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.5)',
    fontStyle: 'italic',
  },
});
