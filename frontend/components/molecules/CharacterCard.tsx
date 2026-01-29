/**
 * CharacterCard Component
 * 
 * Card displaying character information.
 */

import React from 'react';
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  Dimensions,
  StyleSheet,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { theme, getShadow } from '../../theme/config';
import { Character } from '../../types';
import { Ionicons } from '@expo/vector-icons';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = SCREEN_WIDTH * 0.85;

interface CharacterCardProps {
  character: Character;
  onPress: () => void;
  isLocked?: boolean;
}

export const CharacterCard: React.FC<CharacterCardProps> = ({
  character,
  onPress,
  isLocked = false,
}) => {
  return (
    <View style={styles.container}>
      <View style={styles.card}>
        {/* Character Image */}
        <Image
          source={{ uri: character.avatarUrl }}
          style={styles.image}
          resizeMode="cover"
        />

        {/* Gradient Overlay */}
        <LinearGradient
          colors={['transparent', 'rgba(0,0,0,0.8)']}
          style={styles.gradient}
        />

        {/* Premium Badge */}
        {isLocked && (
          <View style={styles.premiumBadge}>
            <Ionicons name="lock-closed" size={12} color={theme.colors.text.inverse} />
            <Text style={styles.premiumText}>PREMIUM</Text>
          </View>
        )}

        {/* Spicy Badge */}
        {character.isSpicy && (
          <View style={styles.spicyBadge}>
            <Ionicons name="flame" size={14} color="#FF6B6B" />
          </View>
        )}

        {/* Character Info */}
        <View style={styles.infoContainer}>
          <Text style={styles.name}>{character.name}</Text>
          <Text style={styles.description} numberOfLines={2}>
            {character.description}
          </Text>

          {/* Tags */}
          <View style={styles.tagsContainer}>
            {character.tags.slice(0, 3).map((tag, index) => (
              <View key={index} style={styles.tag}>
                <Text style={styles.tagText}>{tag}</Text>
              </View>
            ))}
          </View>

          {/* Chat Now Button */}
          <TouchableOpacity
            style={styles.chatButton}
            onPress={onPress}
            activeOpacity={0.8}
          >
            <LinearGradient
              colors={theme.colors.primary.gradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.chatButtonGradient}
            >
              <Text style={styles.chatButtonText}>
                {isLocked ? 'Unlock' : 'Chat Now'}
              </Text>
              <Ionicons
                name={isLocked ? 'lock-closed' : 'chatbubble-ellipses'}
                size={20}
                color={theme.colors.text.inverse}
              />
            </LinearGradient>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: CARD_WIDTH,
    alignSelf: 'center',
  },
  card: {
    width: '100%',
    height: 420,
    borderRadius: theme.borderRadius.xl,
    overflow: 'hidden',
    backgroundColor: theme.colors.background.secondary,
    ...getShadow('xl'),
  },
  image: {
    width: '100%',
    height: '100%',
    position: 'absolute',
  },
  gradient: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: '60%',
  },
  premiumBadge: {
    position: 'absolute',
    top: theme.spacing.md,
    right: theme.spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.primary.main,
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
    borderRadius: theme.borderRadius.full,
    gap: 4,
  },
  premiumText: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.text.inverse,
  },
  spicyBadge: {
    position: 'absolute',
    top: theme.spacing.md,
    left: theme.spacing.md,
    backgroundColor: 'rgba(255, 107, 107, 0.2)',
    padding: theme.spacing.sm,
    borderRadius: theme.borderRadius.full,
  },
  infoContainer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: theme.spacing.lg,
  },
  name: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize['2xl'],
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.xs,
  },
  description: {
    fontFamily: theme.typography.fontFamily.regular,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
    lineHeight: theme.typography.fontSize.base * theme.typography.lineHeight.normal,
    marginBottom: theme.spacing.md,
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.xs,
    marginBottom: theme.spacing.md,
  },
  tag: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
    borderRadius: theme.borderRadius.full,
  },
  tagText: {
    fontFamily: theme.typography.fontFamily.medium,
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.text.secondary,
  },
  chatButton: {
    borderRadius: theme.borderRadius.lg,
    overflow: 'hidden',
  },
  chatButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: theme.spacing.md,
    gap: theme.spacing.sm,
  },
  chatButtonText: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize.lg,
    color: theme.colors.text.inverse,
  },
});
