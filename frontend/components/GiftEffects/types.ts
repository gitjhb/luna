/**
 * Gift Effects Types
 * 
 * 注意：礼物类型必须和后端 gift_catalog 保持一致！
 * 后端 API: GET /api/v1/gifts/catalog
 */

// 礼物类型 - 匹配后端 gift_type
export type GiftType = string;  // 动态支持所有后端礼物类型

// 礼物配置
export interface GiftConfig {
  type: string;
  name: string;
  nameCn: string;
  emoji: string;
  price: number;
  xpReward: number;
  animationDuration: number;
}

// 礼物动画 Props
export interface GiftAnimationProps {
  type: string;
  autoPlay?: boolean;
  loop?: boolean;
  speed?: number;
  style?: object;
  onAnimationFinish?: () => void;
}

// 礼物覆盖层 Props
export interface GiftOverlayProps {
  visible: boolean;
  giftType: string;
  senderName?: string;
  receiverName?: string;
  onAnimationEnd?: () => void;
  onClose?: () => void;
}

// 礼物配置表 - 和后端保持一致
export const GIFT_CONFIGS: Record<string, GiftConfig> = {
  // Tier 1: 基础消耗品
  hot_coffee: {
    type: 'hot_coffee',
    name: 'Hot Coffee',
    nameCn: '热咖啡',
    emoji: '☕',
    price: 10,
    xpReward: 10,
    animationDuration: 3000,
  },
  red_rose: {
    type: 'red_rose',
    name: 'Red Rose',
    nameCn: '红玫瑰',
    emoji: '🌹',
    price: 20,
    xpReward: 20,
    animationDuration: 3000,
  },
  small_cake: {
    type: 'small_cake',
    name: 'Small Cake',
    nameCn: '小蛋糕',
    emoji: '🍰',
    price: 50,
    xpReward: 50,
    animationDuration: 3000,
  },
  energy_drink: {
    type: 'energy_drink',
    name: 'Energy Drink',
    nameCn: '能量饮料',
    emoji: '⚡',
    price: 30,
    xpReward: 30,
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
  
  // Tier 2: 状态触发
  tipsy_wine: {
    type: 'tipsy_wine',
    name: 'Fine Red Wine',
    nameCn: '微醺红酒',
    emoji: '🍷',
    price: 200,
    xpReward: 250,
    animationDuration: 4000,
  },
  maid_headband: {
    type: 'maid_headband',
    name: 'Maid Headband',
    nameCn: '女仆发带',
    emoji: '🎀',
    price: 500,
    xpReward: 600,
    animationDuration: 4000,
  },
  
  // Tier 3: 修复关系
  apology_scroll: {
    type: 'apology_scroll',
    name: 'Apology Scroll',
    nameCn: '悔过书',
    emoji: '📜',
    price: 200,
    xpReward: 200,
    animationDuration: 3500,
  },
  apology_bouquet: {
    type: 'apology_bouquet',
    name: 'Apology Bouquet',
    nameCn: '道歉花束',
    emoji: '💐',
    price: 500,
    xpReward: 500,
    animationDuration: 4000,
  },
  
  // Tier 4: 土豪礼物
  premium_rose: {
    type: 'premium_rose',
    name: 'Premium Rose',
    nameCn: '精品玫瑰',
    emoji: '🌷',
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
  
  // 兼容旧的类型名
  rose: {
    type: 'rose',
    name: 'Rose',
    nameCn: '玫瑰花',
    emoji: '🌹',
    price: 10,
    xpReward: 20,
    animationDuration: 3000,
  },
};

// 获取礼物配置（支持未知类型的降级）
export const getGiftConfig = (type: string): GiftConfig => {
  return GIFT_CONFIGS[type] || {
    type: type,
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
