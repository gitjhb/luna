/**
 * Daily Reward Modal
 * 限时签到活动弹窗
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
  Image,
  Platform,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
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
  const [eventCheckins, setEventCheckins] = useState(0);
  const { updateWallet } = useUserStore();
  
  // 动画
  const scaleAnim = useRef(new Animated.Value(0.8)).current;
  const coinAnim = useRef(new Animated.Value(0)).current;
  const sparkleAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible) {
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 8,
        tension: 40,
        useNativeDriver: true,
      }).start();
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
    
    if (Platform.OS !== 'web') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    }
    
    setLoading(true);
    try {
      const result = await dailyRewardService.claim();
      
      if (result.success) {
        setClaimedAmount(result.reward_amount);
        setEventCheckins(result.event_checkins || 0);
        setClaimed(true);
        
        if (result.new_balance !== undefined) {
          updateWallet({ totalCredits: result.new_balance });
        }
        
        if (Platform.OS !== 'web') {
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        }
        
        // 成功动画
        Animated.parallel([
          Animated.sequence([
            Animated.timing(coinAnim, {
              toValue: 1.2,
              duration: 200,
              useNativeDriver: true,
            }),
            Animated.spring(coinAnim, {
              toValue: 1,
              friction: 4,
              tension: 100,
              useNativeDriver: true,
            }),
          ]),
          Animated.loop(
            Animated.sequence([
              Animated.timing(sparkleAnim, {
                toValue: 1,
                duration: 300,
                useNativeDriver: true,
              }),
              Animated.timing(sparkleAnim, {
                toValue: 0,
                duration: 300,
                useNativeDriver: true,
              }),
            ]),
            { iterations: 3 }
          ),
        ]).start();
      }
    } catch (e) {
      console.error('Failed to claim daily reward:', e);
      if (Platform.OS !== 'web') {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      }
    } finally {
      setLoading(false);
    }
  };

  if (!visible) return null;

  // 活动已结束
  if (status && !status.event_active) {
    return (
      <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
        <View style={styles.overlay}>
          <Animated.View style={[styles.container, { transform: [{ scale: scaleAnim }] }]}>
            <LinearGradient colors={['#2D1B4E', '#1A1025']} style={styles.card}>
              <TouchableOpacity style={styles.closeButton} onPress={onClose}>
                <Ionicons name="close" size={24} color="rgba(255,255,255,0.5)" />
              </TouchableOpacity>
              <View style={styles.header}>
                <Text style={styles.title}>📅 活动已结束</Text>
                <Text style={styles.subtitle}>敬请期待下次活动~</Text>
              </View>
              <TouchableOpacity style={styles.okButton} onPress={onClose}>
                <Text style={styles.okButtonText}>知道了</Text>
              </TouchableOpacity>
            </LinearGradient>
          </Animated.View>
        </View>
      </Modal>
    );
  }

  const maxDays = status?.max_days || 7;
  const currentCheckins = claimed ? eventCheckins : (status?.event_checkins || 0);

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <Animated.View style={[styles.container, { transform: [{ scale: scaleAnim }] }]}>
          <LinearGradient colors={['#2D1B4E', '#1A1025']} style={styles.card}>
            {/* 关闭按钮 */}
            <TouchableOpacity style={styles.closeButton} onPress={onClose}>
              <Ionicons name="close" size={24} color="rgba(255,255,255,0.5)" />
            </TouchableOpacity>

            {/* 标题 */}
            <View style={styles.header}>
              <Text style={styles.eventName}>{status?.event_name || '🎊 签到活动'}</Text>
              <Text style={styles.title}>
                {claimed ? '🎉 签到成功!' : '✨ 每日签到'}
              </Text>
              {status?.days_left !== undefined && status.days_left > 0 && (
                <Text style={styles.daysLeft}>⏰ 活动剩余 {status.days_left} 天</Text>
              )}
            </View>

            {/* 签到进度 */}
            <View style={styles.progressContainer}>
              <Text style={styles.progressLabel}>
                已签到 {currentCheckins} / {maxDays} 天
              </Text>
              <View style={styles.progressDots}>
                {Array.from({ length: maxDays }, (_, i) => i + 1).map((day) => {
                  const isActive = currentCheckins >= day;
                  return (
                    <View 
                      key={day} 
                      style={[styles.progressDot, isActive && styles.progressDotActive]}
                    >
                      {isActive ? (
                        <Ionicons name="checkmark" size={14} color="#fff" />
                      ) : (
                        <Text style={styles.progressDotText}>{day}</Text>
                      )}
                    </View>
                  );
                })}
              </View>
            </View>

            {/* 奖励展示 */}
            <View style={styles.rewardContainer}>
              <Animated.View style={[
                styles.coinIcon,
                { transform: [{ 
                  scale: coinAnim.interpolate({
                    inputRange: [0, 1, 1.2],
                    outputRange: [1, 1.3, 1],
                    extrapolate: 'clamp',
                  })
                }]}
              ]}>
                <Image 
                  source={require('../assets/icons/moon-shard.png')} 
                  style={styles.coinImage}
                  resizeMode="contain"
                />
                {claimed && (
                  <Animated.View style={[styles.sparkleOverlay, { opacity: sparkleAnim }]}>
                    <Text style={styles.sparkleText}>✨</Text>
                  </Animated.View>
                )}
              </Animated.View>
              
              <Animated.Text style={[
                styles.rewardAmount,
                { transform: [{ scale: coinAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [1, 1.1],
                  extrapolate: 'clamp',
                })}]}
              ]}>
                {claimed ? `+${claimedAmount}` : `+${status?.reward_amount || 50}`}
              </Animated.Text>
              
              <Text style={styles.rewardLabel}>月石 / 天</Text>
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
                    colors={['#8B5CF6', '#00D4FF']}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.claimButtonGradient}
                  >
                    <Text style={styles.claimButtonText}>
                      {loading ? '领取中...' : '🎁 领取奖励'}
                    </Text>
                  </LinearGradient>
                </TouchableOpacity>
              ) : status?.already_claimed ? (
                <View style={styles.claimedBadge}>
                  <Ionicons name="checkmark-circle" size={20} color="#4ADE80" />
                  <Text style={styles.claimedText}>今日已签到</Text>
                </View>
              ) : (
                <View style={styles.claimedBadge}>
                  <Ionicons name="trophy" size={20} color="#FFD700" />
                  <Text style={styles.completeText}>已签满全部天数!</Text>
                </View>
              )
            ) : (
              <View style={styles.successContainer}>
                <Ionicons name="checkmark-circle" size={48} color="#4ADE80" />
                <Text style={styles.successText}>
                  {eventCheckins >= maxDays ? '🎊 恭喜集齐全部奖励!' : '明天继续哦~'}
                </Text>
              </View>
            )}

            {/* 累计奖励 */}
            {(status?.total_rewards || 0) > 0 && (
              <Text style={styles.totalRewards}>
                💎 累计获得 {status?.total_rewards} 月石
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
    maxWidth: 340,
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
    marginBottom: 20,
  },
  eventName: {
    fontSize: 14,
    color: '#FFD700',
    fontWeight: '600',
    marginBottom: 4,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.6)',
  },
  daysLeft: {
    fontSize: 13,
    color: '#00D4FF',
    marginTop: 8,
  },
  
  // 进度
  progressContainer: {
    width: '100%',
    marginBottom: 24,
  },
  progressLabel: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    textAlign: 'center',
    marginBottom: 12,
    fontWeight: '600',
  },
  progressDots: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
  },
  progressDot: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(255,255,255,0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.2)',
  },
  progressDotActive: {
    backgroundColor: '#4ADE80',
    borderColor: '#4ADE80',
  },
  progressDotText: {
    fontSize: 12,
    fontWeight: '700',
    color: 'rgba(255,255,255,0.5)',
  },
  
  // 奖励
  rewardContainer: {
    alignItems: 'center',
    marginBottom: 28,
  },
  coinIcon: {
    marginBottom: 12,
    position: 'relative',
  },
  coinImage: {
    width: 80,
    height: 80,
  },
  sparkleOverlay: {
    position: 'absolute',
    top: -10,
    right: -10,
  },
  sparkleText: {
    fontSize: 20,
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
  
  // 按钮
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
  completeText: {
    fontSize: 16,
    color: '#FFD700',
    fontWeight: '600',
  },
  successContainer: {
    alignItems: 'center',
    gap: 8,
  },
  successText: {
    fontSize: 16,
    color: '#4ADE80',
    fontWeight: '600',
  },
  okButton: {
    paddingHorizontal: 32,
    paddingVertical: 12,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 12,
    marginTop: 20,
  },
  okButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  totalRewards: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.5)',
    marginTop: 16,
  },
});
