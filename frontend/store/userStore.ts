/**
 * User Store (Zustand)
 * 
 * Manages user authentication state, subscription status, and credit balance.
 * Persisted to AsyncStorage for offline access.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface User {
  userId: string;
  email: string;
  displayName: string;
  avatar?: string;
  subscriptionTier: 'free' | 'premium' | 'vip';
  subscriptionExpiresAt?: string;
  createdAt: string;
}

export interface Wallet {
  totalCredits: number;
  dailyFreeCredits: number;
  purchedCredits: number;
  bonusCredits: number;
  dailyCreditsLimit: number;
  dailyCreditsRefreshedAt?: string;
}

interface UserState {
  // Authentication
  isAuthenticated: boolean;
  user: User | null;
  accessToken: string | null;
  
  // Wallet & Credits
  wallet: Wallet | null;
  
  // Subscription helpers
  isSubscribed: boolean;
  isPremium: boolean;
  isVip: boolean;
  
  // Actions
  login: (user: User, token: string, wallet: Wallet) => void;
  logout: () => void;
  updateWallet: (wallet: Partial<Wallet>) => void;
  deductCredits: (amount: number) => void;
  updateUser: (user: Partial<User>) => void;
  setSubscription: (tier: 'free' | 'premium' | 'vip', expiresAt?: string) => void;
}

export const useUserStore = create<UserState>()(
  persist(
    (set, get) => ({
      // Initial state
      isAuthenticated: false,
      user: null,
      accessToken: null,
      wallet: null,
      isSubscribed: false,
      isPremium: false,
      isVip: false,
      
      // Actions
      login: (user, token, wallet) => {
        const isSubscribed = user.subscriptionTier !== 'free';
        set({
          isAuthenticated: true,
          user,
          accessToken: token,
          wallet,
          isSubscribed,
          isPremium: user.subscriptionTier === 'premium' || user.subscriptionTier === 'vip',
          isVip: user.subscriptionTier === 'vip',
        });
      },
      
      logout: () => {
        set({
          isAuthenticated: false,
          user: null,
          accessToken: null,
          wallet: null,
          isSubscribed: false,
          isPremium: false,
          isVip: false,
        });
      },
      
      updateWallet: (walletUpdate) => {
        const currentWallet = get().wallet;
        if (currentWallet) {
          set({
            wallet: {
              ...currentWallet,
              ...walletUpdate,
            },
          });
        }
      },
      
      deductCredits: (amount) => {
        const currentWallet = get().wallet;
        if (currentWallet) {
          set({
            wallet: {
              ...currentWallet,
              totalCredits: Math.max(0, currentWallet.totalCredits - amount),
            },
          });
        }
      },
      
      updateUser: (userUpdate) => {
        const currentUser = get().user;
        if (currentUser) {
          const updatedUser = {
            ...currentUser,
            ...userUpdate,
          };
          
          const isSubscribed = updatedUser.subscriptionTier !== 'free';
          
          set({
            user: updatedUser,
            isSubscribed,
            isPremium: updatedUser.subscriptionTier === 'premium' || updatedUser.subscriptionTier === 'vip',
            isVip: updatedUser.subscriptionTier === 'vip',
          });
        }
      },
      
      setSubscription: (tier, expiresAt) => {
        const currentUser = get().user;
        if (currentUser) {
          const updatedUser = {
            ...currentUser,
            subscriptionTier: tier,
            subscriptionExpiresAt: expiresAt,
          };
          
          const isSubscribed = tier !== 'free';
          
          set({
            user: updatedUser,
            isSubscribed,
            isPremium: tier === 'premium' || tier === 'vip',
            isVip: tier === 'vip',
          });
        }
      },
    }),
    {
      name: 'user-storage',
      storage: createJSONStorage(() => AsyncStorage),
    }
  )
);

/**
 * Selectors for optimized re-renders
 */
export const selectUser = (state: UserState) => state.user;
export const selectWallet = (state: UserState) => state.wallet;
export const selectIsAuthenticated = (state: UserState) => state.isAuthenticated;
export const selectIsSubscribed = (state: UserState) => state.isSubscribed;
export const selectCredits = (state: UserState) => state.wallet?.totalCredits ?? 0;
