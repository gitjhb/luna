/**
 * DateEventCard Component
 * 
 * 约会事件特殊卡片，显示在聊天记录中
 * 
 * 卡片内容：
 * - 场景名称和图标
 * - 进度显示 (5/5)
 * - 结局类型 (perfect/good/normal/bad)
 * - 好感度分数
 * - 获得的奖励 (XP, 情绪)
 * - 简短的约会总结
 * - 点击查看详情（需要解锁）
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
  Dimensions,
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
  FadeIn,
  FadeInDown,
} from 'react-native-reanimated';
import { BlurView } from 'expo-blur';
import { api } from '../services/api';
import { useUserStore } from '../store/userStore';
import { useLocale, tpl } from '../i18n';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// 获取结局类型配置
const getEndingConfig = (t: any, ending: string) => {
  const configs: Record<string, {
    icon: string;
    title: string;
    color: string;
    gradientColors: [string, string];
    sparkle: boolean;
  }> = {
    perfect: {
      icon: '💕',
      title: t.date.ending.perfect,
      color: '#FF69B4',
      gradientColors: ['rgba(255, 105, 180, 0.25)', 'rgba(255, 182, 193, 0.15)'],
      sparkle: true,
    },
    good: {
      icon: '😊',
      title: t.date.ending.good,
      color: '#00D4FF',
      gradientColors: ['rgba(0, 212, 255, 0.2)', 'rgba(147, 112, 219, 0.15)'],
      sparkle: false,
    },
    normal: {
      icon: '🙂',
      title: t.date.ending.normal,
      color: '#A0A0A0',
      gradientColors: ['rgba(160, 160, 160, 0.15)', 'rgba(128, 128, 128, 0.1)'],
      sparkle: false,
    },
    bad: {
      icon: '😅',
      title: t.date.ending.bad,
      color: '#808080',
      gradientColors: ['rgba(128, 128, 128, 0.2)', 'rgba(64, 64, 64, 0.15)'],
      sparkle: false,
    },
  };
  return configs[ending] || configs.normal;
};

// 卡片数据接口
export interface DateEventData {
  type: 'event';
  event_type: 'date';
  summary: string;
  detail_id?: string;
  icon?: string;
  display?: {
    title: string;
    subtitle: string;
  };
  unlock_cost?: number;
  is_unlocked?: boolean;
  metadata?: {
    date_card?: boolean;
    ending?: string;
    progress?: string;
    affection?: number;
    rewards?: {
      xp?: number;
      emotion?: number;
    };
    summary?: string;
  };
}

interface DateEventCardProps {
  eventData: DateEventData;
  characterId: string;
  characterName?: string;
  onDetailViewed?: () => void;
}

const AnimatedTouchable = Animated.createAnimatedComponent(TouchableOpacity);

export default function DateEventCard({
  eventData,
  characterId,
  characterName = '角色',
  onDetailViewed,
}: DateEventCardProps) {
  // i18n
  const { t } = useLocale();

  const [showDetailModal, setShowDetailModal] = useState(false);
  const [detailContent, setDetailContent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isUnlocked, setIsUnlocked] = useState(eventData.is_unlocked || false);
  
  const { wallet, updateWallet } = useUserStore();
  
  // 动画值
  const scale = useSharedValue(1);
  const glowOpacity = useSharedValue(0.5);
  
  // 提取数据
  const metadata = eventData.metadata || {};
  const ending = metadata.ending || 'normal';
  const progress = metadata.progress || '5/5';
  const affection = metadata.affection ?? 0;
  const rewards = metadata.rewards || {};
  const storySummary = metadata.summary || eventData.summary;
  const scenarioName = eventData.display?.title || '约会';
  const unlockCost = eventData.unlock_cost || 10;
  const hasDetail = !!eventData.detail_id;
  
  // 获取结局配置
  const endingConfig = getEndingConfig(t, ending);
  
  // 呼吸灯效果（完美结局）
  React.useEffect(() => {
    if (endingConfig.sparkle) {
      glowOpacity.value = withRepeat(
        withSequence(
          withTiming(1, { duration: 1500, easing: Easing.inOut(Easing.ease) }),
          withTiming(0.4, { duration: 1500, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        true
      );
    }
  }, [ending]);
  
  const cardAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));
  
  const glowAnimatedStyle = useAnimatedStyle(() => ({
    opacity: glowOpacity.value,
  }));
  
  const handlePressIn = () => {
    scale.value = withSpring(0.97, { damping: 15 });
  };
  
  const handlePressOut = () => {
    scale.value = withSpring(1, { damping: 10 });
  };
  
  // 点击查看详情
  const handlePress = async () => {
    if (!hasDetail) return;
    
    if (isUnlocked || unlockCost === 0) {
      await loadDetail();
      return;
    }
    
    // 需要付费解锁
    Alert.alert(
      t.date.unlockMemory,
      tpl(t.date.unlockPrompt, { cost: unlockCost, balance: wallet?.totalCredits || 0 }),
      [
        { text: t.common.cancel, style: 'cancel' },
        { text: tpl(t.date.unlockButton, { cost: unlockCost }), onPress: handleUnlock },
      ]
    );
  };
  
  // 解锁详情
  const handleUnlock = async () => {
    if ((wallet?.totalCredits || 0) < unlockCost) {
      Alert.alert(t.date.insufficientFunds, '请先充值月石');
      return;
    }
    
    setIsLoading(true);
    try {
      const result = await api.post<{
        success: boolean;
        content?: string;
        new_balance?: number;
        error?: string;
      }>('/events/unlock', {
        character_id: characterId,
        detail_id: eventData.detail_id,
        event_type: 'date',
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
        Alert.alert(t.date.unlockFailed, result.error || '请稍后重试');
      }
    } catch (e: any) {
      Alert.alert(t.date.unlockFailed, e.message || t.date.networkError);
    } finally {
      setIsLoading(false);
    }
  };
  
  // 加载详情
  const loadDetail = async () => {
    if (detailContent) {
      setShowDetailModal(true);
      return;
    }
    
    setIsLoading(true);
    try {
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
        Alert.alert(t.date.loadFailed, result.error || '请稍后重试');
      }
    } catch (e: any) {
      Alert.alert(t.date.loadFailed, e.message || t.date.networkError);
    } finally {
      setIsLoading(false);
    }
  };
  
  // 获取好感度显示颜色
  const getAffectionColor = (score: number) => {
    if (score >= 60) return '#FF69B4';
    if (score >= 30) return '#00D4FF';
    if (score >= 0) return '#A0A0A0';
    return '#FF6B6B';
  };
  
  return (
    <Animated.View 
      style={styles.container}
      entering={FadeInDown.duration(400).springify()}
    >
      <AnimatedTouchable
        style={[styles.cardWrapper, cardAnimatedStyle]}
        onPress={handlePress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        activeOpacity={0.95}
        disabled={isLoading}
      >
        {/* 完美结局的发光效果 */}
        {endingConfig.sparkle && (
          <Animated.View 
            style={[
              styles.glowEffect, 
              glowAnimatedStyle,
              { borderColor: endingConfig.color }
            ]} 
          />
        )}
        
        <LinearGradient
          colors={endingConfig.gradientColors}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.card, { borderColor: endingConfig.color + '60' }]}
        >
          {/* 头部：图标 + 标题 + 结局标签 */}
          <View style={styles.header}>
            <View style={styles.headerLeft}>
              <Text style={styles.mainIcon}>{endingConfig.icon}</Text>
              <View>
                <Text style={styles.scenarioName}>{scenarioName}</Text>
                <Text style={[styles.endingBadge, { color: endingConfig.color }]}>
                  {endingConfig.title}
                </Text>
              </View>
            </View>
            
            <View style={styles.headerRight}>
              <View style={styles.progressBadge}>
                <Text style={styles.progressText}>{progress}</Text>
              </View>
            </View>
          </View>
          
          {/* 数据区：好感度 + 奖励 */}
          <View style={styles.statsRow}>
            {/* 好感度 */}
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>{t.date.affection}</Text>
              <Text style={[styles.statValue, { color: getAffectionColor(affection) }]}>
                {affection >= 0 ? `+${affection}` : affection}
              </Text>
            </View>
            
            {/* XP 奖励 */}
            {rewards.xp !== undefined && rewards.xp > 0 && (
              <View style={styles.statItem}>
                <Text style={styles.statLabel}>{t.date.experience}</Text>
                <Text style={[styles.statValue, { color: '#FFD700' }]}>
                  +{rewards.xp}
                </Text>
              </View>
            )}
            
            {/* 情绪变化 */}
            {rewards.emotion !== undefined && (
              <View style={styles.statItem}>
                <Text style={styles.statLabel}>{t.date.mood}</Text>
                <Text style={[
                  styles.statValue, 
                  { color: rewards.emotion >= 0 ? '#7CFC00' : '#FF6B6B' }
                ]}>
                  {rewards.emotion >= 0 ? `+${rewards.emotion}` : rewards.emotion}
                </Text>
              </View>
            )}
          </View>
          
          {/* 摘要 */}
          <Text style={styles.summary} numberOfLines={3}>
            {storySummary}
          </Text>
          
          {/* 底部：查看详情按钮 */}
          {hasDetail && (
            <View style={styles.footer}>
              {isLoading ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <View style={styles.detailButton}>
                  {!isUnlocked && unlockCost > 0 ? (
                    <View style={styles.unlockBadge}>
                      <Ionicons name="lock-closed" size={12} color="#C4B5FD" />
                      <Text style={styles.unlockText}>{tpl(t.date.unlockDetails, { cost: unlockCost })}</Text>
                    </View>
                  ) : (
                    <>
                      <Text style={styles.detailText}>{t.date.viewDetails}</Text>
                      <Ionicons name="chevron-forward" size={16} color="rgba(255,255,255,0.6)" />
                    </>
                  )}
                </View>
              )}
            </View>
          )}
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
          <BlurView intensity={40} style={styles.blurView}>
            <View style={styles.modalContent}>
              {/* Header */}
              <View style={styles.modalHeader}>
                <View style={styles.modalHeaderLeft}>
                  <Text style={styles.modalIcon}>{endingConfig.icon}</Text>
                  <View>
                    <Text style={styles.modalTitle}>{scenarioName}</Text>
                    <Text style={[styles.modalSubtitle, { color: endingConfig.color }]}>
                      {endingConfig.title}
                    </Text>
                  </View>
                </View>
                <TouchableOpacity 
                  onPress={() => setShowDetailModal(false)}
                  style={styles.closeButton}
                >
                  <Ionicons name="close" size={24} color="#fff" />
                </TouchableOpacity>
              </View>
              
              {/* Story Content */}
              <ScrollView 
                style={styles.modalScroll}
                showsVerticalScrollIndicator={false}
              >
                <Text style={styles.storyContent}>
                  {detailContent || t.common.loading}
                </Text>
                
                {/* 与角色的回忆提示 */}
                <View style={styles.memoryNote}>
                  <Text style={styles.memoryNoteText}>
                    {tpl(t.date.dateMemoryWith, { name: characterName })}
                  </Text>
                </View>
              </ScrollView>
            </View>
          </BlurView>
        </View>
      </Modal>
    </Animated.View>
  );
}

