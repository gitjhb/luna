/**
 * Profile Screen - Purple Pink Theme
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme, getShadow } from '../../theme/config';
import { useUserStore } from '../../store/userStore';
import { walletService } from '../../services/walletService';
import { CreditPackage, SubscriptionPlan } from '../../types';

export default function ProfileScreen() {
  const router = useRouter();
  const { user, wallet, updateWallet, logout, isSubscribed } = useUserStore();
  
  const [refreshing, setRefreshing] = useState(false);
  const [creditPackages, setCreditPackages] = useState<CreditPackage[]>([]);
  const [subscriptionPlans, setSubscriptionPlans] = useState<SubscriptionPlan[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [balance, packages, plans] = await Promise.all([
        walletService.getBalance(),
        walletService.getCreditPackages(),
        walletService.getSubscriptionPlans(),
      ]);
      updateWallet(balance);
      setCreditPackages(packages);
      setSubscriptionPlans(plans);
    } catch (error) {
      console.error('Failed to load profile data:', error);
    }
  };

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  }, []);

  const handleBuyCredits = async (pkg: CreditPackage) => {
    Alert.alert('购买积分', `购买 ${pkg.credits} 积分，$${(pkg.priceUsd ?? 0).toFixed(2)}？`, [
      { text: '取消', style: 'cancel' },
      { text: '购买', onPress: () => Alert.alert('提示', '支付功能即将上线') },
    ]);
  };

  const handleLogout = () => {
    Alert.alert('退出登录', '确定要退出吗？', [
      { text: '取消', style: 'cancel' },
      { text: '退出', style: 'destructive', onPress: () => { logout(); router.replace('/auth/login'); }},
    ]);
  };

  return (
    <LinearGradient colors={theme.colors.background.gradient} style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <ScrollView
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.primary.main} />
          }
        >
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.title}>我的</Text>
          </View>

          {/* User Card */}
          <View style={styles.section}>
            <View style={styles.userCard}>
              <LinearGradient colors={theme.colors.primary.gradient} style={styles.avatar}>
                <Text style={styles.avatarText}>{user?.displayName?.charAt(0).toUpperCase() || 'U'}</Text>
              </LinearGradient>
              <View style={styles.userInfo}>
                <Text style={styles.userName}>{user?.displayName || 'Guest'}</Text>
                <Text style={styles.userEmail}>{user?.email || ''}</Text>
              </View>
              <View style={[styles.tierBadge, isSubscribed && styles.tierBadgePremium]}>
                <Text style={styles.tierText}>{isSubscribed ? 'VIP' : '免费'}</Text>
              </View>
            </View>
          </View>

          {/* Credits */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>我的积分</Text>
            <View style={styles.creditsCard}>
              <View style={styles.creditsMain}>
                <Ionicons name="diamond" size={28} color={theme.colors.primary.main} />
                <Text style={styles.creditsAmount}>{wallet?.totalCredits?.toFixed(0) || '0'}</Text>
              </View>
              <View style={styles.creditsBreakdown}>
                <View style={styles.creditsRow}>
                  <Text style={styles.creditsLabel}>每日赠送</Text>
                  <Text style={styles.creditsValue}>{wallet?.dailyFreeCredits?.toFixed(0) || '0'}</Text>
                </View>
                <View style={styles.creditsRow}>
                  <Text style={styles.creditsLabel}>已购买</Text>
                  <Text style={styles.creditsValue}>{wallet?.purchedCredits?.toFixed(0) || '0'}</Text>
                </View>
              </View>
            </View>
          </View>

          {/* Buy Credits */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>购买积分</Text>
            <View style={styles.packagesGrid}>
              {creditPackages.map((pkg) => (
                <TouchableOpacity
                  key={pkg.sku}
                  style={[styles.packageCard, pkg.popular && styles.packageCardPopular]}
                  onPress={() => handleBuyCredits(pkg)}
                >
                  {pkg.popular && (
                    <View style={styles.popularBadge}>
                      <Text style={styles.popularBadgeText}>热门</Text>
                    </View>
                  )}
                  <Text style={styles.packageCredits}>{pkg.credits}</Text>
                  <Text style={styles.packageLabel}>积分</Text>
                  <Text style={styles.packagePrice}>${(pkg.priceUsd ?? 0).toFixed(2)}</Text>
                  {(pkg.discountPercentage ?? 0) > 0 && (
                    <Text style={styles.packageDiscount}>-{pkg.discountPercentage}%</Text>
                  )}
                </TouchableOpacity>
              ))}
            </View>
          </View>

          {/* Settings */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>设置</Text>
            <View style={styles.settingsCard}>
              <TouchableOpacity style={styles.settingsRow}>
                <Ionicons name="notifications-outline" size={22} color={theme.colors.text.secondary} />
                <Text style={styles.settingsText}>通知设置</Text>
                <Ionicons name="chevron-forward" size={18} color={theme.colors.text.tertiary} />
              </TouchableOpacity>
              <TouchableOpacity style={styles.settingsRow}>
                <Ionicons name="shield-outline" size={22} color={theme.colors.text.secondary} />
                <Text style={styles.settingsText}>隐私设置</Text>
                <Ionicons name="chevron-forward" size={18} color={theme.colors.text.tertiary} />
              </TouchableOpacity>
              <TouchableOpacity style={styles.settingsRow}>
                <Ionicons name="help-circle-outline" size={22} color={theme.colors.text.secondary} />
                <Text style={styles.settingsText}>帮助与反馈</Text>
                <Ionicons name="chevron-forward" size={18} color={theme.colors.text.tertiary} />
              </TouchableOpacity>
            </View>
          </View>

          {/* Logout */}
          <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
            <Ionicons name="log-out-outline" size={22} color={theme.colors.error} />
            <Text style={styles.logoutText}>退出登录</Text>
          </TouchableOpacity>

          <View style={{ height: 100 }} />
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safeArea: { flex: 1 },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
  },
  section: {
    paddingHorizontal: 20,
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 12,
  },
  userCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 20,
    padding: 16,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    fontSize: 22,
    fontWeight: '700',
    color: '#fff',
  },
  userInfo: {
    flex: 1,
    marginLeft: 14,
  },
  userName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  userEmail: {
    fontSize: 13,
    color: theme.colors.text.secondary,
    marginTop: 2,
  },
  tierBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  tierBadgePremium: {
    backgroundColor: 'rgba(236, 72, 153, 0.2)',
  },
  tierText: {
    fontSize: 13,
    fontWeight: '600',
    color: theme.colors.primary.main,
  },
  creditsCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 20,
    padding: 20,
  },
  creditsMain: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 16,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  creditsAmount: {
    fontSize: 36,
    fontWeight: '700',
    color: theme.colors.primary.main,
  },
  creditsBreakdown: { gap: 8 },
  creditsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  creditsLabel: {
    fontSize: 14,
    color: theme.colors.text.secondary,
  },
  creditsValue: {
    fontSize: 14,
    fontWeight: '500',
    color: '#fff',
  },
  packagesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  packageCard: {
    width: '47%',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
  },
  packageCardPopular: {
    borderWidth: 2,
    borderColor: theme.colors.primary.main,
  },
  popularBadge: {
    position: 'absolute',
    top: -10,
    backgroundColor: theme.colors.primary.main,
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 10,
  },
  popularBadgeText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#fff',
  },
  packageCredits: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
  },
  packageLabel: {
    fontSize: 13,
    color: theme.colors.text.secondary,
  },
  packagePrice: {
    fontSize: 17,
    fontWeight: '600',
    color: theme.colors.primary.main,
    marginTop: 8,
  },
  packageDiscount: {
    fontSize: 12,
    fontWeight: '600',
    color: theme.colors.success,
    marginTop: 4,
  },
  settingsCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 16,
    overflow: 'hidden',
  },
  settingsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
    gap: 12,
  },
  settingsText: {
    flex: 1,
    fontSize: 15,
    color: '#fff',
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginHorizontal: 20,
    padding: 14,
    borderRadius: 14,
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    gap: 8,
  },
  logoutText: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.error,
  },
});
