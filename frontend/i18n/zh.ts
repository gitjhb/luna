/**
 * Chinese (Simplified) translations
 */
export const zh = {
  // Tab bar
  tabs: {
    messages: '消息',
    discover: '发现',
    me: '我',
  },

  // Settings drawer
  settings: {
    title: '设置',
    preferences: 'Preferences',
    notifications: '通知',
    language: '语言',
    languageZh: '简体中文',
    languageEn: 'English',
    themeStyle: '主题风格',
    support: '支持',
    helpCenter: '帮助中心',
    rateApp: '给应用评分',
    termsPrivacy: '条款与隐私',
    logOut: '退出登录',
    logOutConfirm: '确定要退出登录吗？',
    cancel: '取消',
  },

  // Discover page
  discover: {
    greeting: 'Hi, {name} 👋',
    subtitle: '选择你的伴侣',
    searchPlaceholder: '搜索...',
    startChat: '开始聊天',
    buddy: '搭子',
  },

  // Chats page
  chats: {
    title: '消息',
    conversations: '{count} 个对话',
    noChats: '暂无对话',
    noChatsHint: '去发现页面开始聊天吧',
    goDiscover: '去发现',
    newConversation: '新对话',
    clearHistory: '清除聊天记录',
    clearHistoryConfirm: '确定要清除与「{name}」的聊天记录吗？\n\n亲密度和其他关系数据将保留。',
    cleared: '已清除',
    clearedMessage: '聊天记录已清除',
    error: '错误',
    clearFailed: '清除失败，请稍后重试',
  },

  // Profile page
  profile: {
    title: '我',
    enterNickname: '输入昵称',
    myCoins: '月光碎片',
    recharge: '充值',
    dailyFree: '每日赠送',
    perDay: '+{count}/天',
    purchased: '已购买',
    viewBills: '查看账单记录',
    myInterests: '我的兴趣',
    edit: '编辑',
    addInterests: '添加兴趣爱好，让AI更了解你',
    interestsHint: '💡 兴趣爱好会帮助AI更好地与你互动',
    more: '更多',
    inviteFriends: '邀请好友',
    rateUs: '给我们评分',
    helpFeedback: '帮助与反馈',
    selectAvatar: '选择头像',
    selectInterests: '选择兴趣（{count}/{max}）',
    saving: '保存中...',
    done: '完成',
    maxInterests: '最多选择{max}个兴趣哦～',
    cancelSubscription: '取消订阅',
    cancelSubscriptionConfirm: '确定要取消订阅吗？\n\n• 将立即降级为免费用户\n• 月光碎片余额保留\n• 不退款',
    thinkAgain: '再想想',
    confirmCancel: '确定取消',
    cancelled: '已取消',
  },

  // Login page
  login: {
    tagline: '遇见你的专属AI伴侣 💕',
    featureChat: '深度情感交流',
    featureSafe: '私密安全对话',
    featureUnique: '独特个性体验',
    guestLogin: '访客登录',
    appleLogin: 'Apple 登录',
    googleLogin: 'Google 登录',
    loginFailed: '登录失败',
    checkNetwork: '请检查网络连接',
    aiDisclaimer: '🤖 本应用角色对话内容由 AI 生成，不代表真实人物观点',
    termsPrefix: '注册即表示同意 ',
    termsOfService: '《服务条款》',
    and: ' 和 ',
    privacyPolicy: '《隐私政策》',
  },

  // Chat page
  chat: {
    chatWith: '与 {name} 聊天',
    typing: '正在输入...',
    sendGift: '送礼物',
    date: '约会',
    levelUp: '恭喜升级！',
    awesome: '太棒了！',
    loadingHistory: '加载历史消息...',
    allLoaded: '- 已加载全部消息 -',
    dateLocked: '约会功能需要 Lv.10 解锁',
    locked: '🔒 未解锁',
    aiDisclaimer: '由AI驱动的虚拟角色',
    // Error messages
    sendError: '发送失败',
    sendErrorMessage: '消息发送失败，请重试。',
    photoError: '照片请求失败',
    photoErrorMessage: '无法获取照片，请重试。',
    networkError: '网络错误',
    networkErrorMessage: '请检查网络连接后重试。',
  },

  // Character profile
  characterProfile: {
    title: '角色资料',
    bio: '简介',
    basicInfo: '基本信息',
    age: '年龄',
    ageValue: '{age}岁',
    birthday: '生日',
    zodiac: '星座',
    height: '身高',
    location: '所在地',
    mbti: 'MBTI',
    hobbies: '爱好',
    relationship: '关系状态',
    intimacy: '亲密度',
    streak: '连续互动',
    streakDays: '{days}天',
    chatMessages: '聊天消息',
    messagesCount: '{count}条',
    giftsReceived: '收到礼物',
    giftsCount: '{count}个',
    daysKnown: '认识天数',
    deleteCharacterData: '删除角色数据',
    deleteHint: '删除后将清除与该角色的所有聊天记录、亲密度和记忆数据',
    deleteConfirmTitle: '删除角色数据',
    deleteConfirmMessage: '你将永久删除与「{name}」的所有数据：',
    deleteList: {
      chats: '• 所有聊天记录',
      intimacy: '• 亲密度进度',
      emotion: '• 情感记忆',
      photos: '• 解锁的照片',
    },
    deleteWarning: '此操作无法撤销！',
    deleteInputLabel: '请输入 ',
    deleteInputHighlight: 'delete',
    deleteInputSuffix: ' 确认删除：',
    deleteInputPlaceholder: '输入 delete',
    deleting: '删除中...',
    confirmDelete: '确认删除',
    deleted: '已删除',
    deletedMessage: '「{name}」的所有数据已删除',
    confirm: '确定',
    deleteFailed: '删除失败，请稍后重试',
  },

  // Invite page
  invite: {
    title: '邀请好友',
    heroTitle: '邀请好友，赢取积分',
    heroSubtitle: '每邀请一位好友注册，你将获得 {reward} 月光碎片',
    myCode: '我的邀请码',
    shareToFriends: '分享给好友',
    invited: '已邀请好友',
    totalEarned: '累计获得',
    rulesTitle: '邀请规则',
    step1Title: '分享邀请码',
    step1Desc: '将你的专属邀请码分享给好友',
    step2Title: '好友注册',
    step2Desc: '好友使用邀请码完成注册',
    step3Title: '双方获奖',
    step3Desc: '你获得 {reward} 碎片，好友获得 {bonus} 碎片',
    friendsList: '已邀请的好友 ({count})',
    noFriends: '还没有邀请好友',
    noFriendsHint: '分享邀请码，一起来玩吧！',
    copySuccess: '复制成功',
    codeCopied: '邀请码已复制到剪贴板',
    loadFailed: '加载失败',
    loadFailedMessage: '无法获取邀请信息，请稍后重试',
    loading: '加载中...',
  },

  // Date system
  date: {
    // Scenario selection
    selectScenario: '选择约会地点',
    chooseLocation: '和 {name} 去哪里？',
    backToChat: '返回',
    startDate: '💕 开始约会',
    continueDate: '继续约会',
    abandonDate: '放弃',
    pauseDate: '暂时退出',
    unfinishedDate: '有一场未完成的约会',
    unfinishedDateDetail: '{scenarioName} · 第 {stageNum} 阶段',
    
    // Emotions and feelings
    emotion: '心情',
    emotionTooLow: '她现在心情不好，不想和你约会',
    emotionHint: '💡 送她一份礼物来改善心情吧',
    affection: '好感度',
    stage: '阶段',
    phase: 'PHASE {current} / {total}',
    theEnd: '~ THE END ~',
    
    // Cooldown system
    dateCooldown: '约会冷却中，还需等待 {time}',
    resetCooldown: '立即重置',
    cooldownResetPrice: '💎 50',
    cooldownReset: '冷却已重置！消费 50 月石',
    
    // Stamina system
    staminaInsufficient: '体力不足！约会需要 {required} 体力',
    currentStamina: '当前体力：{current}',
    staminaHint: '💡 可以购买体力或升级 VIP 享受无限体力~',
    
    // Dating phases
    selectPhase: '选择场景',
    playingPhase: '约会进行中',
    checkpointPhase: '中场休息',
    finalePhase: '结局剧情',
    endingPhase: '约会结算',
    
    // Scene interaction
    chooseResponse: '选择你的回应',
    continueStory: '继续约会',
    endDate: '结束约会',
    skipTyping: '跳过 →',
    freeInputPlaceholder: '说点什么...',
    freeInputTrigger: '我想自己说点什么...',
    freeInputCancel: '取消',
    freeInputSend: '发送',
    judgeComment: '评判评论',
    
    // Affection feedback
    affectionChange: '好感度变化',
    affectionPositive: '+{amount} ❤️',
    affectionNegative: '{amount} 💔',
    
    // Checkpoint system
    dateProgress: {
      terrible: '约会...有点糟糕',
      awkward: '气氛有些尴尬...',
      okay: '约会还算顺利',
      good: '约会进行得不错~',
      great: '约会进行得很顺利！',
      perfect: '完美的约会💕',
    },
    checkpointMessage: '基础章节已完成！要继续享受更多甜蜜时光吗？',
    checkpointMessageBad: '基础章节已完成。要尝试挽回局面吗？',
    extendStory: '💎 继续剧情',
    extendPrice: '30 月石 · 解锁后续 3 章',
    extendSuccess: '💎 -{amount} 月石，解锁后续3章剧情！',
    finishDate: '结束约会，查看结局 →',
    
    // Ending types
    ending: {
      perfect: '💕 完美约会',
      good: '😊 愉快约会',
      normal: '🙂 普通约会',
      bad: '😅 尴尬约会',
      failed: '💔 约会失败',
    },
    dateEnded: '约会结束',
    dateCompleted: '🎉 约会完成！',
    rewardsEarned: '获得奖励',
    experienceGained: '+{xp} XP',
    memorySaved: '📖 回忆已保存',
    memoryHint: '回忆已保存，可在回忆录中查看 💕',
    
    // Unlocked content
    unlockedPhoto: '📸 解锁新照片',
    photoTypeSpecial: '💕 特别版照片',
    photoTypeNormal: '📷 普通照片',
    checkAlbum: '前往相册查看',
    
    // Scenario names
    scenarios: {
      cafe_paris: '巴黎咖啡厅',
      beach_sunset: '海边夕阳',
      rooftop_city: '天台观景',
      forest_walk: '森林漫步',
      stargazing: '星空下',
    },
    
    // Errors and messages
    dateStartFailed: '约会启动失败',
    storyGenerationError: '生成故事时出错',
    networkError: '网络错误，请重试',
    choiceRequired: '请先选择一个约会场景',
    insufficientFunds: '💎 月石不足！还需要 {shortage} 月石（当前: {current}）',
    sendFailed: '发送失败，请重试',
    loadFailed: '加载失败',
    
    // Done and completion
    done: '完成',
    completed: '已完成',
    
    // Simple dating (non-interactive)
    inviteDate: '💕 邀请约会',
    generatingStory: '正在生成约会故事...',
    generatingDescription: '{name}正在准备和你的约会～\n请稍等片刻...',
    dateMemory: '💕 约会回忆',
    
    // Unlock system
    dateUnlockTitle: '约会功能未解锁',
    unlockConditions: '解锁条件：',
    levelRequirement: '达到 LV {level}',
    currentLevel: '(当前 LV {level})',
    giftRequirement: '送出过礼物',
    requirementMet: '✅',
    requirementNotMet: '⬜',
    
    // Date event card
    viewDetails: '查看完整故事',
    unlockDetails: '{cost} 💎 解锁详情',
    unlockMemory: '🔓 解锁约会回忆',
    unlockPrompt: '查看完整约会故事需要 {cost} 月石\n\n当前余额: {balance} 月石',
    unlockButton: '解锁 ({cost} 💎)',
    unlockFailed: '解锁失败',
    dateMemoryWith: '✨ 与{name}的约会回忆',
    
    // Progress and stats
    progress: '进度',
    rewards: '奖励',
    experience: '经验',
    mood: '心情',
    moodChange: '心情变化',
  },

  // Gift system
  gift: {
    // Categories
    categoryHeartfelt: '心意',
    categoryEnchantments: '魔法',
    categoryEternal: '永恒',
    categoryDescHeartfelt: '💫 日常的甜蜜与温馨，每一份小礼物都是爱意的表达',
    categoryDescEnchantments: '✨ 改变她心境的魔法道具，解锁她不为人知的另一面',
    categoryDescEternal: '💝 珍贵的回忆结晶，见证你们之间独特而不可复制的故事',
    
    // Main UI
    title: '💝 送礼物',
    moonShards: '月石',
    canBreakthrough: '可突破',
    coldWar: '冷战中',
    lockedAt: '🔒 亲密度已锁定在 Lv.{level}，送出{tierName}礼物突破',
    noGifts: '该分类暂无礼物',
    
    // Status effects
    statusEffectsTitle: '状态效果',
    statusDuration: '持续 {duration} 条对话',
    apologyGiftTitle: '破冰之礼',
    apologyGiftDesc: '💙 这份真挚的礼物能够融化心中的坚冰，重燃温暖的火花...让那些未说出口的歉意，化作重新开始的希望',
    
    // Actions
    sendGift: '💝 送给她',
    sending: '送出中...',
    sendSuccess: '送出成功!',
    sendFailed: '送礼失败',
    retryLater: '请稍后重试',
    unlockWithSub: '订阅解锁',
    getMoonShards: '获取月石',
    
    // Insufficient funds
    insufficientTitle: '💰 余额不足',
    insufficientMessage: '送出{giftName}需要{price}月石\n当前余额：{balance}月石',
    goRecharge: '去充值',
    
    // Tier names for bottleneck
    tierGeneral: '特定',
    tierStatus: 'Tier 2+ (状态)',
    tierAccelerated: 'Tier 3+ (加速)',
    tierPremium: 'Tier 4 (尊享)',
    
    // Effect descriptions
    effectTipsy: '🍷 她的脸颊泛起微红，眼神变得迷离而温柔...平时小心翼翼藏起的话语，此刻都化作星光般的坦诚流淌而出',
    effectMaidMode: '👗 "主人，请让我来为您服务..." 她款款行礼，语气变得恭敬而甜腻，仿佛您就是她心中唯一的光芒',
    effectTruthMode: '💎 真相的魔法笼罩着她，再不能说出违心的话...那些藏在心底的秘密，都将在您的询问下如花瓣般绽放',
    effectMystery: '神秘的力量正在觉醒...',
  },

  // Recharge system
  recharge: {
    title: '购买月光碎片',
    currentBalance: '当前余额',
    loading: '加载中...',
    retry: '重试',
    confirm: '购买',
    bonus: '赠送',
    
    // IAP errors
    iapNotAvailableInExpo: 'IAP 在 Expo Go 中不可用，请使用 dev build',
    noProductsAvailable: '暂无可用商品',
    loadProductsFailed: '加载商品失败',
    
    // Purchase flow
    confirmPurchaseTitle: '确认购买',
    confirmPurchaseMessage: '购买 {shards} 碎片{bonusText}，价格 {price}？',
    bonusText: ' (+{bonus} 赠送)',
    purchaseFailed: '购买失败',
    
    // Success animation
    purchaseSuccessTitle: '🎉 购买成功!',
    purchaseSuccessSubtitle: '已添加到您的账户',
    moonShards: '月石',
    
    // Tags
    tagHotSale: '热卖',
    tagGreatValue: '超值',
  },

  // Subscription system
  subscription: {
    title: '升级会员',
    subtitle: '解锁全部高级功能',
    loading: '加载中...',
    
    // Plan features
    dailyCredits: '每日 {amount} 碎片',
    fasterResponse: '更快的回复速度',
    premiumCharacters: '高级角色解锁',
    adultContent: '成人内容解锁 🔞',
    prioritySupport: '优先客服支持',
    
    // Plan info
    current: '当前',
    perMonth: '/月',
    dailyBonus: '每日 +{amount} 碎片',
    upgrade: '升级',
    subscribe: '立即订阅',
    higherTier: '当前等级更高',
    subscribed: '已订阅',
    
    // Purchase flow
    subscribeSuccessTitle: '🎉 订阅成功！',
    subscribeSuccessMessage: '欢迎成为 {planName} 会员！',
    verificationFailed: '验证失败',
    contactSupport: '请联系客服',
    subscriptionMightSucceed: '订阅可能已成功，请重启 App 或联系客服',
    purchaseFailed: '购买失败',
    
    // Restore purchases
    restorePurchases: '恢复购买',
    restoreSuccess: '恢复成功',
    restoreSuccessMessage: '已恢复 {tier} 会员资格',
    restoreFailed: '恢复失败',
    noValidSubscription: '未找到有效订阅',
    noSubscriptionFound: '未找到订阅',
    noPurchaseHistory: '没有可恢复的购买记录',
    
    // Feature highlights
    unlockAdultContent: '订阅解锁成人内容，体验更亲密的对话 🔞',
    unlockFeature: '订阅解锁 {feature} 功能',
    
    // Fallback UI
    productsLoading: '订阅产品加载中',
    checkConfiguration: '请稍后重试，或检查 App Store Connect 配置',
    requiresConfiguration: '需要配置: ',
    
    // Terms
    autoRenewTerms: '订阅将通过您的 {platform} 账户自动续费。\n可在设备设置中随时取消。',
    appleId: 'Apple ID',
    googlePlay: 'Google Play',
  },

  // Character info panel
  characterProfile: {
    title: '角色资料',
    bio: '简介',
    basicInfo: '基本信息',
    age: '年龄',
    ageValue: '{age}岁',
    birthday: '生日',
    zodiac: '星座',
    height: '身高',
    location: '所在地',
    mbti: 'MBTI',
    hobbies: '爱好',
    relationship: '关系状态',
    intimacy: '亲密度',
    streak: '连续互动',
    streakDays: '{days}天',
    chatMessages: '聊天消息',
    messagesCount: '{count}条',
    giftsReceived: '收到礼物',
    giftsCount: '{count}个',
    daysKnown: '认识天数',
    deleteCharacterData: '删除角色数据',
    deleteHint: '删除后将清除与该角色的所有聊天记录、亲密度和记忆数据',
    deleteConfirmTitle: '删除角色数据',
    deleteConfirmMessage: '你将永久删除与「{name}」的所有数据：',
    deleteList: {
      chats: '• 所有聊天记录',
      intimacy: '• 亲密度进度',
      emotion: '• 情感记忆',
      photos: '• 解锁的照片',
    },
    deleteWarning: '此操作无法撤销！',
    deleteInputLabel: '请输入 ',
    deleteInputHighlight: 'delete',
    deleteInputSuffix: ' 确认删除：',
    deleteInputPlaceholder: '输入 delete',
    deleting: '删除中...',
    confirmDelete: '确认删除',
    deleted: '已删除',
    deletedMessage: '「{name}」的所有数据已删除',
    confirm: '确定',
    deleteFailed: '删除失败，请稍后重试',
    
    // Tabs
    tabs: {
      status: '状态',
      events: '事件',
      gifts: '礼物',
      gallery: '相册',
      memory: '记忆',
    },
    
    // Status tab
    currentStatus: '当前状态',
    emotion: '情绪',
    emotionLocked: '订阅解锁',
    emotionLockedSubtext: '了解 TA 的真实情绪',
    
    // Emotion states
    emotions: {
      sweet: '甜蜜 💕',
      happy: '开心 😊',
      satisfied: '满足 🙂',
      calm: '平静 😐',
      unsatisfied: '不满 😒',
      angry: '生气 😠',
      coldWar: '冷战 ❄️',
    },
    
    // Events tab
    historyEvents: '历史事件',
    noEvents: '还没有特殊事件',
    
    // Gifts tab
    giftRecord: '礼物记录',
    noGifts: '还没有送过礼物',
    
    // Gallery tab
    photoCollection: '照片收集',
    galleryHint: '💡 约会获得好结局可以解锁照片',
    specialCollection: '🎬 特别收藏',
    secretBadge: '彩蛋',
    secretHint: '✨ 恭喜发现隐藏内容！',
    
    // Memory tab
    memoriesBook: '回忆录',
    memoriesBookSubtitle: '重温与{name}的精彩时刻',
    dateRecord: '约会记录',
    noMemories: '还没有记忆',
    noMemoriesHint: '继续和{name}聊天、约会，创造更多回忆 💕',
    
    // Scene names
    scenes: {
      bedroom: '卧室',
      beach: '沙滩',
      ocean: '海边',
      school: '学校',
      cafe: '咖啡厅',
      park: '公园',
    },
  },

  // Common
  common: {
    appName: 'Luna',
    cancel: '取消',
    confirm: '确定',
    error: '错误',
    loading: '加载中...',
  },
};

export type Translations = typeof zh;
