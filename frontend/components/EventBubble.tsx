/**
 * EventBubble Component
 * 
 * 通用事件气泡组件，用于显示约会、礼物、里程碑等事件。
 * 
 * Features:
 * - 根据 event_type 显示不同样式和图标
 * - 支持点击展开详情
 * - 付费解锁详情功能
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withRepeat,
  withSequence,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { eventService } from '../services/eventService';
import { api } from '../services/api';
import { useUserStore } from '../store/userStore';

// 事件类型配置
const EVENT_CONFIG: Record<string, {
  icon: string;
  name_cn: string;
  gradientColors: [string, string];
  borderColor: string;
}> = {
  date: {
    icon: '💕',
    name_cn: '约会',
    gradientColors: ['rgba(236, 72, 153, 0.2)', 'rgba(168, 85, 247, 0.2)'],
    borderColor: '#EC4899',
  },
  gift: {
    icon: '🎁',
    name_cn: '礼物',
    gradientColors: ['rgba(251, 191, 36, 0.2)', 'rgba(245, 158, 11, 0.2)'],
    borderColor: '#FBBF24',
  },
  milestone: {
    icon: '🎉',
    name_cn: '里程碑',
    gradientColors: ['rgba(139, 92, 246, 0.2)', 'rgba(99, 102, 241, 0.2)'],
    borderColor: '#8B5CF6',
  },
  confession: {
    icon: '💝',
    name_cn: '表白',
    gradientColors: ['rgba(244, 63, 94, 0.2)', 'rgba(251, 113, 133, 0.2)'],
    borderColor: '#F43F5E',
  },
  kiss: {
    icon: '💋',
    name_cn: '初吻',
    gradientColors: ['rgba(244, 63, 94, 0.25)', 'rgba(190, 24, 93, 0.25)'],
    borderColor: '#F43F5E',
  },
  intimate: {
    icon: '🔥',
    name_cn: '亲密时刻',
    gradientColors: ['rgba(239, 68, 68, 0.25)', 'rgba(185, 28, 28, 0.25)'],
    borderColor: '#EF4444',
  },
  mood: {
    icon: '💭',
    name_cn: '心情变化',
    gradientColors: ['rgba(96, 165, 250, 0.2)', 'rgba(59, 130, 246, 0.2)'],
    borderColor: '#60A5FA',
  },
};

// 事件消息接口
export interface EventMessageData {
  type: 'event';
  event_type: string;
  summary: string;
  detail_id?: string;
  icon?: string;
  display?: {
    title: string;
    subtitle: string;
  };
  unlock_cost?: number;
  is_unlocked?: boolean;
  metadata?: Record<string, any>;
}

interface EventBubbleProps {
  eventData: EventMessageData;
  characterId: string;
  characterName?: string;
  onDetailViewed?: () => void;
}

const AnimatedTouchable = Animated.createAnimatedComponent(TouchableOpacity);

export default function EventBubble({
  eventData,
  characterId,
  characterName = '角色',
  onDetailViewed,
}: EventBubbleProps) {
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [detailContent, setDetailContent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isUnlocked, setIsUnlocked] = useState(eventData.is_unlocked || false);
  
  const { wallet, updateWallet } = useUserStore();
  
  // 动画值
  const scale = useSharedValue(1);
  const glowOpacity = useSharedValue(0.5);
  
  // 呼吸灯效果（未解锁时）
  React.useEffect(() => {
    if (!isUnlocked && eventData.detail_id) {
      glowOpacity.value = withRepeat(
        withSequence(
          withTiming(1, { duration: 1000, easing: Easing.inOut(Easing.ease) }),
          withTiming(0.5, { duration: 1000, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        true
      );
    }
  }, [isUnlocked]);
  
  const cardAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));
  
  const glowAnimatedStyle = useAnimatedStyle(() => ({
    opacity: glowOpacity.value,
  }));
  
  const handlePressIn = () => {
    scale.value = withSpring(0.96, { damping: 15 });
  };
  
  const handlePressOut = () => {
    scale.value = withSpring(1, { damping: 10 });
  };
  
  // 获取事件配置
  const config = EVENT_CONFIG[eventData.event_type] || {
    icon: eventData.icon || '📖',
    name_cn: eventData.event_type,
    gradientColors: ['rgba(107, 114, 128, 0.2)', 'rgba(75, 85, 99, 0.2)'] as [string, string],
    borderColor: '#6B7280',
  };
  
  const displayIcon = eventData.icon || config.icon;
  const displayTitle = eventData.display?.title || config.name_cn;
  const displaySubtitle = eventData.display?.subtitle || eventData.summary;
  const unlockCost = eventData.unlock_cost || 0;
  const hasDetail = !!eventData.detail_id;
  
  // 点击查看详情
  const handlePress = async () => {
    if (!hasDetail) return;
    
    // 如果已解锁或免费，直接加载详情
    if (isUnlocked || unlockCost === 0) {
      await loadDetail();
      return;
    }
    
    // 需要付费解锁
    Alert.alert(
      '🔓 解锁回忆',
      `查看详细回忆需要 ${unlockCost} 月石\n\n当前余额: ${wallet?.totalCredits || 0} 月石`,
      [
        { text: '取消', style: 'cancel' },
        { 
          text: `解锁 (${unlockCost} 💎)`, 
          onPress: () => handleUnlock(),
        },
      ]
    );
  };
  
  // 解锁详情
  const handleUnlock = async () => {
    if ((wallet?.totalCredits || 0) < unlockCost) {
      Alert.alert('月石不足', '请先充值月石');
      return;
    }
    
    setIsLoading(true);
    try {
      // 调用后端解锁API
      const result = await api.post<{
        success: boolean;
        content?: string;
        new_balance?: number;
        error?: string;
      }>('/events/unlock', {
        character_id: characterId,
        detail_id: eventData.detail_id,
        event_type: eventData.event_type,
      });
      
      if (result.success) {
        setIsUnlocked(true);
        if (result.new_balance !== undefined) {
          updateWallet({ totalCredits: result.new_balance });
        }
        if (result.content) {
          setDetailContent(result.content);
          setShowDetailModal(true);
        }
        onDetailViewed?.();
      } else {
        Alert.alert('解锁失败', result.error || '请稍后重试');
      }
    } catch (e: any) {
      Alert.alert('解锁失败', e.message || '网络错误');
    } finally {
      setIsLoading(false);
    }
  };
  
  // 加载详情内容
  const loadDetail = async () => {
    if (detailContent) {
      setShowDetailModal(true);
      return;
    }
    
    setIsLoading(true);
    try {
      // 获取详情内容
      const result = await api.get<{
        success: boolean;
        content?: string;
        error?: string;
      }>(`/events/detail/${characterId}/${eventData.detail_id}`);
      
      if (result.success && result.content) {
        setDetailContent(result.content);
        setShowDetailModal(true);
        onDetailViewed?.();
      } else {
        Alert.alert('加载失败', result.error || '请稍后重试');
      }
    } catch (e: any) {
      Alert.alert('加载失败', e.message || '网络错误');
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <View style={styles.container}>
      <AnimatedTouchable
        style={[styles.cardWrapper, cardAnimatedStyle]}
        onPress={handlePress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        activeOpacity={0.9}
        disabled={isLoading}
      >
        {/* 呼吸灯效果 */}
        {hasDetail && !isUnlocked && unlockCost > 0 && (
          <Animated.View 
            style={[
              styles.glowEffect, 
              glowAnimatedStyle,
              { borderColor: config.borderColor }
            ]} 
          />
        )}
        
        <LinearGradient
          colors={config.gradientColors}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.card, { borderColor: config.borderColor }]}
        >
          {/* 图标 */}
          <View style={styles.iconContainer}>
            <Text style={styles.icon}>{displayIcon}</Text>
          </View>
          
          {/* 内容 */}
          <View style={styles.content}>
            <Text style={styles.title}>{displayTitle}</Text>
            <Text style={styles.subtitle} numberOfLines={2}>
              {displaySubtitle}
            </Text>
          </View>
          
          {/* 右侧状态 */}
          <View style={styles.statusContainer}>
            {isLoading ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : hasDetail ? (
              <>
                {!isUnlocked && unlockCost > 0 ? (
                  <View style={styles.unlockBadge}>
                    <Text style={styles.unlockBadgeText}>{unlockCost} 💎</Text>
                  </View>
                ) : (
                  <Ionicons name="eye-outline" size={18} color="rgba(255,255,255,0.6)" />
                )}
                <Ionicons name="chevron-forward" size={18} color="rgba(255,255,255,0.5)" />
              </>
            ) : null}
          </View>
        </LinearGradient>
      </AnimatedTouchable>
      
      {/* 详情弹窗 */}
      <Modal
        visible={showDetailModal}
        transparent
        animationType="slide"
        onRequestClose={() => setShowDetailModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            {/* Header */}
            <View style={styles.modalHeader}>
              <View style={styles.modalHeaderLeft}>
                <Text style={styles.modalIcon}>{displayIcon}</Text>
                <Text style={styles.modalTitle}>{displayTitle}</Text>
              </View>
              <TouchableOpacity 
                onPress={() => setShowDetailModal(false)}
                style={styles.closeButton}
              >
                <Ionicons name="close" size={24} color="#fff" />
              </TouchableOpacity>
            </View>
            
            {/* Content */}
            <ScrollView 
              style={styles.modalScroll}
              showsVerticalScrollIndicator={false}
            >
              <Text style={styles.storyContent}>
                {detailContent || '加载中...'}
              </Text>
              
              {/* 与角色相关的提示 */}
              <Text style={styles.characterNote}>
                ✨ 与{characterName}的珍贵回忆
              </Text>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
}

