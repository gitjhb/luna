/**
 * Referral Service
 * 
 * Handles referral code management and friend invitations.
 */

import { api } from './api';
import { Share, Platform } from 'react-native';

// Types
export interface ReferralCodeResponse {
  referral_code: string;
  total_referrals: number;
  total_rewards_earned: number;
  reward_per_referral: number;
  new_user_bonus: number;
  share_text: string;
}

export interface ApplyReferralResponse {
  success: boolean;
  message: string;
  error?: string;
  new_user_bonus?: number;
  new_balance?: number;
}

export interface ReferredFriend {
  user_id: string;
  display_name: string;
  avatar_url?: string;
  referred_at?: string;
  reward_earned: number;
}

export interface ReferredFriendsResponse {
  friends: ReferredFriend[];
  total_count: number;
  total_rewards: number;
}

export interface ReferralStats {
  referralCode: string;
  totalReferrals: number;
  totalRewardsEarned: number;
  rewardPerReferral: number;
  newUserBonus: number;
  shareText: string;
}

// Test mode mock data
const MOCK_REFERRAL_CODE = 'LUNA8888';
const MOCK_REWARD_PER_REFERRAL = 50;
const MOCK_NEW_USER_BONUS = 20;

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Check if we're in test mode
const isTestMode = () => process.env.EXPO_PUBLIC_PAYMENT_TEST_MODE === 'true' || __DEV__;

export const referralService = {
  /**
   * Get current user's referral code and stats
   */
  getMyReferralCode: async (): Promise<ReferralStats> => {
    if (isTestMode()) {
      await delay(300);
      return {
        referralCode: MOCK_REFERRAL_CODE,
        totalReferrals: 3,
        totalRewardsEarned: 150,
        rewardPerReferral: MOCK_REWARD_PER_REFERRAL,
        newUserBonus: MOCK_NEW_USER_BONUS,
        shareText: `我正在使用 Luna AI 陪伴，超有趣！\n使用我的邀请码 ${MOCK_REFERRAL_CODE} 注册，你我都能获得金币奖励！`,
      };
    }

    try {
      const data = await api.get<ReferralCodeResponse>('/referral/code');
      return {
        referralCode: data.referral_code,
        totalReferrals: data.total_referrals,
        totalRewardsEarned: data.total_rewards_earned,
        rewardPerReferral: data.reward_per_referral,
        newUserBonus: data.new_user_bonus,
        shareText: data.share_text,
      };
    } catch (error) {
      console.error('Failed to get referral code:', error);
      throw error;
    }
  },

  /**
   * Apply a referral code (for new users)
   */
  applyReferralCode: async (code: string): Promise<ApplyReferralResponse> => {
    if (isTestMode()) {
      await delay(500);
      const upperCode = code.toUpperCase().trim();
      
      // Simulate validation
      if (upperCode.length < 6) {
        return { success: false, message: '无效的邀请码', error: 'invalid_code' };
      }
      if (upperCode === MOCK_REFERRAL_CODE) {
        return { success: false, message: '不能使用自己的邀请码', error: 'self_referral' };
      }
      
      return {
        success: true,
        message: `邀请码使用成功！获得${MOCK_NEW_USER_BONUS}金币奖励`,
        new_user_bonus: MOCK_NEW_USER_BONUS,
        new_balance: 70, // 50 (initial) + 20 (bonus)
      };
    }

    try {
      const data = await api.post<ApplyReferralResponse>('/referral/apply', {
        referral_code: code,
      });
      return data;
    } catch (error) {
      console.error('Failed to apply referral code:', error);
      return {
        success: false,
        message: '网络错误，请稍后重试',
        error: 'network_error',
      };
    }
  },

  /**
   * Get list of friends referred by current user
   */
  getReferredFriends: async (limit: number = 50, offset: number = 0): Promise<ReferredFriendsResponse> => {
    if (isTestMode()) {
      await delay(300);
      return {
        friends: [
          {
            user_id: 'friend-1',
            display_name: '小明',
            avatar_url: 'https://i.pravatar.cc/200?img=1',
            referred_at: new Date(Date.now() - 86400000 * 2).toISOString(),
            reward_earned: 50,
          },
          {
            user_id: 'friend-2',
            display_name: '小红',
            avatar_url: 'https://i.pravatar.cc/200?img=5',
            referred_at: new Date(Date.now() - 86400000 * 5).toISOString(),
            reward_earned: 50,
          },
          {
            user_id: 'friend-3',
            display_name: '小华',
            avatar_url: 'https://i.pravatar.cc/200?img=8',
            referred_at: new Date(Date.now() - 86400000 * 10).toISOString(),
            reward_earned: 50,
          },
        ],
        total_count: 3,
        total_rewards: 150,
      };
    }

    try {
      const data = await api.get<ReferredFriendsResponse>('/referral/friends', { limit, offset });
      return data;
    } catch (error) {
      console.error('Failed to get referred friends:', error);
      return { friends: [], total_count: 0, total_rewards: 0 };
    }
  },

  /**
   * Share referral code via system share sheet
   */
  shareReferralCode: async (code: string, shareText?: string): Promise<boolean> => {
    const message = shareText || 
      `我正在使用 Luna AI 陪伴，超有趣！\n` +
      `使用我的邀请码 ${code} 注册，你我都能获得金币奖励！\n` +
      `下载链接: https://luna.app/download`;

    try {
      const result = await Share.share({
        message,
        title: '邀请你加入 Luna',
      });

      if (result.action === Share.sharedAction) {
        console.log('[Referral] Shared successfully');
        return true;
      }
      return false;
    } catch (error) {
      console.error('[Referral] Share failed:', error);
      return false;
    }
  },

  /**
   * Copy referral code to clipboard
   */
  copyReferralCode: async (code: string): Promise<boolean> => {
    try {
      const Clipboard = await import('expo-clipboard');
      await Clipboard.setStringAsync(code);
      return true;
    } catch (error) {
      console.error('[Referral] Copy failed:', error);
      return false;
    }
  },
};

export default referralService;
