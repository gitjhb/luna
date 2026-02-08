/**
 * Gift Bottom Sheet
 * 
 * 礼物选择面板 - 按 Tier 分类展示
 * 
 * Tier 1: 日常消耗品 (Consumables)
 * Tier 2: 状态触发器 (State Triggers) ⭐ MVP 重点
 * Tier 3: 关系加速器 (Speed Dating)
 * Tier 4: 榜一大哥尊享 (Whale Bait)
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
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../theme/config';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const SHEET_HEIGHT = SCREEN_HEIGHT * 0.75;

// Tier 分类配置
const GIFT_TIERS = [
  { id: 1, name: '日常', icon: 'cafe-outline', color: '#4ECDC4' },
  { id: 2, name: '状态', icon: 'sparkles', color: '#FF6B9D' },
  { id: 3, name: '加速', icon: 'rocket-outline', color: '#9B59B6' },
  { id: 4, name: '尊享', icon: 'diamond', color: '#F1C40F' },
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
  bottleneckLocked = false,
  bottleneckRequiredTier = null,
  bottleneckLockLevel = null,
}: GiftBottomSheetProps) {
  const [selectedTier, setSelectedTier] = useState(1);
  const [selectedGift, setSelectedGift] = useState<GiftItem | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  
  const translateY = useRef(new Animated.Value(SHEET_HEIGHT)).current;
  const backdropOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible) {
      // 如果在冷战中，默认选择 Tier 2 (有悔过书)
      if (inColdWar) {
        setSelectedTier(2);
      }
      // 如果瓶颈锁激活，默认选择对应 tier
      if (bottleneckLocked && bottleneckRequiredTier) {
        setSelectedTier(bottleneckRequiredTier);
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
    }
  }, [visible, inColdWar]);

  // 按 Tier 过滤礼物
  const filteredGifts = gifts.filter(gift => gift.tier === selectedTier);

  const handleSelectGift = (gift: GiftItem) => {
    setSelectedGift(gift);
    setShowDetail(true);
  };

  const handleConfirmGift = () => {
    if (selectedGift) {
      onSelectGift(selectedGift);
      setSelectedGift(null);
      setShowDetail(false);
      onClose();
    }
  };

  const canAfford = (gift: GiftItem) => gift.price <= userCredits;
  const needsSubscription = (gift: GiftItem) => gift.requires_subscription && !isSubscribed;

  const renderTierTab = (tier: typeof GIFT_TIERS[0]) => {
    const isActive = selectedTier === tier.id;
    const tierGifts = gifts.filter(g => g.tier === tier.id);
    
    return (
      <TouchableOpacity
        key={tier.id}
        style={[
          styles.tierTab,
          isActive && { backgroundColor: tier.color + '30', borderColor: tier.color },
        ]}
        onPress={() => setSelectedTier(tier.id)}
      >
        <Ionicons
          name={tier.icon as any}
          size={18}
          color={isActive ? tier.color : 'rgba(255,255,255,0.5)'}
        />
        <Text style={[
          styles.tierTabText,
          isActive && { color: tier.color },
        ]}>
          {tier.name}
        </Text>
        {tierGifts.length > 0 && (
          <View style={[styles.tierBadge, { backgroundColor: tier.color }]}>
            <Text style={styles.tierBadgeText}>{tierGifts.length}</Text>
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
        activeOpacity={0.7}
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
          <Text style={styles.moonStoneIcon}>💎</Text>
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
              <Ionicons name="heart" size={16} color="#2ECC71" />
              <Text style={[styles.effectTitle, { color: '#2ECC71' }]}>修复关系</Text>
            </View>
            <Text style={styles.effectDesc}>
              这份礼物可以解除冷战状态，让你们重新开始对话
            </Text>
          </View>
        )}
        
        {/* 价格和按钮 */}
        <View style={styles.detailFooter}>
          <View style={styles.detailPriceBox}>
            <Text style={styles.moonStoneIcon}>💎</Text>
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
            <TouchableOpacity style={styles.rechargeButton}>
              <Ionicons name="add-circle" size={16} color="#fff" />
              <Text style={styles.rechargeButtonText}>充值</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              style={styles.confirmButton}
              onPress={handleConfirmGift}
            >
              <LinearGradient
                colors={['#00D4FF', '#8B5CF6']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.confirmButtonGradient}
              >
                <Text style={styles.confirmButtonText}>送出</Text>
                <Ionicons name="gift" size={18} color="#fff" />
              </LinearGradient>
            </TouchableOpacity>
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
              <Text style={styles.moonStoneIcon}>💎</Text>
              <Text style={styles.creditsText}>{userCredits}</Text>
              <Text style={styles.creditsLabel}>月石</Text>
              {onRecharge && <Ionicons name="add-circle" size={16} color="#FFD700" style={{ marginLeft: 4 }} />}
            </TouchableOpacity>
          </View>

          {/* Tier 标签 */}
          <View style={styles.tierTabContainer}>
            {GIFT_TIERS.map(renderTierTab)}
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

          {/* Tier 描述 */}
          <View style={styles.tierDescContainer}>
            <Text style={styles.tierDesc}>
              {getTierDescription(selectedTier)}
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

// 获取效果描述
function getEffectDescription(effectType: string): string {
  const descriptions: Record<string, string> = {
    tipsy: '她会变得微醺，说话更加柔软放松，防御心降低，更容易说出心里话...',
    maid_mode: '她会进入女仆模式，称呼你为"主人"，语气变得恭敬服务导向~',
    truth_mode: '她必须诚实回答所有问题，包括那些平时会回避的隐私问题...',
  };
  return descriptions[effectType] || '特殊效果';
}

// 获取 Tier 描述
function getTierDescription(tier: number): string {
  const descriptions: Record<number, string> = {
    1: '日常小礼物，维持好感，修补小摩擦',
    2: '状态触发器，改变她的行为模式 ⭐',
    3: '关系加速器，快速提升亲密度',
    4: '榜一大哥专属，解锁终极特权',
  };
  return descriptions[tier] || '';
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
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
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
    backgroundColor: 'rgba(139, 92, 246, 0.2)',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    gap: 6,
  },
  moonStoneIcon: {
    fontSize: 14,
  },
  creditsText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#A78BFA',
  },
  creditsLabel: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.6)',
  },
  tierTabContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    gap: 8,
  },
  tierTab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderWidth: 1,
    borderColor: 'transparent',
    gap: 6,
  },
  tierTabText: {
    fontSize: 13,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.5)',
  },
  tierBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
  },
  tierBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#fff',
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
  tierDescContainer: {
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  tierDesc: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.5)',
    textAlign: 'center',
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
    width: (SCREEN_WIDTH - 52) / 4,
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderRadius: 14,
    padding: 10,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: 'transparent',
  },
  giftItemSelected: {
    borderColor: '#00D4FF',
    backgroundColor: 'rgba(236, 72, 153, 0.15)',
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
    color: '#A78BFA',
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
