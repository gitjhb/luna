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
  backgroundUrl?: string;
  description: string;
  personalityTraits: string[];
  tierRequired: 'free' | 'premium' | 'vip';
  isSpicy: boolean;
  tags: string[];
  greeting?: string;  // 角色开场白
  createdAt?: string;
  // Extended profile fields
  age?: number;
  zodiac?: string;  // 星座
  occupation?: string;  // 职业
  hobbies?: string[];  // 爱好
  mbti?: string;  // MBTI 性格类型
  birthday?: string;  // 生日
  height?: string;  // 身高
  location?: string;  // 所在地
}

// Extended character info with unlockable secrets (like Stardew Valley)
export interface CharacterProfile extends Character {
  // Basic info (always visible)
  age?: number;
  occupation?: string;
  
  // Personality secrets (unlock at different intimacy levels)
  personalitySecrets: PersonalitySecret[];
  
  // Likes/Dislikes (unlock progressively)
  likes: UnlockableInfo[];
  dislikes: UnlockableInfo[];
  
  // Background story (unlock at higher levels)
  backstory: UnlockableInfo[];
  
  // Special dialogue unlocks
  specialDialogues: UnlockableInfo[];
}

export interface PersonalitySecret {
  id: string;
  title: string;           // e.g., "Hidden Talent"
  content: string;         // The actual secret
  unlockLevel: number;     // Level required to unlock
  isUnlocked?: boolean;    // Computed based on user's intimacy level
}

export interface UnlockableInfo {
  id: string;
  content: string;
  unlockLevel: number;
  category?: string;       // e.g., "Food", "Hobby", "Memory"
  isUnlocked?: boolean;
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
  transactionType: 'chat_deduction' | 'purchase' | 'daily_refresh' | 'bonus' | 'refund' | 'gift' | 'deduction' | 'subscription' | 'referral';
  amount: number;
  balanceBefore: number;
  balanceAfter: number;
  description?: string;
  createdAt: string;
  extraData?: {
    currency?: 'USD' | 'credits';
    [key: string]: any;
  };
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

// ============================================================================
// Intimacy System Types
// ============================================================================

export type IntimacyStage = 'strangers' | 'acquaintances' | 'close_friends' | 'ambiguous' | 'soulmates';

export type ActionType = 'message' | 'continuous_chat' | 'checkin' | 'emotional' | 'voice' | 'share';

export interface ActionAvailability {
  actionType: ActionType;
  actionName: string;
  xpReward: number;
  dailyLimit: number | null;
  usedToday: number;
  available: boolean;
  cooldownSeconds: number | null;
}

export interface IntimacyStatus {
  characterId: string;
  characterName: string | null;
  currentLevel: number;
  totalXp: number;
  xpForCurrentLevel: number;
  xpForNextLevel: number;
  xpProgressInLevel: number;
  progressPercent: number;
  intimacyStage: IntimacyStage;
  stageNameCn: string;
  streakDays: number;
  lastInteractionDate: string | null;
  dailyXpEarned: number;
  dailyXpLimit: number;
  dailyXpRemaining: number;
  availableActions: ActionAvailability[];
  unlockedFeatures: string[];
  // 统计数据
  totalMessages: number;
  giftsCount: number;
  specialEvents: number;
}

export interface XPAwardResponse {
  success: boolean;
  actionType: ActionType;
  xpAwarded: number;
  xpBefore: number;
  newTotalXp: number;
  levelBefore: number;
  newLevel: number;
  levelUp: boolean;
  levelsGained: number;
  stageBefore: IntimacyStage | null;
  newStage: IntimacyStage | null;
  stageChanged: boolean;
  dailyXpEarned: number;
  dailyXpRemaining: number;
  streakDays: number;
  celebrationMessage: string | null;
  unlockedFeatures: string[];
}

export interface DailyCheckinResponse {
  success: boolean;
  message: string;
  xpAwarded: number;
  streakDays: number;
  streakBonus: number;
  totalXpAwarded: number;
  newTotalXp: number;
  newLevel: number;
  levelUp: boolean;
}

export interface IntimacyHistoryEntry {
  actionType: ActionType;
  actionName: string;
  xpAwarded: number;
  createdAt: string;
}

export interface IntimacyHistoryResponse {
  characterId: string;
  entries: IntimacyHistoryEntry[];
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

export interface StageInfo {
  stageId: IntimacyStage;
  stageName: string;
  stageNameCn: string;
  levelRange: string;
  minLevel: number;
  maxLevel: number;
  description: string;
  aiAttitude: string;
  keyUnlocks: string[];
}

export interface AllStagesResponse {
  stages: StageInfo[];
  currentStage: IntimacyStage;
  currentLevel: number;
}

export interface FeatureUnlock {
  level: number;
  featureId: string;
  featureName: string;
  featureNameCn: string;
  description: string;
  isUnlocked: boolean;
}

export interface AllFeaturesResponse {
  features: FeatureUnlock[];
  currentLevel: number;
  totalUnlocked: number;
  totalFeatures: number;
}
