/**
 * Recharge Modal - Shared coin purchase component
 * 
 * Used in both Profile and Chat screens
 */

import React, { useState, useEffect } from 'react';
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
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { pricingService, CoinPack } from '../services/pricingService';
import { paymentService } from '../services/paymentService';
import { useUserStore } from '../store/userStore';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

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
  const [coinPacks, setCoinPacks] = useState<CoinPack[]>([]);
  const [loading, setLoading] = useState(false);
  const [purchasing, setPurchasing] = useState<string | null>(null);

  // Load coin packs when modal opens
  useEffect(() => {
    if (visible) {
      loadCoinPacks();
    }
  }, [visible]);

  const loadCoinPacks = async () => {
    try {
      setLoading(true);
      const packs = await pricingService.getCoinPacks();
      setCoinPacks(packs);
    } catch (error) {
      console.error('Failed to load coin packs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePurchase = (pack: CoinPack) => {
    Alert.alert(
      '确认购买',
      `购买 ${pack.coins.toLocaleString()} 金币${pack.bonusCoins ? ` (+${pack.bonusCoins} 赠送)` : ''}，价格 $${pack.price.toFixed(2)}？`,
      [
        { text: '取消', style: 'cancel' },
        {
          text: '购买',
          onPress: async () => {
            try {
              setPurchasing(pack.id);
              const result = await paymentService.purchaseCredits(pack.id);
              
              if (result.success) {
                // Update local wallet state
                updateWallet({ totalCredits: result.wallet.total_credits });
                
                // Notify parent
                onPurchaseSuccess?.(result.credits_added, result.wallet.total_credits);
                
                onClose();
                Alert.alert('🎉 购买成功！', `获得 ${result.credits_added.toLocaleString()} 金币`);
              }
            } catch (error: any) {
              Alert.alert('购买失败', error.message || '请稍后重试');
            } finally {
              setPurchasing(null);
            }
          },
        },
      ]
    );
  };

  const handleFreeCoins = async () => {
    try {
      setPurchasing('free');
      const result = await paymentService.addCredits(500);
      
      if (result.success) {
        updateWallet({ totalCredits: result.wallet.total_credits });
        onPurchaseSuccess?.(500, result.wallet.total_credits);
        Alert.alert('🎁 领取成功！', '获得 500 测试金币');
      }
    } catch (error: any) {
      Alert.alert('领取失败', error.message || '请稍后重试');
    } finally {
      setPurchasing(null);
    }
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <View style={styles.content}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.title}>购买金币</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>
          </View>

          {/* Current Balance */}
          <View style={styles.balanceRow}>
            <Text style={styles.balanceLabel}>当前余额</Text>
            <View style={styles.balanceValue}>
              <Text style={styles.coinEmoji}>🪙</Text>
              <Text style={styles.balanceAmount}>{wallet?.totalCredits?.toFixed(0) || '0'}</Text>
            </View>
          </View>

          {/* Coin Packs */}
          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#EC4899" />
            </View>
          ) : (
            <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>
              <View style={styles.packsGrid}>
                {coinPacks.map((pack) => (
                  <TouchableOpacity
                    key={pack.id}
                    style={[
                      styles.packCard,
                      purchasing === pack.id && styles.packCardPurchasing,
                    ]}
                    onPress={() => handlePurchase(pack)}
                    disabled={purchasing !== null}
                  >
                    {/* Popular Badge */}
                    {pack.popular && (
                      <View style={styles.popularBadge}>
                        <Text style={styles.badgeText}>热卖</Text>
                      </View>
                    )}

                    {/* Discount Badge */}
                    {pack.discount && (
                      <View style={styles.discountBadge}>
                        <Text style={styles.badgeText}>{pack.discount}% OFF</Text>
                      </View>
                    )}

                    {/* Coins */}
                    <Text style={styles.packCoins}>
                      🪙 {pack.coins.toLocaleString()}
                    </Text>

                    {/* Bonus Coins */}
                    {pack.bonusCoins && pack.bonusCoins > 0 && (
                      <Text style={styles.packBonus}>
                        +{pack.bonusCoins.toLocaleString()} 赠送
                      </Text>
                    )}

                    {/* Price */}
                    <Text style={styles.packPrice}>
                      ${pack.price.toFixed(2)}
                    </Text>

                    {/* Loading indicator */}
                    {purchasing === pack.id && (
                      <View style={styles.purchasingOverlay}>
                        <ActivityIndicator size="small" color="#fff" />
                      </View>
                    )}
                  </TouchableOpacity>
                ))}
              </View>

              {/* Test: Free Coins Button */}
              <TouchableOpacity
                style={[
                  styles.freeButton,
                  purchasing === 'free' && styles.freeButtonDisabled,
                ]}
                onPress={handleFreeCoins}
                disabled={purchasing !== null}
              >
                {purchasing === 'free' ? (
                  <ActivityIndicator size="small" color="#EC4899" />
                ) : (
                  <Text style={styles.freeButtonText}>🎁 领取 500 测试金币</Text>
                )}
              </TouchableOpacity>

              <View style={{ height: 20 }} />
            </ScrollView>
          )}
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'flex-end',
  },
  content: {
    backgroundColor: '#1A1A2E',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '75%',
    paddingBottom: 34,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
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
    paddingVertical: 16,
    backgroundColor: 'rgba(255, 215, 0, 0.08)',
  },
  balanceLabel: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.7)',
  },
  balanceValue: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  coinEmoji: {
    fontSize: 18,
  },
  balanceAmount: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFD700',
  },
  loadingContainer: {
    height: 200,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scroll: {
    maxHeight: 450,
  },
  packsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 16,
    gap: 12,
    justifyContent: 'center',
  },
  packCard: {
    width: (SCREEN_WIDTH - 56) / 2,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
    position: 'relative',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  packCardPurchasing: {
    opacity: 0.7,
  },
  popularBadge: {
    position: 'absolute',
    top: -8,
    right: -8,
    backgroundColor: '#EC4899',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 10,
  },
  discountBadge: {
    position: 'absolute',
    top: -8,
    left: -8,
    backgroundColor: '#EC4899',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 10,
  },
  badgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#fff',
  },
  packCoins: {
    fontSize: 22,
    fontWeight: '700',
    color: '#FFD700',
    marginTop: 8,
    marginBottom: 4,
  },
  packBonus: {
    fontSize: 13,
    fontWeight: '600',
    color: '#EC4899',
    marginTop: 2,
  },
  packPrice: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
    marginTop: 8,
  },
  purchasingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  freeButton: {
    backgroundColor: 'rgba(236, 72, 153, 0.15)',
    borderWidth: 1,
    borderColor: '#EC4899',
    borderRadius: 12,
    paddingVertical: 14,
    marginHorizontal: 16,
    marginTop: 16,
    alignItems: 'center',
  },
  freeButtonDisabled: {
    opacity: 0.6,
  },
  freeButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#EC4899',
  },
});

export default RechargeModal;
