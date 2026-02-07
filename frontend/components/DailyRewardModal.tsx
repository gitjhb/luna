/**
 * Daily Reward Modal
 * 每日登录奖励弹窗
 */

import React, { useEffect, useState, useRef } from 'react';
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { dailyRewardService, DailyRewardStatus } from '../services/dailyRewardService';
import { useUserStore } from '../store/userStore';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface DailyRewardModalProps {
  visible: boolean;
  onClose: () => void;
}

export default function DailyRewardModal({ visible, onClose }: DailyRewardModalProps) {
  const [status, setStatus] = useState<DailyRewardStatus | null>(null);
  const [claimed, setClaimed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [claimedAmount, setClaimedAmount] = useState(0);
  const { updateWallet } = useUserStore();
  
  // 动画
  const scaleAnim = useRef(new Animated.Value(0.8)).current;
  const coinAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible) {
      // 入场动画
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 8,
        tension: 40,
        useNativeDriver: true,
      }).start();
      
      // 获取状态
      checkStatus();
    } else {
      scaleAnim.setValue(0.8);
      coinAnim.setValue(0);
      setClaimed(false);
    }
  }, [visible]);

  const checkStatus = async () => {
    try {
      const result = await dailyRewardService.getStatus();
      setStatus(result);
    } catch (e) {
      console.error('Failed to get daily reward status:', e);
    }
  };

  const handleClaim = async () => {
    if (loading || !status?.can_claim) return;
    
    setLoading(true);
    try {
      const result = await dailyRewardService.claim();
      
      if (result.success) {
        setClaimedAmount(result.reward_amount);
        setClaimed(true);
        
        // 更新钱包余额
        if (result.new_balance !== undefined) {
          updateWallet({ totalCredits: result.new_balance });
        }
        
        // 金币动画
        Animated.sequence([
          Animated.timing(coinAnim, {
            toValue: 1,
            duration: 300,
            useNativeDriver: true,
          }),
          Animated.spring(coinAnim, {
            toValue: 0.8,
            friction: 3,
            useNativeDriver: true,
          }),
        ]).start();
      }
    } catch (e) {
      console.error('Failed to claim daily reward:', e);
    } finally {
      setLoading(false);
    }
  };

  if (!visible) return null;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <Animated.View style={[styles.container, { transform: [{ scale: scaleAnim }] }]}>
          <LinearGradient
            colors={['#2D1B4E', '#1A1025']}
            style={styles.card}
          >
            {/* 关闭按钮 */}
            <TouchableOpacity style={styles.closeButton} onPress={onClose}>
              <Ionicons name="close" size={24} color="rgba(255,255,255,0.5)" />
            </TouchableOpacity>

            {/* 标题 */}
            <View style={styles.header}>
              <Text style={styles.title}>✨ 每日登录奖励</Text>
              <Text style={styles.subtitle}>
                {status?.tier === 'vip' ? 'VIP 专属奖励' : 
                 status?.tier === 'premium' ? 'Premium 专属奖励' : '订阅解锁每日奖励'}
              </Text>
            </View>

            {/* 奖励展示 */}
            <View style={styles.rewardContainer}>
              <Animated.View style={[
                styles.coinIcon,
                { transform: [{ scale: Animated.add(1, coinAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0, 0.3],
                }))}] }
              ]}>
                <Text style={styles.coinEmoji}>🌙</Text>
              </Animated.View>
              
              <Text style={styles.rewardAmount}>
                {claimed ? `+${claimedAmount}` : `+${status?.reward_amount || 0}`}
              </Text>
              <Text style={styles.rewardLabel}>月石</Text>
            </View>

            {/* 按钮 */}
            {!claimed ? (
              status?.can_claim ? (
                <TouchableOpacity
                  style={styles.claimButton}
                  onPress={handleClaim}
                  disabled={loading}
                  activeOpacity={0.85}
                >
                  <LinearGradient
                    colors={['#8B5CF6', '#EC4899']}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.claimButtonGradient}
                  >
                    <Text style={styles.claimButtonText}>
                      {loading ? '领取中...' : '领取奖励'}
                    </Text>
                  </LinearGradient>
                </TouchableOpacity>
              ) : status?.already_claimed ? (
                <View style={styles.claimedBadge}>
                  <Ionicons name="checkmark-circle" size={20} color="#4ADE80" />
                  <Text style={styles.claimedText}>今日已领取</Text>
                </View>
              ) : (
                <TouchableOpacity style={styles.subscribeHint} onPress={onClose}>
                  <Text style={styles.subscribeHintText}>订阅解锁每日奖励 →</Text>
                </TouchableOpacity>
              )
            ) : (
              <View style={styles.successContainer}>
                <Ionicons name="checkmark-circle" size={48} color="#4ADE80" />
                <Text style={styles.successText}>领取成功！</Text>
              </View>
            )}

            {/* 提示 */}
            {status?.tier && status.tier !== 'free' && (
              <Text style={styles.tipText}>
                {status.tier === 'vip' ? 'VIP 每日可领 20 月石' : 'Premium 每日可领 10 月石'}
              </Text>
            )}
          </LinearGradient>
        </Animated.View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  container: {
    width: '100%',
    maxWidth: 320,
  },
  card: {
    borderRadius: 24,
    padding: 28,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.3)',
  },
  closeButton: {
    position: 'absolute',
    top: 16,
    right: 16,
    padding: 4,
  },
  header: {
    alignItems: 'center',
    marginBottom: 24,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.6)',
  },
  rewardContainer: {
    alignItems: 'center',
    marginBottom: 28,
  },
  coinIcon: {
    marginBottom: 12,
  },
  coinEmoji: {
    fontSize: 64,
  },
  rewardAmount: {
    fontSize: 48,
    fontWeight: '800',
    color: '#FFD700',
    textShadowColor: 'rgba(255, 215, 0, 0.5)',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 10,
  },
  rewardLabel: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.7)',
    marginTop: 4,
  },
  claimButton: {
    width: '100%',
    borderRadius: 16,
    overflow: 'hidden',
  },
  claimButtonGradient: {
    paddingVertical: 16,
    alignItems: 'center',
  },
  claimButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  claimedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 12,
  },
  claimedText: {
    fontSize: 16,
    color: '#4ADE80',
    fontWeight: '600',
  },
  subscribeHint: {
    paddingVertical: 12,
  },
  subscribeHintText: {
    fontSize: 15,
    color: '#EC4899',
    fontWeight: '500',
  },
  successContainer: {
    alignItems: 'center',
    gap: 8,
  },
  successText: {
    fontSize: 18,
    color: '#4ADE80',
    fontWeight: '600',
  },
  tipText: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.4)',
    marginTop: 20,
  },
});
