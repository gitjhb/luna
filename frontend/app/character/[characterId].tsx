/**
 * Character Profile Screen
 * Shows character details with unlockable secrets (Stardew Valley style)
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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { theme } from '../../theme/config';
import { characterService } from '../../services/characterService';
import { intimacyService } from '../../services/intimacyService';
import { CharacterProfile, PersonalitySecret, UnlockableInfo, IntimacyStatus } from '../../types';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// Mock data for demo (replace with real API)
const getMockCharacterProfile = (characterId: string): CharacterProfile => ({
  characterId,
  name: 'Sophia',
  avatarUrl: 'https://i.pravatar.cc/300?img=1',
  backgroundUrl: 'https://i.imgur.com/vB5HQXQ.jpg',
  description: 'A sophisticated and intelligent companion who loves deep conversations.',
  personalityTraits: ['Intelligent', 'Empathetic', 'Sophisticated'],
  tierRequired: 'free',
  isSpicy: false,
  tags: ['Conversation', 'Advice', 'Philosophy'],
  age: 24,
  occupation: 'Graduate Student',
  personalitySecrets: [
    { id: '1', title: '🎭 Hidden Side', content: 'Actually loves watching trashy reality TV shows in secret', unlockLevel: 5 },
    { id: '2', title: '💭 Deep Fear', content: 'Afraid of being alone and forgotten', unlockLevel: 15 },
    { id: '3', title: '🌟 Dream', content: 'Wants to write a novel about parallel universes', unlockLevel: 25 },
    { id: '4', title: '💔 Past', content: 'Had her heart broken in college, still healing', unlockLevel: 35 },
    { id: '5', title: '🔮 Secret Wish', content: 'Wishes she could turn back time and make different choices', unlockLevel: 50 },
  ],
  likes: [
    { id: 'l1', content: '☕ Coffee', unlockLevel: 1, category: 'Food' },
    { id: 'l2', content: '📚 Classic Literature', unlockLevel: 3, category: 'Hobby' },
    { id: 'l3', content: '🌙 Late Night Talks', unlockLevel: 8, category: 'Activity' },
    { id: 'l4', content: '🎹 Jazz Music', unlockLevel: 12, category: 'Music' },
    { id: 'l5', content: '🌸 Cherry Blossoms', unlockLevel: 20, category: 'Nature' },
  ],
  dislikes: [
    { id: 'd1', content: '🔊 Loud Places', unlockLevel: 2, category: 'Environment' },
    { id: 'd2', content: '🤥 Dishonesty', unlockLevel: 6, category: 'Trait' },
    { id: 'd3', content: '⏰ Being Rushed', unlockLevel: 10, category: 'Situation' },
  ],
  backstory: [
    { id: 'b1', content: 'Grew up in a small town, always dreamed of the big city', unlockLevel: 10 },
    { id: 'b2', content: 'Parents divorced when she was 12, shaped her views on love', unlockLevel: 20 },
    { id: 'b3', content: 'Met her best friend in college, but lost touch after graduation', unlockLevel: 30 },
    { id: 'b4', content: 'Once almost gave up on her dreams, but a stranger\'s kindness changed everything', unlockLevel: 40 },
  ],
  specialDialogues: [
    { id: 's1', content: '💕 Confession Scene', unlockLevel: 25 },
    { id: 's2', content: '🌙 Midnight Heart-to-Heart', unlockLevel: 35 },
    { id: 's3', content: '💍 Future Together Talk', unlockLevel: 50 },
  ],
});

interface UnlockableCardProps {
  item: UnlockableInfo | PersonalitySecret;
  currentLevel: number;
  showTitle?: boolean;
}

const UnlockableCard = ({ item, currentLevel, showTitle }: UnlockableCardProps) => {
  const isUnlocked = currentLevel >= item.unlockLevel;
  const title = 'title' in item ? item.title : null;
  
  return (
    <View style={[styles.unlockableCard, !isUnlocked && styles.unlockableCardLocked]}>
      {isUnlocked ? (
        <>
          {showTitle && title && <Text style={styles.secretTitle}>{title}</Text>}
          <Text style={styles.unlockableContent}>{item.content}</Text>
          {'category' in item && item.category && (
            <Text style={styles.unlockableCategory}>{item.category}</Text>
          )}
        </>
      ) : (
        <View style={styles.lockedContent}>
          <Ionicons name="lock-closed" size={20} color={theme.colors.text.tertiary} />
          <Text style={styles.lockedText}>Unlock at Level {item.unlockLevel}</Text>
        </View>
      )}
    </View>
  );
};

export default function CharacterProfileScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ characterId: string }>();
  
  const [profile, setProfile] = useState<CharacterProfile | null>(null);
  const [intimacy, setIntimacy] = useState<IntimacyStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'about' | 'secrets' | 'story'>('about');

  useEffect(() => {
    loadData();
  }, [params.characterId]);

  const loadData = async () => {
    try {
      // In production, fetch from API
      // const profile = await characterService.getCharacterProfile(params.characterId);
      const mockProfile = getMockCharacterProfile(params.characterId);
      setProfile(mockProfile);
      
      try {
        const intimacyStatus = await intimacyService.getStatus(params.characterId);
        setIntimacy(intimacyStatus);
      } catch (e) {
        // Default to level 1 if no intimacy data
        setIntimacy({ currentLevel: 1 } as IntimacyStatus);
      }
    } catch (error) {
      console.error('Failed to load character profile:', error);
    } finally {
      setLoading(false);
    }
  };

  const currentLevel = intimacy?.currentLevel || 1;
  
  const countUnlocked = (items: (UnlockableInfo | PersonalitySecret)[]) => 
    items.filter(item => currentLevel >= item.unlockLevel).length;

  if (loading || !profile) {
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
        source={{ uri: profile.backgroundUrl || profile.avatarUrl }} 
        style={styles.backgroundImage}
        blurRadius={20}
      />
      <LinearGradient
        colors={['transparent', 'rgba(26,16,37,0.8)', 'rgba(26,16,37,1)']}
        style={styles.backgroundOverlay}
      />

      <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Character Profile</Text>
          <View style={styles.headerRight} />
        </View>

        <ScrollView showsVerticalScrollIndicator={false}>
          {/* Profile Header */}
          <View style={styles.profileHeader}>
            <Image source={{ uri: profile.avatarUrl }} style={styles.avatar} />
            <Text style={styles.name}>{profile.name}</Text>
            {profile.occupation && (
              <Text style={styles.occupation}>{profile.occupation}</Text>
            )}
            
            {/* Intimacy Level Badge */}
            <View style={styles.levelBadge}>
              <Ionicons name="heart" size={16} color="#EC4899" />
              <Text style={styles.levelText}>Level {currentLevel}</Text>
              <Text style={styles.stageText}>{intimacy?.stageNameCn || 'Strangers'}</Text>
            </View>
            
            {/* Progress hint */}
            <Text style={styles.progressHint}>
              💡 Chat more to unlock secrets
            </Text>
          </View>

          {/* Tabs */}
          <View style={styles.tabBar}>
            {[
              { id: 'about', label: 'About', icon: 'person-outline' },
              { id: 'secrets', label: 'Secrets', icon: 'key-outline' },
              { id: 'story', label: 'Story', icon: 'book-outline' },
            ].map(tab => (
              <TouchableOpacity
                key={tab.id}
                style={[styles.tab, activeTab === tab.id && styles.tabActive]}
                onPress={() => setActiveTab(tab.id as any)}
              >
                <Ionicons 
                  name={tab.icon as any} 
                  size={18} 
                  color={activeTab === tab.id ? theme.colors.primary.main : theme.colors.text.tertiary} 
                />
                <Text style={[styles.tabText, activeTab === tab.id && styles.tabTextActive]}>
                  {tab.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Tab Content */}
          <View style={styles.content}>
            {activeTab === 'about' && (
              <>
                {/* Description */}
                <View style={styles.section}>
                  <Text style={styles.sectionTitle}>Description</Text>
                  <Text style={styles.description}>{profile.description}</Text>
                </View>

                {/* Likes */}
                <View style={styles.section}>
                  <View style={styles.sectionHeader}>
                    <Text style={styles.sectionTitle}>❤️ Likes</Text>
                    <Text style={styles.unlockCount}>
                      {countUnlocked(profile.likes)}/{profile.likes.length}
                    </Text>
                  </View>
                  <View style={styles.itemsGrid}>
                    {profile.likes.map(item => (
                      <UnlockableCard key={item.id} item={item} currentLevel={currentLevel} />
                    ))}
                  </View>
                </View>

                {/* Dislikes */}
                <View style={styles.section}>
                  <View style={styles.sectionHeader}>
                    <Text style={styles.sectionTitle}>💔 Dislikes</Text>
                    <Text style={styles.unlockCount}>
                      {countUnlocked(profile.dislikes)}/{profile.dislikes.length}
                    </Text>
                  </View>
                  <View style={styles.itemsGrid}>
                    {profile.dislikes.map(item => (
                      <UnlockableCard key={item.id} item={item} currentLevel={currentLevel} />
                    ))}
                  </View>
                </View>
              </>
            )}

            {activeTab === 'secrets' && (
              <>
                {/* Personality Secrets */}
                <View style={styles.section}>
                  <View style={styles.sectionHeader}>
                    <Text style={styles.sectionTitle}>🔮 Hidden Personality</Text>
                    <Text style={styles.unlockCount}>
                      {countUnlocked(profile.personalitySecrets)}/{profile.personalitySecrets.length}
                    </Text>
                  </View>
                  {profile.personalitySecrets.map(secret => (
                    <UnlockableCard 
                      key={secret.id} 
                      item={secret} 
                      currentLevel={currentLevel}
                      showTitle 
                    />
                  ))}
                </View>

                {/* Special Dialogues */}
                <View style={styles.section}>
                  <View style={styles.sectionHeader}>
                    <Text style={styles.sectionTitle}>💬 Special Events</Text>
                    <Text style={styles.unlockCount}>
                      {countUnlocked(profile.specialDialogues)}/{profile.specialDialogues.length}
                    </Text>
                  </View>
                  {profile.specialDialogues.map(item => (
                    <UnlockableCard key={item.id} item={item} currentLevel={currentLevel} />
                  ))}
                </View>
              </>
            )}

            {activeTab === 'story' && (
              <View style={styles.section}>
                <View style={styles.sectionHeader}>
                  <Text style={styles.sectionTitle}>📖 Backstory</Text>
                  <Text style={styles.unlockCount}>
                    {countUnlocked(profile.backstory)}/{profile.backstory.length}
                  </Text>
                </View>
                {profile.backstory.map((item, index) => (
                  <View key={item.id} style={styles.storyItem}>
                    <View style={styles.storyTimeline}>
                      <View style={[
                        styles.storyDot, 
                        currentLevel >= item.unlockLevel && styles.storyDotUnlocked
                      ]} />
                      {index < profile.backstory.length - 1 && (
                        <View style={styles.storyLine} />
                      )}
                    </View>
                    <View style={styles.storyContent}>
                      <UnlockableCard item={item} currentLevel={currentLevel} />
                    </View>
                  </View>
                ))}
              </View>
            )}
          </View>

          {/* Chat Button */}
          <TouchableOpacity 
            style={styles.chatButton}
            onPress={() => router.push({
              pathname: '/chat/[characterId]',
              params: { characterId: profile.characterId, characterName: profile.name },
            })}
          >
            <LinearGradient
              colors={['#EC4899', '#8B5CF6']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.chatButtonGradient}
            >
              <Ionicons name="chatbubble-ellipses" size={20} color="#fff" />
              <Text style={styles.chatButtonText}>Continue Chatting</Text>
            </LinearGradient>
          </TouchableOpacity>

          <View style={{ height: 40 }} />
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

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
    height: SCREEN_HEIGHT * 0.4,
  },
  backgroundOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: SCREEN_HEIGHT * 0.5,
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
  profileHeader: {
    alignItems: 'center',
    paddingTop: 20,
    paddingBottom: 24,
  },
  avatar: {
    width: 100,
    height: 100,
    borderRadius: 50,
    borderWidth: 3,
    borderColor: theme.colors.primary.main,
  },
  name: {
    fontSize: 26,
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
    marginTop: 16,
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
  progressHint: {
    fontSize: 13,
    color: theme.colors.text.tertiary,
    marginTop: 12,
  },
  tabBar: {
    flexDirection: 'row',
    marginHorizontal: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: 12,
    padding: 4,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    borderRadius: 10,
    gap: 6,
  },
  tabActive: {
    backgroundColor: 'rgba(139, 92, 246, 0.2)',
  },
  tabText: {
    fontSize: 13,
    fontWeight: '500',
    color: theme.colors.text.tertiary,
  },
  tabTextActive: {
    color: theme.colors.primary.main,
  },
  content: {
    paddingHorizontal: 20,
    paddingTop: 24,
  },
  section: {
    marginBottom: 28,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: '#fff',
  },
  unlockCount: {
    fontSize: 13,
    color: theme.colors.text.tertiary,
  },
  description: {
    fontSize: 15,
    lineHeight: 22,
    color: theme.colors.text.secondary,
  },
  itemsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  unlockableCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 12,
    padding: 12,
    minWidth: 100,
  },
  unlockableCardLocked: {
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
  },
  secretTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 6,
  },
  unlockableContent: {
    fontSize: 14,
    color: '#fff',
  },
  unlockableCategory: {
    fontSize: 11,
    color: theme.colors.text.tertiary,
    marginTop: 4,
  },
  lockedContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 4,
  },
  lockedText: {
    fontSize: 13,
    color: theme.colors.text.tertiary,
  },
  storyItem: {
    flexDirection: 'row',
    marginBottom: 0,
  },
  storyTimeline: {
    width: 24,
    alignItems: 'center',
  },
  storyDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    marginTop: 14,
  },
  storyDotUnlocked: {
    backgroundColor: theme.colors.primary.main,
  },
  storyLine: {
    width: 2,
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    marginVertical: 4,
  },
  storyContent: {
    flex: 1,
    marginLeft: 8,
    marginBottom: 12,
  },
  chatButton: {
    marginHorizontal: 20,
    marginTop: 16,
    borderRadius: 24,
    overflow: 'hidden',
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
});
