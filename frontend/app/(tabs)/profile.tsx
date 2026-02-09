/**
 * Profile Screen - User Profile with Avatar, Name, Interests
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
  TextInput,
  Image,
  Modal,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../theme/config';
import { useUserStore } from '../../store/userStore';
import { walletService } from '../../services/walletService';
import { paymentService } from '../../services/paymentService';
import { RechargeModal } from '../../components/RechargeModal';
import { SubscriptionModalRC as SubscriptionModal } from '../../components/SubscriptionModalRC';
import { TransactionHistoryModal } from '../../components/TransactionHistoryModal';
import { interestsService, InterestItem } from '../../services/interestsService';
import { useLocale, tpl } from '../../i18n';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// No default avatar placeholders - use user's real photo or show initials

export default function ProfileScreen() {
  const router = useRouter();
  const { t } = useLocale();
  const { user, wallet, updateWallet, updateUser, isSubscribed, isVip, isPremium } = useUserStore();
  
  // Get display tier name
  const getTierDisplay = () => {
    if (isVip) return 'VIP';
    if (isPremium) return 'Premium';
    return 'Free';
  };
  
  const [refreshing, setRefreshing] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [nameInput, setNameInput] = useState(user?.displayName || '');
  // Avatar picker removed - users use their Google/Apple photo
  const [showInterestsPicker, setShowInterestsPicker] = useState(false);
  const [showRechargeModal, setShowRechargeModal] = useState(false);
  const [showSubscriptionModal, setShowSubscriptionModal] = useState(false);
  const [showTransactionHistory, setShowTransactionHistory] = useState(false);
  
  // User preferences - use real avatar or null
  const [userAvatar, setUserAvatar] = useState(user?.avatar || null);
  const [selectedInterestIds, setSelectedInterestIds] = useState<number[]>([]);
  const [availableInterests, setAvailableInterests] = useState<InterestItem[]>([]);
  const [savingInterests, setSavingInterests] = useState(false);

  // Alias for backward compat in rendering
  const selectedInterests = selectedInterestIds;

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      // 同步钱包
      const balance = await walletService.getBalance();
      updateWallet(balance);
      
      // 同步订阅状态
      const subscription = await paymentService.getSubscription();
      if (subscription) {
        updateUser({ 
          subscriptionTier: subscription.tier || 'free',
          subscriptionExpiresAt: subscription.expires_at || undefined,
        });
      }
      
      // 加载兴趣列表和用户已选兴趣
      try {
        const [interestList, userInterests] = await Promise.all([
          interestsService.getInterestList(),
          interestsService.getUserInterests(),
        ]);
        setAvailableInterests(interestList.interests);
        setSelectedInterestIds(userInterests.interestIds);
      } catch (e) {
        console.warn('Failed to load interests:', e);
      }
    } catch (error) {
      console.error('Failed to load profile data:', error);
    }
  };

  const handleManageSubscription = async () => {
    // RevenueCat方式：打开系统订阅管理页面
    // 用户可以在那里取消或更改订阅计划
    try {
      const Purchases = require('react-native-purchases').default;
      await Purchases.showManageSubscriptions();
    } catch (e: any) {
      // Fallback: 提示用户手动去设置
      Alert.alert(
        '管理订阅',
        '请前往 设置 → Apple ID → 订阅 来管理您的订阅。\n\n取消后，您仍可享用权益直到当前周期结束。',
        [{ text: '好的', style: 'default' }]
      );
    }
  };

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  }, []);

  const handleSaveName = () => {
    if (nameInput.trim()) {
      updateUser({ displayName: nameInput.trim() });
      setEditingName(false);
    }
  };

  // handleSelectAvatar removed - users use their Google/Apple photo

  const MAX_INTERESTS = 5;

  const toggleInterest = (interestId: number) => {
    setSelectedInterestIds(prev => {
      if (prev.includes(interestId)) {
        return prev.filter(id => id !== interestId);
      }
      if (prev.length >= MAX_INTERESTS) {
        Alert.alert('', tpl(t.profile.maxInterests, { max: MAX_INTERESTS }));
        return prev;
      }
      return [...prev, interestId];
    });
  };

  const handleSaveInterests = async () => {
    setSavingInterests(true);
    try {
      await interestsService.updateUserInterests(selectedInterestIds);
    } catch (e) {
      console.warn('Failed to save interests:', e);
    } finally {
      setSavingInterests(false);
      setShowInterestsPicker(false);
    }
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
            <Text style={styles.title}>{t.profile.title}</Text>
          </View>

          {/* Profile Card */}
          <View style={styles.profileCard}>
            {/* Avatar */}
            <View style={styles.avatarContainer}>
              {userAvatar ? (
                <Image source={{ uri: userAvatar }} style={styles.avatar} />
              ) : (
                <View style={[styles.avatar, styles.avatarPlaceholder]}>
                  <Text style={styles.avatarInitials}>
                    {(user?.displayName || 'U').charAt(0).toUpperCase()}
                  </Text>
                </View>
              )}
            </View>

            {/* Name */}
            <View style={styles.nameContainer}>
              {editingName ? (
                <View style={styles.nameEditRow}>
                  <TextInput
                    style={styles.nameInput}
                    value={nameInput}
                    onChangeText={setNameInput}
                    placeholder={t.profile.enterNickname}
                    placeholderTextColor={theme.colors.text.tertiary}
                    autoFocus
                    maxLength={20}
                  />
                  <TouchableOpacity style={styles.nameSaveButton} onPress={handleSaveName}>
                    <Ionicons name="checkmark" size={20} color="#fff" />
                  </TouchableOpacity>
                </View>
              ) : (
                <TouchableOpacity 
                  style={styles.nameRow}
                  onPress={() => { setNameInput(user?.displayName || ''); setEditingName(true); }}
                >
                  <Text style={styles.userName}>{user?.displayName || 'Guest'}</Text>
                  <Ionicons name="pencil" size={16} color={theme.colors.text.tertiary} />
                </TouchableOpacity>
              )}
              <Text style={styles.userEmail}>{user?.email || ''}</Text>
            </View>

            {/* Membership Badge - Clickable */}
            <TouchableOpacity 
              style={[styles.membershipBadge, isSubscribed && styles.membershipBadgePremium]}
              onPress={() => setShowSubscriptionModal(true)}
              activeOpacity={0.7}
            >
              <Ionicons 
                name={isSubscribed ? 'diamond' : 'person'} 
                size={14} 
                color={isSubscribed ? '#FFD700' : theme.colors.text.tertiary} 
              />
              <Text style={[styles.membershipText, isSubscribed && styles.membershipTextPremium]}>
                {getTierDisplay()}
              </Text>
              {!isSubscribed && (
                <Ionicons name="chevron-forward" size={12} color={theme.colors.text.tertiary} />
              )}
            </TouchableOpacity>
            
            {/* Cancel Subscription Link */}
            {isSubscribed && (
              <TouchableOpacity 
                style={styles.cancelSubscriptionLink}
                onPress={handleManageSubscription}
              >
                <Text style={styles.cancelSubscriptionText}>管理订阅</Text>
              </TouchableOpacity>
            )}
          </View>

          {/* Credits Card */}
          <View style={styles.section}>
            <View style={styles.creditsCard}>
              <View style={styles.creditsHeader}>
                <View style={styles.creditsIconContainer}>
                  <Image 
                    source={require('../../assets/icons/moon-shard.png')} 
                    style={styles.creditsIconImage}
                  />
                </View>
                <View style={styles.creditsInfo}>
                  <Text style={styles.creditsLabel}>{t.profile.myCoins}</Text>
                  <Text style={styles.creditsAmount}>{wallet?.totalCredits?.toFixed(0) || '0'}</Text>
                </View>
                <TouchableOpacity 
                  style={styles.rechargeButton}
                  onPress={() => setShowRechargeModal(true)}
                >
                  <Text style={styles.rechargeText}>{t.profile.recharge}</Text>
                </TouchableOpacity>
              </View>
              <View style={styles.creditsDivider} />
              <View style={styles.creditsDetails}>
                <View style={styles.creditsDetailItem}>
                  <Text style={styles.creditsDetailLabel}>{t.profile.dailyFree}</Text>
                  <Text style={styles.creditsDetailValue}>{tpl(t.profile.perDay, { count: wallet?.dailyFreeCredits || 0 })}</Text>
                </View>
                <View style={styles.creditsDetailItem}>
                  <Text style={styles.creditsDetailLabel}>{t.profile.purchased}</Text>
                  <Text style={styles.creditsDetailValue}>{wallet?.purchedCredits || 0}</Text>
                </View>
              </View>
              {/* Transaction History Button */}
              <TouchableOpacity 
                style={styles.transactionHistoryButton}
                onPress={() => setShowTransactionHistory(true)}
              >
                <Ionicons name="receipt-outline" size={16} color={theme.colors.text.secondary} />
                <Text style={styles.transactionHistoryText}>{t.profile.viewBills}</Text>
                <Ionicons name="chevron-forward" size={16} color={theme.colors.text.tertiary} />
              </TouchableOpacity>
            </View>
          </View>

          {/* Interests Section */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>{t.profile.myInterests}</Text>
              <TouchableOpacity onPress={() => setShowInterestsPicker(true)}>
                <Text style={styles.editLink}>{t.profile.edit}</Text>
              </TouchableOpacity>
            </View>
            <View style={styles.interestsCard}>
              {selectedInterestIds.length > 0 ? (
                <View style={styles.interestTags}>
                  {selectedInterestIds.map(id => {
                    const interest = availableInterests.find(i => i.id === id);
                    return interest ? (
                      <View key={id} style={styles.interestTag}>
                        <Text style={styles.interestTagEmoji}>{interest.icon || '⭐'}</Text>
                        <Text style={styles.interestTagText}>{interest.displayName?.replace(/^[^\s]+\s/, '') || interest.name}</Text>
                      </View>
                    ) : null;
                  })}
                </View>
              ) : (
                <TouchableOpacity 
                  style={styles.addInterestsButton}
                  onPress={() => setShowInterestsPicker(true)}
                >
                  <Ionicons name="add-circle-outline" size={24} color={theme.colors.primary.main} />
                  <Text style={styles.addInterestsText}>{t.profile.addInterests}</Text>
                </TouchableOpacity>
              )}
            </View>
            <Text style={styles.interestsHint}>
              {t.profile.interestsHint}
            </Text>
          </View>

          {/* Quick Actions */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{t.profile.more}</Text>
            <View style={styles.actionsCard}>
              {/* MVP: Invite friends hidden for now */}
              <TouchableOpacity style={styles.actionRow}>
                <View style={styles.actionIcon}>
                  <Ionicons name="star-outline" size={20} color={theme.colors.primary.main} />
                </View>
                <Text style={styles.actionText}>{t.profile.rateUs}</Text>
                <Ionicons name="chevron-forward" size={18} color={theme.colors.text.tertiary} />
              </TouchableOpacity>
              <TouchableOpacity style={styles.actionRow}>
                <View style={styles.actionIcon}>
                  <Ionicons name="help-circle-outline" size={20} color={theme.colors.primary.main} />
                </View>
                <Text style={styles.actionText}>{t.profile.helpFeedback}</Text>
                <Ionicons name="chevron-forward" size={18} color={theme.colors.text.tertiary} />
              </TouchableOpacity>
            </View>
          </View>

          <View style={{ height: 120 }} />
        </ScrollView>
      </SafeAreaView>

      {/* Interests Picker Modal */}
      <Modal
        visible={showInterestsPicker}
        transparent
        animationType="slide"
        onRequestClose={() => setShowInterestsPicker(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>{tpl(t.profile.selectInterests, { count: selectedInterestIds.length, max: MAX_INTERESTS })}</Text>
              <TouchableOpacity onPress={handleSaveInterests} disabled={savingInterests}>
                <Text style={styles.modalDoneText}>{savingInterests ? t.profile.saving : t.profile.done}</Text>
              </TouchableOpacity>
            </View>
            <ScrollView style={styles.interestsGrid}>
              <View style={styles.interestsGridInner}>
                {availableInterests.map(interest => (
                  <TouchableOpacity
                    key={interest.id}
                    style={[
                      styles.interestOption,
                      selectedInterestIds.includes(interest.id) && styles.interestOptionSelected,
                    ]}
                    onPress={() => toggleInterest(interest.id)}
                  >
                    <Text style={styles.interestOptionEmoji}>{interest.icon || '⭐'}</Text>
                    <Text style={[
                      styles.interestOptionText,
                      selectedInterestIds.includes(interest.id) && styles.interestOptionTextSelected,
                    ]}>
                      {interest.displayName?.replace(/^[^\s]+\s/, '') || interest.name}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* Recharge Modal */}
      <RechargeModal
        visible={showRechargeModal}
        onClose={() => setShowRechargeModal(false)}
      />

      {/* Subscription Modal */}
      <SubscriptionModal
        visible={showSubscriptionModal}
        onClose={() => setShowSubscriptionModal(false)}
      />

      {/* Transaction History Modal */}
      <TransactionHistoryModal
        visible={showTransactionHistory}
        onClose={() => setShowTransactionHistory(false)}
      />
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  safeArea: { flex: 1 },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  title: {
    fontSize: 22,
    fontWeight: '300',
    color: '#fff',
    letterSpacing: 2,
  },
  profileCard: {
    alignItems: 'center',
    paddingVertical: 24,
    paddingHorizontal: 20,
  },
  avatarContainer: {
    position: 'relative',
    marginBottom: 16,
  },
  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
    borderWidth: 1,
    borderColor: theme.colors.primary.main,
    // HUD glow effect
    shadowColor: theme.colors.primary.main,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 12,
  },
  avatarPlaceholder: {
    backgroundColor: 'rgba(0, 212, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.4)',
  },
  avatarInitials: {
    fontSize: 36,
    fontWeight: '300',
    color: theme.colors.primary.main,
    fontFamily: 'Courier',  // Monospace for 2077 feel
  },
  avatarEditBadge: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: theme.colors.primary.main,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: theme.colors.background.primary,
  },
  nameContainer: {
    alignItems: 'center',
    marginBottom: 12,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  nameEditRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  userName: {
    fontSize: 22,
    fontWeight: '700',
    color: '#fff',
  },
  nameInput: {
    fontSize: 20,
    fontWeight: '600',
    color: '#fff',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 12,
    minWidth: 150,
    textAlign: 'center',
  },
  nameSaveButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: theme.colors.primary.main,
    justifyContent: 'center',
    alignItems: 'center',
  },
  userEmail: {
    fontSize: 14,
    color: theme.colors.text.secondary,
    marginTop: 4,
  },
  membershipBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'transparent',
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 8,
    gap: 6,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  membershipBadgePremium: {
    borderColor: 'rgba(0, 245, 212, 0.4)',
    shadowColor: '#00F5D4',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  membershipText: {
    fontSize: 12,
    fontWeight: '400',
    color: theme.colors.text.secondary,
    letterSpacing: 1,
    fontFamily: 'Courier',
  },
  membershipTextPremium: {
    color: '#00F5D4',
  },
  cancelSubscriptionLink: {
    marginTop: 8,
  },
  cancelSubscriptionText: {
    fontSize: 12,
    color: theme.colors.text.tertiary,
    textDecorationLine: 'underline',
  },
  section: {
    paddingHorizontal: 20,
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 12,
  },
  editLink: {
    fontSize: 14,
    color: theme.colors.primary.main,
    marginBottom: 12,
  },
  creditsCard: {
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.15)',
    // HUD glow
    shadowColor: theme.colors.primary.main,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
  },
  creditsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  creditsIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 12,
    backgroundColor: 'rgba(0, 212, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.2)',
  },
  creditsIconImage: {
    width: 40,
    height: 40,
    borderRadius: 20,
  },
  creditsIcon: {
    fontSize: 24,
  },
  creditsInfo: {
    flex: 1,
    marginLeft: 14,
  },
  creditsLabel: {
    fontSize: 13,
    color: theme.colors.text.secondary,
  },
  creditsAmount: {
    fontSize: 32,
    fontWeight: '300',
    color: theme.colors.primary.main,
    fontFamily: 'Courier',  // Monospace for data display
    letterSpacing: 2,
  },
  rechargeButton: {
    backgroundColor: 'transparent',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.colors.primary.main,
  },
  rechargeText: {
    fontSize: 13,
    fontWeight: '500',
    color: theme.colors.primary.main,
    letterSpacing: 1,
  },
  creditsDivider: {
    height: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    marginVertical: 16,
  },
  creditsDetails: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  creditsDetailItem: {
    alignItems: 'center',
  },
  creditsDetailLabel: {
    fontSize: 13,
    color: theme.colors.text.tertiary,
    marginBottom: 4,
  },
  creditsDetailValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  transactionHistoryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
    gap: 8,
  },
  transactionHistoryText: {
    fontSize: 14,
    color: theme.colors.text.secondary,
  },
  interestsCard: {
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    borderRadius: 12,
    padding: 16,
    minHeight: 80,
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.1)',
  },
  interestTags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  interestTag: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 212, 255, 0.1)',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    gap: 6,
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.2)',
  },
  interestTagEmoji: {
    fontSize: 16,
  },
  interestTagText: {
    fontSize: 14,
    color: '#fff',
  },
  addInterestsButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 16,
  },
  addInterestsText: {
    fontSize: 14,
    color: theme.colors.text.secondary,
  },
  interestsHint: {
    fontSize: 12,
    color: theme.colors.text.tertiary,
    marginTop: 8,
    textAlign: 'center',
  },
  actionsCard: {
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.1)',
  },
  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(0, 212, 255, 0.1)',
  },
  actionIcon: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: 'rgba(0, 212, 255, 0.08)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.15)',
  },
  actionText: {
    flex: 1,
    fontSize: 15,
    color: '#fff',
  },
  // Modal styles - Luna 2077
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#0A0F14',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '70%',
    paddingBottom: 34,
    borderWidth: 1,
    borderBottomWidth: 0,
    borderColor: 'rgba(0, 212, 255, 0.2)',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0, 212, 255, 0.1)',
  },
  modalTitle: {
    fontSize: 16,
    fontWeight: '400',
    color: '#fff',
    letterSpacing: 1,
  },
  modalDoneText: {
    fontSize: 14,
    fontWeight: '500',
    color: theme.colors.primary.main,
    letterSpacing: 1,
  },
  avatarGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 20,
    gap: 16,
    justifyContent: 'center',
  },
  avatarOption: {
    borderRadius: 40,
    borderWidth: 3,
    borderColor: 'transparent',
  },
  avatarOptionSelected: {
    borderColor: theme.colors.primary.main,
  },
  avatarOptionImage: {
    width: 72,
    height: 72,
    borderRadius: 36,
  },
  interestsGrid: {
    maxHeight: 400,
  },
  interestsGridInner: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 20,
    gap: 12,
  },
  interestOption: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 8,
    gap: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  interestOptionSelected: {
    backgroundColor: 'rgba(0, 212, 255, 0.15)',
    borderColor: theme.colors.primary.main,
    shadowColor: theme.colors.primary.main,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  interestOptionEmoji: {
    fontSize: 18,
  },
  interestOptionText: {
    fontSize: 15,
    color: theme.colors.text.secondary,
  },
  interestOptionTextSelected: {
    color: '#fff',
    fontWeight: '500',
  },
  // Recharge Modal styles
  rechargeScroll: {
    maxHeight: 450,
  },
  coinPacksGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 20,
    gap: 12,
    justifyContent: 'center',
  },
  coinPackCard: {
    width: (SCREEN_WIDTH - 64) / 2,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
    position: 'relative',
  },
  coinPackPopular: {
    position: 'absolute',
    top: -8,
    right: -8,
    backgroundColor: '#00D4FF',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  coinPackPopularText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#fff',
  },
  coinPackDiscount: {
    position: 'absolute',
    top: -8,
    left: -8,
    backgroundColor: '#10B981',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  coinPackDiscountText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#fff',
  },
  coinPackCoins: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFD700',
    marginTop: 8,
    marginBottom: 4,
  },
  coinPackBonus: {
    fontSize: 12,
    fontWeight: '500',
    color: '#10B981',
    marginTop: 2,
  },
  coinPackPrice: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
    marginTop: 4,
  },
  freeCoinsButton: {
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
    borderWidth: 1,
    borderColor: '#10B981',
    borderRadius: 12,
    paddingVertical: 14,
    marginHorizontal: 20,
    marginTop: 16,
    marginBottom: 20,
    alignItems: 'center',
  },
  freeCoinsText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#10B981',
  },
});
