/**
 * Emotion Service
 *
 * Handles character emotion state API calls
 * Note: Emotion state is a VIP-only feature
 */

import { api } from './api';

export type EmotionalState = 
  | 'loving'   // 热恋、甜蜜 ❤️
  | 'happy'    // 开心、满足 😊
  | 'neutral'  // 平静、正常 😐
  | 'curious'  // 好奇、感兴趣 🤔
  | 'annoyed'  // 有点烦躁 😒
  | 'angry'    // 生气 😠
  | 'hurt'     // 受伤、难过 😢
  | 'cold'     // 冷淡、疏远 🥶
  | 'silent';  // 不想说话 🤐

export interface EmotionStatus {
  userId: string;
  characterId: string;
  emotionalState: EmotionalState;
  emotionIntensity: number;  // 0-100
  emotionReason: string | null;
  timesAngered: number;
  timesHurt: number;
  emotionChangedAt: string | null;
}

export const EMOTION_DISPLAY: Record<EmotionalState, { emoji: string; label: string; labelCn: string; color: string }> = {
  loving: { emoji: '❤️', label: 'Loving', labelCn: '热恋', color: '#FF6B9D' },
  happy: { emoji: '😊', label: 'Happy', labelCn: '开心', color: '#FFD93D' },
  neutral: { emoji: '😐', label: 'Neutral', labelCn: '平静', color: '#6BCB77' },
  curious: { emoji: '🤔', label: 'Curious', labelCn: '好奇', color: '#4ECDC4' },
  annoyed: { emoji: '😒', label: 'Annoyed', labelCn: '烦躁', color: '#FFC93C' },
  angry: { emoji: '😠', label: 'Angry', labelCn: '生气', color: '#FF6B6B' },
  hurt: { emoji: '😢', label: 'Hurt', labelCn: '难过', color: '#A8E6CF' },
  cold: { emoji: '🥶', label: 'Cold', labelCn: '冷淡', color: '#636E72' },
  silent: { emoji: '🤐', label: 'Silent', labelCn: '沉默', color: '#2D3436' },
};

const transformEmotionStatus = (data: any): EmotionStatus => ({
  userId: data.user_id,
  characterId: data.character_id,
  emotionalState: data.emotional_state,
  emotionIntensity: data.emotion_intensity,
  emotionReason: data.emotion_reason,
  timesAngered: data.times_angered,
  timesHurt: data.times_hurt,
  emotionChangedAt: data.emotion_changed_at,
});

export const emotionService = {
  /**
   * Get current emotion status with a character
   * Note: Returns null for non-VIP users (emotion is a premium feature)
   */
  getStatus: async (characterId: string): Promise<EmotionStatus | null> => {
    try {
      const data = await api.get(`/emotion/${characterId}`);
      return transformEmotionStatus(data);
    } catch (error: any) {
      // 403 means not VIP, emotion hidden
      if (error?.response?.status === 403) {
        return null;
      }
      throw error;
    }
  },
};

export default emotionService;

export const resetEmotion = async (characterId: string): Promise<{ success: boolean; message: string }> => {
  return await api.post(`/emotion/${characterId}/reset`);
};

