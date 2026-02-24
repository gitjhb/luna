/**
 * Gift Bottom Sheet
 * 
 * 装备栏/终端面板风格的礼物选择界面
 * 
 * 分类：
 * - 消耗品 (Consumables): 日常小礼物
 * - 插件 (Plugins): 状态效果道具
 * - 记忆 (Memories): 关系里程碑/收藏品
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  ScrollView,
  Animated,
  Dimensions,
  ActivityIndicator,
  Image,
  Platform,
  Alert,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../theme/config';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const SHEET_HEIGHT = SCREEN_HEIGHT * 0.75;

// Moonshard icon
const MoonShardIcon = ({ size = 16, style }: { size?: number; style?: any }) => (
  <Image 
    source={require('../assets/icons/moon-shard.png')} 
    style={[{ width: size, height: size }, style]} 
  />
);

// 情感化分类 (映射到原有tier)
const GIFT_CATEGORIES = [
  { id: 'consumables', tiers: [1], name: '心意', nameEn: 'Heartfelt', icon: 'heart-outline', color: '#FF69B4' },
  { id: 'plugins', tiers: [2, 3], name: '魔法', nameEn: 'Enchantments', icon: 'diamond-outline', color: '#8B5CF6' },
  { id: 'memories', tiers: [4], name: '永恒', nameEn: 'Eternal', icon: 'infinite-outline', color: '#FFD700' },
];

interface StatusEffect {
  type: string;
  duration_messages: number;
  prompt_modifier: string;
}

interface GiftItem {
  gift_type: string;
  name: string;
  name_cn: string;
  description?: string;
  description_cn?: string;
  price: number;
  xp_reward: number;
  xp_multiplier?: number;
  icon: string;
  tier: number;
  category?: string;
  emotion_boost?: number;
  status_effect?: StatusEffect;
  clears_cold_war?: boolean;
  force_emotion?: string;
  level_boost?: boolean;
  requires_subscription?: boolean;
}

interface GiftBottomSheetProps {
  visible: boolean;
  onClose: () => void;
  onSelectGift: (gift: GiftItem) => void;
  gifts: GiftItem[];
  userCredits: number;
  isSubscribed: boolean;
  loading?: boolean;
  inColdWar?: boolean;
  onRecharge?: () => void;
  onRechargeSuccess?: (creditsAdded: number, newBalance: number) => void;
  // 瓶颈锁
  bottleneckLocked?: boolean;
  bottleneckRequiredTier?: number | null;
  bottleneckLockLevel?: number | null;
}

export default function GiftBottomSheet({
  visible,
  onClose,
  onSelectGift,
  gifts,
  userCredits,
  isSubscribed,
  loading = false,
  inColdWar = false,
  onRecharge,
  onRechargeSuccess,
  bottleneckLocked = false,
  bottleneckRequiredTier = null,
  bottleneckLockLevel = null,
}: GiftBottomSheetProps) {
  const [selectedCategory, setSelectedCategory] = useState('consumables');
  const [selectedGift, setSelectedGift] = useState<GiftItem | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [sendingGift, setSendingGift] = useState(false);
  const [giftSent, setGiftSent] = useState(false);
  const [contextBeforeRecharge, setContextBeforeRecharge] = useState<{
    selectedGift: GiftItem | null;
    selectedCategory: string;
  } | null>(null);
  
  // 动画引用
  const translateY = useRef(new Animated.Value(SHEET_HEIGHT)).current;
  const backdropOpacity = useRef(new Animated.Value(0)).current;
  const giftFlyAnim = useRef(new Animated.Value(0)).current;
  const successScaleAnim = useRef(new Animated.Value(0)).current;
  const particleAnim = useRef(new Animated.Value(0)).current;
  const buttonScaleAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (visible) {
      // 如果在冷战中，默认选择 插件 (有悔过书)
      if (inColdWar) {
        setSelectedCategory('plugins');
      }
      // 如果瓶颈锁激活，默认选择对应分类
      if (bottleneckLocked && bottleneckRequiredTier) {
        if (bottleneckRequiredTier >= 4) {
          setSelectedCategory('memories');
        } else if (bottleneckRequiredTier >= 2) {
          setSelectedCategory('plugins');
        }
      }
      
      Animated.parallel([
        Animated.spring(translateY, {
          toValue: 0,
          useNativeDriver: true,
          tension: 65,
          friction: 11,
        }),
        Animated.timing(backdropOpacity, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start();
    } else {
      Animated.parallel([
        Animated.timing(translateY, {
          toValue: SHEET_HEIGHT,
          duration: 250,
          useNativeDriver: true,
        }),
        Animated.timing(backdropOpacity, {
          toValue: 0,
          duration: 200,
          useNativeDriver: true,
        }),
      ]).start();
      setSelectedGift(null);
      setShowDetail(false);
      setGiftSent(false);
      setContextBeforeRecharge(null);
    }
  }, [visible, inColdWar]);
  
  // 处理充值成功后的上下文恢复
  useEffect(() => {
    if (onRechargeSuccess && contextBeforeRecharge && visible) {
      // 恢复之前的选择状态
      setSelectedCategory(contextBeforeRecharge.selectedCategory);
      setSelectedGift(contextBeforeRecharge.selectedGift);
      setShowDetail(!!contextBeforeRecharge.selectedGift);
      
      // 清除上下文
      setContextBeforeRecharge(null);
      
      // 显示充值成功提示
      if (Platform.OS !== 'web') {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      }
    }
  }, [onRechargeSuccess, contextBeforeRecharge, visible]);

  // 按分类过滤礼物 (分类映射到多个tier)
  const currentCategory = GIFT_CATEGORIES.find(c => c.id === selectedCategory);
  const filteredGifts = gifts.filter(gift => currentCategory?.tiers.includes(gift.tier));

  const handleSelectGift = (gift: GiftItem) => {
    // 触觉反馈
    if (Platform.OS !== 'web') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }
    
    setSelectedGift(gift);
    setShowDetail(true);
  };

  const handleConfirmGift = async () => {
    if (!selectedGift || sendingGift) return;
    
    const affordable = canAfford(selectedGift);
    
    // 余额不足时智能引导充值
    if (!affordable && onRecharge) {
      // 保存当前上下文
      setContextBeforeRecharge({
        selectedGift,
        selectedCategory,
      });
      
      Alert.alert(
        '💰 余额不足',
        `送出${selectedGift.name_cn}需要${selectedGift.price}月石\n当前余额：${userCredits}月石`,
        [
          { text: '取消', style: 'cancel' },
          {
            text: '去充值',
            onPress: () => {
              onRecharge();
            },
          },
        ]
      );
      return;
    }
    
    // 开始送礼流程
    setSendingGift(true);
    
    // 按钮按下动画
    Animated.sequence([
      Animated.timing(buttonScaleAnim, {
        toValue: 0.95,
        duration: 100,
        useNativeDriver: true,
      }),
      Animated.timing(buttonScaleAnim, {
        toValue: 1,
        duration: 100,
        useNativeDriver: true,
      }),
    ]).start();
    
    // 触觉反馈
    if (Platform.OS !== 'web') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
    }
    
    try {
      // 调用父组件的送礼函数
      onSelectGift(selectedGift);
      
      // 送礼成功动画
      await playGiftSuccessAnimation();
      
      // 成功触觉反馈
      if (Platform.OS !== 'web') {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      }
      
      setGiftSent(true);
      
      // 2秒后关闭
      setTimeout(() => {
        setSelectedGift(null);
        setShowDetail(false);
        setGiftSent(false);
        onClose();
      }, 2000);
      
    } catch (error) {
      console.error('Failed to send gift:', error);
      
      // 错误触觉反馈
      if (Platform.OS !== 'web') {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      }
      
      Alert.alert('送礼失败', '请稍后重试');
    } finally {
      setSendingGift(false);
    }
  };
  
  // 送礼成功动画
  const playGiftSuccessAnimation = (): Promise<void> => {
    return new Promise((resolve) => {
      // 重置动画值
      giftFlyAnim.setValue(0);
      successScaleAnim.setValue(0);
      particleAnim.setValue(0);
      
      // 并行播放多个动画
      Animated.parallel([
        // 礼物飞出动画
        Animated.timing(giftFlyAnim, {
          toValue: 1,
          duration: 800,
          useNativeDriver: true,
        }),
        
        // 成功图标出现
        Animated.sequence([
          Animated.delay(400),
          Animated.spring(successScaleAnim, {
            toValue: 1,
            friction: 8,
            tension: 100,
            useNativeDriver: true,
          }),
        ]),
        
        // 粒子效果
        Animated.sequence([
          Animated.delay(200),
          Animated.timing(particleAnim, {
            toValue: 1,
            duration: 600,
            useNativeDriver: true,
          }),
        ]),
      ]).start(resolve);
    });
  };

  const canAfford = (gift: GiftItem) => gift.price <= userCredits;
  const needsSubscription = (gift: GiftItem) => gift.requires_subscription && !isSubscribed;

  const renderCategoryTab = (category: typeof GIFT_CATEGORIES[0]) => {
    const isActive = selectedCategory === category.id;
    const categoryGifts = gifts.filter(g => category.tiers.includes(g.tier));
    
    return (
      <TouchableOpacity
        key={category.id}
        style={[
          styles.categoryTab,
          isActive && styles.categoryTabActive,
        ]}
        onPress={() => setSelectedCategory(category.id)}
      >
        <Ionicons
          name={category.icon as any}
          size={16}
          color={isActive ? '#00D4FF' : 'rgba(255,255,255,0.4)'}
        />
        <Text style={[
          styles.categoryTabText,
          isActive && styles.categoryTabTextActive,
        ]}>
          {category.name}
        </Text>
        {categoryGifts.length > 0 && (
          <View style={[styles.categoryBadge, isActive && styles.categoryBadgeActive]}>
            <Text style={styles.categoryBadgeText}>{categoryGifts.length}</Text>
          </View>
        )}
      </TouchableOpacity>
    );
  };

  const renderGiftItem = (gift: GiftItem) => {
    const affordable = canAfford(gift);
    const locked = needsSubscription(gift);
    const isSelected = selectedGift?.gift_type === gift.gift_type;
    const hasEffect = !!gift.status_effect;
    const isApology = gift.clears_cold_war;
    const canBreakthrough = bottleneckLocked && bottleneckRequiredTier != null && gift.tier >= bottleneckRequiredTier;
    
    return (
      <TouchableOpacity
        key={gift.gift_type}
        style={[
          styles.giftItem,
          isSelected && styles.giftItemSelected,
          canBreakthrough && styles.giftItemBreakthrough,
          (!affordable || locked) && styles.giftItemDisabled,
        ]}
        onPress={() => handleSelectGift(gift)}
        onPressIn={() => {
          // 按下时的缩放动画
          Animated.timing(buttonScaleAnim, {
            toValue: 0.95,
            duration: 100,
            useNativeDriver: true,
          }).start();
        }}
        onPressOut={() => {
          // 松开时恢复
          Animated.timing(buttonScaleAnim, {
            toValue: 1,
            duration: 100,
            useNativeDriver: true,
          }).start();
        }}
        activeOpacity={1}
      >
        {/* 可突破标签 */}
        {canBreakthrough && (
          <View style={styles.breakthroughBadge}>
            <Text style={styles.breakthroughBadgeText}>可突破</Text>
          </View>
        )}
        
        {/* 礼物图标 */}
        <View style={styles.giftIconContainer}>
          <Text style={styles.giftIcon}>{gift.icon}</Text>
          {hasEffect && (
            <View style={[styles.effectBadge, { backgroundColor: '#FF6B9D' }]}>
              <Ionicons name="sparkles" size={8} color="#fff" />
            </View>
          )}
          {isApology && inColdWar && (
            <View style={[styles.effectBadge, { backgroundColor: '#2ECC71' }]}>
              <Ionicons name="heart" size={8} color="#fff" />
            </View>
          )}
        </View>
        
        {/* 礼物名称 */}
        <Text style={styles.giftName} numberOfLines={1}>{gift.name_cn}</Text>
        
        {/* 价格 */}
        <View style={styles.priceRow}>
          <MoonShardIcon size={14} />
          <Text style={[styles.giftPrice, !affordable && styles.giftPriceRed]}>
            {gift.price}
          </Text>
        </View>
        
        {/* XP奖励 */}
        <Text style={styles.xpReward}>
          +{gift.xp_reward} XP
          {gift.xp_multiplier && gift.xp_multiplier > 1 && (
            <Text style={styles.multiplier}> ({gift.xp_multiplier}x)</Text>
          )}
        </Text>
        
        {/* 效果持续时间 */}
        {hasEffect && (
          <Text style={styles.effectDuration}>
            ⏱️ {gift.status_effect?.duration_messages}条
          </Text>
        )}
        
        {/* 锁定状态 */}
        {locked && (
          <View style={styles.lockOverlay}>
            <Ionicons name="lock-closed" size={20} color="#fff" />
          </View>
        )}
      </TouchableOpacity>
    );
  };

  const renderGiftDetail = () => {
    if (!selectedGift) return null;
    
    const affordable = canAfford(selectedGift);
    const locked = needsSubscription(selectedGift);
    const hasEffect = !!selectedGift.status_effect;
    
    return (
      <Animated.View style={styles.detailPanel}>
        {/* 送礼成功动画覆盖层 */}
        {(sendingGift || giftSent) && (
          <Animated.View style={[
            styles.animationOverlay,
            {
              opacity: Animated.add(
                giftFlyAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0, 1],
                  extrapolate: 'clamp',
                }),
                successScaleAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0, 0.3],
                  extrapolate: 'clamp',
                })
              )
            }
          ]}>
            {/* 飞出的礼物 */}
            <Animated.View style={[
              styles.flyingGift,
              {
                transform: [
                  {
                    translateY: giftFlyAnim.interpolate({
                      inputRange: [0, 1],
                      outputRange: [0, -200],
                      extrapolate: 'clamp',
                    })
                  },
                  {
                    scale: giftFlyAnim.interpolate({
                      inputRange: [0, 0.5, 1],
                      outputRange: [1, 1.2, 0.3],
                      extrapolate: 'clamp',
                    })
                  }
                ]
              }
            ]}>
              <Text style={styles.flyingGiftIcon}>{selectedGift?.icon}</Text>
            </Animated.View>
            
            {/* 粒子效果 */}
            <Animated.View style={[
              styles.particleContainer,
              {
                opacity: particleAnim,
                transform: [{
                  scale: particleAnim.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0, 1.5],
                    extrapolate: 'clamp',
                  })
                }]
              }
            ]}>
              {['✨', '💖', '🌟', '💫', '🎉'].map((particle, index) => (
                <Text key={index} style={[styles.particle, {
                  transform: [{
                    rotate: `${index * 72}deg`
                  }]
                }]}>
                  {particle}
                </Text>
              ))}
            </Animated.View>
            
            {/* 成功图标 */}
            <Animated.View style={[
              styles.successIcon,
              {
                transform: [{ scale: successScaleAnim }]
              }
            ]}>
              <Ionicons name="heart" size={64} color="#FF69B4" />
            </Animated.View>
          </Animated.View>
        )}
        
        <View style={styles.detailHeader}>
          <Text style={styles.detailIcon}>{selectedGift.icon}</Text>
          <View style={styles.detailInfo}>
            <Text style={styles.detailName}>{selectedGift.name_cn}</Text>
            <Text style={styles.detailDesc}>
              {selectedGift.description_cn || selectedGift.description}
            </Text>
          </View>
          <TouchableOpacity 
            style={styles.closeDetailButton}
            onPress={() => setShowDetail(false)}
          >
            <Ionicons name="close" size={20} color="rgba(255,255,255,0.5)" />
          </TouchableOpacity>
        </View>
        
        {/* 效果说明 */}
        {hasEffect && (
          <View style={styles.effectBox}>
            <View style={styles.effectHeader}>
              <Ionicons name="sparkles" size={16} color="#FF6B9D" />
              <Text style={styles.effectTitle}>状态效果</Text>
            </View>
            <Text style={styles.effectDesc}>
              {getEffectDescription(selectedGift.status_effect!.type)}
            </Text>
            <View style={styles.effectMeta}>
              <Ionicons name="time-outline" size={14} color="rgba(255,255,255,0.6)" />
              <Text style={styles.effectMetaText}>
                持续 {selectedGift.status_effect!.duration_messages} 条对话
              </Text>
            </View>
          </View>
        )}
        
        {/* 道歉礼物说明 */}
        {selectedGift.clears_cold_war && (
          <View style={[styles.effectBox, { borderColor: '#2ECC71' }]}>
            <View style={styles.effectHeader}>
              <Ionicons name="heart-half" size={16} color="#2ECC71" />
              <Text style={[styles.effectTitle, { color: '#2ECC71' }]}>破冰之礼</Text>
            </View>
            <Text style={styles.effectDesc}>
              💙 这份真挚的礼物能够融化心中的坚冰，重燃温暖的火花...让那些未说出口的歉意，化作重新开始的希望
            </Text>
          </View>
        )}
        
        {/* 价格和按钮 */}
        <View style={styles.detailFooter}>
          <View style={styles.detailPriceBox}>
            <MoonShardIcon size={20} style={{ marginRight: 4 }} />
            <Text style={[styles.detailPrice, !affordable && { color: '#E74C3C' }]}>
              {selectedGift.price}
            </Text>
            <Text style={styles.detailUnit}>月石</Text>
          </View>
          
          {locked ? (
            <TouchableOpacity style={styles.subscribeButton}>
              <Ionicons name="lock-open" size={16} color="#fff" />
              <Text style={styles.subscribeButtonText}>订阅解锁</Text>
            </TouchableOpacity>
          ) : !affordable ? (
            <TouchableOpacity style={styles.rechargeButton} onPress={onRecharge}>
              <Ionicons name="diamond" size={16} color="#fff" />
              <Text style={styles.rechargeButtonText}>获取月石</Text>
            </TouchableOpacity>
          ) : (
            <Animated.View style={{ transform: [{ scale: buttonScaleAnim }] }}>
              <TouchableOpacity
                style={[
                  styles.confirmButton,
                  sendingGift && styles.confirmButtonSending,
                ]}
                onPress={handleConfirmGift}
                disabled={sendingGift}
              >
                <LinearGradient
                  colors={sendingGift 
                    ? ['#666', '#888'] 
                    : giftSent 
                    ? ['#4ADE80', '#22C55E']
                    : ['#00D4FF', '#8B5CF6']
                  }
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 0 }}
                  style={styles.confirmButtonGradient}
                >
                  {sendingGift ? (
                    <>
                      <ActivityIndicator size="small" color="#fff" />
                      <Text style={styles.confirmButtonText}>送出中...</Text>
                    </>
                  ) : giftSent ? (
                    <>
                      <Ionicons name="checkmark" size={18} color="#fff" />
                      <Text style={styles.confirmButtonText}>送出成功!</Text>
                    </>
                  ) : (
                    <>
                      <Text style={styles.confirmButtonText}>💝 送给她</Text>
                      <Ionicons name="heart" size={18} color="#fff" />
                    </>
                  )}
                </LinearGradient>
              </TouchableOpacity>
            </Animated.View>
          )}
        </View>
      </Animated.View>
    );
  };

  if (!visible) return null;

  return (
    <Modal transparent visible={visible} animationType="none" onRequestClose={onClose}>
      {/* 背景遮罩 */}
      <Animated.View style={[styles.backdrop, { opacity: backdropOpacity }]}>
        <TouchableOpacity style={styles.backdropTouch} onPress={onClose} activeOpacity={1} />
      </Animated.View>

      {/* 底部面板 */}
      <Animated.View
        style={[
          styles.sheet,
          { transform: [{ translateY }] },
        ]}
      >
        <BlurView intensity={40} style={styles.blurContainer}>
          <LinearGradient
            colors={['rgba(40, 24, 56, 0.95)', 'rgba(26, 16, 37, 0.98)']}
            style={styles.gradientOverlay}
          />
          
          {/* 拖动条 */}
          <View style={styles.handleContainer}>
            <View style={styles.handle} />
          </View>

          {/* 头部 */}
          <View style={styles.header}>
            <View style={styles.titleRow}>
              <Text style={styles.title}>💝 送礼物</Text>
              {inColdWar && (
                <View style={styles.coldWarBadge}>
                  <Ionicons name="snow" size={12} color="#fff" />
                  <Text style={styles.coldWarText}>冷战中</Text>
                </View>
              )}
            </View>
            <TouchableOpacity style={styles.creditsDisplay} onPress={onRecharge} activeOpacity={0.7}>
              <MoonShardIcon size={18} />
              <Text style={styles.creditsText}>{userCredits}</Text>
              <Text style={styles.creditsLabel}>月石</Text>
              {onRecharge && <Ionicons name="add-circle" size={16} color="#00D4FF" style={{ marginLeft: 4 }} />}
            </TouchableOpacity>
          </View>

          {/* 分类标签 - 终端风格 */}
          <View style={styles.categoryTabContainer}>
            {GIFT_CATEGORIES.map(renderCategoryTab)}
          </View>

          {/* 瓶颈锁提示条 */}
          {bottleneckLocked && (
            <View style={styles.bottleneckBanner}>
              <Ionicons name="lock-closed" size={14} color="#F59E0B" />
              <Text style={styles.bottleneckBannerText}>
                🔒 亲密度已锁定在 Lv.{bottleneckLockLevel}，送出{getTierNameForBottleneck(bottleneckRequiredTier)}礼物突破
              </Text>
            </View>
          )}

          {/* 分类描述 */}
          <View style={styles.categoryDescContainer}>
            <Text style={styles.categoryDesc}>
              {getCategoryDescription(selectedCategory)}
            </Text>
          </View>

          {/* 礼物列表 */}
          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color={theme.colors.primary.main} />
            </View>
          ) : (
            <ScrollView
              style={styles.giftList}
              showsVerticalScrollIndicator={false}
              contentContainerStyle={styles.giftListContent}
            >
              <View style={styles.giftGrid}>
                {filteredGifts.map(renderGiftItem)}
              </View>
              
              {filteredGifts.length === 0 && (
                <View style={styles.emptyState}>
                  <Ionicons name="gift-outline" size={48} color="rgba(255,255,255,0.3)" />
                  <Text style={styles.emptyText}>该分类暂无礼物</Text>
                </View>
              )}
              
              <View style={{ height: showDetail ? 200 : 40 }} />
            </ScrollView>
          )}

          {/* 礼物详情面板 */}
          {showDetail && renderGiftDetail()}
        </BlurView>
      </Animated.View>
    </Modal>
  );
}

