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
import { pricingService, CoinPack } from '../../services/pricingService';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Predefined interests that users can select
const INTEREST_OPTIONS = [
  { id: 'movies', label: '电影', emoji: '🎬' },
  { id: 'music', label: '音乐', emoji: '🎵' },
  { id: 'gaming', label: '游戏', emoji: '🎮' },
  { id: 'travel', label: '旅行', emoji: '✈️' },
  { id: 'food', label: '美食', emoji: '🍜' },
  { id: 'sports', label: '运动', emoji: '⚽' },
  { id: 'reading', label: '阅读', emoji: '📚' },
  { id: 'art', label: '艺术', emoji: '🎨' },
  { id: 'tech', label: '科技', emoji: '💻' },
  { id: 'anime', label: '动漫', emoji: '🎌' },
  { id: 'pets', label: '宠物', emoji: '🐱' },
  { id: 'fashion', label: '时尚', emoji: '👗' },
  { id: 'photography', label: '摄影', emoji: '📷' },
  { id: 'cooking', label: '烹饪', emoji: '👨‍🍳' },
  { id: 'fitness', label: '健身', emoji: '💪' },
];

// Default avatar options
const AVATAR_OPTIONS = [
  'https://i.pravatar.cc/200?img=1',
  'https://i.pravatar.cc/200?img=3',
  'https://i.pravatar.cc/200?img=5',
  'https://i.pravatar.cc/200?img=7',
  'https://i.pravatar.cc/200?img=8',
  'https://i.pravatar.cc/200?img=9',
  'https://i.pravatar.cc/200?img=11',
  'https://i.pravatar.cc/200?img=12',
];

