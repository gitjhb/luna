/**
 * Daily Reward Service
 * 每日登录奖励
 */

import { api } from './api';

export interface DailyRewardStatus {
  success: boolean;
  tier: string;
  reward_amount: number;
  can_claim: boolean;
  already_claimed: boolean;
  last_claim_date: string | null;
}

export interface DailyRewardClaim {
  success: boolean;
  message: string;
  reward_amount: number;
  tier?: string;
  new_balance?: number;
  already_claimed?: boolean;
}

export const dailyRewardService = {
  /**
   * 获取每日奖励状态
   */
  getStatus: async (): Promise<DailyRewardStatus> => {
    return await api.get<DailyRewardStatus>('/daily-reward/status');
  },

  /**
   * 领取每日奖励
   */
  claim: async (): Promise<DailyRewardClaim> => {
    return await api.post<DailyRewardClaim>('/daily-reward/claim');
  },
};

export default dailyRewardService;
