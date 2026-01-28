/**
 * Companions Screen (Home)
 * 
 * Main screen displaying available AI companions.
 * Features:
 * - Horizontal scrolling character cards
 * - Filter by tier/tags
 * - Search functionality
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
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme, getShadow } from '../../../theme/config';
import { useUserStore } from '../../../store/userStore';
import { CharacterCard } from '../../../components/molecules/CharacterCard';
import { Character } from '../../../types';
import { characterService } from '../../../services/characterService';

export default function CompanionsScreen() {
  const router = useRouter();
  const { user, isSubscribed } = useUserStore();
  
  const [characters, setCharacters] = useState<Character[]>([]);
  const [filteredCharacters, setFilteredCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'free' | 'premium' | 'spicy'>('all');

  useEffect(() => {
    loadCharacters();
  }, []);

  useEffect(() => {
    filterCharacters();
  }, [characters, searchQuery, selectedFilter]);

  const loadCharacters = async () => {
    try {
      const data = await characterService.getCharacters();
      setCharacters(data);
    } catch (error) {
      console.error('Failed to load characters:', error);
    } finally {
      setLoading(false);
    }
  };

  const filterCharacters = () => {
    let filtered = characters;

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(
        (char) =>
          char.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          char.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
          char.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()))
      );
    }

    // Apply tier filter
    if (selectedFilter === 'free') {
      filtered = filtered.filter((char) => char.tierRequired === 'free');
    } else if (selectedFilter === 'premium') {
      filtered = filtered.filter((char) => char.tierRequired !== 'free');
    } else if (selectedFilter === 'spicy') {
      filtered = filtered.filter((char) => char.isSpicy);
    }

    setFilteredCharacters(filtered);
  };

  const handleCharacterPress = (character: Character) => {
    // Check if character is locked
    const isLocked = character.tierRequired !== 'free' && !isSubscribed;
    
    if (isLocked) {
      // Show paywall or upgrade prompt
      return;
    }

    router.push({
      pathname: '/chat/[characterId]',
      params: {
        characterId: character.characterId,
        characterName: character.name,
      },
    });
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={theme.colors.primary.main} />
      </View>
    );
  }

  return (
    <LinearGradient colors={theme.colors.background.gradient} style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Hello, {user?.displayName || 'there'}</Text>
            <Text style={styles.subtitle}>Choose your companion</Text>
          </View>
          
          <TouchableOpacity
            style={styles.profileButton}
            onPress={() => router.push('/profile')}
          >
            <LinearGradient
              colors={theme.colors.primary.gradient}
              style={styles.profileButtonGradient}
            >
              <Ionicons name="person" size={24} color={theme.colors.text.inverse} />
            </LinearGradient>
          </TouchableOpacity>
        </View>

        {/* Search Bar */}
        <View style={styles.searchContainer}>
          <Ionicons name="search" size={20} color={theme.colors.text.tertiary} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search companions..."
            placeholderTextColor={theme.colors.text.tertiary}
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={() => setSearchQuery('')}>
              <Ionicons name="close-circle" size={20} color={theme.colors.text.tertiary} />
            </TouchableOpacity>
          )}
        </View>

        {/* Filters */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.filtersContainer}
        >
          <FilterChip
            label="All"
            active={selectedFilter === 'all'}
            onPress={() => setSelectedFilter('all')}
          />
          <FilterChip
            label="Free"
            active={selectedFilter === 'free'}
            onPress={() => setSelectedFilter('free')}
          />
          <FilterChip
            label="Premium"
            active={selectedFilter === 'premium'}
            onPress={() => setSelectedFilter('premium')}
            icon="diamond"
          />
          <FilterChip
            label="Spicy"
            active={selectedFilter === 'spicy'}
            onPress={() => setSelectedFilter('spicy')}
            icon="flame"
          />
        </ScrollView>

        {/* Characters List */}
        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.charactersContainer}
        >
          {filteredCharacters.map((character) => {
            const isLocked = character.tierRequired !== 'free' && !isSubscribed;
            
            return (
              <CharacterCard
                key={character.characterId}
                character={character}
                onPress={() => handleCharacterPress(character)}
                isLocked={isLocked}
              />
            );
          })}

          {filteredCharacters.length === 0 && (
            <View style={styles.emptyState}>
              <Ionicons name="search" size={64} color={theme.colors.text.tertiary} />
              <Text style={styles.emptyStateText}>No companions found</Text>
              <Text style={styles.emptyStateSubtext}>
                Try adjusting your search or filters
              </Text>
            </View>
          )}
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const FilterChip: React.FC<{
  label: string;
  active: boolean;
  onPress: () => void;
  icon?: any;
}> = ({ label, active, onPress, icon }) => (
  <TouchableOpacity
    style={[styles.filterChip, active && styles.filterChipActive]}
    onPress={onPress}
    activeOpacity={0.7}
  >
    {active ? (
      <LinearGradient
        colors={theme.colors.primary.gradient}
        style={styles.filterChipGradient}
      >
        {icon && <Ionicons name={icon} size={16} color={theme.colors.text.inverse} />}
        <Text style={[styles.filterChipText, styles.filterChipTextActive]}>{label}</Text>
      </LinearGradient>
    ) : (
      <>
        {icon && <Ionicons name={icon} size={16} color={theme.colors.text.secondary} />}
        <Text style={styles.filterChipText}>{label}</Text>
      </>
    )}
  </TouchableOpacity>
);

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
    backgroundColor: theme.colors.background.primary,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.md,
  },
  greeting: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize['2xl'],
    color: theme.colors.text.primary,
  },
  subtitle: {
    fontFamily: theme.typography.fontFamily.regular,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
  },
  profileButton: {
    borderRadius: theme.borderRadius.full,
    overflow: 'hidden',
    ...getShadow('md'),
  },
  profileButtonGradient: {
    width: 48,
    height: 48,
    justifyContent: 'center',
    alignItems: 'center',
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.background.secondary,
    marginHorizontal: theme.spacing.lg,
    marginBottom: theme.spacing.md,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    borderRadius: theme.borderRadius.lg,
    gap: theme.spacing.sm,
  },
  searchInput: {
    flex: 1,
    fontFamily: theme.typography.fontFamily.regular,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.primary,
  },
  filtersContainer: {
    paddingHorizontal: theme.spacing.lg,
    paddingBottom: theme.spacing.md,
    gap: theme.spacing.sm,
  },
  filterChip: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    borderRadius: theme.borderRadius.full,
    backgroundColor: theme.colors.background.secondary,
    gap: theme.spacing.xs,
  },
  filterChipActive: {
    backgroundColor: 'transparent',
  },
  filterChipGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    borderRadius: theme.borderRadius.full,
    gap: theme.spacing.xs,
  },
  filterChipText: {
    fontFamily: theme.typography.fontFamily.medium,
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.secondary,
  },
  filterChipTextActive: {
    color: theme.colors.text.inverse,
  },
  charactersContainer: {
    paddingVertical: theme.spacing.md,
    gap: theme.spacing.lg,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: theme.spacing['3xl'],
  },
  emptyStateText: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize.xl,
    color: theme.colors.text.secondary,
    marginTop: theme.spacing.md,
  },
  emptyStateSubtext: {
    fontFamily: theme.typography.fontFamily.regular,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.tertiary,
    marginTop: theme.spacing.xs,
  },
});