export default function ProfileScreen() {
  const router = useRouter();
  const { user, wallet, updateWallet, updateUser, isSubscribed } = useUserStore();
  
  const [refreshing, setRefreshing] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [nameInput, setNameInput] = useState(user?.displayName || '');
  const [showAvatarPicker, setShowAvatarPicker] = useState(false);
  const [showInterestsPicker, setShowInterestsPicker] = useState(false);
  const [showRechargeModal, setShowRechargeModal] = useState(false);
  const [coinPacks, setCoinPacks] = useState<CoinPack[]>([]);
  
  // User preferences stored locally (in production, sync with backend)
  const [userAvatar, setUserAvatar] = useState(user?.avatar || AVATAR_OPTIONS[0]);
  const [selectedInterests, setSelectedInterests] = useState<string[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [balance, packs] = await Promise.all([
        walletService.getBalance(),
        pricingService.getCoinPacks(),
      ]);
      updateWallet(balance);
      setCoinPacks(packs);
    } catch (error) {
      console.error('Failed to load profile data:', error);
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

  const handleSelectAvatar = (avatar: string) => {
    setUserAvatar(avatar);
    updateUser({ avatar });
    setShowAvatarPicker(false);
  };

  const toggleInterest = (interestId: string) => {
    setSelectedInterests(prev => 
      prev.includes(interestId) 
        ? prev.filter(id => id !== interestId)
        : [...prev, interestId]
    );
  };

  const handleSaveInterests = () => {
    // In production, save to backend
    setShowInterestsPicker(false);
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
            <Text style={styles.title}>我</Text>
          </View>

          {/* Profile Card */}
          <View style={styles.profileCard}>
            {/* Avatar */}
            <TouchableOpacity 
              style={styles.avatarContainer}
              onPress={() => setShowAvatarPicker(true)}
            >
              <Image source={{ uri: userAvatar }} style={styles.avatar} />
              <View style={styles.avatarEditBadge}>
                <Ionicons name="camera" size={14} color="#fff" />
              </View>
            </TouchableOpacity>

            {/* Name */}
            <View style={styles.nameContainer}>
              {editingName ? (
                <View style={styles.nameEditRow}>
                  <TextInput
                    style={styles.nameInput}
                    value={nameInput}
                    onChangeText={setNameInput}
                    placeholder="输入昵称"
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

            {/* Membership Badge */}
            <View style={[styles.membershipBadge, isSubscribed && styles.membershipBadgePremium]}>
              <Ionicons 
                name={isSubscribed ? 'diamond' : 'person'} 
                size={14} 
                color={isSubscribed ? '#FFD700' : theme.colors.text.tertiary} 
              />
              <Text style={[styles.membershipText, isSubscribed && styles.membershipTextPremium]}>
                {isSubscribed ? 'Premium' : 'Free'}
              </Text>
            </View>
          </View>

          {/* Credits Card */}
          <View style={styles.section}>
            <View style={styles.creditsCard}>
              <View style={styles.creditsHeader}>
                <View style={styles.creditsIconContainer}>
                  <Text style={styles.creditsIcon}>🪙</Text>
                </View>
                <View style={styles.creditsInfo}>
                  <Text style={styles.creditsLabel}>我的金币</Text>
                  <Text style={styles.creditsAmount}>{wallet?.totalCredits?.toFixed(0) || '0'}</Text>
                </View>
                <TouchableOpacity 
                  style={styles.rechargeButton}
                  onPress={() => setShowRechargeModal(true)}
                >
                  <Text style={styles.rechargeText}>充值</Text>
                </TouchableOpacity>
              </View>
              <View style={styles.creditsDivider} />
              <View style={styles.creditsDetails}>
                <View style={styles.creditsDetailItem}>
                  <Text style={styles.creditsDetailLabel}>每日赠送</Text>
                  <Text style={styles.creditsDetailValue}>+{wallet?.dailyFreeCredits || 0}/天</Text>
                </View>
                <View style={styles.creditsDetailItem}>
                  <Text style={styles.creditsDetailLabel}>已购买</Text>
                  <Text style={styles.creditsDetailValue}>{wallet?.purchedCredits || 0}</Text>
                </View>
              </View>
            </View>
          </View>

          {/* Interests Section */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>我的兴趣</Text>
              <TouchableOpacity onPress={() => setShowInterestsPicker(true)}>
                <Text style={styles.editLink}>编辑</Text>
              </TouchableOpacity>
            </View>
            <View style={styles.interestsCard}>
              {selectedInterests.length > 0 ? (
                <View style={styles.interestTags}>
                  {selectedInterests.map(id => {
                    const interest = INTEREST_OPTIONS.find(i => i.id === id);
                    return interest ? (
                      <View key={id} style={styles.interestTag}>
                        <Text style={styles.interestTagEmoji}>{interest.emoji}</Text>
                        <Text style={styles.interestTagText}>{interest.label}</Text>
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
                  <Text style={styles.addInterestsText}>添加兴趣爱好，让AI更了解你</Text>
                </TouchableOpacity>
              )}
            </View>
            <Text style={styles.interestsHint}>
              💡 兴趣爱好会帮助AI更好地与你互动
            </Text>
          </View>

          {/* Quick Actions */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>更多</Text>
            <View style={styles.actionsCard}>
              <TouchableOpacity style={styles.actionRow}>
                <View style={styles.actionIcon}>
                  <Ionicons name="gift-outline" size={20} color={theme.colors.primary.main} />
                </View>
                <Text style={styles.actionText}>邀请好友</Text>
                <Ionicons name="chevron-forward" size={18} color={theme.colors.text.tertiary} />
              </TouchableOpacity>
              <TouchableOpacity style={styles.actionRow}>
                <View style={styles.actionIcon}>
                  <Ionicons name="star-outline" size={20} color={theme.colors.primary.main} />
                </View>
                <Text style={styles.actionText}>给我们评分</Text>
                <Ionicons name="chevron-forward" size={18} color={theme.colors.text.tertiary} />
              </TouchableOpacity>
              <TouchableOpacity style={styles.actionRow}>
                <View style={styles.actionIcon}>
                  <Ionicons name="help-circle-outline" size={20} color={theme.colors.primary.main} />
                </View>
                <Text style={styles.actionText}>帮助与反馈</Text>
                <Ionicons name="chevron-forward" size={18} color={theme.colors.text.tertiary} />
              </TouchableOpacity>
            </View>
          </View>

          <View style={{ height: 120 }} />
        </ScrollView>
      </SafeAreaView>

      {/* Avatar Picker Modal */}
      <Modal
        visible={showAvatarPicker}
        transparent
        animationType="slide"
        onRequestClose={() => setShowAvatarPicker(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>选择头像</Text>
              <TouchableOpacity onPress={() => setShowAvatarPicker(false)}>
                <Ionicons name="close" size={24} color="#fff" />
              </TouchableOpacity>
            </View>
            <View style={styles.avatarGrid}>
              {AVATAR_OPTIONS.map((avatar, index) => (
                <TouchableOpacity
                  key={index}
                  style={[
                    styles.avatarOption,
                    userAvatar === avatar && styles.avatarOptionSelected,
                  ]}
                  onPress={() => handleSelectAvatar(avatar)}
                >
                  <Image source={{ uri: avatar }} style={styles.avatarOptionImage} />
                </TouchableOpacity>
              ))}
            </View>
          </View>
        </View>
      </Modal>

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
              <Text style={styles.modalTitle}>选择兴趣</Text>
              <TouchableOpacity onPress={handleSaveInterests}>
                <Text style={styles.modalDoneText}>完成</Text>
              </TouchableOpacity>
            </View>
            <ScrollView style={styles.interestsGrid}>
              <View style={styles.interestsGridInner}>
                {INTEREST_OPTIONS.map(interest => (
                  <TouchableOpacity
                    key={interest.id}
                    style={[
                      styles.interestOption,
                      selectedInterests.includes(interest.id) && styles.interestOptionSelected,
                    ]}
                    onPress={() => toggleInterest(interest.id)}
                  >
                    <Text style={styles.interestOptionEmoji}>{interest.emoji}</Text>
                    <Text style={[
                      styles.interestOptionText,
                      selectedInterests.includes(interest.id) && styles.interestOptionTextSelected,
                    ]}>
                      {interest.label}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* Recharge Modal */}
      <Modal
        visible={showRechargeModal}
        transparent
        animationType="slide"
        onRequestClose={() => setShowRechargeModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Buy Coins</Text>
              <TouchableOpacity onPress={() => setShowRechargeModal(false)}>
                <Ionicons name="close" size={24} color="#fff" />
              </TouchableOpacity>
            </View>
            <ScrollView style={styles.rechargeScroll} showsVerticalScrollIndicator={false}>
              <View style={styles.coinPacksGrid}>
                {coinPacks.map((pack) => (
                  <TouchableOpacity 
                    key={pack.id} 
                    style={styles.coinPackCard}
                    onPress={() => Alert.alert('Purchase', `Buy ${pack.coins} coins for $${pack.price.toFixed(2)}?`)}
                  >
                    {pack.popular && (
                      <View style={styles.coinPackPopular}>
                        <Text style={styles.coinPackPopularText}>Best Value</Text>
                      </View>
                    )}
                    {pack.discount && (
                      <View style={styles.coinPackDiscount}>
                        <Text style={styles.coinPackDiscountText}>{pack.discount}% OFF</Text>
                      </View>
                    )}
                    <Text style={styles.coinPackCoins}>🪙 {pack.coins.toLocaleString()}</Text>
                    {pack.bonusCoins && (
                      <Text style={styles.coinPackBonus}>+{pack.bonusCoins} bonus</Text>
                    )}
                    <Text style={styles.coinPackPrice}>${pack.price.toFixed(2)}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
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
});
