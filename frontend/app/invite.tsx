/**
 * Invite Friends Screen
 * 
 * Shows user's referral code, share options, and list of referred friends.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Image,
  Alert,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../theme/config';
import { referralService, ReferralStats, ReferredFriend } from '../services/referralService';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

export default function InviteScreen() {
  const router = useRouter();
  
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [referralStats, setReferralStats] = useState<ReferralStats | null>(null);
  const [friends, setFriends] = useState<ReferredFriend[]>([]);
  const [copying, setCopying] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [stats, friendsData] = await Promise.all([
        referralService.getMyReferralCode(),
        referralService.getReferredFriends(),
      ]);
      setReferralStats(stats);
      setFriends(friendsData.friends);
    } catch (error) {
      console.error('Failed to load referral data:', error);
      Alert.alert('加载失败', '无法获取邀请信息，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  }, []);

  const handleCopyCode = async () => {
    if (!referralStats || copying) return;
    
    setCopying(true);
    const success = await referralService.copyReferralCode(referralStats.referralCode);
    setCopying(false);
    
    if (success) {
      Alert.alert('复制成功', '邀请码已复制到剪贴板');
    }
  };

  const handleShare = async () => {
    if (!referralStats) return;
    await referralService.shareReferralCode(
      referralStats.referralCode,
      referralStats.shareText
    );
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}月${date.getDate()}日`;
  };

  if (loading) {
    return (
      <LinearGradient colors={theme.colors.background.gradient} style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={theme.colors.primary.main} />
            <Text style={styles.loadingText}>加载中...</Text>
          </View>
        </SafeAreaView>
      </LinearGradient>
    );
  }

  return (
    <LinearGradient colors={theme.colors.background.gradient} style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <ScrollView
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl 
              refreshing={refreshing} 
              onRefresh={onRefresh} 
              tintColor={theme.colors.primary.main} 
            />
          }
        >
          {/* Header */}
          <View style={styles.header}>
            <TouchableOpacity 
              style={styles.backButton}
              onPress={() => router.back()}
            >
              <Ionicons name="chevron-back" size={24} color="#fff" />
            </TouchableOpacity>
            <Text style={styles.title}>邀请好友</Text>
            <View style={{ width: 40 }} />
          </View>

          {/* Hero Section */}
          <View style={styles.heroSection}>
            <View style={styles.heroIconContainer}>
              <Text style={styles.heroIcon}>🎁</Text>
            </View>
            <Text style={styles.heroTitle}>邀请好友，共享金币</Text>
            <Text style={styles.heroSubtitle}>
              每邀请一位好友注册，你将获得 
              <Text style={styles.highlightText}> {referralStats?.rewardPerReferral || 50} </Text>
              金币奖励
            </Text>
          </View>

          {/* Referral Code Card */}
          <View style={styles.codeCard}>
            <Text style={styles.codeLabel}>我的邀请码</Text>
            <View style={styles.codeContainer}>
              <Text style={styles.codeText}>{referralStats?.referralCode || '------'}</Text>
              <TouchableOpacity 
                style={styles.copyButton}
                onPress={handleCopyCode}
                disabled={copying}
              >
                <Ionicons 
                  name={copying ? 'checkmark' : 'copy-outline'} 
                  size={20} 
                  color={theme.colors.primary.main} 
                />
              </TouchableOpacity>
            </View>
            
            <TouchableOpacity 
              style={styles.shareButton}
              onPress={handleShare}
            >
              <Ionicons name="share-social" size={20} color="#fff" />
              <Text style={styles.shareButtonText}>分享给好友</Text>
            </TouchableOpacity>
          </View>

          {/* Stats Card */}
          <View style={styles.statsCard}>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{referralStats?.totalReferrals || 0}</Text>
              <Text style={styles.statLabel}>已邀请好友</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statValueGold}>
                {referralStats?.totalRewardsEarned || 0}
                <Text style={styles.statValueUnit}> 🪙</Text>
              </Text>
              <Text style={styles.statLabel}>累计获得</Text>
            </View>
          </View>

          {/* How It Works */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>邀请规则</Text>
            <View style={styles.rulesCard}>
              <View style={styles.ruleItem}>
                <View style={styles.ruleStep}>
                  <Text style={styles.ruleStepText}>1</Text>
                </View>
                <View style={styles.ruleContent}>
                  <Text style={styles.ruleTitle}>分享邀请码</Text>
                  <Text style={styles.ruleDesc}>将你的专属邀请码分享给好友</Text>
                </View>
              </View>
              <View style={styles.ruleLine} />
              <View style={styles.ruleItem}>
                <View style={styles.ruleStep}>
                  <Text style={styles.ruleStepText}>2</Text>
                </View>
                <View style={styles.ruleContent}>
                  <Text style={styles.ruleTitle}>好友注册</Text>
                  <Text style={styles.ruleDesc}>好友使用邀请码完成注册</Text>
                </View>
              </View>
              <View style={styles.ruleLine} />
              <View style={styles.ruleItem}>
                <View style={styles.ruleStep}>
                  <Text style={styles.ruleStepText}>3</Text>
                </View>
                <View style={styles.ruleContent}>
                  <Text style={styles.ruleTitle}>双方获奖</Text>
                  <Text style={styles.ruleDesc}>
                    你获得 {referralStats?.rewardPerReferral || 50} 金币，
                    好友获得 {referralStats?.newUserBonus || 20} 金币
                  </Text>
                </View>
              </View>
            </View>
          </View>

          {/* Friends List */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              已邀请的好友 ({referralStats?.totalReferrals || 0})
            </Text>
            
            {friends.length > 0 ? (
              <View style={styles.friendsCard}>
                {friends.map((friend, index) => (
                  <View 
                    key={friend.user_id} 
                    style={[
                      styles.friendItem,
                      index < friends.length - 1 && styles.friendItemBorder
                    ]}
                  >
                    <Image 
                      source={{ uri: friend.avatar_url || 'https://i.pravatar.cc/200' }}
                      style={styles.friendAvatar}
                    />
                    <View style={styles.friendInfo}>
                      <Text style={styles.friendName}>{friend.display_name}</Text>
                      <Text style={styles.friendDate}>{formatDate(friend.referred_at)}</Text>
                    </View>
                    <View style={styles.friendReward}>
                      <Text style={styles.friendRewardText}>+{friend.reward_earned} 🪙</Text>
                    </View>
                  </View>
                ))}
              </View>
            ) : (
              <View style={styles.emptyCard}>
                <Text style={styles.emptyIcon}>👥</Text>
                <Text style={styles.emptyText}>还没有邀请好友</Text>
                <Text style={styles.emptyHint}>分享邀请码，一起来玩吧！</Text>
              </View>
            )}
          </View>

          <View style={{ height: 40 }} />
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safeArea: { flex: 1 },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: theme.colors.text.secondary,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  backButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  
  // Hero Section
  heroSection: {
    alignItems: 'center',
    paddingVertical: 32,
    paddingHorizontal: 20,
  },
  heroIconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(255, 215, 0, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  heroIcon: {
    fontSize: 40,
  },
  heroTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 8,
  },
  heroSubtitle: {
    fontSize: 15,
    color: theme.colors.text.secondary,
    textAlign: 'center',
    lineHeight: 22,
  },
  highlightText: {
    color: '#FFD700',
    fontWeight: '700',
  },
  
  // Code Card
  codeCard: {
    marginHorizontal: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 20,
    padding: 24,
    alignItems: 'center',
  },
  codeLabel: {
    fontSize: 14,
    color: theme.colors.text.secondary,
    marginBottom: 12,
  },
  codeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 20,
  },
  codeText: {
    fontSize: 32,
    fontWeight: '800',
    color: '#fff',
    letterSpacing: 4,
  },
  copyButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(139, 92, 246, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  shareButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.colors.primary.main,
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 25,
    gap: 8,
    width: '100%',
  },
  shareButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  
  // Stats Card
  statsCard: {
    marginHorizontal: 20,
    marginTop: 16,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 16,
    padding: 20,
    flexDirection: 'row',
    alignItems: 'center',
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 28,
    fontWeight: '700',
    color: '#fff',
  },
  statValueGold: {
    fontSize: 28,
    fontWeight: '700',
    color: '#FFD700',
  },
  statValueUnit: {
    fontSize: 18,
  },
  statLabel: {
    fontSize: 13,
    color: theme.colors.text.secondary,
    marginTop: 4,
  },
  statDivider: {
    width: 1,
    height: 40,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
  },
  
  // Section
  section: {
    marginTop: 32,
    paddingHorizontal: 20,
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 16,
  },
  
  // Rules Card
  rulesCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 16,
    padding: 20,
  },
  ruleItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  ruleStep: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: theme.colors.primary.main,
    justifyContent: 'center',
    alignItems: 'center',
  },
  ruleStepText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#fff',
  },
  ruleContent: {
    flex: 1,
    marginLeft: 14,
  },
  ruleTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 2,
  },
  ruleDesc: {
    fontSize: 13,
    color: theme.colors.text.secondary,
    lineHeight: 18,
  },
  ruleLine: {
    width: 2,
    height: 20,
    backgroundColor: 'rgba(139, 92, 246, 0.3)',
    marginLeft: 13,
    marginVertical: 4,
  },
  
  // Friends List
  friendsCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 16,
    overflow: 'hidden',
  },
  friendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
  },
  friendItemBorder: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(255, 255, 255, 0.08)',
  },
  friendAvatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
  },
  friendInfo: {
    flex: 1,
    marginLeft: 12,
  },
  friendName: {
    fontSize: 15,
    fontWeight: '500',
    color: '#fff',
  },
  friendDate: {
    fontSize: 12,
    color: theme.colors.text.tertiary,
    marginTop: 2,
  },
  friendReward: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: 'rgba(255, 215, 0, 0.15)',
    borderRadius: 12,
  },
  friendRewardText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#FFD700',
  },
  
  // Empty State
  emptyCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 16,
    padding: 40,
    alignItems: 'center',
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 16,
    fontWeight: '500',
    color: '#fff',
    marginBottom: 4,
  },
  emptyHint: {
    fontSize: 13,
    color: theme.colors.text.secondary,
  },
});
