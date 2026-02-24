/**
 * Daily Reward Service
 * 限时签到活动
 */

import { api } from './api';

export interface DailyRewardStatus {
  success: boolean;
  event_active: boolean;
  event_name: string;
  reward_amount?: number;
  can_claim: boolean;
  already_claimed?: boolean;
  last_claim_date?: string | null;
  event_checkins?: number;
  max_days?: number;
  days_left?: number;
  total_rewards?: number;
  message?: string;
}

export interface DailyRewardClaim {
  success: boolean;
  message: string;
  reward_amount: number;
  new_balance?: number;
  event_checkins?: number;
  max_days?: number;
  remaining?: number;
  days_left?: number;
  is_complete?: boolean;
  already_claimed?: boolean;
}

export const dailyRewardService = {
  /**
   * 获取签到状态
   */
  getStatus: async (): Promise<DailyRewardStatus> => {
    return await api.get<DailyRewardStatus>('/daily/status');
  },

  /**
   * 签到领取奖励
   */
  claim: async (): Promise<DailyRewardClaim> => {
    return await api.post<DailyRewardClaim>('/daily/checkin');
  },
};

export default dailyRewardService;