// 工具函数：检查是否是约会卡片
export function isDateEventCard(eventData: any): eventData is DateEventData {
  return (
    eventData?.type === 'event' &&
    eventData?.event_type === 'date' &&
    eventData?.metadata?.date_card === true
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    marginVertical: 16,
    paddingHorizontal: 12,
  },
  cardWrapper: {
    width: '100%',
    maxWidth: SCREEN_WIDTH - 40,
    position: 'relative',
  },
  glowEffect: {
    position: 'absolute',
    top: -3,
    left: -3,
    right: -3,
    bottom: -3,
    borderRadius: 20,
    borderWidth: 2,
  },
  card: {
    borderRadius: 16,
    borderWidth: 1.5,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    padding: 16,
    overflow: 'hidden',
  },
  // Header
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  mainIcon: {
    fontSize: 32,
    marginRight: 12,
  },
  scenarioName: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 2,
  },
  endingBadge: {
    fontSize: 12,
    fontWeight: '600',
  },
  headerRight: {
    alignItems: 'flex-end',
  },
  progressBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  progressText: {
    fontSize: 12,
    fontWeight: '600',
    color: 'rgba(255, 255, 255, 0.8)',
  },
  // Stats
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'flex-start',
    marginBottom: 12,
    gap: 20,
  },
  statItem: {
    alignItems: 'center',
  },
  statLabel: {
    fontSize: 10,
    color: 'rgba(255, 255, 255, 0.5)',
    marginBottom: 2,
  },
  statValue: {
    fontSize: 16,
    fontWeight: '700',
  },
  // Summary
  summary: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.8)',
    lineHeight: 20,
    marginBottom: 12,
  },
  // Footer
  footer: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
  },
  detailButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  detailText: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.6)',
  },
  unlockBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'rgba(139, 92, 246, 0.3)',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
  },
  unlockText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#C4B5FD',
  },
  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
  },
  blurView: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#1a1a2e',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '85%',
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
    gap: 12,
  },
  modalIcon: {
    fontSize: 28,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  modalSubtitle: {
    fontSize: 13,
    fontWeight: '600',
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
  memoryNote: {
    marginTop: 24,
    alignItems: 'center',
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
  },
  memoryNoteText: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.5)',
    fontStyle: 'italic',
  },
});
