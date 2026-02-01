/**
 * Gift Bottom Sheet
 * 
 * 礼物选择面板 - 分类展示，带质感的 BottomSheet
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
  PanResponder,
  ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../theme/config';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const SHEET_HEIGHT = SCREEN_HEIGHT * 0.7;

// 礼物分类配置
const GIFT_CATEGORIES = [
  { id: 'all', name: '全部', icon: 'apps' },
  { id: 'normal', name: '日常', icon: 'heart' },
  { id: 'romantic', name: '浪漫', icon: 'rose' },
  { id: 'props', name: '道具', icon: 'cube' },
  { id: 'jewelry', name: '珠宝', icon: 'diamond' },
  { id: 'clothing', name: '服饰', icon: 'shirt' },
  { id: 'apology', name: '道歉', icon: 'sad' },
  { id: 'spicy', name: '🔥', icon: 'flame' },
];

interface GiftItem {
  gift_type: string;
  name: string;
  name_cn: string;
  description_cn: string;
  price: number;
  xp_reward: number;
  icon: string;
  category: string;
  is_spicy?: boolean;
  requires_subscription?: boolean;
  triggers_scene?: string;
}

interface GiftBottomSheetProps {
  visible: boolean;
  onClose: () => void;
  onSelectGift: (gift: GiftItem) => void;
  gifts: GiftItem[];
  userCredits: number;
  isSubscribed: boolean;
  loading?: boolean;
}

export default function GiftBottomSheet({
  visible,
  onClose,
  onSelectGift,
  gifts,
  userCredits,
  isSubscribed,
  loading = false,
}: GiftBottomSheetProps) {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedGift, setSelectedGift] = useState<GiftItem | null>(null);
  
  const translateY = useRef(new Animated.Value(SHEET_HEIGHT)).current;
  const backdropOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible) {
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
    }
  }, [visible]);

  // 过滤礼物
  const filteredGifts = gifts.filter(gift => {
    if (selectedCategory === 'all') return true;
    return gift.category === selectedCategory;
  });

  // 按价格分组
  const groupedGifts = {
    free: filteredGifts.filter(g => g.price <= 30),
    premium: filteredGifts.filter(g => g.price > 30 && g.price <= 100),
    luxury: filteredGifts.filter(g => g.price > 100),
  };

  const handleSelectGift = (gift: GiftItem) => {
    if (gift.requires_subscription && !isSubscribed) {
      // 需要订阅但未订阅
      setSelectedGift(gift);
      return;
    }
    if (gift.price > userCredits) {
      // 余额不足
      setSelectedGift(gift);
      return;
    }
    setSelectedGift(gift);
  };

  const handleConfirmGift = () => {
    if (selectedGift) {
      onSelectGift(selectedGift);
      setSelectedGift(null);
      onClose();
    }
  };

  const renderGiftItem = (gift: GiftItem) => {
    const canAfford = gift.price <= userCredits;
    const needsSubscription = gift.requires_subscription && !isSubscribed;
    const isSelected = selectedGift?.gift_type === gift.gift_type;
    
    return (
      <TouchableOpacity
        key={gift.gift_type}
        style={[
          styles.giftItem,
          isSelected && styles.giftItemSelected,
          (!canAfford || needsSubscription) && styles.giftItemDisabled,
        ]}
        onPress={() => handleSelectGift(gift)}
        activeOpacity={0.7}
      >
        {/* 礼物图标 */}
        <View style={styles.giftIconContainer}>
          <Text style={styles.giftIcon}>{gift.icon}</Text>
          {gift.is_spicy && (
            <View style={styles.spicyBadge}>
              <Text style={styles.spicyBadgeText}>🔥</Text>
            </View>
          )}
        </View>
        
        {/* 礼物信息 */}
        <Text style={styles.giftName} numberOfLines={1}>{gift.name_cn}</Text>
        
        {/* 价格 */}
        <View style={styles.priceRow}>
          <Ionicons name="diamond" size={12} color={theme.colors.primary.main} />
          <Text style={[styles.giftPrice, !canAfford && styles.giftPriceRed]}>
            {gift.price}
          </Text>
        </View>
        
        {/* XP奖励 */}
        <Text style={styles.xpReward}>+{gift.xp_reward} XP</Text>
        
        {/* 锁定状态 */}
        {needsSubscription && (
          <View style={styles.lockOverlay}>
            <Ionicons name="lock-closed" size={20} color="#fff" />
          </View>
        )}
      </TouchableOpacity>
    );
  };

  const renderGiftSection = (title: string, items: GiftItem[], icon: string) => {
    if (items.length === 0) return null;
    
    return (
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Ionicons name={icon as any} size={16} color={theme.colors.text.secondary} />
          <Text style={styles.sectionTitle}>{title}</Text>
          <Text style={styles.sectionCount}>{items.length}</Text>
        </View>
        <View style={styles.giftGrid}>
          {items.map(renderGiftItem)}
        </View>
      </View>
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
            <Text style={styles.title}>送礼物</Text>
            <View style={styles.creditsDisplay}>
              <Ionicons name="diamond" size={16} color={theme.colors.primary.main} />
              <Text style={styles.creditsText}>{userCredits}</Text>
            </View>
          </View>

          {/* 分类标签 */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.categoryScroll}
            contentContainerStyle={styles.categoryContainer}
          >
            {GIFT_CATEGORIES.map((cat) => (
              <TouchableOpacity
                key={cat.id}
                style={[
                  styles.categoryTab,
                  selectedCategory === cat.id && styles.categoryTabActive,
                ]}
                onPress={() => setSelectedCategory(cat.id)}
              >
                {cat.id === 'spicy' ? (
                  <Text style={styles.categoryIcon}>{cat.name}</Text>
                ) : (
                  <Ionicons
                    name={cat.icon as any}
                    size={16}
                    color={selectedCategory === cat.id ? '#fff' : theme.colors.text.tertiary}
                  />
                )}
                {cat.id !== 'spicy' && (
                  <Text style={[
                    styles.categoryText,
                    selectedCategory === cat.id && styles.categoryTextActive,
                  ]}>
                    {cat.name}
                  </Text>
                )}
              </TouchableOpacity>
            ))}
          </ScrollView>

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
              {selectedCategory === 'all' ? (
                <>
                  {renderGiftSection('基础礼物', groupedGifts.free, 'heart-outline')}
                  {renderGiftSection('精选礼物', groupedGifts.premium, 'star-outline')}
                  {renderGiftSection('奢华礼物', groupedGifts.luxury, 'diamond-outline')}
                </>
              ) : (
                <View style={styles.giftGrid}>
                  {filteredGifts.map(renderGiftItem)}
                </View>
              )}
              
              {filteredGifts.length === 0 && (
                <View style={styles.emptyState}>
                  <Ionicons name="gift-outline" size={48} color={theme.colors.text.tertiary} />
                  <Text style={styles.emptyText}>该分类暂无礼物</Text>
                </View>
              )}
              
              <View style={{ height: 100 }} />
            </ScrollView>
          )}

          {/* 底部确认栏 */}
          {selectedGift && (
            <View style={styles.confirmBar}>
              <View style={styles.selectedGiftInfo}>
                <Text style={styles.selectedGiftIcon}>{selectedGift.icon}</Text>
                <View>
                  <Text style={styles.selectedGiftName}>{selectedGift.name_cn}</Text>
                  <Text style={styles.selectedGiftPrice}>
                    {selectedGift.price} 钻石 · +{selectedGift.xp_reward} XP
                  </Text>
                </View>
              </View>
              
              {selectedGift.requires_subscription && !isSubscribed ? (
                <TouchableOpacity style={styles.subscribeButton}>
                  <Text style={styles.subscribeButtonText}>订阅解锁</Text>
                </TouchableOpacity>
              ) : selectedGift.price > userCredits ? (
                <TouchableOpacity style={styles.rechargeButton}>
                  <Text style={styles.rechargeButtonText}>充值</Text>
                </TouchableOpacity>
              ) : (
                <TouchableOpacity
                  style={styles.confirmButton}
                  onPress={handleConfirmGift}
                >
                  <LinearGradient
                    colors={theme.colors.primary.gradient}
                    style={styles.confirmButtonGradient}
                  >
                    <Text style={styles.confirmButtonText}>送出</Text>
                    <Ionicons name="send" size={16} color="#fff" />
                  </LinearGradient>
                </TouchableOpacity>
              )}
            </View>
          )}
        </BlurView>
      </Animated.View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.5)',
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
    paddingBottom: 12,
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
  },
  creditsDisplay: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(236, 72, 153, 0.15)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    gap: 6,
  },
  creditsText: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.primary.main,
  },
  categoryScroll: {
    maxHeight: 44,
  },
  categoryContainer: {
    paddingHorizontal: 16,
    gap: 8,
  },
  categoryTab: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.08)',
    gap: 6,
  },
  categoryTabActive: {
    backgroundColor: theme.colors.primary.main,
  },
  categoryIcon: {
    fontSize: 14,
  },
  categoryText: {
    fontSize: 13,
    color: theme.colors.text.tertiary,
  },
  categoryTextActive: {
    color: '#fff',
    fontWeight: '600',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  giftList: {
    flex: 1,
    marginTop: 12,
  },
  giftListContent: {
    paddingHorizontal: 16,
  },
  section: {
    marginBottom: 20,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 8,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.text.secondary,
  },
  sectionCount: {
    fontSize: 12,
    color: theme.colors.text.tertiary,
    backgroundColor: 'rgba(255,255,255,0.1)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  giftGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  giftItem: {
    width: (SCREEN_WIDTH - 52) / 4,
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderRadius: 12,
    padding: 10,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: 'transparent',
  },
  giftItemSelected: {
    borderColor: theme.colors.primary.main,
    backgroundColor: 'rgba(236, 72, 153, 0.15)',
  },
  giftItemDisabled: {
    opacity: 0.5,
  },
  giftIconContainer: {
    position: 'relative',
    marginBottom: 6,
  },
  giftIcon: {
    fontSize: 28,
  },
  spicyBadge: {
    position: 'absolute',
    top: -4,
    right: -8,
  },
  spicyBadgeText: {
    fontSize: 10,
  },
  giftName: {
    fontSize: 11,
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
    fontSize: 12,
    fontWeight: '600',
    color: theme.colors.primary.main,
  },
  giftPriceRed: {
    color: '#E74C3C',
  },
  xpReward: {
    fontSize: 9,
    color: '#2ECC71',
    marginTop: 2,
  },
  lockOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 12,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: 14,
    color: theme.colors.text.tertiary,
    marginTop: 12,
  },
  confirmBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    paddingBottom: 32,
    backgroundColor: 'rgba(26, 16, 37, 0.95)',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.1)',
  },
  selectedGiftInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  selectedGiftIcon: {
    fontSize: 32,
  },
  selectedGiftName: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
  },
  selectedGiftPrice: {
    fontSize: 12,
    color: theme.colors.text.secondary,
    marginTop: 2,
  },
  confirmButton: {
    borderRadius: 20,
    overflow: 'hidden',
  },
  confirmButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingVertical: 12,
    gap: 8,
  },
  confirmButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
  },
  subscribeButton: {
    backgroundColor: '#9B59B6',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 20,
  },
  subscribeButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  rechargeButton: {
    backgroundColor: '#E67E22',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 20,
  },
  rechargeButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
});
