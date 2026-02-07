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
import { SubscriptionModal } from '../../components/SubscriptionModal';
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

  const handleCancelSubscription = () => {
    Alert.alert(
      t.profile.cancelSubscription,
      t.profile.cancelSubscriptionConfirm,
      [
        { text: t.profile.thinkAgain, style: 'cancel' },
        {
          text: t.profile.confirmCancel,
          style: 'destructive',
          onPress: async () => {
            try {
              const result = await paymentService.cancelSubscription();
              if (result.success) {
                updateUser({ subscriptionTier: 'free' });
                Alert.alert(t.profile.cancelled, result.message || '订阅已取消');
              } else {
                Alert.alert(t.common.error, result.message || '请稍后重试');
              }
            } catch (e: any) {
              Alert.alert(t.common.error, e.message || '请稍后重试');
            }
          },
        },
      ]
    );
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
                onPress={handleCancelSubscription}
              >
                <Text style={styles.cancelSubscriptionText}>{t.profile.cancelSubscription}</Text>
              </TouchableOpacity>
            )}
          </View>

          {/* Credits Card */}
          <View style={styles.section}>
            <View style={styles.creditsCard}>
              <View style={styles.creditsHeader}>
                <View style={styles.creditsIconContainer}>
                  <Text style={styles.creditsIcon}>🪙</Text>
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
              <TouchableOpacity 
                style={styles.actionRow}
                onPress={() => router.push('/invite')}
              >
                <View style={styles.actionIcon}>
                  <Ionicons name="gift-outline" size={20} color={theme.colors.primary.main} />
                </View>
                <Text style={styles.actionText}>{t.profile.inviteFriends}</Text>
                <Ionicons name="chevron-forward" size={18} color={theme.colors.text.tertiary} />
              </TouchableOpacity>
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
    borderWidth: 3,
    borderColor: theme.colors.primary.main,
  },
  avatarPlaceholder: {
    backgroundColor: theme.colors.primary.main,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarInitials: {
    fontSize: 36,
    fontWeight: '700',
    color: '#fff',
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
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 16,
    gap: 6,
  },
  membershipBadgePremium: {
    backgroundColor: 'rgba(255, 215, 0, 0.15)',
  },
  membershipText: {
    fontSize: 13,
    fontWeight: '600',
    color: theme.colors.text.secondary,
  },
  membershipTextPremium: {
    color: '#FFD700',
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
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 20,
    padding: 20,
  },
  creditsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  creditsIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(255, 215, 0, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
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
    fontSize: 28,
    fontWeight: '700',
    color: '#FFD700',
  },
  rechargeButton: {
    backgroundColor: theme.colors.primary.main,
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
  },
  rechargeText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
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
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 16,
    padding: 16,
    minHeight: 80,
  },
  interestTags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  interestTag: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(139, 92, 246, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 16,
    gap: 6,
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
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 16,
    overflow: 'hidden',
  },
  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(255, 255, 255, 0.08)',
  },
  actionIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: 'rgba(139, 92, 246, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  actionText: {
    flex: 1,
    fontSize: 15,
    color: '#fff',
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: theme.colors.background.secondary,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '70%',
    paddingBottom: 34,
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
  modalDoneText: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.primary.main,
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
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
    gap: 8,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  interestOptionSelected: {
    backgroundColor: 'rgba(139, 92, 246, 0.2)',
    borderColor: theme.colors.primary.main,
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
    backgroundColor: '#EC4899',
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