// 工具函数：解析事件消息
export function parseEventMessage(content: string): EventMessageData | null {
  try {
    const data = JSON.parse(content);
    if (data.type === 'event') {
      return data as EventMessageData;
    }
  } catch {
    // 不是 JSON 格式
  }
  return null;
}

// 工具函数：检查是否是事件消息
export function isEventMessage(content: string): boolean {
  return parseEventMessage(content) !== null;
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    marginVertical: 12,
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
    paddingVertical: 14,
    paddingHorizontal: 14,
    borderRadius: 16,
    borderWidth: 1.5,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
  },
  iconContainer: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  icon: {
    fontSize: 22,
  },
  content: {
    flex: 1,
    marginLeft: 12,
  },
  title: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 2,
  },
  subtitle: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.7)',
    lineHeight: 16,
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  unlockBadge: {
    backgroundColor: 'rgba(139, 92, 246, 0.3)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 10,
  },
  unlockBadgeText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#C4B5FD',
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#1a1a2e',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '80%',
    paddingBottom: 40,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  modalHeaderLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  modalIcon: {
    fontSize: 24,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  closeButton: {
    padding: 4,
  },
  modalScroll: {
    padding: 20,
  },
  storyContent: {
    fontSize: 15,
    color: 'rgba(255, 255, 255, 0.9)',
    lineHeight: 26,
  },
  characterNote: {
    marginTop: 24,
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.5)',
    fontStyle: 'italic',
    textAlign: 'center',
  },
});
