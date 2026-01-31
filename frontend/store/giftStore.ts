/**
 * Gift Store - 礼物目录管理
 * 
 * 核心原则：后端为准
 * - App 启动时从后端加载礼物目录
 * - 前端只做 icon 映射（备用）
 * - 扣费按后端配置来
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { GiftCatalogItem, getGiftCatalog } from '../services/giftService';

export type { GiftCatalogItem };

interface GiftStore {
  // State
  catalog: GiftCatalogItem[];
  lastFetched: number | null;
  isLoading: boolean;
  error: string | null;
  _hasHydrated: boolean;
  
  // Actions
  setHasHydrated: (state: boolean) => void;
  fetchCatalog: () => Promise<void>;
  getGift: (giftType: string) => GiftCatalogItem | undefined;
  needsRefresh: () => boolean;
}

// 缓存有效期：1小时
const CACHE_TTL = 60 * 60 * 1000;

// 前端 icon 备用映射（当后端 icon 为空时使用）
const FALLBACK_ICONS: Record<string, string> = {
  rose: '🌹',
  chocolate: '🍫',
  teddy_bear: '🧸',
  premium_rose: '💐',
  diamond_ring: '💍',
  crown: '👑',
};

export const useGiftStore = create<GiftStore>()(
  persist(
    (set, get) => ({
      catalog: [],
      lastFetched: null,
      isLoading: false,
      error: null,
      _hasHydrated: false,
      
      setHasHydrated: (state) => set({ _hasHydrated: state }),
      
      fetchCatalog: async () => {
        set({ isLoading: true, error: null });
        
        try {
          const catalog = await getGiftCatalog();
          
          // 确保每个礼物都有 icon
          const catalogWithIcons = catalog.map(gift => ({
            ...gift,
            icon: gift.icon || FALLBACK_ICONS[gift.gift_type] || '🎁',
          }));
          
          set({
            catalog: catalogWithIcons,
            lastFetched: Date.now(),
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          console.error('Failed to fetch gift catalog:', error);
          set({
            isLoading: false,
            error: error.message || '加载礼物列表失败',
          });
        }
      },
      
      getGift: (giftType: string) => {
        return get().catalog.find(g => g.gift_type === giftType);
      },
      
      needsRefresh: () => {
        const { lastFetched, catalog } = get();
        
        // 没有数据，需要刷新
        if (catalog.length === 0) return true;
        
        // 缓存过期，需要刷新
        if (!lastFetched || Date.now() - lastFetched > CACHE_TTL) return true;
        
        return false;
      },
    }),
    {
      name: 'gift-store',
      storage: createJSONStorage(() => AsyncStorage),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
      partialize: (state) => ({
        catalog: state.catalog,
        lastFetched: state.lastFetched,
      }),
    }
  )
);
