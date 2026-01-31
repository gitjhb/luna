/**
 * Gift Effects Module
 * 
 * 礼物特效模块 - 提供精美的礼物动画效果
 * 
 * @example
 * ```tsx
 * import { GiftOverlay, GiftPicker, useGiftEffect } from '@/components/GiftEffects';
 * 
 * const { isVisible, currentGift, sendGift, hideGift } = useGiftEffect();
 * 
 * // Gift picker for selecting and sending
 * <GiftPicker
 *   visible={showPicker}
 *   characterId="char-1"
 *   userBalance={100}
 *   onClose={() => setShowPicker(false)}
 *   onGiftSent={(response) => {
 *     sendGift(response.gift_type);  // Trigger animation
 *   }}
 * />
 * 
 * // Gift animation overlay
 * <GiftOverlay
 *   visible={isVisible}
 *   giftType={currentGift || 'rose'}
 *   onAnimationEnd={hideGift}
 * />
 * ```
 */

// Components
export { GiftAnimation } from './GiftAnimation';
export { GiftOverlay } from './GiftOverlay';
export { GiftPicker } from './GiftPicker';

// Hook
export { useGiftEffect } from './useGiftEffect';

// Types
export type { 
  GiftType, 
  GiftConfig, 
  GiftAnimationProps, 
  GiftOverlayProps 
} from './types';

export { 
  GIFT_CONFIGS, 
  getGiftConfig, 
  getAllGifts 
} from './types';
