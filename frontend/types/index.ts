/**
 * Global TypeScript Types
 */

// ============================================================================
// Character Types
// ============================================================================

export interface Character {
  characterId: string;
  name: string;
  avatarUrl: string;
  description: string;
  personalityTraits: string[];
  tierRequired: 'free' | 'premium' | 'vip';
  isSpicy: boolean;
  tags: string[];
  createdAt?: string;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

// ============================================================================
// Credit & Payment Types
// ============================================================================

export interface CreditPackage {
  sku: string;
  name: string;
  credits: number;
  priceUsd: number;
  discountPercentage: number;
  popular?: boolean;
}

export interface SubscriptionPlan {
  sku: string;
  name: string;
  tier: 'premium' | 'vip';
  priceUsd: number;
  billingPeriod: 'monthly' | 'yearly';
  bonusCredits: number;
  features: string[];
  popular?: boolean;
}

export interface Transaction {
  transactionId: string;
  transactionType: 'chat_deduction' | 'purchase' | 'daily_refresh' | 'bonus' | 'refund';
  amount: number;
  balanceBefore: number;
  balanceAfter: number;
  description?: string;
  createdAt: string;
}

// ============================================================================
// Navigation Types (Expo Router)
// ============================================================================

export type RootStackParamList = {
  '(tabs)': undefined;
  'auth/login': undefined;
  'chat/[characterId]': { characterId: string; characterName: string };
  'profile/subscription': undefined;
  'profile/credits': undefined;
  'profile/transactions': undefined;
};

// ============================================================================
// Component Props Types
// ============================================================================

export interface CharacterCardProps {
  character: Character;
  onPress: () => void;
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
}

export interface ChatBubbleProps {
  message: {
    messageId: string;
    role: 'user' | 'assistant';
    content: string;
    type?: 'text' | 'image';
    isLocked?: boolean;
    imageUrl?: string;
    createdAt: string;
  };
  onUnlock?: (messageId: string) => void;
}

export interface CreditHeaderProps {
  credits: number;
  onBuyCredits: () => void;
}

// ============================================================================
// Error Types
// ============================================================================

export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, any>;
}

export interface InsufficientCreditsError extends ApiError {
  currentBalance: number;
  required: number;
}

export interface RateLimitError extends ApiError {
  retryAfter: number;
}

// ============================================================================
// Form Types
// ============================================================================

export interface LoginFormData {
  provider: 'google' | 'apple';
  idToken: string;
}

export interface SendMessageFormData {
  sessionId: string;
  message: string;
}

// ============================================================================
// Utility Types
// ============================================================================

export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}