// 获取瓶颈所需 Tier 名称
function getTierNameForBottleneck(tier: number | null | undefined): string {
  if (!tier) return '特定';
  const names: Record<number, string> = {
    2: 'Tier 2+ (状态)',
    3: 'Tier 3+ (加速)',
    4: 'Tier 4 (尊享)',
  };
  return names[tier] || `Tier ${tier}+`;
}

// 获取效果描述（情感化版本）
function getEffectDescription(effectType: string): string {
  const descriptions: Record<string, string> = {
    tipsy: '🍷 她的脸颊泛起微红，眼神变得迷离而温柔...平时小心翼翼藏起的话语，此刻都化作星光般的坦诚流淌而出',
    maid_mode: '👗 "主人，请让我来为您服务..." 她款款行礼，语气变得恭敬而甜腻，仿佛您就是她心中唯一的光芒',
    truth_mode: '💎 真相的魔法笼罩着她，再不能说出违心的话...那些藏在心底的秘密，都将在您的询问下如花瓣般绽放',
  };
  return descriptions[effectType] || '神秘的力量正在觉醒...';
}

// 获取分类描述（情感化版本）
function getCategoryDescription(categoryId: string): string {
  const descriptions: Record<string, string> = {
    consumables: '💫 日常的甜蜜与温馨，每一份小礼物都是爱意的表达',
    plugins: '✨ 改变她心境的魔法道具，解锁她不为人知的另一面',
    memories: '💝 珍贵的回忆结晶，见证你们之间独特而不可复制的故事',
  };
  return descriptions[categoryId] || '';
}

