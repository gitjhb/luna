/**
 * Companions Screen - Purple Pink Theme
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  RefreshControl,
  Image,
  Dimensions,
  Alert,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { getShadow, useTheme } from '../../theme/config';
import { useUserStore } from '../../store/userStore';
import { Character } from '../../types';
import { characterService } from '../../services/characterService';
import SettingsDrawer from '../../components/SettingsDrawer';
import MockModeBanner from '../../components/MockModeBanner';
import { useLocale, tpl } from '../../i18n';
import { getCharacterAvatar, getCharacterBackground } from '../../assets/characters';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = SCREEN_WIDTH - 48;

export default function CompanionsScreen() {
  const router = useRouter();
  const { theme } = useTheme();
  const { t } = useLocale();
  const { user, wallet, isSubscribed } = useUserStore();
  
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showSettingsDrawer, setShowSettingsDrawer] = useState(false);

  useEffect(() => {
    loadCharacters();
  }, []);

  const loadCharacters = async () => {
    try {
      const data = await characterService.getCharacters();
      setCharacters(data);
    } catch (error) {
      console.error('Failed to load characters:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadCharacters();
  };

  const filteredCharacters = characters.filter(char =>
    !searchQuery || 
    char.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    char.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Check if character is locked (requires subscription)
  const isCharacterLocked = (character: Character) => {
    if (isSubscribed) return false;
    return character.tierRequired === 'premium' || character.tierRequired === 'vip';
  };

  const handleCharacterPress = (character: Character) => {
    // Check if character requires subscription
    if (isCharacterLocked(character)) {
      Alert.alert(
        '🔒 专属角色',
        `${character.name} 是订阅专属角色\n\n订阅后即可解锁聊天`,
        [
          { text: '取消', style: 'cancel' },
          { text: '去订阅', onPress: () => router.push('/(tabs)/profile') },
        ]
      );
      return;
    }
    
    router.push({
      pathname: '/chat/[characterId]',
      params: {
        characterId: character.characterId,
        characterName: character.name,
        avatarUrl: character.avatarUrl,
        backgroundUrl: character.backgroundUrl,
      },
    });
  };

  if (loading) {
    return (
      <View style={[styles.loadingContainer, { backgroundColor: theme.colors.background.primary }]}>
        <ActivityIndicator size="large" color={theme.colors.primary.main} />
      </View>
    );
  }

  return (
    <LinearGradient colors={[...theme.colors.background.gradient]} style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity 
            style={styles.menuButton}
            onPress={() => setShowSettingsDrawer(true)}
          >
            <Ionicons name="menu-outline" size={26} color="#fff" />
          </TouchableOpacity>
          
          <View style={styles.headerCenter}>
            <Text style={styles.greeting}>{tpl(t.discover.greeting, { name: user?.displayName || 'there' })}</Text>
            <Text style={styles.subtitle}>{t.discover.subtitle}</Text>
          </View>
          
          <TouchableOpacity style={styles.creditsBadge} onPress={() => router.push('/(tabs)/profile')}>
            <Image source={require('../../assets/icons/moon-shard.png')} style={styles.shardIcon} />
            <Text style={styles.creditsText}>{wallet?.totalCredits?.toFixed(0) || '0'}</Text>
          </TouchableOpacity>
        </View>

        {/* Search */}
        <View style={styles.searchContainer}>
          <Ionicons name="search" size={18} color={theme.colors.text.tertiary} />
          <TextInput
            style={styles.searchInput}
            placeholder={t.discover.searchPlaceholder}
            placeholderTextColor={theme.colors.text.tertiary}
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
        </View>

        {/* Mock Mode Warning */}
        <MockModeBanner />

        {/* Characters */}
        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.charactersContainer}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={theme.colors.primary.main}
            />
          }
        >
          {filteredCharacters.map((character) => (
            <TouchableOpacity
              key={character.characterId}
              style={styles.characterCard}
              onPress={() => handleCharacterPress(character)}
              activeOpacity={0.9}
            >
              <Image
                source={getCharacterAvatar(character.characterId, character.avatarUrl)}
                style={styles.characterImage}
              />
              <LinearGradient
                colors={['transparent', 'rgba(26,16,37,0.8)', 'rgba(26,16,37,0.98)'] as [string, string, string]}
                style={styles.cardGradient}
              />
              <View style={styles.cardContent}>
                <View style={styles.cardHeader}>
                  <Text style={styles.characterName}>{character.name}</Text>
                  {character.characterType === 'buddy' ? (
                    <View style={styles.buddyBadge}>
                      <Text style={styles.buddyBadgeText}>{t.discover.buddy}</Text>
                    </View>
                  ) : null}
                  {isCharacterLocked(character) && (
                    <View style={styles.premiumBadge}>
                      <Ionicons name="lock-closed" size={12} color="#FFD700" />
                      <Text style={styles.premiumBadgeText}>订阅</Text>
                    </View>
                  )}
                  {/* Spicy badge hidden for App Store compliance */}
                </View>
                <Text style={styles.characterDesc} numberOfLines={2}>
                  {character.description}
                </Text>
                <View style={styles.tagsRow}>
                  {(character.personalityTraits || []).slice(0, 3).map((trait, i) => (
                    <View key={i} style={styles.tag}>
                      <Text style={styles.tagText}>{trait}</Text>
                    </View>
                  ))}
                </View>
                <TouchableOpacity style={styles.chatButton} onPress={() => handleCharacterPress(character)}>
                  <LinearGradient colors={theme.colors.primary.gradient} style={styles.chatButtonGradient}>
                    <Text style={styles.chatButtonText}>{t.discover.startChat}</Text>
                    <Ionicons name="chatbubble-ellipses" size={18} color="#fff" />
                  </LinearGradient>
                </TouchableOpacity>
              </View>
            </TouchableOpacity>
          ))}
          
          <View style={{ height: 100 }} />
        </ScrollView>
      </SafeAreaView>

      <SettingsDrawer visible={showSettingsDrawer} onClose={() => setShowSettingsDrawer(false)} />
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  safeArea: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    // backgroundColor set via inline style for theme support
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  menuButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerCenter: {
    flex: 1,
    marginLeft: 8,
  },
  greeting: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
  },
  subtitle: {
    fontSize: 15,
    color: 'rgba(255, 255, 255, 0.7)',
    marginTop: 2,
  },
  creditsBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(236, 72, 153, 0.15)',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    gap: 6,
  },
  creditsText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#00D4FF',
  },
  shardIcon: {
    width: 20,
    height: 20,
    borderRadius: 10,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    marginHorizontal: 20,
    marginBottom: 16,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 14,
    gap: 10,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    color: '#fff',
  },
  charactersContainer: {
    paddingHorizontal: 20,
    gap: 20,
  },
  characterCard: {
    width: CARD_WIDTH,
    height: 380,
    borderRadius: 24,
    overflow: 'hidden',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    ...getShadow('lg'),
  },
  characterImage: {
    width: '100%',
    height: '100%',
    position: 'absolute',
  },
  cardGradient: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: '65%',
  },
  cardContent: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 20,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 6,
  },
  characterName: {
    fontSize: 22,
    fontWeight: '700',
    color: '#fff',
  },
  spicyBadge: {
    backgroundColor: 'rgba(255, 107, 107, 0.2)',
    padding: 6,
    borderRadius: 12,
  },
  buddyBadge: {
    backgroundColor: 'rgba(99, 199, 255, 0.2)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  buddyBadgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#63C7FF',
  },
  premiumBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 215, 0, 0.2)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  premiumBadgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#FFD700',
  },
  characterDesc: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.7)',
    lineHeight: 20,
    marginBottom: 12,
  },
  tagsRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 14,
  },
  tag: {
    backgroundColor: 'rgba(255, 255, 255, 0.12)',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
  },
  tagText: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.7)',
  },
  chatButton: {
    borderRadius: 20,
    overflow: 'hidden',
  },
  chatButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 13,
    gap: 8,
  },
  chatButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
});
