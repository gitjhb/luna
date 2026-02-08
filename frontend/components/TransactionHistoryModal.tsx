/**
 * Transaction History Modal - Shows credit transaction history
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
  RefreshControl,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../theme/config';
import { walletService } from '../services/walletService';
import { Transaction } from '../types';

interface TransactionHistoryModalProps {
  visible: boolean;
  onClose: () => void;
}

// Transaction type display config
const TRANSACTION_TYPES: Record<string, { label: string; icon: string; color: string; isCash?: boolean }> = {
  purchase: { label: '充值', icon: 'add-circle', color: '#10B981' },
  bonus: { label: '奖励', icon: 'gift', color: '#8B5CF6' },
  deduction: { label: '消费', icon: 'remove-circle', color: '#F59E0B' },
  gift: { label: '送礼', icon: 'heart', color: '#EC4899' },
  daily_refresh: { label: '每日赠送', icon: 'sunny', color: '#06B6D4' },
  refund: { label: '退款', icon: 'refresh-circle', color: '#6366F1' },
  subscription: { label: '订阅', icon: 'diamond', color: '#FFD700', isCash: true },
  referral: { label: '邀请奖励', icon: 'people', color: '#10B981' },
};

// Gift type -> emoji mapping (sync with backend gift catalog)
const GIFT_ICONS: Record<string, string> = {
  coffee: '☕',
  hot_coffee: '☕',
  cake: '🎂',
  small_cake: '🎂',
  rose: '🌹',
  chocolate: '🍫',
  teddy_bear: '🧸',
  wine: '🍷',
  red_wine: '🍷',
  diamond_ring: '💍',
  crown: '👑',
  castle: '🏰',
  apology_scroll: '📜',
  truth_serum: '🧪',
  maid_costume: '🎀',
};

// Check if transaction involves real money (not credits)
const isCashTransaction = (tx: Transaction): boolean => {
  // Subscription is always cash
  if (tx.transactionType === 'subscription') return true;
  // Check description for subscription keywords
  if (tx.description?.toLowerCase().includes('subscribe')) return true;
  // Check extra_data for currency
  if (tx.extraData?.currency === 'USD') return true;
  return false;
};

export const TransactionHistoryModal: React.FC<TransactionHistoryModalProps> = ({
  visible,
  onClose,
}) => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (visible) {
      loadTransactions();
    }
  }, [visible]);

  const loadTransactions = async () => {
    setLoading(true);
    try {
      const data = await walletService.getTransactions(50, 0);
      setTransactions(data);
    } catch (error) {
      console.error('Failed to load transactions:', error);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadTransactions();
    setRefreshing(false);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return `今天 ${date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`;
    } else if (days === 1) {
      return `昨天 ${date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`;
    } else if (days < 7) {
      return `${days}天前`;
    } else {
      return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
    }
  };

  const getTransactionConfig = (type: string) => {
    return TRANSACTION_TYPES[type] || { label: type, icon: 'help-circle', color: '#9CA3AF' };
  };

  const renderTransaction = (tx: Transaction, index: number) => {
    const config = getTransactionConfig(tx.transactionType);
    const isCash = isCashTransaction(tx);
    const isPositive = tx.amount > 0;
    
    // Get gift emoji from gift_type
    const giftType = tx.extraData?.gift_type || tx.extraData?.giftType;
    const giftEmoji = giftType ? GIFT_ICONS[giftType] : null;
    
    // Format amount based on currency type
    const formatAmount = () => {
      if (isCash) {
        // Real money - show as expense (negative)
        return `-$${Math.abs(tx.amount).toFixed(2)}`;
      } else {
        // Credits
        return `${isPositive ? '+' : ''}${tx.amount} 碎片`;
      }
    };

    return (
      <View key={tx.transactionId || index} style={styles.transactionItem}>
        <View style={[styles.transactionIcon, { backgroundColor: `${config.color}20` }]}>
          {giftEmoji ? (
            <Text style={{ fontSize: 20 }}>{giftEmoji}</Text>
          ) : (
            <Ionicons name={config.icon as any} size={20} color={config.color} />
          )}
        </View>
        <View style={styles.transactionInfo}>
          <Text style={styles.transactionTitle}>{tx.description || config.label}</Text>
          <Text style={styles.transactionDate}>{formatDate(tx.createdAt)}</Text>
        </View>
        <View style={styles.transactionAmount}>
          <Text style={[
            styles.transactionAmountText,
            { color: isCash ? '#EC4899' : (isPositive ? '#10B981' : '#F59E0B') }
          ]}>
            {formatAmount()}
          </Text>
          {!isCash && (
            <Text style={styles.transactionBalance}>余额: {tx.balanceAfter} 碎片</Text>
          )}
        </View>
      </View>
    );
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          {/* Header */}
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>账单记录</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>
          </View>

          {/* Content */}
          {loading && transactions.length === 0 ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color={theme.colors.primary.main} />
              <Text style={styles.loadingText}>加载中...</Text>
            </View>
          ) : transactions.length === 0 ? (
            <View style={styles.emptyContainer}>
              <Ionicons name="receipt-outline" size={64} color={theme.colors.text.tertiary} />
              <Text style={styles.emptyTitle}>暂无账单记录</Text>
              <Text style={styles.emptySubtitle}>充值或消费后记录会显示在这里</Text>
            </View>
          ) : (
            <ScrollView
              style={styles.transactionList}
              showsVerticalScrollIndicator={false}
              refreshControl={
                <RefreshControl
                  refreshing={refreshing}
                  onRefresh={onRefresh}
                  tintColor={theme.colors.primary.main}
                />
              }
            >
              {transactions.map((tx, index) => renderTransaction(tx, index))}
              <View style={{ height: 20 }} />
            </ScrollView>
          )}
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: theme.colors.background.secondary,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '80%',
    minHeight: '50%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  closeButton: {
    padding: 4,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: theme.colors.text.secondary,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
    marginTop: 16,
  },
  emptySubtitle: {
    fontSize: 14,
    color: theme.colors.text.tertiary,
    marginTop: 8,
  },
  transactionList: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 12,
  },
  transactionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(255, 255, 255, 0.08)',
  },
  transactionIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  transactionInfo: {
    flex: 1,
    marginLeft: 14,
  },
  transactionTitle: {
    fontSize: 15,
    fontWeight: '500',
    color: '#fff',
  },
  transactionDate: {
    fontSize: 12,
    color: theme.colors.text.tertiary,
    marginTop: 4,
  },
  transactionAmount: {
    alignItems: 'flex-end',
  },
  transactionAmountText: {
    fontSize: 16,
    fontWeight: '600',
  },
  transactionBalance: {
    fontSize: 11,
    color: theme.colors.text.tertiary,
    marginTop: 2,
  },
});

export default TransactionHistoryModal;
