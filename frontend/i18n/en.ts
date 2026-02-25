/**
 * English translations
 */
import type { Translations } from './zh';

export const en: Translations = {
  // Tab bar
  tabs: {
    messages: 'Messages',
    discover: 'Discover',
    me: 'Me',
  },

  // Settings drawer
  settings: {
    title: 'Settings',
    preferences: 'Preferences',
    notifications: 'Notifications',
    language: 'Language',
    languageZh: '简体中文',
    languageEn: 'English',
    themeStyle: 'Theme',
    support: 'Support',
    helpCenter: 'Help Center',
    rateApp: 'Rate App',
    termsPrivacy: 'Terms & Privacy',
    logOut: 'Log Out',
    logOutConfirm: 'Are you sure you want to log out?',
    cancel: 'Cancel',
  },

  // Discover page
  discover: {
    greeting: 'Hi, {name} 👋',
    subtitle: 'Choose your companion',
    searchPlaceholder: 'Search...',
    startChat: 'Start Chat',
    buddy: 'Buddy',
  },

  // Chats page
  chats: {
    title: 'Messages',
    conversations: '{count} conversations',
    noChats: 'No conversations yet',
    noChatsHint: 'Go to Discover and start chatting!',
    goDiscover: 'Discover',
    newConversation: 'New Conversation',
    clearHistory: 'Clear Chat History',
    clearHistoryConfirm: 'Clear all chat history with "{name}"?\n\nIntimacy and relationship data will be preserved.',
    cleared: 'Cleared',
    clearedMessage: 'Chat history cleared',
    error: 'Error',
    clearFailed: 'Failed to clear. Please try again.',
  },

  // Profile page
  profile: {
    title: 'Me',
    enterNickname: 'Enter nickname',
    myCoins: 'Moon Shards',
    recharge: 'Recharge',
    dailyFree: 'Daily Free',
    perDay: '+{count}/day',
    purchased: 'Purchased',
    viewBills: 'View Transactions',
    myInterests: 'My Interests',
    edit: 'Edit',
    addInterests: 'Add interests to help AI know you better',
    interestsHint: '💡 Interests help AI interact with you better',
    more: 'More',
    inviteFriends: 'Invite Friends',
    rateUs: 'Rate Us',
    helpFeedback: 'Help & Feedback',
    selectAvatar: 'Select Avatar',
    selectInterests: 'Select Interests ({count}/{max})',
    saving: 'Saving...',
    done: 'Done',
    maxInterests: 'You can select up to {max} interests',
    cancelSubscription: 'Cancel Subscription',
    cancelSubscriptionConfirm: 'Are you sure?\n\n• You will be downgraded to free\n• Coin balance will be kept\n• No refund',
    thinkAgain: 'Think Again',
    confirmCancel: 'Confirm Cancel',
    cancelled: 'Cancelled',
  },

  // Login page
  login: {
    tagline: 'Meet your AI companion 💕',
    featureChat: 'Deep emotional connections',
    featureSafe: 'Private & secure',
    featureUnique: 'Unique personalities',
    guestLogin: 'Guest Login',
    appleLogin: 'Sign in with Apple',
    googleLogin: 'Sign in with Google',
    loginFailed: 'Login Failed',
    checkNetwork: 'Please check your network connection',
    aiDisclaimer: '🤖 All character conversations are AI-generated and do not represent real people',
    termsPrefix: 'By signing up, you agree to our ',
    termsOfService: 'Terms of Service',
    and: ' and ',
    privacyPolicy: 'Privacy Policy',
  },

  // Chat page
  chat: {
    chatWith: 'Chat with {name}',
    typing: 'Typing...',
    sendGift: 'Gift',
    date: 'Date',
    levelUp: 'Level Up!',
    awesome: 'Awesome!',
    loadingHistory: 'Loading history...',
    allLoaded: '- All messages loaded -',
    dateLocked: 'Dates unlock at Lv.10',
    locked: '🔒 Locked',
    aiDisclaimer: 'AI-powered virtual character',
    // Error messages
    sendError: 'Send Failed',
    sendErrorMessage: 'Failed to send message. Please try again.',
    photoError: 'Photo Request Failed',
    photoErrorMessage: 'Failed to request photo. Please try again.',
    networkError: 'Network Error',
    networkErrorMessage: 'Please check your connection and try again.',
  },

  // Character profile
  characterProfile: {
    title: 'Character Profile',
    bio: 'Bio',
    basicInfo: 'Basic Info',
    age: 'Age',
    ageValue: '{age}',
    birthday: 'Birthday',
    zodiac: 'Zodiac',
    height: 'Height',
    location: 'Location',
    mbti: 'MBTI',
    hobbies: 'Hobbies',
    relationship: 'Relationship',
    intimacy: 'Intimacy',
    streak: 'Streak',
    streakDays: '{days} days',
    chatMessages: 'Messages',
    messagesCount: '{count}',
    giftsReceived: 'Gifts',
    giftsCount: '{count}',
    daysKnown: 'Days Known',
    deleteCharacterData: 'Delete Character Data',
    deleteHint: 'This will clear all chat history, intimacy, and memories with this character',
    deleteConfirmTitle: 'Delete Character Data',
    deleteConfirmMessage: 'You will permanently delete all data with "{name}":',
    deleteList: {
      chats: '• All chat history',
      intimacy: '• Intimacy progress',
      emotion: '• Emotional memories',
      photos: '• Unlocked photos',
    },
    deleteWarning: 'This cannot be undone!',
    deleteInputLabel: 'Type ',
    deleteInputHighlight: 'delete',
    deleteInputSuffix: ' to confirm:',
    deleteInputPlaceholder: 'Type delete',
    deleting: 'Deleting...',
    confirmDelete: 'Confirm Delete',
    deleted: 'Deleted',
    deletedMessage: 'All data for "{name}" has been deleted',
    confirm: 'OK',
    deleteFailed: 'Failed to delete. Please try again.',
  },

  // Invite page
  invite: {
    title: 'Invite Friends',
    heroTitle: 'Invite Friends, Earn Points',
    heroSubtitle: 'Earn {reward} Moon Shards for each friend who signs up',
    myCode: 'My Invite Code',
    shareToFriends: 'Share with Friends',
    invited: 'Friends Invited',
    totalEarned: 'Total Earned',
    rulesTitle: 'How It Works',
    step1Title: 'Share your code',
    step1Desc: 'Share your unique invite code with friends',
    step2Title: 'Friend signs up',
    step2Desc: 'Your friend registers using your code',
    step3Title: 'Both get rewarded',
    step3Desc: 'You get {reward} shards, friend gets {bonus} shards',
    friendsList: 'Invited Friends ({count})',
    noFriends: 'No friends invited yet',
    noFriendsHint: 'Share your code and start earning!',
    copySuccess: 'Copied',
    codeCopied: 'Invite code copied to clipboard',
    loadFailed: 'Load Failed',
    loadFailedMessage: 'Could not load invite info. Please try again.',
    loading: 'Loading...',
  },

  // Date system
  date: {
    // Scenario selection
    selectScenario: 'Select scenario',
    chooseLocation: 'Where to go with {name}?',
    backToChat: 'Back',
    startDate: '💕 Start date',
    continueDate: 'Continue date',
    abandonDate: 'Abandon',
    pauseDate: 'Pause',
    unfinishedDate: 'You have an unfinished date',
    unfinishedDateDetail: '{scenarioName} · Stage {stageNum}',
    
    // Emotions and feelings
    emotion: 'Mood',
    emotionTooLow: 'She\'s not in the mood for a date right now',
    emotionHint: '💡 Send her a gift to improve her mood',
    affection: 'Affection',
    stage: 'Stage',
    phase: 'PHASE {current} / {total}',
    theEnd: '~ THE END ~',
    
    // Cooldown system
    dateCooldown: 'Date cooldown, wait {time} more',
    resetCooldown: 'Reset now',
    cooldownResetPrice: '💎 50',
    cooldownReset: 'Cooldown reset! 50 moon shards spent',
    
    // Stamina system
    staminaInsufficient: 'Not enough stamina! Date requires {required} stamina',
    currentStamina: 'Current stamina: {current}',
    staminaHint: '💡 You can purchase stamina or upgrade VIP for unlimited stamina~',
    
    // Dating phases
    selectPhase: 'Select scenario',
    playingPhase: 'Dating in progress',
    checkpointPhase: 'Checkpoint',
    finalePhase: 'Finale story',
    endingPhase: 'Date summary',
    
    // Scene interaction
    chooseResponse: 'Choose your response',
    continueStory: 'Continue date',
    endDate: 'End date',
    skipTyping: 'Skip →',
    freeInputPlaceholder: 'Say something...',
    freeInputTrigger: 'I want to say something myself...',
    freeInputCancel: 'Cancel',
    freeInputSend: 'Send',
    judgeComment: 'Judge comment',
    
    // Affection feedback
    affectionChange: 'Affection change',
    affectionPositive: '+{amount} ❤️',
    affectionNegative: '{amount} 💔',
    
    // Checkpoint system
    dateProgress: {
      terrible: 'The date... was terrible',
      awkward: 'Things got a bit awkward...',
      okay: 'The date went okay',
      good: 'The date went well~',
      great: 'The date went really well!',
      perfect: 'Perfect date💕',
    },
    checkpointMessage: 'Basic chapters complete! Want to continue for more sweet moments?',
    checkpointMessageBad: 'Basic chapters complete. Want to try to turn things around?',
    extendStory: '💎 Continue story',
    extendPrice: '30 moon shards · Unlock 3 more chapters',
    extendSuccess: '💎 -{amount} moon shards, unlocked 3 more story chapters!',
    finishDate: 'End date and see the ending →',
    
    // Ending types
    ending: {
      perfect: '💕 Perfect date',
      good: '😊 Great date',
      normal: '🙂 Normal date',
      bad: '😅 Awkward date',
      failed: '💔 Date failed',
    },
    dateEnded: 'Date ended',
    dateCompleted: '🎉 Date completed!',
    rewardsEarned: 'Rewards earned',
    experienceGained: '+{xp} XP',
    memorySaved: '📖 Memory saved',
    memoryHint: 'Memory saved, you can view it in your memory book 💕',
    
    // Unlocked content
    unlockedPhoto: '📸 New photo unlocked',
    photoTypeSpecial: '💕 Special edition photo',
    photoTypeNormal: '📷 Regular photo',
    checkAlbum: 'Check photo album',
    
    // Scenario names
    scenarios: {
      cafe_paris: 'Paris Cafe',
      beach_sunset: 'Beach Sunset',
      rooftop_city: 'City Rooftop',
      forest_walk: 'Forest Walk',
      stargazing: 'Stargazing',
    },
    
    // Errors and messages
    dateStartFailed: 'Failed to start date',
    storyGenerationError: 'Error generating story',
    networkError: 'Network error, please try again',
    choiceRequired: 'Please select a date scenario first',
    insufficientFunds: '💎 Not enough moon shards! Need {shortage} more (current: {current})',
    sendFailed: 'Send failed, please retry',
    loadFailed: 'Load failed',
    
    // Done and completion
    done: 'Done',
    completed: 'Completed',
    
    // Simple dating (non-interactive)
    inviteDate: '💕 Invite on date',
    generatingStory: 'Generating date story...',
    generatingDescription: '{name} is preparing for your date~\nPlease wait a moment...',
    dateMemory: '💕 Date memory',
    
    // Unlock system
    dateUnlockTitle: 'Date feature not unlocked',
    unlockConditions: 'Unlock conditions:',
    levelRequirement: 'Reach LV {level}',
    currentLevel: '(current LV {level})',
    giftRequirement: 'Send a gift',
    requirementMet: '✅',
    requirementNotMet: '⬜',
    
    // Date event card
    viewDetails: 'View full story',
    unlockDetails: '{cost} 💎 Unlock details',
    unlockMemory: '🔓 Unlock date memory',
    unlockPrompt: 'Viewing the full date story requires {cost} moon shards\n\nCurrent balance: {balance} moon shards',
    unlockButton: 'Unlock ({cost} 💎)',
    unlockFailed: 'Unlock failed',
    dateMemoryWith: '✨ Date memory with {name}',
    
    // Progress and stats
    progress: 'Progress',
    rewards: 'Rewards',
    experience: 'Experience',
    mood: 'Mood',
    moodChange: 'Mood change',
  },

  // Gift system
  gift: {
    // Categories
    categoryHeartfelt: 'Heartfelt',
    categoryEnchantments: 'Enchantments',
    categoryEternal: 'Eternal',
    categoryDescHeartfelt: '💫 Daily sweetness and warmth, every little gift expresses love',
    categoryDescEnchantments: '✨ Magical items that change her mood, unlock her unknown side',
    categoryDescEternal: '💝 Precious memory crystals, witnessing your unique and irreplaceable story',
    
    // Main UI
    title: '💝 Send Gift',
    moonShards: 'Moon Shards',
    canBreakthrough: 'Can Breakthrough',
    coldWar: 'Cold War',
    lockedAt: '🔒 Intimacy locked at Lv.{level}, send {tierName} gift to break through',
    noGifts: 'No gifts in this category',
    
    // Status effects
    statusEffectsTitle: 'Status Effects',
    statusDuration: 'Lasts {duration} messages',
    apologyGiftTitle: 'Ice Breaker',
    apologyGiftDesc: '💙 This heartfelt gift can melt the ice in her heart, rekindle warm sparks... let those unspoken apologies become hope for a fresh start',
    
    // Actions
    sendGift: '💝 Give to Her',
    sending: 'Sending...',
    sendSuccess: 'Sent Successfully!',
    sendFailed: 'Gift Failed',
    retryLater: 'Please try again later',
    unlockWithSub: 'Unlock with Subscription',
    getMoonShards: 'Get Moon Shards',
    
    // Insufficient funds
    insufficientTitle: '💰 Insufficient Balance',
    insufficientMessage: 'Sending {giftName} requires {price} moon shards\nCurrent balance: {balance} moon shards',
    goRecharge: 'Recharge',
    
    // Tier names for bottleneck
    tierGeneral: 'Specific',
    tierStatus: 'Tier 2+ (Status)',
    tierAccelerated: 'Tier 3+ (Accelerated)',
    tierPremium: 'Tier 4 (Premium)',
    
    // Effect descriptions
    effectTipsy: '🍷 Her cheeks flush with a rosy tint, her eyes become dreamy and tender... words usually kept hidden flow out like starlight in honest streams',
    effectMaidMode: '👗 "Master, please let me serve you..." She curtsies gracefully, her tone becoming respectful and sweet, as if you are the only light in her heart',
    effectTruthMode: '💎 Truth\'s magic surrounds her, she can no longer speak against her heart... secrets hidden deep inside will bloom like petals under your questioning',
    effectMystery: 'Mysterious powers are awakening...',
  },

  // Recharge system
  recharge: {
    title: 'Purchase Moon Shards',
    currentBalance: 'Current Balance',
    loading: 'Loading...',
    retry: 'Retry',
    confirm: 'Purchase',
    bonus: 'Bonus',
    
    // IAP errors
    iapNotAvailableInExpo: 'IAP not available in Expo Go, please use dev build',
    noProductsAvailable: 'No products available',
    loadProductsFailed: 'Failed to load products',
    
    // Purchase flow
    confirmPurchaseTitle: 'Confirm Purchase',
    confirmPurchaseMessage: 'Purchase {shards} shards{bonusText} for {price}?',
    bonusText: ' (+{bonus} bonus)',
    purchaseFailed: 'Purchase Failed',
    
    // Success animation
    purchaseSuccessTitle: '🎉 Purchase Successful!',
    purchaseSuccessSubtitle: 'Added to your account',
    moonShards: 'Moon Shards',
    
    // Tags
    tagHotSale: 'Hot Sale',
    tagGreatValue: 'Great Value',
  },

  // Subscription system
  subscription: {
    title: 'Upgrade Membership',
    subtitle: 'Unlock all premium features',
    loading: 'Loading...',
    
    // Plan features
    dailyCredits: '{amount} daily shards',
    fasterResponse: 'Faster response speed',
    premiumCharacters: 'Premium characters unlocked',
    adultContent: 'Adult content unlocked 🔞',
    prioritySupport: 'Priority customer support',
    
    // Plan info
    current: 'Current',
    perMonth: '/month',
    dailyBonus: 'Daily +{amount} shards',
    upgrade: 'Upgrade',
    subscribe: 'Subscribe Now',
    higherTier: 'Current tier is higher',
    subscribed: 'Subscribed',
    
    // Purchase flow
    subscribeSuccessTitle: '🎉 Subscription Successful!',
    subscribeSuccessMessage: 'Welcome to {planName} membership!',
    verificationFailed: 'Verification Failed',
    contactSupport: 'Please contact support',
    subscriptionMightSucceed: 'Subscription may have succeeded, please restart app or contact support',
    purchaseFailed: 'Purchase Failed',
    
    // Restore purchases
    restorePurchases: 'Restore Purchases',
    restoreSuccess: 'Restore Successful',
    restoreSuccessMessage: 'Restored {tier} membership',
    restoreFailed: 'Restore Failed',
    noValidSubscription: 'No valid subscription found',
    noSubscriptionFound: 'No Subscription Found',
    noPurchaseHistory: 'No purchase history to restore',
    
    // Feature highlights
    unlockAdultContent: 'Subscribe to unlock adult content and experience more intimate conversations 🔞',
    unlockFeature: 'Subscribe to unlock {feature} feature',
    
    // Fallback UI
    productsLoading: 'Subscription products loading',
    checkConfiguration: 'Please try again later, or check App Store Connect configuration',
    requiresConfiguration: 'Requires configuration: ',
    
    // Terms
    autoRenewTerms: 'Subscription will auto-renew through your {platform} account.\nYou can cancel anytime in device settings.',
    appleId: 'Apple ID',
    googlePlay: 'Google Play',
  },

  // Character info panel
  characterProfile: {
    title: 'Character Profile',
    bio: 'Bio',
    basicInfo: 'Basic Info',
    age: 'Age',
    ageValue: '{age}',
    birthday: 'Birthday',
    zodiac: 'Zodiac',
    height: 'Height',
    location: 'Location',
    mbti: 'MBTI',
    hobbies: 'Hobbies',
    relationship: 'Relationship',
    intimacy: 'Intimacy',
    streak: 'Streak',
    streakDays: '{days} days',
    chatMessages: 'Messages',
    messagesCount: '{count}',
    giftsReceived: 'Gifts',
    giftsCount: '{count}',
    daysKnown: 'Days Known',
    deleteCharacterData: 'Delete Character Data',
    deleteHint: 'This will clear all chat history, intimacy, and memories with this character',
    deleteConfirmTitle: 'Delete Character Data',
    deleteConfirmMessage: 'You will permanently delete all data with "{name}":',
    deleteList: {
      chats: '• All chat history',
      intimacy: '• Intimacy progress',
      emotion: '• Emotional memories',
      photos: '• Unlocked photos',
    },
    deleteWarning: 'This cannot be undone!',
    deleteInputLabel: 'Type ',
    deleteInputHighlight: 'delete',
    deleteInputSuffix: ' to confirm:',
    deleteInputPlaceholder: 'Type delete',
    deleting: 'Deleting...',
    confirmDelete: 'Confirm Delete',
    deleted: 'Deleted',
    deletedMessage: 'All data for "{name}" has been deleted',
    confirm: 'OK',
    deleteFailed: 'Failed to delete. Please try again.',
    
    // Tabs
    tabs: {
      status: 'Status',
      events: 'Events',
      gifts: 'Gifts',
      gallery: 'Gallery',
      memory: 'Memory',
    },
    
    // Status tab
    currentStatus: 'Current Status',
    emotion: 'Emotion',
    emotionLocked: 'Subscribe to Unlock',
    emotionLockedSubtext: 'Understand their true emotions',
    
    // Emotion states
    emotions: {
      sweet: 'Sweet 💕',
      happy: 'Happy 😊',
      satisfied: 'Satisfied 🙂',
      calm: 'Calm 😐',
      unsatisfied: 'Unsatisfied 😒',
      angry: 'Angry 😠',
      coldWar: 'Cold War ❄️',
    },
    
    // Events tab
    historyEvents: 'History Events',
    noEvents: 'No special events yet',
    
    // Gifts tab
    giftRecord: 'Gift Record',
    noGifts: 'No gifts sent yet',
    
    // Gallery tab
    photoCollection: 'Photo Collection',
    galleryHint: '💡 Get good endings on dates to unlock photos',
    specialCollection: '🎬 Special Collection',
    secretBadge: 'Easter Egg',
    secretHint: '✨ Congratulations on finding hidden content!',
    
    // Memory tab
    memoriesBook: 'Memory Book',
    memoriesBookSubtitle: 'Relive wonderful moments with {name}',
    dateRecord: 'Date Record',
    noMemories: 'No memories yet',
    noMemoriesHint: 'Continue chatting and dating with {name} to create more memories 💕',
    
    // Scene names
    scenes: {
      bedroom: 'Bedroom',
      beach: 'Beach',
      ocean: 'Ocean',
      school: 'School',
      cafe: 'Cafe',
      park: 'Park',
    },
  },

  // Common
  common: {
    appName: 'Luna',
    cancel: 'Cancel',
    confirm: 'OK',
    error: 'Error',
    loading: 'Loading...',
  },
};