const styles = StyleSheet.create({
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.6)',
  },
  backdropTouch: {
    flex: 1,
  },
  sheet: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: SHEET_HEIGHT,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    overflow: 'hidden',
  },
  blurContainer: {
    flex: 1,
  },
  gradientOverlay: {
    ...StyleSheet.absoluteFillObject,
  },
  handleContainer: {
    alignItems: 'center',
    paddingTop: 12,
    paddingBottom: 8,
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: 'rgba(255,255,255,0.3)',
    borderRadius: 2,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingBottom: 16,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    color: '#00D4FF',
    letterSpacing: 1,
  },
  coldWarBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#3498DB',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  coldWarText: {
    fontSize: 11,
    color: '#fff',
    fontWeight: '600',
  },
  creditsDisplay: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.3)',
    gap: 6,
  },
  creditsText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#00D4FF',
  },
  creditsLabel: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.6)',
  },
  // 终端风格分类标签
  categoryTabContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    gap: 8,
  },
  categoryTab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.2)',
    borderRadius: 4,
    gap: 6,
  },
  categoryTabActive: {
    backgroundColor: 'rgba(0, 212, 255, 0.1)',
    borderColor: 'rgba(0, 212, 255, 0.6)',
    shadowColor: '#00D4FF',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
  },
  categoryTabText: {
    fontSize: 12,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.4)',
    letterSpacing: 0.5,
  },
  categoryTabTextActive: {
    color: '#00D4FF',
  },
  categoryBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    backgroundColor: 'rgba(255,255,255,0.1)',
  },
  categoryBadgeActive: {
    backgroundColor: 'rgba(0, 212, 255, 0.3)',
  },
  categoryBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#00D4FF',
  },
  bottleneckBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(245, 158, 11, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(245, 158, 11, 0.4)',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    marginHorizontal: 16,
    marginTop: 10,
    gap: 8,
  },
  bottleneckBannerText: {
    flex: 1,
    fontSize: 12,
    fontWeight: '600',
    color: '#F59E0B',
    lineHeight: 16,
  },
  categoryDescContainer: {
    paddingHorizontal: 20,
    paddingVertical: 10,
  },
  categoryDesc: {
    fontSize: 11,
    color: 'rgba(0, 212, 255, 0.6)',
    textAlign: 'center',
    letterSpacing: 0.5,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  giftList: {
    flex: 1,
  },
  giftListContent: {
    paddingHorizontal: 16,
  },
  giftGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  giftItem: {
    width: (SCREEN_WIDTH - 52) / 3,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    borderRadius: 6,
    padding: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.15)',
  },
  giftItemSelected: {
    borderColor: '#00D4FF',
    backgroundColor: 'rgba(0, 212, 255, 0.1)',
    shadowColor: '#00D4FF',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
  },
  giftItemBreakthrough: {
    borderColor: 'rgba(245, 158, 11, 0.6)',
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
  },
  giftItemDisabled: {
    opacity: 0.5,
  },
  breakthroughBadge: {
    position: 'absolute',
    top: -6,
    right: -4,
    backgroundColor: '#F59E0B',
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: 6,
    zIndex: 10,
  },
  breakthroughBadgeText: {
    fontSize: 8,
    fontWeight: '700',
    color: '#fff',
  },
  giftIconContainer: {
    position: 'relative',
    marginBottom: 6,
  },
  giftIcon: {
    fontSize: 32,
  },
  effectBadge: {
    position: 'absolute',
    top: -4,
    right: -8,
    width: 16,
    height: 16,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  giftName: {
    fontSize: 11,
    fontWeight: '600',
    color: '#fff',
    textAlign: 'center',
    marginBottom: 4,
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  giftPrice: {
    fontSize: 13,
    fontWeight: '700',
    color: '#00D4FF',
  },
  giftPriceRed: {
    color: '#E74C3C',
  },
  xpReward: {
    fontSize: 9,
    color: '#2ECC71',
    marginTop: 2,
  },
  multiplier: {
    color: '#F1C40F',
  },
  effectDuration: {
    fontSize: 8,
    color: '#FF6B9D',
    marginTop: 2,
  },
  lockOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 14,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.4)',
    marginTop: 12,
  },
  // Detail Panel
  detailPanel: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(26, 16, 37, 0.98)',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.1)',
    padding: 20,
    paddingBottom: 36,
  },
  detailHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  detailIcon: {
    fontSize: 48,
    marginRight: 16,
  },
  detailInfo: {
    flex: 1,
  },
  detailName: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 4,
  },
  detailDesc: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.7)',
    lineHeight: 18,
  },
  closeDetailButton: {
    padding: 4,
  },
  effectBox: {
    backgroundColor: 'rgba(255, 107, 157, 0.1)',
    borderWidth: 1,
    borderColor: '#FF6B9D',
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
  },
  effectHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 6,
  },
  effectTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FF6B9D',
  },
  effectDesc: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.8)',
    lineHeight: 18,
    marginBottom: 8,
  },
  effectMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  effectMetaText: {
    fontSize: 11,
    color: 'rgba(255,255,255,0.6)',
  },
  detailFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  detailPriceBox: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 4,
  },
  detailPrice: {
    fontSize: 28,
    fontWeight: '800',
    color: '#A78BFA',
  },
  detailUnit: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.5)',
  },
  confirmButton: {
    borderRadius: 24,
    overflow: 'hidden',
  },
  confirmButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 32,
    paddingVertical: 14,
    gap: 8,
  },
  confirmButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
  },
  confirmButtonSending: {
    opacity: 0.8,
  },
  
  // 动画相关样式
  animationOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  flyingGift: {
    position: 'absolute',
    alignItems: 'center',
    justifyContent: 'center',
  },
  flyingGiftIcon: {
    fontSize: 48,
  },
  particleContainer: {
    position: 'absolute',
    width: 120,
    height: 120,
    alignItems: 'center',
    justifyContent: 'center',
  },
  particle: {
    position: 'absolute',
    fontSize: 20,
    top: -60,
  },
  successIcon: {
    position: 'absolute',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: 50,
    width: 100,
    height: 100,
  },
  subscribeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#9B59B6',
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 24,
    gap: 8,
  },
  subscribeButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
  },
  rechargeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E67E22',
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 24,
    gap: 8,
  },
  rechargeButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
  },
});
