/**
 * Recharge Modal - Moon Shards purchase via RevenueCat
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Modal,
  ScrollView,
  Alert,
  Dimensions,
  ActivityIndicator,
  Image,
  Animated,
  Platform,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { Ionicons } from '@expo/vector-icons';
import Constants from 'expo-constants';
import { PurchasesPackage } from 'react-native-purchases';
import { revenueCatService } from '../services/revenueCatService';
import { useUserStore } from '../store/userStore';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Check if running in Expo Go
const isExpoGo = Constants.appOwnership === 'expo';

// Extract shard count from product ID (e.g., "com.luna.companion.6480moonshards" -> 6480)
const getShardCount = (productId: string): number => {
  const match = productId.match(/(\d+)(?:moon)?shards/i);
  return match ? parseInt(match[1], 10) : 0;
};

// Bonus amounts for each tier (not stored in RevenueCat)
const SHARD_BONUSES: { [key: number]: { bonus: number; tag?: string } } = {
  60: { bonus: 0 },
  300: { bonus: 30 },
  980: { bonus: 110, tag: '热卖' },
  1980: { bonus: 260 },
  3280: { bonus: 600 },
  6480: { bonus: 1600, tag: '超值' },
};

interface RechargeModalProps {
  visible: boolean;
  onClose: () => void;
  onPurchaseSuccess?: (creditsAdded: number, newBalance: number) => void;
}

export const RechargeModal: React.FC<RechargeModalProps> = ({
  visible,
  onClose,
  onPurchaseSuccess,
}) => {
  const { wallet, updateWallet } = useUserStore();
  const [packages, setPackages] = useState<PurchasesPackage[]>([]);
  const [loading, setLoading] = useState(false);
  const [purchasing, setPurchasing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSuccessAnimation, setShowSuccessAnimation] = useState(false);
  const [purchasedAmount, setPurchasedAmount] = useState(0);
  
  // 动画引用
  const successScaleAnim = useRef(new Animated.Value(0)).current;
  const confettiAnim = useRef(new Animated.Value(0)).current;
  const glowAnim = useRef(new Animated.Value(0)).current;
  const bounceAnim = useRef(new Animated.Value(1)).current;

  // Load packages when modal opens
  useEffect(() => {
    if (visible) {
      loadPackages();
    }
  }, [visible]);

  const loadPackages = async () => {
    if (isExpoGo) {
      setError('IAP 在 Expo Go 中不可用，请使用 dev build');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      // Get 'sale' offering for moon shards
      const allOfferings = await revenueCatService.getAllOfferings();
      const saleOffering = allOfferings['sale'];
      
      if (saleOffering && saleOffering.availablePackages.length > 0) {
        // Sort by price
        const sorted = [...saleOffering.availablePackages].sort(
          (a, b) => a.product.price - b.product.price
        );
        setPackages(sorted);
        console.log('[RechargeModal] Loaded', sorted.length, 'packages');
      } else {
        console.warn('[RechargeModal] No sale offering found');
        setError('暂无可用商品');
      }
    } catch (err: any) {
      console.error('[RechargeModal] Failed to load packages:', err);
      setError(err.message || '加载商品失败');
    } finally {
      setLoading(false);
    }
  };

  const handlePurchase = async (pkg: PurchasesPackage) => {
    const shardCount = getShardCount(pkg.product.identifier);
    const bonusInfo = SHARD_BONUSES[shardCount] || { bonus: 0 };
    const totalShards = shardCount + bonusInfo.bonus;

    Alert.alert(
      '确认购买',
      `购买 ${shardCount.toLocaleString()} 碎片${bonusInfo.bonus ? ` (+${bonusInfo.bonus} 赠送)` : ''}，价格 ${pkg.product.priceString}？`,
      [
        { text: '取消', style: 'cancel' },
        {
          text: '购买',
          onPress: async () => {
            try {
              setPurchasing(pkg.identifier);
              
              const result = await revenueCatService.purchasePackage(pkg);
              
              if (result.success) {
                // Update wallet locally (backend should also be notified via webhook)
                const newBalance = (wallet?.totalCredits || 0) + totalShards;
                updateWallet({ totalCredits: newBalance });
                
                // 设置购买金额并显示成功动画
                setPurchasedAmount(totalShards);
                setShowSuccessAnimation(true);
                
                // 播放成功动画
                await playSuccessAnimation();
                
                // 成功触觉反馈
                if (Platform.OS !== 'web') {
                  Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
                }
                
                // 调用成功回调
                onPurchaseSuccess?.(totalShards, newBalance);
                
                // 2.5秒后关闭
                setTimeout(() => {
                  setShowSuccessAnimation(false);
                  onClose();
                }, 2500);
              }
            } catch (err: any) {
              if (!err.userCancelled) {
                Alert.alert('购买失败', err.message || '请稍后重试');
              }
            } finally {
              setPurchasing(null);
            }
          },
        },
      ]
    );
  };

  // 播放购买成功动画
  const playSuccessAnimation = (): Promise<void> => {
    return new Promise((resolve) => {
      // 重置动画值
      successScaleAnim.setValue(0);
      confettiAnim.setValue(0);
      glowAnim.setValue(0);
      bounceAnim.setValue(1);
      
      // 并行动画序列
      Animated.parallel([
        // 成功图标弹出
        Animated.spring(successScaleAnim, {
          toValue: 1,
          friction: 6,
          tension: 100,
          useNativeDriver: true,
        }),
        
        // 彩带效果
        Animated.sequence([
          Animated.delay(300),
          Animated.timing(confettiAnim, {
            toValue: 1,
            duration: 1000,
            useNativeDriver: true,
          }),
        ]),
        
        // 光晕效果
        Animated.loop(
          Animated.sequence([
            Animated.timing(glowAnim, {
              toValue: 1,
              duration: 800,
              useNativeDriver: true,
            }),
            Animated.timing(glowAnim, {
              toValue: 0,
              duration: 800,
              useNativeDriver: true,
            }),
          ]),
          { iterations: 2 }
        ),
        
        // 整体弹跳
        Animated.sequence([
          Animated.delay(100),
          Animated.spring(bounceAnim, {
            toValue: 0.95,
            friction: 3,
            useNativeDriver: true,
          }),
          Animated.spring(bounceAnim, {
            toValue: 1,
            friction: 8,
            useNativeDriver: true,
          }),
        ]),
      ]).start(resolve);
    });
  };

  const renderPackage = (pkg: PurchasesPackage) => {
    const shardCount = getShardCount(pkg.product.identifier);
    const bonusInfo = SHARD_BONUSES[shardCount] || { bonus: 0 };
    const isPurchasing = purchasing === pkg.identifier;

    return (
      <TouchableOpacity
        key={pkg.identifier}
        style={[styles.packCard, isPurchasing && styles.packCardDisabled]}
        onPress={() => handlePurchase(pkg)}
        disabled={!!purchasing}
      >
        {bonusInfo.tag && (
          <View style={styles.tagBadge}>
            <Text style={styles.tagText}>{bonusInfo.tag}</Text>
          </View>
        )}
        <View style={styles.shardRow}>
          <Image 
            source={require('../assets/icons/moon-shard.png')} 
            style={styles.packShardIcon} 
          />
          <Text style={styles.shardAmount}>
            {shardCount > 0 ? shardCount.toLocaleString() : '?'}
          </Text>
        </View>
        {bonusInfo.bonus > 0 && (
          <Text style={styles.bonusText}>+{bonusInfo.bonus} 赠送</Text>
        )}
        <Text style={styles.priceText}>{pkg.product.priceString}</Text>
        {isPurchasing && (
          <ActivityIndicator size="small" color="#00D4FF" style={styles.purchaseLoader} />
        )}
      </TouchableOpacity>
    );
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <Animated.View style={[
          styles.content,
          { transform: [{ scale: bounceAnim }] }
        ]}>
          
          {/* 购买成功动画覆盖层 */}
          {showSuccessAnimation && (
            <Animated.View style={[styles.successOverlay, { opacity: successScaleAnim }]}>
              {/* 彩带效果 */}
              {['🎉', '🎊', '✨', '💫', '⭐', '🌟', '💎', '💰'].map((confetti, index) => (
                <Animated.Text
                  key={index}
                  style={[
                    styles.confettiItem,
                    {
                      left: `${(index * 12) % 100}%`,
                      top: `${20 + (index * 8) % 40}%`,
                      transform: [{
                        translateY: confettiAnim.interpolate({
                          inputRange: [0, 1],
                          outputRange: [0, 200],
                          extrapolate: 'clamp',
                        })
                      }],
                      opacity: confettiAnim.interpolate({
                        inputRange: [0, 0.5, 1],
                        outputRange: [1, 1, 0],
                        extrapolate: 'clamp',
                      }),
                    }
                  ]}
                >
                  {confetti}
                </Animated.Text>
              ))}
              
              {/* 成功信息 */}
              <Animated.View style={[
                styles.successContent,
                { transform: [{ scale: successScaleAnim }] }
              ]}>
                <Animated.View style={[
                  styles.successIcon,
                  {
                    shadowOpacity: glowAnim.interpolate({
                      inputRange: [0, 1],
                      outputRange: [0.3, 0.8],
                      extrapolate: 'clamp',
                    }),
                  }
                ]}>
                  <Text style={styles.successIconText}>💎</Text>
                </Animated.View>
                
                <Text style={styles.successTitle}>🎉 购买成功!</Text>
                <Text style={styles.successAmount}>
                  +{purchasedAmount.toLocaleString()} 月石
                </Text>
                <Text style={styles.successSubtitle}>
                  已添加到您的账户
                </Text>
              </Animated.View>
            </Animated.View>
          )}
          
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.title}>购买月光碎片</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>
          </View>

          {/* Current Balance */}
          <View style={styles.balanceRow}>
            <Text style={styles.balanceLabel}>当前余额</Text>
            <View style={styles.balanceValue}>
              <Image 
                source={require('../assets/icons/moon-shard.png')} 
                style={styles.shardIcon} 
              />
              <Text style={styles.balanceAmount}>
                {wallet?.totalCredits?.toFixed(0) || '0'}
              </Text>
            </View>
          </View>

          {/* Content */}
          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#00D4FF" />
              <Text style={styles.loadingText}>加载中...</Text>
            </View>
          ) : error ? (
            <View style={styles.errorContainer}>
              <Ionicons name="alert-circle" size={48} color="#ff6b6b" />
              <Text style={styles.errorText}>{error}</Text>
              <TouchableOpacity style={styles.retryButton} onPress={loadPackages}>
                <Text style={styles.retryText}>重试</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>
              <View style={styles.packsGrid}>
                {packages.map(renderPackage)}
              </View>
            </ScrollView>
          )}
        </Animated.View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    justifyContent: 'flex-end',
  },
  content: {
    backgroundColor: '#1a1a2e',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingTop: 20,
    paddingBottom: 40,
    maxHeight: '80%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    marginBottom: 16,
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
  },
  closeButton: {
    padding: 4,
  },
  balanceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
    backgroundColor: 'rgba(0, 212, 255, 0.1)',
    marginHorizontal: 16,
    borderRadius: 12,
    marginBottom: 16,
  },
  balanceLabel: {
    fontSize: 14,
    color: '#aaa',
  },
  balanceValue: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  shardIcon: {
    width: 24,
    height: 24,
    marginRight: 6,
  },
  balanceAmount: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFD700',
  },
  loadingContainer: {
    padding: 60,
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    color: '#888',
    fontSize: 14,
  },
  errorContainer: {
    padding: 40,
    alignItems: 'center',
  },
  errorText: {
    marginTop: 12,
    color: '#ff6b6b',
    fontSize: 14,
    textAlign: 'center',
  },
  retryButton: {
    marginTop: 16,
    paddingHorizontal: 24,
    paddingVertical: 10,
    backgroundColor: 'rgba(0, 212, 255, 0.2)',
    borderRadius: 8,
  },
  retryText: {
    color: '#00D4FF',
    fontWeight: '600',
  },
  scroll: {
    paddingHorizontal: 16,
  },
  packsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  packCard: {
    width: (SCREEN_WIDTH - 48) / 2,
    backgroundColor: 'rgba(0, 212, 255, 0.08)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.2)',
  },
  packCardDisabled: {
    opacity: 0.6,
  },
  tagBadge: {
    position: 'absolute',
    top: -8,
    right: 8,
    backgroundColor: '#FF6B6B',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  tagText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '700',
  },
  shardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  packShardIcon: {
    width: 28,
    height: 28,
    marginRight: 6,
  },
  shardAmount: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFD700',
  },
  bonusText: {
    fontSize: 12,
    color: '#4CAF50',
    marginBottom: 4,
  },
  priceText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  purchaseLoader: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    marginLeft: -10,
    marginTop: -10,
  },
  
  // 成功动画样式
  successOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    zIndex: 1000,
    alignItems: 'center',
    justifyContent: 'center',
  },
  confettiItem: {
    position: 'absolute',
    fontSize: 20,
    zIndex: 1001,
  },
  successContent: {
    alignItems: 'center',
    zIndex: 1002,
  },
  successIcon: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: 'rgba(255, 215, 0, 0.2)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
    shadowColor: '#FFD700',
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 20,
    elevation: 20,
  },
  successIconText: {
    fontSize: 48,
  },
  successTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFD700',
    marginBottom: 8,
    textAlign: 'center',
  },
  successAmount: {
    fontSize: 36,
    fontWeight: '800',
    color: '#4ADE80',
    marginBottom: 8,
    textAlign: 'center',
    textShadowColor: 'rgba(74, 222, 128, 0.5)',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 10,
  },
  successSubtitle: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.8)',
    textAlign: 'center',
  },
});

export default RechargeModal;
