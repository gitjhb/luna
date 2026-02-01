/**
 * Character Profile Screen - Settings Style
 * Shows character details with settings-style sections
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  Dimensions,
  ActivityIndicator,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { theme } from '../../theme/config';
import { characterService } from '../../services/characterService';
import { intimacyService } from '../../services/intimacyService';
import { emotionService, EmotionStatus, EMOTION_DISPLAY } from '../../services/emotionService';
import { Character, IntimacyStatus } from '../../types';
import { getCharacterAvatar, getCharacterBackground } from '../../assets/characters';
import { useUserStore } from '../../store/userStore';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// ============================================================================
// Settings-style Components
// ============================================================================

interface ProfileItemProps {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  value?: string;
  subtitle?: string;
  iconColor?: string;
}

const ProfileItem = ({ icon, title, value, subtitle, iconColor }: ProfileItemProps) => (
  <View style={styles.profileItem}>
    <View style={[styles.profileIcon, iconColor && { backgroundColor: iconColor + '20' }]}>
      <Ionicons name={icon} size={20} color={iconColor || theme.colors.primary.main} />
    </View>
    <View style={styles.profileContent}>
      <Text style={styles.profileTitle}>{title}</Text>
      {subtitle && <Text style={styles.profileSubtitle}>{subtitle}</Text>}
    </View>
    {value && <Text style={styles.profileValue}>{value}</Text>}
  </View>
);

interface ProfileSectionProps {
  title: string;
  children: React.ReactNode;
}

const ProfileSection = ({ title, children }: ProfileSectionProps) => (
  <View style={styles.section}>
    <Text style={styles.sectionTitle}>{title}</Text>
    <View style={styles.sectionContent}>{children}</View>
  </View>
);

// ============================================================================
// Main Component
// ============================================================================

export default function CharacterProfileScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ characterId: string }>();
  const isVip = useUserStore((s) => s.isVip);
  
  const [character, setCharacter] = useState<Character | null>(null);
  const [intimacy, setIntimacy] = useState<IntimacyStatus | null>(null);
  const [emotion, setEmotion] = useState<EmotionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAvatarModal, setShowAvatarModal] = useState(false);
  const [stats, setStats] = useState<{
    streakDays: number;
    totalMessages: number;
    totalGifts: number;
    specialEvents: number;
    daysKnown: number;
  }>({
    streakDays: 0,
    totalMessages: 0,
    totalGifts: 0,
    specialEvents: 0,
    daysKnown: 0,
  });

  useEffect(() => {
    loadData();
  }, [params.characterId]);

  const loadData = async () => {
    try {
      // Load character from API
      const characterData = await characterService.getCharacter(params.characterId);
      setCharacter(characterData);
      
      // Load intimacy status
      try {
        const intimacyStatus = await intimacyService.getStatus(params.characterId);
        setIntimacy(intimacyStatus);
        setStats(prev => ({
          ...prev,
          streakDays: intimacyStatus.streakDays || 0,
          totalMessages: intimacyStatus.totalMessages || 0,
          totalGifts: intimacyStatus.giftsCount || 0,
          specialEvents: intimacyStatus.specialEvents || 0,
        }));
        
        // Calculate days known from first interaction
        if (intimacyStatus.lastInteractionDate) {
          const firstDay = new Date(intimacyStatus.lastInteractionDate);
          const today = new Date();
          const diffDays = Math.floor((today.getTime() - firstDay.getTime()) / (1000 * 60 * 60 * 24));
          setStats(prev => ({ ...prev, daysKnown: Math.max(1, diffDays) }));
        }
      } catch (e) {
        setIntimacy({ currentLevel: 1, streakDays: 0, dailyXpEarned: 0, totalXp: 0, progressPercent: 0, xpProgressInLevel: 0, xpForNextLevel: 100, stageNameCn: '陌生人' } as IntimacyStatus);
      }

      // Load emotion status
      try {
        const emotionStatus = await emotionService.getStatus(params.characterId);
        setEmotion(emotionStatus);
      } catch (e) {
        setEmotion(null);
      }
      
      // Load stats from backend
      try {
        const { api } = await import('../../services/api');
        const statsData = await api.get<any>(`/characters/${params.characterId}/stats`);
        setStats(prev => ({
          ...prev,
          streakDays: statsData.streak_days || prev.streakDays,
          totalMessages: statsData.total_messages || prev.totalMessages,
          totalGifts: statsData.total_gifts || prev.totalGifts,
          specialEvents: statsData.special_events || prev.specialEvents,
        }));
      } catch (e) {
        console.log('Stats not available');
      }
    } catch (error) {
      console.error('Failed to load character profile:', error);
    } finally {
      setLoading(false);
    }
  };

  const currentLevel = intimacy?.currentLevel || 1;
  
  // Get intimacy stage name
  const getStageName = (level: number): string => {
    if (level <= 3) return '👋 初识';
    if (level <= 10) return '😊 熟悉';
    if (level <= 25) return '💛 好友';
    if (level <= 40) return '💕 亲密';
    return '❤️ 挚爱';
  };

  if (loading || !character) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={theme.colors.primary.main} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Background */}
      <Image 
        source={getCharacterBackground(character.characterId, character.backgroundUrl || character.avatarUrl)} 
        style={styles.backgroundImage}
        blurRadius={25}
      />
      <LinearGradient
        colors={['transparent', 'rgba(26,16,37,0.85)', 'rgba(26,16,37,1)']}
        style={styles.backgroundOverlay}
      />

      <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>角色资料</Text>
          <View style={styles.headerRight} />
        </View>

        <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
          {/* Large Avatar & Name */}
          <View style={styles.avatarSection}>
            <TouchableOpacity onPress={() => setShowAvatarModal(true)} activeOpacity={0.9}>
              <Image 
                source={getCharacterAvatar(character.characterId, character.avatarUrl)} 
                style={styles.largeAvatar} 
              />
            </TouchableOpacity>
            <Text style={styles.characterName}>{character.name}</Text>
            {character.occupation && (
              <Text style={styles.occupation}>{character.occupation}</Text>
            )}
            
            {/* Intimacy Level Badge */}
            <View style={styles.levelBadge}>
              <Ionicons name="heart" size={16} color="#EC4899" />
              <Text style={styles.levelText}>Lv.{currentLevel}</Text>
              <Text style={styles.stageText}>{getStageName(currentLevel)}</Text>
            </View>
            
            {/* Personality Tags */}
            <View style={styles.tagsContainer}>
              {character.personalityTraits.slice(0, 4).map((trait, index) => (
                <View key={index} style={styles.tag}>
                  <Text style={styles.tagText}>{trait}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* Description */}
          <ProfileSection title="简介">
            <View style={styles.descriptionCard}>
              <Text style={styles.descriptionText}>{character.description}</Text>
            </View>
          </ProfileSection>

          {/* Basic Info */}
          <ProfileSection title="基本信息">
            {character.age && (
              <ProfileItem icon="calendar-outline" title="年龄" value={`${character.age}岁`} />
            )}
            {character.birthday && (
              <ProfileItem icon="gift-outline" title="生日" value={character.birthday} iconColor="#FF6B6B" />
            )}
            {character.zodiac && (
              <ProfileItem icon="star-outline" title="星座" value={character.zodiac} iconColor="#FFD700" />
            )}
            {character.height && (
              <ProfileItem icon="resize-outline" title="身高" value={character.height} />
            )}
            {character.location && (
              <ProfileItem icon="location-outline" title="所在地" value={character.location} iconColor="#4ECDC4" />
            )}
            {character.mbti && (
              <ProfileItem icon="analytics-outline" title="MBTI" value={character.mbti} iconColor="#9B59B6" />
            )}
          </ProfileSection>

          {/* Hobbies */}
          {character.hobbies && character.hobbies.length > 0 && (
            <ProfileSection title="爱好">
              <View style={styles.hobbiesContainer}>
                {character.hobbies.map((hobby, index) => (
                  <View key={index} style={styles.hobbyTag}>
                    <Text style={styles.hobbyText}>{hobby}</Text>
                  </View>
                ))}
              </View>
            </ProfileSection>
          )}

          {/* Relationship Status */}
          <ProfileSection title="关系状态">
            <ProfileItem 
              icon="heart" 
              title="亲密度" 
              value={`Lv.${currentLevel}`}
              subtitle={intimacy?.stageNameCn || getStageName(currentLevel)}
              iconColor="#EC4899"
            />
            <ProfileItem 
              icon="flame" 
              title="连续互动" 
              value={`${stats.streakDays}天`}
              iconColor="#FF6B35"
            />
            <ProfileItem 
              icon="chatbubbles" 
              title="聊天消息" 
              value={`${stats.totalMessages}条`}
              iconColor="#3498DB"
            />
            <ProfileItem 
              icon="gift" 
              title="收到礼物" 
              value={`${stats.totalGifts}个`}
              iconColor="#9B59B6"
            />
            {stats.daysKnown > 0 && (
              <ProfileItem 
                icon="time" 
                title="认识天数" 
                value={`${stats.daysKnown}天`}
                iconColor="#2ECC71"
              />
            )}
          </ProfileSection>

          <View style={{ height: 40 }} />
        </ScrollView>
      </SafeAreaView>

      {/* Avatar Full Screen Modal */}
      <Modal
        visible={showAvatarModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowAvatarModal(false)}
      >
        <TouchableOpacity 
          style={styles.avatarModalOverlay} 
          activeOpacity={1}
          onPress={() => setShowAvatarModal(false)}
        >
          <Image 
            source={getCharacterAvatar(character.characterId, character.avatarUrl)}
            style={styles.avatarModalImage}
            resizeMode="contain"
          />
          <TouchableOpacity 
            style={styles.avatarModalClose}
            onPress={() => setShowAvatarModal(false)}
          >
            <Ionicons name="close" size={28} color="#fff" />
          </TouchableOpacity>
        </TouchableOpacity>
      </Modal>
    </View>
  );
}

