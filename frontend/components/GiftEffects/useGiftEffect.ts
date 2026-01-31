/**
 * useGiftEffect Hook
 * 
 * 管理礼物特效状态的 Hook
 */

import { useState, useCallback } from 'react';
import { GiftType, GIFT_CONFIGS, GiftConfig } from './types';

interface UseGiftEffectOptions {
  onGiftSent?: (config: GiftConfig) => void;
  onAnimationEnd?: () => void;
}

interface UseGiftEffectReturn {
  // 状态
  isVisible: boolean;
  currentGift: GiftType | null;
  
  // 方法
  sendGift: (type: GiftType) => void;
  hideGift: () => void;
  
  // 工具
  getGiftConfig: (type: GiftType) => GiftConfig;
  getAllGifts: () => GiftConfig[];
  canAfford: (type: GiftType, balance: number) => boolean;
}

/**
 * 礼物特效 Hook
 */
export const useGiftEffect = (options: UseGiftEffectOptions = {}): UseGiftEffectReturn => {
  const { onGiftSent, onAnimationEnd } = options;
  
  const [isVisible, setIsVisible] = useState(false);
  const [currentGift, setCurrentGift] = useState<GiftType | null>(null);

  const sendGift = useCallback((type: GiftType) => {
    const config = GIFT_CONFIGS[type];
    setCurrentGift(type);
    setIsVisible(true);
    onGiftSent?.(config);
  }, [onGiftSent]);

  const hideGift = useCallback(() => {
    setIsVisible(false);
    setCurrentGift(null);
    onAnimationEnd?.();
  }, [onAnimationEnd]);

  const getGiftConfig = useCallback((type: GiftType): GiftConfig => {
    return GIFT_CONFIGS[type];
  }, []);

  const getAllGifts = useCallback((): GiftConfig[] => {
    return Object.values(GIFT_CONFIGS);
  }, []);

  const canAfford = useCallback((type: GiftType, balance: number): boolean => {
    return balance >= GIFT_CONFIGS[type].price;
  }, []);

  return {
    isVisible,
    currentGift,
    sendGift,
    hideGift,
    getGiftConfig,
    getAllGifts,
    canAfford,
  };
};

export default useGiftEffect;
