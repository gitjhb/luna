/**
 * MemoriesModal Component
 * 
 * Shows all generated event memories for a character.
 * Allows users to re-read past stories.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  ScrollView,
  Dimensions,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import Animated, {
  FadeIn,
  FadeInDown,
  Layout,
} from 'react-native-reanimated';
import { eventService, EventMemory } from '../services/eventService';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

interface MemoriesModalProps {
  visible: boolean;
  onClose: () => void;
  characterId: string;
  characterName: string;
  onSelectMemory: (memory: EventMemory) => void;
}

export default function MemoriesModal({
  visible,
  onClose,
  characterId,
  characterName,
  onSelectMemory,
}: MemoriesModalProps) {
  const [memories, setMemories] = useState<EventMemory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  const loadMemories = useCallback(async () => {
    try {
      const data = await eventService.getEventMemories(characterId);
      setMemories(data);
    } catch (error) {
      console.error('Failed to load memories:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [characterId]);
  
  useEffect(() => {
    if (visible) {
      setIsLoading(true);
      loadMemories();
    }
  }, [visible, loadMemories]);
  
  const handleRefresh = () => {
    setIsRefreshing(true);
    loadMemories();
  };
  
  const renderMemoryCard = (memory: EventMemory, index: number) => {
    const eventInfo = eventService.getEventInfo(memory.event_type);
    const date = memory.generated_at 
      ? new Date(memory.generated_at).toLocaleDateString('zh-CN', {
          month: 'short',
          day: 'numeric',
        })
      : '';
    
    // Preview of story content (first 80 chars)
    const preview = memory.story_content.slice(0, 80) + '...';
    
    return (
      <Animated.View
        key={memory.id}
        entering={FadeInDown.delay(index * 100).springify()}
        layout={Layout.springify()}
      >
        <TouchableOpacity
          style={styles.memoryCard}
          onPress={() => onSelectMemory(memory)}
          activeOpacity={0.8}
        >
          <LinearGradient
            colors={['rgba(139, 92, 246, 0.15)', 'rgba(236, 72, 153, 0.15)']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.memoryGradient}
          >
            {/* Header */}
            <View style={styles.memoryHeader}>
              <View style={styles.memoryIconContainer}>
                <Text style={styles.memoryIcon}>{eventInfo.icon}</Text>
              </View>
              <View style={styles.memoryInfo}>
                <Text style={styles.memoryTitle}>{eventInfo.name_cn}</Text>
                <Text style={styles.memoryDate}>{date}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="rgba(255,255,255,0.5)" />
            </View>
            
            {/* Preview */}
            <Text style={styles.memoryPreview} numberOfLines={2}>
              {preview}
            </Text>
          </LinearGradient>
        </TouchableOpacity>
      </Animated.View>
    );
  };
  
  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        <LinearGradient
          colors={['rgba(26, 16, 37, 0.98)', 'rgba(15, 10, 25, 0.99)']}
          style={styles.gradient}
        >
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerLeft}>
              <Text style={styles.headerIcon}>📖</Text>
              <View>
                <Text style={styles.headerTitle}>回忆录</Text>
                <Text style={styles.headerSubtitle}>与{characterName}的回忆</Text>
              </View>
            </View>
            <TouchableOpacity style={styles.closeButton} onPress={onClose}>
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>
          </View>
          
          {/* Content */}
          {isLoading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#EC4899" />
              <Text style={styles.loadingText}>加载中...</Text>
            </View>
          ) : memories.length === 0 ? (
            <View style={styles.emptyContainer}>
              <Animated.View entering={FadeIn.delay(200)}>
                <Text style={styles.emptyIcon}>💭</Text>
                <Text style={styles.emptyTitle}>还没有回忆</Text>
                <Text style={styles.emptySubtitle}>
                  继续和{characterName}聊天，解锁更多精彩剧情！
                </Text>
              </Animated.View>
            </View>
          ) : (
            <ScrollView
              style={styles.scrollView}
              contentContainerStyle={styles.scrollContent}
              showsVerticalScrollIndicator={false}
              refreshControl={
                <RefreshControl
                  refreshing={isRefreshing}
                  onRefresh={handleRefresh}
                  tintColor="#EC4899"
                />
              }
            >
              {/* Stats */}
              <Animated.View entering={FadeIn.delay(100)} style={styles.statsContainer}>
                <View style={styles.statItem}>
                  <Text style={styles.statNumber}>{memories.length}</Text>
                  <Text style={styles.statLabel}>段回忆</Text>
                </View>
              </Animated.View>
              
              {/* Memory cards */}
              {memories.map((memory, index) => renderMemoryCard(memory, index))}
              
              {/* Bottom spacing */}
              <View style={{ height: 40 }} />
            </ScrollView>
          )}
        </LinearGradient>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  gradient: {
    flex: 1,
    marginTop: 60,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  headerIcon: {
    fontSize: 32,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#fff',
  },
  headerSubtitle: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.5)',
  },
  closeButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.6)',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
  },
  emptyIcon: {
    fontSize: 64,
    textAlign: 'center',
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#fff',
    textAlign: 'center',
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.5)',
    textAlign: 'center',
    lineHeight: 22,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: 20,
  },
  statItem: {
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 16,
  },
  statNumber: {
    fontSize: 28,
    fontWeight: '700',
    color: '#EC4899',
  },
  statLabel: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.5)',
    marginTop: 2,
  },
  memoryCard: {
    marginBottom: 16,
    borderRadius: 16,
    overflow: 'hidden',
  },
  memoryGradient: {
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 16,
  },
  memoryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  memoryIconContainer: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  memoryIcon: {
    fontSize: 22,
  },
  memoryInfo: {
    flex: 1,
    marginLeft: 12,
  },
  memoryTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  memoryDate: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.4)',
    marginTop: 2,
  },
  memoryPreview: {
    fontSize: 14,
    lineHeight: 22,
    color: 'rgba(255, 255, 255, 0.6)',
  },
});