// ============================================================================
// Styles
// ============================================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1025',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1a1025',
  },
  backgroundImage: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: SCREEN_HEIGHT * 0.5,
  },
  backgroundOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: SCREEN_HEIGHT * 0.6,
  },
  safeArea: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  backButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: '#fff',
  },
  headerRight: {
    width: 40,
  },
  scrollView: {
    flex: 1,
    paddingHorizontal: 20,
  },

  // Avatar Section
  avatarSection: {
    alignItems: 'center',
    paddingTop: 10,
    paddingBottom: 24,
  },
  largeAvatar: {
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: 4,
    borderColor: 'rgba(236, 72, 153, 0.5)',
  },
  characterName: {
    fontSize: 28,
    fontWeight: '700',
    color: '#fff',
    marginTop: 16,
  },
  occupation: {
    fontSize: 15,
    color: theme.colors.text.secondary,
    marginTop: 4,
  },
  levelBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(236, 72, 153, 0.15)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    marginTop: 12,
    gap: 8,
  },
  levelText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#EC4899',
  },
  stageText: {
    fontSize: 14,
    color: theme.colors.text.secondary,
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    marginTop: 16,
    gap: 8,
  },
  tag: {
    backgroundColor: 'rgba(139, 92, 246, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  tagText: {
    fontSize: 13,
    color: '#A78BFA',
    fontWeight: '500',
  },

  // Settings-style sections
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: theme.colors.text.tertiary,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
    marginLeft: 4,
  },
  sectionContent: {
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: 16,
    overflow: 'hidden',
  },

  // Profile Item (settings style)
  profileItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(255, 255, 255, 0.08)',
  },
  profileIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: 'rgba(139, 92, 246, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  profileContent: {
    flex: 1,
  },
  profileTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#fff',
  },
  profileSubtitle: {
    fontSize: 13,
    color: theme.colors.text.tertiary,
    marginTop: 2,
  },
  profileValue: {
    fontSize: 15,
    color: theme.colors.text.secondary,
  },

  // Description
  descriptionCard: {
    padding: 16,
  },
  descriptionText: {
    fontSize: 15,
    lineHeight: 22,
    color: theme.colors.text.secondary,
  },

  // Hobbies
  hobbiesContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 12,
    gap: 8,
  },
  hobbyTag: {
    backgroundColor: 'rgba(78, 205, 196, 0.15)',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
  },
  hobbyText: {
    fontSize: 14,
    color: '#4ECDC4',
    fontWeight: '500',
  },

  // Emotion
  emotionCard: {
    padding: 16,
  },
  emotionBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 12,
    gap: 12,
    marginBottom: 12,
  },
  emotionEmoji: {
    fontSize: 32,
  },
  emotionLabel: {
    fontSize: 16,
    fontWeight: '600',
  },
  emotionScore: {
    fontSize: 18,
    fontWeight: '700',
  },
  emotionReason: {
    fontSize: 12,
    color: theme.colors.text.tertiary,
    marginTop: 2,
  },
  emotionBar: {
    height: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 3,
    overflow: 'hidden',
  },
  emotionFill: {
    height: '100%',
    borderRadius: 3,
  },

  // Locked
  lockedCard: {
    borderRadius: 12,
    overflow: 'hidden',
  },
  lockedBlur: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 24,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  lockedText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFD700',
    marginTop: 8,
  },
  lockedSubtext: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.6)',
    marginTop: 4,
  },

  // Chat Button
  chatButton: {
    borderRadius: 24,
    overflow: 'hidden',
    marginTop: 8,
  },
  chatButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    gap: 10,
  },
  chatButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  
  // Avatar Modal
  avatarModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.95)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarModalImage: {
    width: SCREEN_WIDTH * 0.9,
    height: SCREEN_WIDTH * 0.9,
    borderRadius: 16,
  },
  avatarModalClose: {
    position: 'absolute',
    top: 60,
    right: 20,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255,255,255,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
});
