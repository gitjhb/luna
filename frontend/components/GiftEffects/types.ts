/**
 * Gift Effects Types
 * 
 * 注意：礼物类型必须和后端 gift_catalog 保持一致！
 * 后端 API: GET /api/v1/gifts/catalog
 */

// 礼物类型 - 匹配后端 gift_type
export type GiftType = 
  | 'rose'          // 🌹 玫瑰花
  | 'chocolate'     // 🍫 巧克力  
  | 'teddy_bear'    // 🧸 泰迪熊
  | 'premium_rose'  // 💐 精品玫瑰
  | 'diamond_ring'  // 💍 钻戒
  | 'crown';        // 👑 皇冠

// 礼物配置
export interface GiftConfig {
  type: GiftType;
  name: string;
  nameCn: string;
  emoji: string;
  price: number;      // 金币价格
  xpReward: number;   // XP 奖励
  animationDuration: number;  // 动画时长 (ms)
}

// 礼物动画 Props
export interface GiftAnimationProps {
  type: GiftType;
  autoPlay?: boolean;
  loop?: boolean;
  speed?: number;
  style?: object;
  onAnimationFinish?: () => void;
}

// 礼物覆盖层 Props
export interface GiftOverlayProps {
  visible: boolean;
  giftType: GiftType;
  senderName?: string;
  receiverName?: string;
  onAnimationEnd?: () => void;
  onClose?: () => void;
}

// 礼物配置表 - 和后端保持一致
export const GIFT_CONFIGS: Record<GiftType, GiftConfig> = {
  rose: {
    type: 'rose',
    name: 'Rose',
    nameCn: '玫瑰花',
    emoji: '🌹',
    price: 10,
    xpReward: 20,
    animationDuration: 3000,
  },
  chocolate: {
    type: 'chocolate',
    name: 'Chocolate',
    nameCn: '巧克力',
    emoji: '🍫',
    price: 20,
    xpReward: 35,
    animationDuration: 3000,
  },
  teddy_bear: {
    type: 'teddy_bear',
    name: 'Teddy Bear',
    nameCn: '泰迪熊',
    emoji: '🧸',
    price: 50,
    xpReward: 80,
    animationDuration: 3500,
  },
  premium_rose: {
    type: 'premium_rose',
    name: 'Premium Rose',
    nameCn: '精品玫瑰',
    emoji: '💐',
    price: 100,
    xpReward: 150,
    animationDuration: 4000,
  },
  diamond_ring: {
    type: 'diamond_ring',
    name: 'Diamond Ring',
    nameCn: '钻戒',
    emoji: '💍',
    price: 500,
    xpReward: 700,
    animationDuration: 5000,
  },
  crown: {
    type: 'crown',
    name: 'Crown',
    nameCn: '皇冠',
    emoji: '👑',
    price: 1000,
    xpReward: 1500,
    animationDuration: 6000,
  },
};

// 获取礼物配置（支持未知类型的降级）
export const getGiftConfig = (type: string): GiftConfig => {
  return GIFT_CONFIGS[type as GiftType] || {
    type: type as GiftType,
    name: type,
    nameCn: type,
    emoji: '🎁',
    price: 0,
    xpReward: 0,
    animationDuration: 3000,
  };
};

// 获取所有礼物列表
export const getAllGifts = (): GiftConfig[] => {
  return Object.values(GIFT_CONFIGS);
};
