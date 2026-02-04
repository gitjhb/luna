/**
 * Character Info Panel
 * 
 * 角色信息面板 - 显示角色详情、历史事件、礼物记录、记忆等
 * 所有数据从后端 API 获取
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  ScrollView,
  Image,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../theme/config';
import { getCharacterAvatar } from '../assets/characters';
import { api } from '../services/api';
import { intimacyService } from '../services/intimacyService';
import { emotionService } from '../services/emotionService';
import { useUserStore } from '../store/userStore';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// 事件类型图标映射
const EVENT_ICONS: Record<string, { icon: string; color: string }> = {
  'first_meet': { icon: 'sparkles', color: '#FFD700' },
  'kiss': { icon: 'heart', color: '#FF69B4' },
  'date': { icon: 'cafe', color: '#FF6B6B' },
  'gift': { icon: 'gift', color: '#9B59B6' },
  'cold_war': { icon: 'snow', color: '#74B9FF' },
  'makeup': { icon: 'sunny', color: '#F39C12' },
  'confession': { icon: 'heart-circle', color: '#E74C3C' },
  'anniversary': { icon: 'ribbon', color: '#E056FD' },
  'level_up': { icon: 'trending-up', color: '#00D9FF' },
  'unlock': { icon: 'lock-open', color: '#2ECC71' },
  'message': { icon: 'chatbubble', color: '#95A5A6' },
};

interface HistoryEvent {
  id: string;
  type: string;
  title: string;
  description: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

interface GiftRecord {
  id: string;
  giftName: string;
  giftIcon: string;
  count: number;
  lastSentAt: string;
}

interface MemoryEntry {
  id: string;
  content: string;
  importance: 'low' | 'medium' | 'high';
  createdAt: string;
}

interface RelationshipStats {
  streakDays: number;
  totalMessages: number;
  totalGifts: number;
  specialEvents: number;
}

interface CharacterInfoPanelProps {
  visible: boolean;
  onClose: () => void;
  characterId: string;
  characterName: string;
  avatarUrl?: string;
  intimacyLevel?: number;
  emotionScore?: number;
  emotionState?: string;
  onOpenMemories?: () => void;
}

type TabType = 'profile' | 'events' | 'gifts' | 'gallery' | 'memory';

export default function CharacterInfoPanel({
  visible,
  onClose,
  characterId,
  characterName,
  avatarUrl,
  intimacyLevel: propIntimacyLevel,
  emotionScore: propEmotionScore,
  emotionState: propEmotionState,
  onOpenMemories,
}: CharacterInfoPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>('profile');
  const [loading, setLoading] = useState(false);
  
  // Get VIP status - only VIP can see emotion
  const isVip = useUserStore((s) => s.isVip);
  
  // State from API
  const [intimacyLevel, setIntimacyLevel] = useState(propIntimacyLevel || 1);
  const [emotionScore, setEmotionScore] = useState(propEmotionScore || 0);
  const [emotionState, setEmotionState] = useState(propEmotionState || 'neutral');
  const [stats, setStats] = useState<RelationshipStats>({
    streakDays: 0,
    totalMessages: 0,
    totalGifts: 0,
    specialEvents: 0,
  });
  const [events, setEvents] = useState<HistoryEvent[]>([]);
  const [gifts, setGifts] = useState<GiftRecord[]>([]);
  const [gallery, setGallery] = useState<{scene: string; name: string; photoType: string; image: any; unlocked: boolean}[]>([]);
  const [selectedPhoto, setSelectedPhoto] = useState<{image: any; name: string} | null>(null);
  const [memories, setMemories] = useState<MemoryEntry[]>([]);

  // Load data when panel opens
  useEffect(() => {
    if (visible && characterId) {
      loadAllData();
    }
  }, [visible, characterId]);

  const loadAllData = async () => {
    setLoading(true);
    
    // Load all data in parallel
    await Promise.all([
      loadIntimacy(),
      loadEmotion(),
      loadStats(),
      loadEvents(),
      loadGifts(),
      loadGallery(),
      loadMemories(),
    ]);
    
    setLoading(false);
  };

  const loadIntimacy = async () => {
    try {
      const data = await intimacyService.getStatus(characterId);
      setIntimacyLevel(data.currentLevel);
      setStats(prev => ({
        ...prev,
        streakDays: data.streakDays || 0,
      }));
    } catch (e) {
      console.log('Failed to load intimacy:', e);
    }
  };

  const loadEmotion = async () => {
    try {
      const data = await emotionService.getStatus(characterId);
      if (data) {
        // Convert emotionIntensity (0-100) to score (-100 to 100)
        // negative emotions have negative score
        const negativeStates = ['annoyed', 'angry', 'hurt', 'cold', 'silent'];
        const isNegative = negativeStates.includes(data.emotionalState);
        const score = isNegative ? -data.emotionIntensity : data.emotionIntensity;
        setEmotionScore(score);
        setEmotionState(data.emotionalState || 'neutral');
      }
    } catch (e) {
      console.log('Failed to load emotion:', e);
    }
  };

  const loadStats = async () => {
    try {
      const data = await api.get<any>(`/characters/${characterId}/stats`);
      setStats({
        streakDays: data.streak_days || data.streakDays || 0,
        totalMessages: data.total_messages || data.totalMessages || 0,
        totalGifts: data.total_gifts || data.totalGifts || 0,
        specialEvents: data.special_events || data.specialEvents || 0,
      });
    } catch (e) {
      console.log('Stats API not available');
    }
  };

  const loadEvents = async () => {
    try {
      const data = await api.get<any[]>(`/characters/${characterId}/events`);
      setEvents(data.map(e => ({
        id: e.id || e.event_id,
        type: e.type || e.event_type || 'message',
        title: e.title,
        description: e.description,
        timestamp: e.timestamp || e.created_at,
      })));
    } catch (e) {
      console.log('Events API not available');
      setEvents([]);
    }
  };

  const loadGifts = async () => {
    try {
      const data = await api.get<any[]>(`/gifts/history`, { character_id: characterId });
      // Group by gift type
      const giftMap = new Map<string, GiftRecord>();
      data.forEach(g => {
        const key = g.gift_type || g.giftType;
        const existing = giftMap.get(key);
        if (existing) {
          existing.count++;
          existing.lastSentAt = g.created_at || g.createdAt;
        } else {
          giftMap.set(key, {
            id: key,
            giftName: g.gift_name_cn || g.gift_name || g.giftName || key,
            giftIcon: g.icon || getGiftIcon(key),
            count: 1,
            lastSentAt: g.created_at || g.createdAt,
          });
        }
      });
      setGifts(Array.from(giftMap.values()));
    } catch (e) {
      console.log('Gifts API not available');
      setGifts([]);
    }
  };

  // 所有可解锁的照片配置（按角色）
  // 每个场景有 3 种图片：基础版、普通版、完美版
  const getAllPhotos = (charId: string) => {
    // Sakura 的场景照片
    if (charId === 'e3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e') {
      return [
        // 卧室 - 3 张
        { scene: 'bedroom', name: '卧室', photoType: 'base', image: require('../assets/characters/sakura/scenes/bedroom.jpeg') },
        { scene: 'bedroom', name: '卧室 💕', photoType: 'normal', image: require('../assets/characters/sakura/scenes/bedroom-normal.jpeg') },
        { scene: 'bedroom', name: '卧室 ✨', photoType: 'perfect', image: require('../assets/characters/sakura/scenes/bedroom-perfect.jpeg') },
        // 沙滩 - 3 张
        { scene: 'beach', name: '沙滩', photoType: 'base', image: require('../assets/characters/sakura/scenes/beach.jpeg') },
        { scene: 'beach', name: '沙滩 💕', photoType: 'normal', image: require('../assets/characters/sakura/scenes/beach-normal.jpeg') },
        { scene: 'beach', name: '沙滩 ✨', photoType: 'perfect', image: require('../assets/characters/sakura/scenes/beach-perfect.jpeg') },
        // 海边 - 3 张
        { scene: 'ocean', name: '海边', photoType: 'base', image: require('../assets/characters/sakura/scenes/ocean.jpeg') },
        { scene: 'ocean', name: '海边 💕', photoType: 'normal', image: require('../assets/characters/sakura/scenes/ocean-normal.jpeg') },
        { scene: 'ocean', name: '海边 ✨', photoType: 'perfect', image: require('../assets/characters/sakura/scenes/ocean-perfect.jpeg') },
        // 学校 - 3 张
        { scene: 'school', name: '学校', photoType: 'base', image: require('../assets/characters/sakura/scenes/school.jpeg') },
        { scene: 'school', name: '学校 💕', photoType: 'normal', image: require('../assets/characters/sakura/scenes/school-normal.jpeg') },
        { scene: 'school', name: '学校 ✨', photoType: 'perfect', image: require('../assets/characters/sakura/scenes/school-perfect.jpeg') },
      ];
    }
    return [];
  };

  const loadGallery = async () => {
    try {
      const data = await api.get<any[]>(`/characters/${characterId}/gallery`);
      // 新格式：{id, scene, photo_type, source, unlocked_at}
      // 转换为 Set 方便查找
      const unlockedSet = new Set(data.map(g => `${g.scene}:${g.photo_type}`));
      
      // 获取该角色的所有可能照片
      const allPhotos = getAllPhotos(characterId);
      
      // 构建完整的照片列表（包含解锁状态）
      const photoList = allPhotos.map(photo => ({
        ...photo,
        unlocked: unlockedSet.has(`${photo.scene}:${photo.photoType}`),
      }));
      
      setGallery(photoList);
    } catch (e) {
      console.log('Gallery API not available');
      // 即使 API 失败，也显示所有可能的照片（全锁定）
      const allPhotos = getAllPhotos(characterId);
      const photoList = allPhotos.map(photo => ({
        ...photo,
        unlocked: false,
      }));
      setGallery(photoList);
    }
  };

  const loadMemories = async () => {
    try {
      const data = await api.get<any[]>(`/characters/${characterId}/memories`);
      setMemories(data.map(m => ({
        id: m.id || m.memory_id,
        content: m.content,
        importance: m.importance || 'medium',
        createdAt: m.created_at || m.createdAt,
      })));
    } catch (e) {
      console.log('Memories API not available');
      setMemories([]);
    }
  };

  const getGiftIcon = (giftType: string): string => {
    const icons: Record<string, string> = {
      rose: '🌹',
      chocolate: '🍫',
      coffee: '☕',
      bear: '🧸',
      diamond: '💎',
      crown: '👑',
      castle: '🏰',
    };
    return icons[giftType] || '🎁';
  };

  // 情绪状态颜色
  const getEmotionColor = () => {
    if (emotionScore >= 50) return '#2ECC71';
    if (emotionScore >= 0) return '#F39C12';
    if (emotionScore >= -50) return '#E67E22';
    return '#E74C3C';
  };

  // 情绪状态文本
  const getEmotionText = () => {
    if (emotionScore >= 75) return '甜蜜 💕';
    if (emotionScore >= 50) return '开心 😊';
    if (emotionScore >= 20) return '满足 🙂';
    if (emotionScore >= -20) return '平静 😐';
    if (emotionScore >= -50) return '不满 😒';
    if (emotionScore >= -75) return '生气 😠';
    return '冷战 ❄️';
  };

  const renderTabs = () => (
    <View style={styles.tabBar}>
      {[
        { key: 'profile', icon: 'person', label: '资料' },
        { key: 'events', icon: 'time', label: '事件' },
        { key: 'gifts', icon: 'gift', label: '礼物' },
        { key: 'gallery', icon: 'images', label: '相册' },
        { key: 'memory', icon: 'bulb', label: '记忆' },
      ].map((tab) => (
        <TouchableOpacity
          key={tab.key}
          style={[styles.tab, activeTab === tab.key && styles.tabActive]}
          onPress={() => setActiveTab(tab.key as TabType)}
        >
          <Ionicons
            name={tab.icon as any}
            size={20}
            color={activeTab === tab.key ? theme.colors.primary.main : theme.colors.text.tertiary}
          />
          <Text style={[styles.tabText, activeTab === tab.key && styles.tabTextActive]}>
            {tab.label}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );

  // 资料页
  const renderProfile = () => (
    <ScrollView style={styles.profileContent} showsVerticalScrollIndicator={false}>
      {/* 高清头像 */}
      <View style={styles.avatarSection}>
        <Image
          source={getCharacterAvatar(characterId, avatarUrl)}
          style={styles.largeAvatar}
          resizeMode="cover"
        />
        <LinearGradient
          colors={['transparent', 'rgba(26,16,37,0.9)']}
          style={styles.avatarGradient}
        />
        <View style={styles.avatarInfo}>
          <Text style={styles.characterNameLarge}>{characterName}</Text>
          <View style={styles.levelBadge}>
            <Ionicons name="heart" size={14} color="#FF69B4" />
            <Text style={styles.levelText}>Lv.{intimacyLevel}</Text>
          </View>
        </View>
      </View>

      {/* 📖 回忆录入口 */}
      {onOpenMemories && (
        <TouchableOpacity style={styles.memoriesButton} onPress={onOpenMemories}>
          <LinearGradient
            colors={['rgba(139, 92, 246, 0.2)', 'rgba(236, 72, 153, 0.2)']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.memoriesButtonGradient}
          >
            <Text style={styles.memoriesButtonIcon}>📖</Text>
            <View style={styles.memoriesButtonContent}>
              <Text style={styles.memoriesButtonTitle}>回忆录</Text>
              <Text style={styles.memoriesButtonSubtitle}>重温与{characterName}的精彩时刻</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="rgba(255,255,255,0.5)" />
          </LinearGradient>
        </TouchableOpacity>
      )}

      {/* 情绪状态 */}
      <View style={styles.statsCard}>
        <Text style={styles.cardTitle}>当前状态</Text>
        {isVip ? (
          <View style={styles.emotionRow}>
            <View style={styles.emotionItem}>
              <Text style={styles.emotionLabel}>情绪</Text>
              <View style={styles.emotionBar}>
                <View 
                  style={[
                    styles.emotionFill, 
                    { 
                      width: `${(emotionScore + 100) / 2}%`,
                      backgroundColor: getEmotionColor(),
                    }
                  ]} 
                />
              </View>
              <Text style={[styles.emotionValue, { color: getEmotionColor() }]}>
                {emotionScore > 0 ? '+' : ''}{emotionScore} {getEmotionText()}
              </Text>
            </View>
          </View>
        ) : (
          <View style={styles.lockedEmotionContainer}>
            <BlurView intensity={20} style={styles.emotionBlur}>
              <View style={styles.emotionRow}>
                <View style={styles.emotionItem}>
                  <Text style={styles.emotionLabel}>情绪</Text>
                  <View style={styles.emotionBar}>
                    <View style={[styles.emotionFill, { width: '50%', backgroundColor: '#666' }]} />
                  </View>
                  <Text style={styles.emotionValue}>??? ???</Text>
                </View>
              </View>
            </BlurView>
            <View style={styles.upgradeOverlay}>
              <Ionicons name="lock-closed" size={24} color="#FFD700" />
              <Text style={styles.upgradeText}>升级到 VIP 解锁</Text>
              <Text style={styles.upgradeSubtext}>了解 TA 的真实情绪</Text>
            </View>
          </View>
        )}
      </View>

    </ScrollView>
  );

  // 事件页
  const renderEvents = () => (
    <ScrollView style={styles.tabContent} showsVerticalScrollIndicator={false}>
      <Text style={styles.sectionTitle}>历史事件</Text>
      {events.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="time-outline" size={48} color={theme.colors.text.tertiary} />
          <Text style={styles.emptyText}>还没有特殊事件</Text>
        </View>
      ) : (
        events.map((event, index) => {
          const eventConfig = EVENT_ICONS[event.type] || { icon: 'ellipse', color: '#95A5A6' };
          return (
            <View key={event.id} style={styles.eventItem}>
              <View style={[styles.eventIcon, { backgroundColor: eventConfig.color + '20' }]}>
                <Ionicons name={eventConfig.icon as any} size={20} color={eventConfig.color} />
              </View>
              <View style={styles.eventContent}>
                <Text style={styles.eventTitle}>{event.title}</Text>
                <Text style={styles.eventDesc}>{event.description}</Text>
                <Text style={styles.eventTime}>{event.timestamp}</Text>
              </View>
              {index < events.length - 1 && <View style={styles.eventLine} />}
            </View>
          );
        })
      )}
    </ScrollView>
  );

  // 礼物页
  const renderGifts = () => (
    <ScrollView style={styles.tabContent} showsVerticalScrollIndicator={false}>
      <Text style={styles.sectionTitle}>礼物记录</Text>
      {gifts.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="gift-outline" size={48} color={theme.colors.text.tertiary} />
          <Text style={styles.emptyText}>还没有送过礼物</Text>
        </View>
      ) : (
        <View style={styles.giftGrid}>
          {gifts.map((gift) => (
            <View key={gift.id} style={styles.giftItem}>
              <Text style={styles.giftIcon}>{gift.giftIcon}</Text>
              <Text style={styles.giftName}>{gift.giftName}</Text>
              <Text style={styles.giftCount}>×{gift.count}</Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );

  // 相册页
  const renderGallery = () => {
    const unlockedCount = gallery.filter(p => p.unlocked).length;
    const totalCount = gallery.length;
    
    return (
      <ScrollView style={styles.tabContent} showsVerticalScrollIndicator={false}>
        <View style={styles.galleryHeader}>
          <Text style={styles.sectionTitle}>照片收集</Text>
          <Text style={styles.galleryProgress}>{unlockedCount}/{totalCount}</Text>
        </View>
        <Text style={styles.galleryHint}>💡 约会获得好结局可以解锁照片</Text>
        
        <View style={styles.galleryGrid}>
          {gallery.map((photo, index) => (
            <TouchableOpacity 
              key={`${photo.scene}-${photo.photoType}-${index}`} 
              style={styles.galleryItem}
              activeOpacity={photo.unlocked ? 0.7 : 1}
              onPress={() => {
                if (photo.unlocked) {
                  setSelectedPhoto({ image: photo.image, name: photo.name });
                }
              }}
            >
              {photo.unlocked ? (
                // 解锁：显示真实图片
                <Image 
                  source={photo.image} 
                  style={styles.galleryImage}
                />
              ) : (
                // 未解锁：只显示占位背景，不加载原图
                <View style={[styles.galleryImage, styles.lockedPlaceholder]}>
                  <LinearGradient
                    colors={['#2a1a3a', '#1a1025']}
                    style={StyleSheet.absoluteFillObject}
                  />
                </View>
              )}
              {!photo.unlocked && (
                <View style={styles.lockedOverlay}>
                  <Ionicons name="lock-closed" size={24} color="#fff" />
                </View>
              )}
              {photo.unlocked && photo.photoType === 'perfect' && (
                <View style={styles.perfectBadge}>
                  <Text style={styles.perfectBadgeText}>💕</Text>
                </View>
              )}
              <View style={styles.photoLabel}>
                <Text style={styles.photoLabelText}>{photo.name}</Text>
              </View>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>
    );
  };
  
  // 照片全屏查看 Modal
  const renderPhotoModal = () => (
    <Modal
      visible={!!selectedPhoto}
      transparent
      animationType="fade"
      onRequestClose={() => setSelectedPhoto(null)}
    >
      <TouchableOpacity 
        style={styles.photoModalOverlay}
        activeOpacity={1}
        onPress={() => setSelectedPhoto(null)}
      >
        <TouchableOpacity 
          style={styles.photoModalClose}
          onPress={() => setSelectedPhoto(null)}
        >
          <Ionicons name="close" size={28} color="#fff" />
        </TouchableOpacity>
        {selectedPhoto && (
          <>
            <Image
              source={selectedPhoto.image}
              style={styles.photoModalImage}
              resizeMode="contain"
            />
            <Text style={styles.photoModalName}>{selectedPhoto.name}</Text>
          </>
        )}
      </TouchableOpacity>
    </Modal>
  );

  // 记忆页 (Debug)
  const renderMemory = () => (
    <ScrollView style={styles.tabContent} showsVerticalScrollIndicator={false}>
      <View style={styles.debugHeader}>
        <Text style={styles.sectionTitle}>角色记忆</Text>
        <View style={styles.debugBadge}>
          <Text style={styles.debugBadgeText}>DEBUG</Text>
        </View>
      </View>
      
      {memories.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="bulb-outline" size={48} color={theme.colors.text.tertiary} />
          <Text style={styles.emptyText}>还没有记忆</Text>
        </View>
      ) : (
        memories.map((memory) => (
          <View key={memory.id} style={styles.memoryItem}>
            <View style={styles.memoryHeader}>
              <View style={[
                styles.importanceDot,
                { backgroundColor: memory.importance === 'high' ? '#E74C3C' : 
                  memory.importance === 'medium' ? '#F39C12' : '#95A5A6' }
              ]} />
              <Text style={styles.memoryDate}>{memory.createdAt}</Text>
            </View>
            <Text style={styles.memoryContent}>{memory.content}</Text>
          </View>
        ))
      )}

      {/* Debug 信息 */}
      <View style={styles.debugSection}>
        <Text style={styles.debugTitle}>状态数据</Text>
        <View style={styles.debugCode}>
          <Text style={styles.debugText}>
            {JSON.stringify({
              characterId,
              intimacyLevel,
              emotionScore,
              emotionState,
              stats,
            }, null, 2)}
          </Text>
        </View>
      </View>
    </ScrollView>
  );

  const renderContent = () => {
    switch (activeTab) {
      case 'profile': return renderProfile();
      case 'events': return renderEvents();
      case 'gifts': return renderGifts();
      case 'gallery': return renderGallery();
      case 'memory': return renderMemory();
      default: return renderProfile();
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={true}
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        <BlurView intensity={20} style={styles.blurBackground} />
        
        <View style={styles.panel}>
          {/* Header */}
          <View style={styles.header}>
            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>{characterName}</Text>
            <View style={{ width: 40 }} />
          </View>

          {/* Tabs */}
          {renderTabs()}

          {/* Content */}
          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color={theme.colors.primary.main} />
            </View>
          ) : (
            renderContent()
          )}
        </View>
      </View>
      
      {/* Photo Fullscreen Modal */}
      {renderPhotoModal()}
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  blurBackground: {
    ...StyleSheet.absoluteFillObject,
  },
  panel: {
    height: SCREEN_HEIGHT * 0.85,
    backgroundColor: 'rgba(26, 16, 37, 0.98)',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  closeButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  tabBar: {
    flexDirection: 'row',
    paddingHorizontal: 8,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 8,
    borderRadius: 8,
  },
  tabActive: {
    backgroundColor: 'rgba(236, 72, 153, 0.15)',
  },
  tabText: {
    fontSize: 11,
    color: theme.colors.text.tertiary,
    marginTop: 4,
  },
  tabTextActive: {
    color: theme.colors.primary.main,
  },
  tabContent: {
    flex: 1,
    padding: 16,
  },
  profileContent: {
    flex: 1,
    padding: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  
  // Profile Tab
  avatarSection: {
    height: 420,
    borderRadius: 0,
    overflow: 'hidden',
    marginBottom: 16,
    marginHorizontal: -16,
    marginTop: -16,
  },
  largeAvatar: {
    width: '100%',
    height: '100%',
  },
  avatarGradient: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: '60%',
  },
  avatarInfo: {
    position: 'absolute',
    bottom: 20,
    left: 20,
    right: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  characterNameLarge: {
    fontSize: 28,
    fontWeight: '700',
    color: '#fff',
    textShadowColor: 'rgba(0,0,0,0.5)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 4,
  },
  levelBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,105,180,0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    gap: 4,
  },
  levelText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FF69B4',
  },
  statsCard: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    marginTop: 8,
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.text.secondary,
    marginBottom: 12,
  },
  emotionRow: {
    gap: 12,
  },
  emotionItem: {
    gap: 8,
  },
  emotionLabel: {
    fontSize: 12,
    color: theme.colors.text.tertiary,
  },
  emotionBar: {
    height: 8,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 4,
    overflow: 'hidden',
  },
  emotionFill: {
    height: '100%',
    borderRadius: 4,
  },
  emotionValue: {
    fontSize: 14,
    fontWeight: '600',
  },
  lockedEmotionContainer: {
    position: 'relative',
    overflow: 'hidden',
    borderRadius: 12,
  },
  emotionBlur: {
    padding: 8,
  },
  upgradeOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 12,
  },
  upgradeText: {
    color: '#FFD700',
    fontSize: 16,
    fontWeight: '700',
    marginTop: 8,
  },
  upgradeSubtext: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 12,
    marginTop: 4,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  statItem: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
  },
  statLabel: {
    fontSize: 12,
    color: theme.colors.text.tertiary,
    marginTop: 4,
  },

  // Events Tab
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 16,
  },
  eventItem: {
    flexDirection: 'row',
    marginBottom: 16,
    position: 'relative',
  },
  eventIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  eventContent: {
    flex: 1,
  },
  eventTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
  },
  eventDesc: {
    fontSize: 13,
    color: theme.colors.text.secondary,
    marginTop: 2,
  },
  eventTime: {
    fontSize: 11,
    color: theme.colors.text.tertiary,
    marginTop: 4,
  },
  eventLine: {
    position: 'absolute',
    left: 19,
    top: 44,
    width: 2,
    height: 20,
    backgroundColor: 'rgba(255,255,255,0.1)',
  },

  // Gifts Tab
  giftGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  giftItem: {
    width: (SCREEN_WIDTH - 64) / 3,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
  },
  giftIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  giftName: {
    fontSize: 13,
    color: '#fff',
    fontWeight: '500',
  },
  giftCount: {
    fontSize: 12,
    color: theme.colors.text.tertiary,
    marginTop: 2,
  },

  // Gallery Tab
  galleryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  galleryItem: {
    width: (SCREEN_WIDTH - 48) / 3,
    aspectRatio: 1,
    borderRadius: 8,
    overflow: 'hidden',
  },
  galleryImage: {
    width: '100%',
    height: '100%',
  },
  galleryHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  galleryProgress: {
    fontSize: 14,
    color: '#FF6B9D',
    fontWeight: '600',
  },
  galleryHint: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.5)',
    marginBottom: 16,
  },
  galleryImageLocked: {
    opacity: 0.6,
  },
  lockedOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 8,
  },
  perfectBadge: {
    position: 'absolute',
    top: 4,
    right: 4,
    backgroundColor: 'rgba(255,107,157,0.9)',
    borderRadius: 10,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  perfectBadgeText: {
    fontSize: 12,
  },
  photoLabel: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(0,0,0,0.6)',
    paddingVertical: 4,
    paddingHorizontal: 6,
    borderBottomLeftRadius: 8,
    borderBottomRightRadius: 8,
  },
  photoLabelText: {
    fontSize: 11,
    color: '#fff',
    textAlign: 'center',
  },

  // Memory Tab
  debugHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  debugBadge: {
    backgroundColor: '#E74C3C',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  debugBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#fff',
  },
  memoryItem: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
  },
  memoryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  importanceDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  memoryDate: {
    fontSize: 11,
    color: theme.colors.text.tertiary,
  },
  memoryContent: {
    fontSize: 14,
    color: '#fff',
    lineHeight: 20,
  },
  debugSection: {
    marginTop: 24,
  },
  debugTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#E74C3C',
    marginBottom: 8,
  },
  debugCode: {
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 8,
    padding: 12,
  },
  debugText: {
    fontSize: 11,
    fontFamily: 'monospace',
    color: '#2ECC71',
  },

  // Empty State
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    fontSize: 15,
    color: theme.colors.text.secondary,
    marginTop: 12,
  },
  emptySubtext: {
    fontSize: 13,
    color: theme.colors.text.tertiary,
    marginTop: 4,
  },
  
  // Memories Button
  memoriesButton: {
    marginBottom: 16,
    borderRadius: 16,
    overflow: 'hidden',
  },
  memoriesButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.3)',
    borderRadius: 16,
  },
  memoriesButtonIcon: {
    fontSize: 28,
    marginRight: 12,
  },
  memoriesButtonContent: {
    flex: 1,
  },
  memoriesButtonTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  memoriesButtonSubtitle: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.5)',
    marginTop: 2,
  },
  
  // Locked Placeholder (no image loaded)
  lockedPlaceholder: {
    backgroundColor: '#1a1025',
  },
  
  // Photo Fullscreen Modal
  photoModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.95)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  photoModalClose: {
    position: 'absolute',
    top: 60,
    right: 20,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  photoModalImage: {
    width: SCREEN_WIDTH * 0.95,
    height: SCREEN_HEIGHT * 0.7,
  },
  photoModalName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginTop: 16,
    textAlign: 'center',
  },
});
