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
  TextInput,
  KeyboardAvoidingView,
  Platform,
  Alert,
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
import { chatService } from '../../services/chatService';
import { useChatStore } from '../../store/chatStore';
import { useLocale, tpl } from '../../i18n';

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
  const { t } = useLocale();
  const isVip = useUserStore((s) => s.isVip);
  
  const [character, setCharacter] = useState<Character | null>(null);
  const [intimacy, setIntimacy] = useState<IntimacyStatus | null>(null);
  const [emotion, setEmotion] = useState<EmotionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAvatarModal, setShowAvatarModal] = useState(false);
  
  // Delete character modal state
  const [deleteModalVisible, setDeleteModalVisible] = useState(false);
  const [deleteInput, setDeleteInput] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  
  const deleteSessionByCharacterId = useChatStore((s) => s.deleteSessionByCharacterId);
  const [stats, setStats] = useState<{
    streakDays: number;
    totalMessages: number;
    totalGifts: number;
    totalDates: number;
    specialEvents: number;
    daysKnown: number;
  }>({
    streakDays: 0,
    totalMessages: 0,
    totalGifts: 0,
    totalDates: 0,
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
        // daysKnown 现在从 /stats API 的 first_interaction_date 计算
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
        
        // 计算认识天数（从第一次互动到今天）
        let daysKnown = 1;
        if (statsData.first_interaction_date) {
          const firstDay = new Date(statsData.first_interaction_date);
          const today = new Date();
          const diffDays = Math.floor((today.getTime() - firstDay.getTime()) / (1000 * 60 * 60 * 24));
          daysKnown = Math.max(1, diffDays + 1); // +1 因为包含当天
        }
        
        setStats(prev => ({
          ...prev,
          streakDays: statsData.streak_days || prev.streakDays,
          totalMessages: statsData.total_messages || prev.totalMessages,
          totalGifts: statsData.total_gifts || prev.totalGifts,
          totalDates: statsData.total_dates || 0,
          specialEvents: statsData.special_events || prev.specialEvents,
          daysKnown: daysKnown,
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
  
  // Delete character handlers
  const handleDeletePress = () => {
    setDeleteInput('');
    setDeleteModalVisible(true);
  };
  
  const confirmDelete = async () => {
    if (deleteInput.toLowerCase() !== 'delete') return;
    
    setIsDeleting(true);
    try {
      await chatService.deleteCharacterData(params.characterId);
      // Remove from local store if exists
      if (deleteSessionByCharacterId) {
        deleteSessionByCharacterId(params.characterId);
      }
      setDeleteModalVisible(false);
      Alert.alert(t.characterProfile.deleted, tpl(t.characterProfile.deletedMessage, { name: character?.name || '' }), [
        { text: t.characterProfile.confirm, onPress: () => router.replace('/(tabs)/') }
      ]);
    } catch (error) {
      console.error('Delete character data failed:', error);
      Alert.alert(t.common.error, t.characterProfile.deleteFailed);
    } finally {
      setIsDeleting(false);
    }
  };
  
  const cancelDelete = () => {
    setDeleteModalVisible(false);
    setDeleteInput('');
  };
  
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
          <Text style={styles.headerTitle}>{t.characterProfile.title}</Text>
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
              <Ionicons 
                name={character.characterType === 'buddy' ? 'paw' : 'heart'} 
                size={16} 
                color={character.characterType === 'buddy' ? '#63C7FF' : '#00D4FF'} 
              />
              <Text style={styles.levelText}>Lv.{currentLevel}</Text>
              <Text style={styles.stageText}>
                {character.characterType === 'buddy' 
                  ? (currentLevel <= 3 ? '🐾 路人' : currentLevel <= 10 ? '😼 认识' : currentLevel <= 25 ? '🤝 搭子' : currentLevel <= 40 ? '💪 铁哥们' : '🫂 过命交情')
                  : getStageName(currentLevel)}
              </Text>
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
          <ProfileSection title={t.characterProfile.bio}>
            <View style={styles.descriptionCard}>
              <Text style={styles.descriptionText}>{character.description}</Text>
            </View>
          </ProfileSection>

          {/* Basic Info */}
          <ProfileSection title={t.characterProfile.basicInfo}>
            {character.age && (
              <ProfileItem icon="calendar-outline" title={t.characterProfile.age} value={tpl(t.characterProfile.ageValue, { age: character.age })} />
            )}
            {character.birthday && (
              <ProfileItem icon="gift-outline" title={t.characterProfile.birthday} value={character.birthday} iconColor="#FF6B6B" />
            )}
            {character.zodiac && (
              <ProfileItem icon="star-outline" title={t.characterProfile.zodiac} value={character.zodiac} iconColor="#FFD700" />
            )}
            {character.height && (
              <ProfileItem icon="resize-outline" title={t.characterProfile.height} value={character.height} />
            )}
            {character.location && (
              <ProfileItem icon="location-outline" title={t.characterProfile.location} value={character.location} iconColor="#4ECDC4" />
            )}
            {character.mbti && (
              <ProfileItem icon="analytics-outline" title={t.characterProfile.mbti} value={character.mbti} iconColor="#9B59B6" />
            )}
          </ProfileSection>

          {/* Hobbies */}
          {character.hobbies && character.hobbies.length > 0 && (
            <ProfileSection title={t.characterProfile.hobbies}>
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
          <ProfileSection title={t.characterProfile.relationship}>
            <ProfileItem 
              icon="heart" 
              title={t.characterProfile.intimacy} 
              value={`Lv.${currentLevel}`}
              subtitle={intimacy?.stageNameCn || getStageName(currentLevel)}
              iconColor="#00D4FF"
            />
            <ProfileItem 
              icon="flame" 
              title={t.characterProfile.streak} 
              value={tpl(t.characterProfile.streakDays, { days: stats.streakDays })}
              iconColor="#FF6B35"
            />
            <ProfileItem 
              icon="chatbubbles" 
              title={t.characterProfile.chatMessages} 
              value={tpl(t.characterProfile.messagesCount, { count: stats.totalMessages })}
              iconColor="#3498DB"
            />
            <ProfileItem 
              icon="gift" 
              title={t.characterProfile.giftsReceived} 
              value={tpl(t.characterProfile.giftsCount, { count: stats.totalGifts })}
              iconColor="#9B59B6"
            />
            <ProfileItem 
              icon="heart" 
              title="约会次数"
              value={`${stats.totalDates} 次`}
              iconColor="#EC4899"
            />
            {stats.daysKnown > 0 && (
              <ProfileItem 
                icon="time" 
                title={t.characterProfile.daysKnown} 
                value={tpl(t.characterProfile.streakDays, { days: stats.daysKnown })}
                iconColor="#2ECC71"
              />
            )}
          </ProfileSection>

          {/* Delete Character Button */}
          <View style={styles.dangerSection}>
            <TouchableOpacity 
              style={styles.deleteButton}
              onPress={handleDeletePress}
            >
              <Ionicons name="trash-outline" size={20} color="#ff4757" />
              <Text style={styles.deleteButtonText}>{t.characterProfile.deleteCharacterData}</Text>
            </TouchableOpacity>
            <Text style={styles.deleteHint}>
              {t.characterProfile.deleteHint}
            </Text>
          </View>

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

      {/* Delete Confirmation Modal */}
      <Modal
        visible={deleteModalVisible}
        transparent
        animationType="fade"
        onRequestClose={cancelDelete}
      >
        <KeyboardAvoidingView 
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.deleteModalOverlay}
        >
          <View style={styles.deleteModalContent}>
            <View style={styles.deleteModalIcon}>
              <Ionicons name="warning" size={32} color="#ff4757" />
            </View>
            
            <Text style={styles.deleteModalTitle}>{t.characterProfile.deleteConfirmTitle}</Text>
            
            <Text style={styles.deleteModalMessage}>
              {tpl(t.characterProfile.deleteConfirmMessage, { name: character?.name || '' })}
            </Text>
            
            <View style={styles.deleteModalList}>
              <Text style={styles.deleteModalListItem}>{t.characterProfile.deleteList.chats}</Text>
              <Text style={styles.deleteModalListItem}>{t.characterProfile.deleteList.intimacy}</Text>
              <Text style={styles.deleteModalListItem}>{t.characterProfile.deleteList.emotion}</Text>
              <Text style={styles.deleteModalListItem}>{t.characterProfile.deleteList.photos}</Text>
            </View>
            
            <Text style={styles.deleteModalWarning}>{t.characterProfile.deleteWarning}</Text>
            
            <Text style={styles.deleteModalInputLabel}>
              {t.characterProfile.deleteInputLabel}<Text style={styles.deleteModalInputHighlight}>{t.characterProfile.deleteInputHighlight}</Text>{t.characterProfile.deleteInputSuffix}
            </Text>
            
            <TextInput
              style={styles.deleteModalInput}
              value={deleteInput}
              onChangeText={setDeleteInput}
              placeholder={t.characterProfile.deleteInputPlaceholder}
              placeholderTextColor="rgba(255,255,255,0.3)"
              autoCapitalize="none"
              autoCorrect={false}
            />
            
            <View style={styles.deleteModalButtons}>
              <TouchableOpacity 
                style={styles.deleteModalCancelButton}
                onPress={cancelDelete}
              >
                <Text style={styles.deleteModalCancelText}>{t.common.cancel}</Text>
              </TouchableOpacity>
              
              <TouchableOpacity 
                style={[
                  styles.deleteModalConfirmButton,
                  deleteInput.toLowerCase() !== 'delete' && styles.deleteModalConfirmButtonDisabled
                ]}
                onPress={confirmDelete}
                disabled={deleteInput.toLowerCase() !== 'delete' || isDeleting}
              >
                <Text style={styles.deleteModalConfirmText}>
                  {isDeleting ? t.characterProfile.deleting : t.characterProfile.confirmDelete}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
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
    color: '#00D4FF',
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
  
  // Danger Section (Delete)
  dangerSection: {
    marginTop: 24,
    marginBottom: 8,
    alignItems: 'center',
  },
  deleteButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 12,
    backgroundColor: 'rgba(255, 71, 87, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(255, 71, 87, 0.3)',
    gap: 8,
  },
  deleteButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#ff4757',
  },
  deleteHint: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.4)',
    textAlign: 'center',
    marginTop: 8,
    paddingHorizontal: 20,
  },
  
  // Delete Confirmation Modal
  deleteModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  deleteModalContent: {
    backgroundColor: '#1a1a2e',
    borderRadius: 20,
    padding: 24,
    width: '100%',
    maxWidth: 340,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 71, 87, 0.3)',
  },
  deleteModalIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: 'rgba(255, 71, 87, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  deleteModalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 12,
  },
  deleteModalMessage: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    textAlign: 'center',
    marginBottom: 12,
  },
  deleteModalList: {
    alignSelf: 'flex-start',
    marginBottom: 12,
    paddingLeft: 8,
  },
  deleteModalListItem: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.6)',
    marginBottom: 4,
  },
  deleteModalWarning: {
    fontSize: 14,
    fontWeight: '600',
    color: '#ff4757',
    marginBottom: 16,
  },
  deleteModalInputLabel: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    marginBottom: 8,
    alignSelf: 'flex-start',
  },
  deleteModalInputHighlight: {
    color: '#ff4757',
    fontWeight: '700',
  },
  deleteModalInput: {
    width: '100%',
    height: 48,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 16,
    color: '#fff',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    marginBottom: 20,
  },
  deleteModalButtons: {
    flexDirection: 'row',
    gap: 12,
    width: '100%',
  },
  deleteModalCancelButton: {
    flex: 1,
    height: 48,
    borderRadius: 12,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  deleteModalCancelText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  deleteModalConfirmButton: {
    flex: 1,
    height: 48,
    borderRadius: 12,
    backgroundColor: '#ff4757',
    justifyContent: 'center',
    alignItems: 'center',
  },
  deleteModalConfirmButtonDisabled: {
    backgroundColor: 'rgba(255, 71, 87, 0.3)',
  },
  deleteModalConfirmText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
});
