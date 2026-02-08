/**
 * Gift Picker Component
 * 
 * 礼物选择器 - 显示礼物列表，让用户选择并发送
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Modal,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { giftService, GiftCatalogItem, SendGiftResponse } from '../../services/giftService';
import { GIFT_CONFIGS, GiftType } from './types';

interface GiftPickerProps {
  visible: boolean;
  characterId: string;
  sessionId?: string;
  userBalance: number;
  onClose: () => void;
  onGiftSent: (response: SendGiftResponse) => void;
  onBalanceChange?: (newBalance: number) => void;
}

export const GiftPicker: React.FC<GiftPickerProps> = ({
  visible,
  characterId,
  sessionId,
  userBalance,
  onClose,
  onGiftSent,
  onBalanceChange,
}) => {
  const [catalog, setCatalog] = useState<GiftCatalogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [selectedGift, setSelectedGift] = useState<string | null>(null);

  // Load catalog when modal opens
  useEffect(() => {
    if (visible) {
      loadCatalog();
    }
  }, [visible]);

  const loadCatalog = async () => {
    try {
      setLoading(true);
      const data = await giftService.getGiftCatalog();
      setCatalog(data);
    } catch (error) {
      console.error('Failed to load gift catalog:', error);
      // Fallback to local config
      setCatalog(Object.values(GIFT_CONFIGS).map(g => ({
        gift_type: g.type,
        name: g.name,
        name_cn: g.nameCn,
        price: g.price,
        xp_reward: g.xpReward,
        icon: g.emoji,
      })));
    } finally {
      setLoading(false);
    }
  };

  const handleSelectGift = (giftType: string) => {
    setSelectedGift(giftType);
  };

  const handleSendGift = async () => {
    if (!selectedGift) return;

    const gift = catalog.find(g => g.gift_type === selectedGift);
    if (!gift) return;

    // Check balance
    if (userBalance < gift.price) {
      Alert.alert(
        '余额不足',
        `需要 ${gift.price} 碎片，当前余额 ${userBalance} 碎片`,
        [{ text: '确定' }]
      );
      return;
    }

    // Confirm expensive gifts
    if (gift.price >= 100) {
      Alert.alert(
        '确认送礼',
        `确定要送出 ${gift.name_cn || gift.name} 吗？\n将花费 ${gift.price} 碎片`,
        [
          { text: '取消', style: 'cancel' },
          { text: '确定', onPress: () => doSendGift(gift) },
        ]
      );
    } else {
      doSendGift(gift);
    }
  };

  const doSendGift = async (gift: GiftCatalogItem) => {
    try {
      setSending(true);
      
      const response = await giftService.sendGift(
        characterId,
        gift.gift_type,
        sessionId,
        true // trigger AI response
      );

      if (response.success) {
        // Update balance
        if (response.new_balance !== undefined && onBalanceChange) {
          onBalanceChange(response.new_balance);
        }
        
        // Notify parent
        onGiftSent(response);
        
        // Close picker
        onClose();
        setSelectedGift(null);
      } else {
        // 根据错误类型显示不同提示
        const errorMessage = response.error === 'insufficient_credits' 
          ? '余额不足' 
          : response.message || '系统异常，请稍后再试';
        Alert.alert('送礼失败', errorMessage);
      }
    } catch (error: any) {
      console.error('Failed to send gift:', error);
      // 网络错误统一提示
      const errorMessage = error.error === 'insufficient_credits'
        ? '余额不足'
        : '网络错误，请稍后重试';
      Alert.alert('送礼失败', errorMessage);
    } finally {
      setSending(false);
    }
  };

  const renderGiftItem = (gift: GiftCatalogItem) => {
    const isSelected = selectedGift === gift.gift_type;
    const canAfford = userBalance >= gift.price;
    
    return (
      <TouchableOpacity
        key={gift.gift_type}
        style={[
          styles.giftItem,
          isSelected && styles.giftItemSelected,
          !canAfford && styles.giftItemDisabled,
        ]}
        onPress={() => handleSelectGift(gift.gift_type)}
        disabled={!canAfford}
      >
        <Text style={styles.giftIcon}>{gift.icon || '🎁'}</Text>
        <Text style={[styles.giftName, !canAfford && styles.textDisabled]}>
          {gift.name_cn || gift.name}
        </Text>
        <View style={styles.priceRow}>
          <Text style={[styles.giftPrice, !canAfford && styles.textDisabled]}>
            {gift.price} 💎
          </Text>
        </View>
        <Text style={styles.xpReward}>+{gift.xp_reward} XP</Text>
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
        <View style={styles.container}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.title}>送礼物</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
              <Text style={styles.closeText}>✕</Text>
            </TouchableOpacity>
          </View>

          {/* Balance */}
          <View style={styles.balanceRow}>
            <Text style={styles.balanceLabel}>余额：</Text>
            <Text style={styles.balanceValue}>{userBalance} 💎</Text>
          </View>

          {/* Gift Grid */}
          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#FF6B9D" />
            </View>
          ) : (
            <ScrollView 
              style={styles.giftList}
              contentContainerStyle={styles.giftGrid}
              showsVerticalScrollIndicator={false}
            >
              {catalog.map(renderGiftItem)}
            </ScrollView>
          )}

          {/* Send Button */}
          <TouchableOpacity
            style={[
              styles.sendButton,
              (!selectedGift || sending) && styles.sendButtonDisabled,
            ]}
            onPress={handleSendGift}
            disabled={!selectedGift || sending}
          >
            {sending ? (
              <ActivityIndicator size="small" color="#FFF" />
            ) : (
              <Text style={styles.sendButtonText}>
                {selectedGift 
                  ? `送出 ${catalog.find(g => g.gift_type === selectedGift)?.name_cn || '礼物'}`
                  : '选择一个礼物'
                }
              </Text>
            )}
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  container: {
    backgroundColor: '#1A1A2E',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingBottom: 34, // Safe area
    maxHeight: '80%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFF',
  },
  closeButton: {
    padding: 4,
  },
  closeText: {
    fontSize: 20,
    color: '#888',
  },
  balanceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    backgroundColor: 'rgba(255, 107, 157, 0.1)',
  },
  balanceLabel: {
    fontSize: 14,
    color: '#AAA',
  },
  balanceValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FF6B9D',
  },
  loadingContainer: {
    height: 200,
    justifyContent: 'center',
    alignItems: 'center',
  },
  giftList: {
    flex: 1,
  },
  giftGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 12,
    justifyContent: 'space-between',
  },
  giftItem: {
    width: '30%',
    aspectRatio: 0.9,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: 'transparent',
  },
  giftItemSelected: {
    borderColor: '#FF6B9D',
    backgroundColor: 'rgba(255, 107, 157, 0.15)',
  },
  giftItemDisabled: {
    opacity: 0.5,
  },
  giftIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  giftName: {
    fontSize: 12,
    fontWeight: '500',
    color: '#FFF',
    textAlign: 'center',
    marginBottom: 4,
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  giftPrice: {
    fontSize: 12,
    color: '#FFD700',
    fontWeight: '600',
  },
  xpReward: {
    fontSize: 10,
    color: '#4CAF50',
    marginTop: 2,
  },
  textDisabled: {
    color: '#666',
  },
  sendButton: {
    backgroundColor: '#FF6B9D',
    marginHorizontal: 16,
    marginTop: 12,
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: '#555',
  },
  sendButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFF',
  },
});

export default GiftPicker;
