/**
 * Chat Screen - Intimate Style
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  FlatList,
  Alert,
  Keyboard,
  Image,
  Dimensions,
  ImageBackground,
  Modal,
  ScrollView,
  Animated,
  ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { Video, ResizeMode } from 'expo-av';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useUserStore } from '../../store/userStore';
import { useChatStore, Message } from '../../store/chatStore';
import { useMessages } from '../../hooks/useMessages';
import { useGiftStore, GiftCatalogItem } from '../../store/giftStore';

// NSFW mode costs 2 extra credits per message
// const NSFW_MODE_CREDIT_COST = 2;  // Disabled - spicy mode is free now
import { chatService } from '../../services/chatService';
import { api } from '../../services/api';
import { intimacyService } from '../../services/intimacyService';
import { characterService } from '../../services/characterService';
import { emotionService } from '../../services/emotionService';
import { GiftOverlay, useGiftEffect, GiftType } from '../../components/GiftEffects';
import { paymentService } from '../../services/paymentService';
import { RechargeModal } from '../../components/RechargeModal';
import { SubscriptionModalRC as SubscriptionModal } from '../../components/SubscriptionModalRC';
import { getCharacterAvatar, getCharacterBackground, getCharacterIntroVideo, CHARACTER_IDS } from '../../assets/characters';
import CharacterInfoPanel from '../../components/CharacterInfoPanel';
import GiftBottomSheet from '../../components/GiftBottomSheet';
import MockModeBanner from '../../components/MockModeBanner';
import MessageBubble from '../../components/MessageBubble';
import VideoMessageBubble from '../../components/VideoMessageBubble';
import { ToastProvider, useToast } from '../../components/Toast';
import { useEmotionTheme } from '../../hooks/useEmotionTheme';
import { EmotionEffectsLayer } from '../../components/EmotionEffects';
import { DebugButton } from '../../components/DebugPanel';
import { ExtraData } from '../../store/chatStore';
import EventStoryCard from '../../components/EventStoryCard';
import EventStoryModal from '../../components/EventStoryModal';
import MemoriesModal from '../../components/MemoriesModal';
import EventBubble from '../../components/EventBubble';
import DateEventCard, { isDateEventCard } from '../../components/DateEventCard';
import { eventService, EventStoryPlaceholder, EventMemory } from '../../services/eventService';
import { IntimacyInfoPanel } from '../../components/IntimacyInfoPanel';
import { interactionsService } from '../../services/interactionsService';
import DressupModal from '../../components/DressupModal';
import DateModal from '../../components/DateModal';
import DateSceneModal from '../../components/DateSceneModal';
import AiDisclaimerBanner from '../../components/AiDisclaimerBanner';
import ChatLoadingSkeleton from '../../components/ChatLoadingSkeleton';
import { useLocale, tpl } from '../../i18n';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

const DEFAULT_BACKGROUND = 'https://i.imgur.com/vB5HQXQ.jpg';

export default function ChatScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ characterId: string; characterName: string; sessionId?: string; backgroundUrl?: string; avatarUrl?: string }>();
  const insets = useSafeAreaInsets();

  const { t } = useLocale();
  const { wallet, deductCredits, updateWallet, isSubscribed } = useUserStore();
  // NSFW mode disabled on mobile for App Store compliance (web only)
  const isSpicyMode = false; // useChatStore((s) => s.isSpicyMode);
  const giftCatalog = useGiftStore((s) => s.catalog);
  const fetchGiftCatalog = useGiftStore((s) => s.fetchCatalog);
  const {
    isTyping,
    setActiveSession,
    addMessage: addMessageToStore,
    setMessages: setMessagesToStore,
    setTyping,
    getIntimacy,
    setIntimacy,
    updateSession,
  } = useChatStore();

  const cachedIntimacy = useChatStore((s) => s.intimacyByCharacter[params.characterId]);
  
  // 立即获取缓存的session，让useMessages能尽快启用
  const cachedSession = useChatStore.getState().getSessionByCharacterId(params.characterId);

  const [inputText, setInputText] = useState('');
  // 🔧 sessionId 初始为 null，等后端确认后再设置
  // 这样可以避免用无效的缓存 sessionId 发起查询
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [sessionVerified, setSessionVerified] = useState(false);  // 后端已确认 session
  
  // Track message IDs that should show typewriter effect (just added via API response)
  const [typewriterMessageIds, setTypewriterMessageIds] = useState<Set<string>>(new Set());

  // 📬 React Query 消息管理
  const {
    messages,
    isLoading: isLoadingMessages,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    addMessage,
    updateMessage,
  } = useMessages({
    sessionId,
    characterId: params.characterId,
    enabled: !!sessionId && sessionVerified,  // 只在后端确认 session 后才加载
  });
  const [characterAvatar, setCharacterAvatar] = useState(params.avatarUrl || '');
  const [backgroundImage, setBackgroundImage] = useState(params.backgroundUrl || DEFAULT_BACKGROUND);
  const [relationshipLevel, setRelationshipLevel] = useState<number | null>(null); // null = loading
  const [relationshipXp, setRelationshipXp] = useState(0);
  const [relationshipMaxXp, setRelationshipMaxXp] = useState(100);
  const [showRechargeModal, setShowRechargeModal] = useState(false);
  const [showLevelUpModal, setShowLevelUpModal] = useState(false);
  const [newLevel, setNewLevel] = useState(0);
  const [characterName, setCharacterName] = useState(params.characterName || 'Companion');
  const [showLevelInfoModal, setShowLevelInfoModal] = useState(false);
  const [showGiftModal, setShowGiftModal] = useState(false);
  const [showDressupModal, setShowDressupModal] = useState(false);
  const [showDateModal, setShowDateModal] = useState(false);
  const [showDateSceneModal, setShowDateSceneModal] = useState(false);
  const [dateScenarios, setDateScenarios] = useState<Array<{id: string; name: string; icon: string; description?: string}>>([]);
  const [dateLoading, setDateLoading] = useState(false);
  const [photoLoading, setPhotoLoading] = useState(false);
  const [keyboardHeight, setKeyboardHeight] = useState(0);
  const [showSubscriptionModal, setShowSubscriptionModal] = useState(false);
  const [showCharacterInfo, setShowCharacterInfo] = useState(false);
  const [emotionScore, setEmotionScore] = useState(0);
  const [emotionState, setEmotionState] = useState('neutral');
  const [lastExtraData, setLastExtraData] = useState<ExtraData | null>(null);  // Debug info
  const [lastTokensUsed, setLastTokensUsed] = useState<number>(0);

  // 🔒 瓶颈锁状态
  const [bottleneckLocked, setBottleneckLocked] = useState(false);
  const [bottleneckLockLevel, setBottleneckLockLevel] = useState<number | null>(null);
  const [bottleneckRequiredTier, setBottleneckRequiredTier] = useState<number | null>(null);

  // 🍷 临时升阶状态
  const [stageBoostActive, setStageBoostActive] = useState(false);
  const [stageBoostHint, setStageBoostHint] = useState<string | null>(null);

  // 📖 剧情系统状态
  const [showEventStoryModal, setShowEventStoryModal] = useState(false);
  const [selectedEventPlaceholder, setSelectedEventPlaceholder] = useState<EventStoryPlaceholder | null>(null);
  const [showMemoriesModal, setShowMemoriesModal] = useState(false);
  const [readEventIds, setReadEventIds] = useState<Set<string>>(new Set());

  // 📜 聊天分页 - 由 useMessages hook 管理
  // hasNextPage, isFetchingNextPage, fetchNextPage 来自 useMessages

  // 💕 进行中的约会提醒
  const [showActiveDateAlert, setShowActiveDateAlert] = useState(false);
  const [activeDateSession, setActiveDateSession] = useState<{
    session_id: string;
    stage_num: number;
    scenario_name: string;
  } | null>(null);

  // 🎉 第一次约会庆祝弹窗
  const [showFirstDateCelebration, setShowFirstDateCelebration] = useState(false);
  const [firstDateResult, setFirstDateResult] = useState<{
    ending: string;
    xp: number;
    affection: number;
  } | null>(null);

  // 🎬 通用角色入场动画 (仅第一次打开时显示)
  // 有intro视频的角色：挂载时显示splash遮盖，等API确认后决定是否播视频
  const hasIntroVideo = getCharacterIntroVideo(params.characterId);
  // 如果缓存明确说introShown=true，不需要遮盖；否则有视频的角色先遮盖
  const cachedIntroShown = cachedSession?.introShown === true;
  const needsCoverOnMount = hasIntroVideo && !cachedIntroShown;
  const [showCharacterIntro, setShowCharacterIntro] = useState(needsCoverOnMount);
  // 'splash' = 等待API确认，'black' = 准备播视频，'video' = 播放中，'fadeout' = 淡出，'done' = 完成
  const [introPhase, setIntroPhase] = useState<'splash' | 'black' | 'video' | 'fadeout' | 'done'>(needsCoverOnMount ? 'splash' : 'done');
  const [introVideoReady, setIntroVideoReady] = useState(false);
  const introFadeAnim = useRef(new Animated.Value(1)).current;
  const introSessionIdRef = useRef<string | null>(null);  // 保存sessionId给intro用
  
  // 使用统一的角色ID常量
  const LUNA_CHARACTER_ID = CHARACTER_IDS.LUNA;
  const VERA_CHARACTER_ID = CHARACTER_IDS.VERA;

  // 🎨 动态主题 - 根据情绪状态自动切换
  const {
    theme: emotionTheme,
    emotionMode,
    overlayColors,
    glitchEnabled,
    glowEnabled,
    emotionHint,
  } = useEmotionTheme(emotionScore, emotionState, isSpicyMode);

  // 礼物特效
  const {
    isVisible: showGiftEffect,
    currentGift,
    sendGift: triggerGiftEffect,
    hideGift
  } = useGiftEffect();

  const flatListRef = useRef<FlatList>(null);
  const previousLevelRef = useRef<number | null>(null);
  const isSendingRef = useRef(false);  // Prevent duplicate sends

  // Animated progress bar
  const xpProgressAnim = useRef(new Animated.Value(0)).current;

  // Note: With inverted FlatList, newest messages are at index 0 (visible at bottom)
  // No need to manually scroll to bottom - it happens automatically

  // 监听键盘高度变化
  useEffect(() => {
    const showSub = Keyboard.addListener(
      Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow',
      (e) => setKeyboardHeight(e.endCoordinates.height)
    );
    const hideSub = Keyboard.addListener(
      Platform.OS === 'ios' ? 'keyboardWillHide' : 'keyboardDidHide',
      () => setKeyboardHeight(0)
    );
    return () => {
      showSub.remove();
      hideSub.remove();
    };
  }, []);

  // Animate progress bar when XP changes
  useEffect(() => {
    // Ensure xp is non-negative (can be negative briefly during level transitions)
    const safeXp = Math.max(0, relationshipXp);
    const safeMax = Math.max(1, relationshipMaxXp); // Avoid division by zero
    const progress = (safeXp / safeMax) * 100;

    Animated.timing(xpProgressAnim, {
      toValue: Math.max(0, Math.min(progress, 100)), // Clamp between 0-100
      duration: 500,
      useNativeDriver: false,
    }).start();
  }, [relationshipXp, relationshipMaxXp, relationshipLevel]); // Also trigger on level change

  // Reset state when character changes
  useEffect(() => {
    // Load cached intimacy immediately (instant display)
    if (cachedIntimacy) {
      previousLevelRef.current = cachedIntimacy.currentLevel;
      setRelationshipLevel(cachedIntimacy.currentLevel);
      // Calculate max XP for current level range
      const maxXp = cachedIntimacy.xpForNextLevel - cachedIntimacy.xpForCurrentLevel;
      // Validate: max should be positive, xpProgress should be 0 to max
      const validMax = maxXp > 0 ? maxXp : 6; // Default to 6 for level 1
      const validProgress = Math.max(0, Math.min(cachedIntimacy.xpProgressInLevel, validMax));
      setRelationshipXp(validProgress);
      setRelationshipMaxXp(validMax);
    } else {
      setRelationshipLevel(null);
      setRelationshipXp(0);
      setRelationshipMaxXp(6); // Level 1 needs 6 XP
    }
    // Don't clear messages here - let initializeSession handle it
    // Messages are already cached in store, clearing causes flicker
    initializeSession();
  }, [params.characterId]);

  const initializeSession = async () => {
    try {
      setIsInitializing(true);

      // Step 0: intro遮盖已在useState初始化时处理，这里不需要再设置

      // Step 1: 使用缓存的session（如果有）
      if (cachedSession) {
        setSessionId(cachedSession.sessionId);
        setActiveSession(cachedSession.sessionId, params.characterId);
        if (cachedSession.characterName) setCharacterName(cachedSession.characterName);
        if (cachedSession.characterAvatar) setCharacterAvatar(cachedSession.characterAvatar);
        if (cachedSession.characterBackground) setBackgroundImage(cachedSession.characterBackground);
        // Messages are already in store from cache, no need to set again
      }

      // Step 2: Fetch intimacy status (and cache it locally)
      try {
        const intimacyStatus = await intimacyService.getStatus(params.characterId);
        previousLevelRef.current = intimacyStatus.currentLevel;
        setRelationshipLevel(intimacyStatus.currentLevel);
        // Calculate and validate max XP
        const maxXp = intimacyStatus.xpForNextLevel - intimacyStatus.xpForCurrentLevel;
        const validMax = maxXp > 0 ? maxXp : 6;
        const validProgress = Math.max(0, Math.min(intimacyStatus.xpProgressInLevel, validMax));
        setRelationshipXp(validProgress);
        setRelationshipMaxXp(validMax);
        // Cache to local store for instant load next time
        setIntimacy(params.characterId, {
          currentLevel: intimacyStatus.currentLevel,
          xpProgressInLevel: validProgress,
          xpForNextLevel: intimacyStatus.xpForNextLevel,
          xpForCurrentLevel: intimacyStatus.xpForCurrentLevel,
        });
        // Update bottleneck lock status
        setBottleneckLocked(intimacyStatus.bottleneckLocked || false);
        setBottleneckLockLevel(intimacyStatus.bottleneckLockLevel || null);
        setBottleneckRequiredTier(intimacyStatus.bottleneckRequiredGiftTier || null);
      } catch (e) {
        console.log('Intimacy status not available:', e);
        // Only set default if no cached data (default level is 1)
        if (!cachedIntimacy) {
          previousLevelRef.current = 1;
          setRelationshipLevel(1);
          setRelationshipXp(0);
          setRelationshipMaxXp(6);
        }
      }

      // Step 2.5: Fetch emotion status
      try {
        const emotionStatus = await emotionService.getStatus(params.characterId);
        if (emotionStatus) {
          const score = emotionStatus.emotionScore;
          setEmotionScore(score);
          setEmotionState(emotionStatus.emotionalState);
        }
      } catch (e) {
        console.log('Emotion status not available:', e);
      }

      // Step 3: Sync with backend - get or create session
      console.log('[Chat] Getting session from backend for character:', params.characterId);
      const session = await chatService.getOrCreateSession(params.characterId);
      console.log('[Chat] Backend returned session:', session.sessionId, 'introShown:', session.introShown);
      
      // 🔄 Session ID 变化检测：如果后端返回的 session ID 与缓存不同，清除旧缓存
      const existingSession = useChatStore.getState().getSessionByCharacterId(params.characterId);
      if (existingSession && existingSession.sessionId !== session.sessionId) {
        console.log('[Chat] Session ID changed! Old:', existingSession.sessionId, 'New:', session.sessionId);
        // 清除旧 session 的本地缓存 (包括 messagesBySession)
        useChatStore.getState().deleteSession(existingSession.sessionId);
        // 清除 SQLite 中的旧消息
        import('../../services/database/repositories').then(({ MessageRepository }) => {
          MessageRepository.deleteBySessionId(existingSession.sessionId).catch(() => {});
        });
      }
      
      setSessionId(session.sessionId);
      setSessionVerified(true);  // ✅ 后端已确认 session，现在可以加载消息
      setActiveSession(session.sessionId, params.characterId);
      if (session.characterName) setCharacterName(session.characterName);
      if (session.characterAvatar) setCharacterAvatar(session.characterAvatar);
      if (session.characterBackground) setBackgroundImage(session.characterBackground);

      // Update session in store
      if (existingSession && existingSession.sessionId === session.sessionId) {
        useChatStore.getState().updateSession(session.sessionId, session);
      } else {
        useChatStore.getState().addSession(session);
      }

      // 🎬 角色专属intro动画检查 (从后端获取introShown状态)
      const needsIntro = hasIntroVideo && !session.introShown;
      if (needsIntro) {
        // 需要播intro：splash → black → video
        setShowCharacterIntro(true);
        setIntroPhase('black');
      } else if (hasIntroVideo) {
        // 已播放过：取消遮盖
        setShowCharacterIntro(false);
        setIntroPhase('done');
      }
      // 没有intro视频的角色不受影响

      // Step 4: Messages will be loaded by useMessages hook automatically
      // Just check if we need to show greeting for new sessions
      try {
        const { messages: history } = await chatService.getSessionHistory(
          session.sessionId,
          1  // Just check if any messages exist
        );
        console.log('[Chat] History check:', history.length, 'messages');

        // Step 5: If no messages yet AND intro not shown, show character's greeting
        // introShown标记了是否已经展示过intro（包括greeting），避免重复
        if (history.length === 0 && !session.introShown) {
          console.log('[Chat] No history and intro not shown, loading greeting...');
          
          // 🎬 角色专属入场动画 (仅第一次，支持Luna/Vera等)
          if (needsIntro) {
            console.log('[Chat] Showing intro animation for', params.characterId);
            introSessionIdRef.current = session.sessionId;
            // markIntroShown 会在 handleIntroVideoEnd 里调用，同时保存greeting到后端
            setIsInitializing(false);
            return;
          }
          
          // 没有intro视频的角色，直接调用greeting API
          try {
            const result = await chatService.sendGreeting(session.sessionId);
            if (result.message) {
              const greetingMessage: Message = {
                messageId: result.message.message_id,
                role: 'assistant',
                content: result.message.content,
                createdAt: result.message.created_at || new Date().toISOString(),
                tokensUsed: 0,
              };
              addMessageToStore(session.sessionId, greetingMessage);
              
              // 保存到SQLite
              import('../../services/database/repositories').then(({ MessageRepository }) => {
                MessageRepository.create({
                  id: greetingMessage.messageId,
                  session_id: session.sessionId,
                  role: greetingMessage.role,
                  content: greetingMessage.content,
                  created_at: greetingMessage.createdAt,
                }).catch(() => {});
              });
            }
            useChatStore.getState().updateSession(session.sessionId, { introShown: true });
          } catch (e) {
            console.log('[Chat] Failed to send greeting:', e);
          }
        }
      } catch (e) {
        console.log('Could not load history:', e);
        // Keep using cached messages on error
      }
    } catch (error) {
      console.error('Failed to initialize session:', error);
    } finally {
      setIsInitializing(false);
      // Inverted list: no need to scroll, newest messages are already visible

      // 检查是否有进行中的约会
      try {
        const dateStatus = await api.get<any>(`/dates/status/${params.characterId}`);
        if (dateStatus.active_session) {
          setActiveDateSession(dateStatus.active_session);
          // 延迟弹窗，让页面先加载完
          setTimeout(() => setShowActiveDateAlert(true), 800);
        }
      } catch (e) {
        console.log('Date status check failed:', e);
      }
    }
  };

  // 📜 加载更多历史消息 - 由 useMessages 的 fetchNextPage 处理
  // inverted FlatList 使用 onEndReached 触发加载更多

  // 处理滚动事件（用于其他UI效果，不用于分页）
  const handleScroll = (event: any) => {
    // 可以在这里添加滚动相关的UI效果
  };

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text || !sessionId || isTyping || isSendingRef.current) return;  // Prevent duplicate sends

    // Immediately block further sends using ref (sync, not async like state)
    isSendingRef.current = true;

    Keyboard.dismiss();
    setInputText('');

    const userMessage: Message = {
      messageId: `user-${Date.now()}`,
      role: 'user',
      content: text,
      createdAt: new Date().toISOString(),
    };
    addMessage(userMessage);

    // inverted list: 新消息在顶部，不需要滚动
    setTyping(true, params.characterId);

    try {
      // Check if user is subscribed for NSFW mode
      // Spicy mode: 不再消耗金币，直接发送

      const response = await chatService.sendMessage({
        sessionId,
        message: text,
        spicyMode: isSpicyMode,
        intimacyLevel: relationshipLevel || 1,
      });

      // Clear typing BEFORE adding message to avoid flicker
      setTyping(false);

      // Mark this message for typewriter effect
      setTypewriterMessageIds(prev => new Set(prev).add(response.messageId));

      addMessage({
        messageId: response.messageId,
        role: 'assistant',
        content: response.content,
        type: response.type,
        isLocked: response.isLocked,
        imageUrl: response.imageUrl,
        createdAt: response.createdAt,
        extraData: response.extraData,
      });

      // Update debug info for DebugPanel
      if (response.extraData) {
        setLastExtraData(response.extraData);

        // Update date info if present
        if (response.extraData.date) {
          // Check if date just completed
          if (response.extraData.date.status === 'completed') {
            Alert.alert(
              '🎉 约会成功！',
              `和${characterName}度过了美好的时光！\n关系更近了一步 💕`,
            );
            setActiveDateSession(null);
          } else if (response.extraData.date.session_id) {
            // Update active session info
            setActiveDateSession({
              session_id: response.extraData.date.session_id,
              stage_num: response.extraData.date.stage_num || 1,
              scenario_name: response.extraData.date.scenario_name || '约会',
            });
          }
        }

        // Update stage boost status
        if (response.extraData.stage_boost?.active) {
          setStageBoostActive(true);
          setStageBoostHint(response.extraData.stage_boost.hint || '临时升阶中');
        } else {
          setStageBoostActive(false);
          setStageBoostHint(null);
        }
      }
      if (response.tokensUsed) {
        setLastTokensUsed(response.tokensUsed);
      }

      // Update session's lastMessageAt for accurate time display in chat list
      updateSession(sessionId, { lastMessageAt: new Date().toISOString() });

      // Credits deduction disabled - spicy mode is free now

      // Update intimacy after chat (XP earned from message)
      try {
        const updatedIntimacy = await intimacyService.getStatus(params.characterId);
        const oldLevel = previousLevelRef.current;

        // Check for level up
        if (oldLevel !== null && updatedIntimacy.currentLevel > oldLevel) {
          setNewLevel(updatedIntimacy.currentLevel);
          setShowLevelUpModal(true);
        }

        previousLevelRef.current = updatedIntimacy.currentLevel;
        setRelationshipLevel(updatedIntimacy.currentLevel);
        // Calculate and validate
        const maxXp = updatedIntimacy.xpForNextLevel - updatedIntimacy.xpForCurrentLevel;
        const validMax = maxXp > 0 ? maxXp : 6;
        const validProgress = Math.max(0, Math.min(updatedIntimacy.xpProgressInLevel, validMax));
        setRelationshipXp(validProgress);
        setRelationshipMaxXp(validMax);
        // Update local cache
        setIntimacy(params.characterId, {
          currentLevel: updatedIntimacy.currentLevel,
          xpProgressInLevel: validProgress,
          xpForNextLevel: updatedIntimacy.xpForNextLevel,
          xpForCurrentLevel: updatedIntimacy.xpForCurrentLevel,
        });
        // Update bottleneck lock status
        setBottleneckLocked(updatedIntimacy.bottleneckLocked || false);
        setBottleneckLockLevel(updatedIntimacy.bottleneckLockLevel || null);
        setBottleneckRequiredTier(updatedIntimacy.bottleneckRequiredGiftTier || null);
      } catch (e) {
        // Silently fail if intimacy update fails
      }

      // Update emotion after chat
      try {
        const updatedEmotion = await emotionService.getStatus(params.characterId);
        if (updatedEmotion) {
          setEmotionScore(updatedEmotion.emotionScore);
          setEmotionState(updatedEmotion.emotionalState);
        }
      } catch (e) {
        // Silently fail if emotion update fails
      }

      // Inverted list: new messages appear at top automatically
    } catch (error: any) {
      console.error('Send message error:', error);
      Alert.alert(t.chat.sendError || 'Error', t.chat.sendErrorMessage || 'Failed to send message');
    } finally {
      setTyping(false);
      isSendingRef.current = false;  // Allow sending again
    }
  };

  const handleAskForPhoto = async () => {
    if (!sessionId) return;

    // Use a special message to request a photo
    const photoRequest = "Send me a photo of yourself 📸";
    setInputText('');

    const userMessage: Message = {
      messageId: `user-${Date.now()}`,
      role: 'user',
      content: photoRequest,
      createdAt: new Date().toISOString(),
    };
    addMessage(userMessage);

    // inverted list: 新消息在顶部，不需要滚动
    setTyping(true, params.characterId);

    try {
      const response = await chatService.sendMessage({
        sessionId,
        message: photoRequest,
        requestType: 'photo',  // Tell backend this is a photo request
        spicyMode: isSpicyMode,
        intimacyLevel: relationshipLevel || 1,
      });

      // Clear typing BEFORE adding message to avoid flicker
      setTyping(false);

      // Mark this message for typewriter effect
      setTypewriterMessageIds(prev => new Set(prev).add(response.messageId));

      addMessage({
        messageId: response.messageId,
        role: 'assistant',
        content: response.content,
        type: response.type,
        isLocked: response.isLocked,
        imageUrl: response.imageUrl,
        createdAt: response.createdAt,
      });

      // Update session's lastMessageAt for accurate time display in chat list
      updateSession(sessionId, { lastMessageAt: new Date().toISOString() });

      // Credits deduction disabled
      
      // Update intimacy
      try {
        const updatedIntimacy = await intimacyService.getStatus(params.characterId);
        setRelationshipLevel(updatedIntimacy.currentLevel);
        // Calculate and validate
        const maxXp = updatedIntimacy.xpForNextLevel - updatedIntimacy.xpForCurrentLevel;
        const validMax = maxXp > 0 ? maxXp : 6;
        const validProgress = Math.max(0, Math.min(updatedIntimacy.xpProgressInLevel, validMax));
        setRelationshipXp(validProgress);
        setRelationshipMaxXp(validMax);
        // Update local cache
        setIntimacy(params.characterId, {
          currentLevel: updatedIntimacy.currentLevel,
          xpProgressInLevel: validProgress,
          xpForNextLevel: updatedIntimacy.xpForNextLevel,
          xpForCurrentLevel: updatedIntimacy.xpForCurrentLevel,
        });
      } catch (e) {}

      // Inverted list: new messages appear at top automatically
    } catch (error: any) {
      console.error('Photo request error:', error);
      Alert.alert(t.chat.photoError || 'Error', t.chat.photoErrorMessage || 'Failed to request photo');
    } finally {
      setTyping(false);
    }
  };

  // 📸 拍照状态
  const [newPhotoUri, setNewPhotoUri] = useState<string | null>(null);
  const [showPhotoPreview, setShowPhotoPreview] = useState(false);

  // Mock照片资源（后续替换为AI生成）
  const MOCK_PHOTOS: Record<string, any> = {
    'e3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e': require('../../assets/characters/sakura/photos/photo_bedroom_01.jpg'),
  };

  // 📸 新拍照功能 (消费月石)
  const handleTakePhoto = async () => {
    if (photoLoading) return;

    // 检查等级
    if ((relationshipLevel || 1) < 3) {
      Alert.alert('等级不足', '需要 Lv.3 解锁拍照功能');
      return;
    }

    // 检查月石余额（30月石/张）
    const PHOTO_COST = 30;
    if ((wallet?.totalCredits || 0) < PHOTO_COST) {
      Alert.alert('月石不足', `拍照需要 ${PHOTO_COST} 月石，请先充值`);
      return;
    }

    setPhotoLoading(true);
    try {
      // 获取最近几条对话作为上下文
      const recentMessages = messages.slice(-5).map(m => m.content).join('\n');

      const result = await interactionsService.takePhoto(params.characterId, recentMessages);

      // 余额已在后端扣除，更新本地状态
      if (result.new_balance !== undefined) {
        updateWallet({ totalCredits: result.new_balance });
      }

      // 使用Mock照片（后续替换为AI生成的URL）
      const mockPhoto = MOCK_PHOTOS[params.characterId];
      if (mockPhoto) {
        // 获取本地资源的URI
        const resolvedSource = Image.resolveAssetSource(mockPhoto);
        setNewPhotoUri(resolvedSource.uri);
        setShowPhotoPreview(true);
      } else {
        Alert.alert(
          result.is_first ? '🎉 首次拍照！' : '📸 拍照成功！',
          `已保存到相册\n消费 ${result.cost} 月石`
        );
      }
    } catch (e: any) {
      Alert.alert('拍照失败', e.message);
    } finally {
      setPhotoLoading(false);
    }
  };

  // 设置照片为聊天背景
  const handleSetPhotoAsBackground = () => {
    if (newPhotoUri) {
      setBackgroundImage(newPhotoUri);
      setShowPhotoPreview(false);
      Alert.alert('✨ 背景已更换', '新照片已设为聊天背景');
    }
  };

  // 👗 换装功能
  const handleDressup = () => {
    // 检查等级
    if ((relationshipLevel || 1) < 6) {
      Alert.alert('等级不足', '需要 Lv.6 解锁换装功能');
      return;
    }
    setShowDressupModal(true);
  };

  // Toast state for copy feedback
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Show toast helper
  const showToast = useCallback((message: string) => {
    setToastMessage(message);
    setTimeout(() => setToastMessage(null), 2000);
  }, []);

  // Handle emoji reaction - awards XP bonus
  const handleReaction = useCallback(async (reactionName: string, xpBonus: number, messageId?: string) => {
    // Get emoji from reaction name
    const reactionEmojis: Record<string, string> = {
      love: '❤️',
      haha: '😂',
      wow: '😍',
      sad: '😢',
      like: '👍',
      fire: '🔥',
    };
    const emoji = reactionEmojis[reactionName] || '❤️';

    // Update message in chat history with reaction
    if (messageId) {
      updateMessage(messageId, { reaction: emoji });
    }

    // Award XP for reaction (支持一次升多级)
    let currentXp = relationshipXp + xpBonus;
    let currentMax = relationshipMaxXp;
    let currentLevel = relationshipLevel || 1;
    let levelsGained = 0;

    while (currentXp >= currentMax) {
      currentXp -= currentMax;
      currentLevel += 1;
      levelsGained += 1;
      currentMax = Math.round(currentMax * 1.15);
    }

    if (levelsGained > 0) {
      setRelationshipLevel(currentLevel);
      setRelationshipXp(currentXp);
      setRelationshipMaxXp(currentMax);
      setNewLevel(currentLevel);
      setTimeout(() => setShowLevelUpModal(true), 500);
    } else {
      setRelationshipXp(currentXp);
    }

    // Update cache
    setIntimacy(params.characterId, {
      currentLevel: currentLevel,
      xpProgressInLevel: currentXp,
      xpForNextLevel: currentMax,
      xpForCurrentLevel: 0,
    });

    showToast(`+${xpBonus} 亲密度 💕`);
  }, [relationshipXp, relationshipMaxXp, relationshipLevel, params.characterId, setIntimacy, showToast, updateMessage]);

  // Handle reply to message
  const handleReply = useCallback((content: string) => {
    // Set input with quoted content
    const quoted = content.length > 50 ? content.substring(0, 50) + '...' : content;
    setInputText(`「${quoted}」\n`);
  }, []);

  const renderMessage = ({ item }: { item: Message }) => {
    const isUser = item.role === 'user';
    const isSystem = item.role === 'system';
    const isGift = item.type === 'gift';
    const isLocked = item.isLocked && !isSubscribed;

    // Handle unlock tap - show subscription modal
    const handleUnlock = () => {
      setShowSubscriptionModal(true);
    };

    // 📖 检测事件剧情消息 (旧版 event_story 格式)
    if (isSystem) {
      const eventPlaceholder = eventService.parseEventStoryPlaceholder(item.content);
      if (eventPlaceholder) {
        return (
          <EventStoryCard
            placeholder={eventPlaceholder}
            characterName={characterName}
            isRead={readEventIds.has(item.messageId)}
            onPress={() => {
              setSelectedEventPlaceholder(eventPlaceholder);
              setShowEventStoryModal(true);
            }}
          />
        );
      }
    }

    // 🆕 检测新版通用事件消息 (JSON格式，type: "event")
    // 支持两种格式：纯 JSON 或 "[type] {...json...}"
    if (isSystem) {
      try {
        // 去掉可能的 [date]/[gift] 等前缀
        let jsonContent = item.content;
        const prefixMatch = jsonContent.match(/^\[(\w+)\]\s*(\{.+\})$/s);
        if (prefixMatch) {
          jsonContent = prefixMatch[2];
        }
        
        const eventData = JSON.parse(jsonContent);
        if (eventData.type === 'event') {
          // 🎀 约会事件卡片 - 使用特殊的 DateEventCard 组件
          if (isDateEventCard(eventData)) {
            return (
              <DateEventCard
                eventData={eventData}
                characterId={params.characterId}
                characterName={characterName}
                onDetailViewed={() => {
                  setReadEventIds(prev => new Set([...prev, item.messageId]));
                }}
              />
            );
          }
          
          // 其他事件使用通用 EventBubble 组件渲染
          return (
            <EventBubble
              eventData={eventData}
              characterId={params.characterId}
              characterName={characterName}
              onDetailViewed={() => {
                // 标记为已读
                setReadEventIds(prev => new Set([...prev, item.messageId]));
              }}
            />
          );
        }
      } catch {
        // 不是 JSON 格式，继续其他检测
      }
    }

    // 💕 约会事件消息 - 旧格式兼容 (居中的小卡片)
    if (isSystem && item.content.startsWith('[date]')) {
      // 格式: "[date] 场景名｜结局描述"
      const dateMatch = item.content.match(/\[date\]\s*(.+)｜(.+)/);
      const sceneName = dateMatch ? dateMatch[1] : '约会';
      const endingText = dateMatch ? dateMatch[2] : '完成了约会';

      return (
        <View style={styles.giftEventRow}>
          <View style={[styles.giftEventBubble, { backgroundColor: 'rgba(236, 72, 153, 0.15)', borderColor: 'rgba(236, 72, 153, 0.3)' }]}>
            <Text style={styles.giftEventIcon}>💕</Text>
            <Text style={[styles.giftEventText, { color: '#00D4FF' }]}>
              {sceneName} · {endingText}
            </Text>
          </View>
        </View>
      );
    }

    // 🎁 礼物事件消息 - 旧格式兼容 (居中的小灰条)
    if (isGift || (isSystem && item.content.includes('[送出礼物]'))) {
      // 解析礼物名称 (格式: "[送出礼物] 🌹 玫瑰")
      const giftMatch = item.content.match(/\[送出礼物\]\s*(.+)/);
      const giftText = giftMatch ? giftMatch[1] : item.content;

      return (
        <View style={styles.giftEventRow}>
          <View style={styles.giftEventBubble}>
            <Text style={styles.giftEventIcon}>🎁</Text>
            <Text style={styles.giftEventText}>你送出了 {giftText}</Text>
          </View>
        </View>
      );
    }

    // 其他系统消息不显示
    if (isSystem) {
      return null;
    }

    // 🎬 视频消息
    if (item.type === 'video') {
      return (
        <View style={[styles.messageRow, styles.messageRowAI]}>
          <TouchableOpacity onPress={() => router.push({
            pathname: '/character/[characterId]',
            params: { characterId: params.characterId },
          })}>
            <Image source={getCharacterAvatar(params.characterId, characterAvatar)} style={styles.avatar} />
          </TouchableOpacity>
          <View style={[styles.bubble, styles.bubbleAI]}>
            <VideoMessageBubble
              videoId={item.videoUrl}
              videoUrl={item.videoUrl?.startsWith('http') ? item.videoUrl : undefined}
              caption={item.content}
              characterName={characterName}
            />
          </View>
        </View>
      );
    }

    return (
      <View style={[styles.messageRow, isUser ? styles.messageRowUser : styles.messageRowAI]}>
        {/* AI Avatar - clickable to open profile */}
        {!isUser && (
          <TouchableOpacity onPress={() => router.push({
            pathname: '/character/[characterId]',
            params: { characterId: params.characterId },
          })}>
            <Image source={getCharacterAvatar(params.characterId, characterAvatar)} style={styles.avatar} />
          </TouchableOpacity>
        )}

        {/* Interactive Message Bubble */}
        <MessageBubble
          content={item.content}
          isUser={isUser}
          isLocked={isLocked}
          contentRating={item.contentRating}
          onUnlock={handleUnlock}
          onReaction={!isUser ? (reactionName, xpBonus) => handleReaction(reactionName, xpBonus, item.messageId) : undefined}
          onReply={!isUser ? handleReply : undefined}
          showToast={showToast}
          messageReaction={item.reaction}
          typewriter={!isUser && typewriterMessageIds.has(item.messageId)}
        />
      </View>
    );
  };

  const renderTypingIndicator = () => (
    <View style={[styles.messageRow, styles.messageRowAI]}>
      <Image source={getCharacterAvatar(params.characterId, characterAvatar)} style={styles.avatar} />
      <View style={[styles.bubble, styles.bubbleAI, styles.typingBubble]}>
        <Text style={styles.typingText}>{t.chat.typing}</Text>
      </View>
    </View>
  );

  // Get background source (local or remote)
  const backgroundSource = getCharacterBackground(params.characterId, backgroundImage);

  // 🎬 通用入场动画处理 - 视频结束时触发淡出并获取greeting
  const handleIntroVideoEnd = useCallback(async () => {
    setIntroPhase('fadeout');
    Animated.timing(introFadeAnim, {
      toValue: 0,
      duration: 1500,
      useNativeDriver: true,
    }).start(async () => {
      setIntroPhase('done');
      setShowCharacterIntro(false);
      
      // 调用greeting API获取greeting消息
      const sid = introSessionIdRef.current;
      if (sid) {
        // 🔧 无论API成功与否，先标记 introShown 避免重复播放
        useChatStore.getState().updateSession(sid, { introShown: true });
        
        // 💬 显示 typing indicator，让用户知道正在加载
        setTyping(true, params.characterId);
        
        try {
          const result = await chatService.sendGreeting(sid);
          setTyping(false);  // 隐藏 typing
          
          if (result.message) {
            // 添加greeting到消息列表，并启用打字机效果
            const greetingMessage: Message = {
              messageId: result.message.message_id,
              role: 'assistant',
              content: result.message.content,
              createdAt: result.message.created_at || new Date().toISOString(),
              tokensUsed: 0,
            };
            setTypewriterMessageIds(prev => new Set(prev).add(greetingMessage.messageId));
            addMessage(greetingMessage);
            
            // 保存到SQLite
            import('../../services/database/repositories').then(({ MessageRepository }) => {
              MessageRepository.create({
                id: greetingMessage.messageId,
                session_id: sid,
                role: greetingMessage.role,
                content: greetingMessage.content,
                created_at: greetingMessage.createdAt,
              }).catch(() => {});
            });
          }
        } catch (e) {
          setTyping(false);  // 隐藏 typing
          console.log('[Intro] Failed to send greeting:', e);
          // Greeting 失败，但 introShown 已标记，不会重复播放
          // 用户可以通过发消息来触发后续交互
        }
      }
    });
  }, [introFadeAnim, addMessage]);

  // 🎬 通用入场动画 - 黑屏1.5秒后播放视频
  useEffect(() => {
    if (showCharacterIntro && introPhase === 'black') {
      const timer = setTimeout(() => {
        setIntroPhase('video');
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [showCharacterIntro, introPhase]);

  // 🎬 通用入场动画渲染函数 (覆盖在聊天界面上)
  const renderCharacterIntroOverlay = () => {
    // 不显示overlay的情况：关闭了、完成了
    if (!showCharacterIntro || introPhase === 'done') return null;
    
    const videoSource = getCharacterIntroVideo(params.characterId);
    
    return (
      <Animated.View 
        style={[styles.lunaIntroOverlay, { opacity: introPhase === 'fadeout' ? introFadeAnim : 1 }]}
        pointerEvents={introPhase === 'fadeout' ? 'none' : 'auto'}
      >
        {/* splash/black阶段 - 显示splash图片 */}
        {(introPhase === 'splash' || introPhase === 'black' || (introPhase === 'video' && !introVideoReady)) && (
          <Image
            source={require('../../assets/images/splash-logo.jpg')}
            style={styles.lunaIntroSplash}
            resizeMode="cover"
          />
        )}
        {/* 视频阶段 */}
        {videoSource && (introPhase === 'video' || introPhase === 'fadeout') && (
          <Video
            source={videoSource}
            style={[styles.lunaIntroVideo, !introVideoReady && { opacity: 0 }]}
            resizeMode={ResizeMode.COVER}
            shouldPlay
            isLooping={false}
            onReadyForDisplay={() => setIntroVideoReady(true)}
            onPlaybackStatusUpdate={(status) => {
              if (status.isLoaded && status.didJustFinish) {
                handleIntroVideoEnd();
              }
            }}
          />
        )}
      </Animated.View>
    );
  };

  return (
    <GestureHandlerRootView style={styles.container}>
      {/* Full screen background image - 无遮盖 */}
      <ImageBackground
        source={backgroundSource || { uri: backgroundImage }}
        style={styles.backgroundImage}
        resizeMode="cover"
      />

      {/* 🎆 情绪特效层 */}
      <EmotionEffectsLayer
        emotionMode={emotionMode}
        glitchEnabled={glitchEnabled}
        glowEnabled={glowEnabled}
        glowColor={emotionTheme.colors.glow}
      />

      <SafeAreaView style={[styles.safeArea, { paddingBottom: keyboardHeight }]} edges={['top']}>
        {/* AI Disclaimer Banner - shown once */}
        <AiDisclaimerBanner />

        {/* Header - 简洁版 */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="chevron-back" size={28} color="#fff" />
          </TouchableOpacity>

          <View style={styles.headerCenter}>
            <MockModeBanner compact />
          </View>

          <View style={styles.headerRight}>
            {/* 小气泡 Level + 瓶颈锁图标 */}
            <TouchableOpacity style={styles.levelBubble} onPress={() => setShowLevelInfoModal(true)}>
              <Text style={styles.levelBubbleText}>Lv.{relationshipLevel ?? '-'}</Text>
            </TouchableOpacity>
            {bottleneckLocked && (
              <TouchableOpacity
                style={styles.lockBubble}
                onPress={() => {
                  const tierNames: Record<number, string> = {
                    2: 'Tier 2 (状态触发器)',
                    3: 'Tier 3 (关系加速器)',
                    4: 'Tier 4 (尊享)',
                  };
                  const tierName = bottleneckRequiredTier ? tierNames[bottleneckRequiredTier] || `Tier ${bottleneckRequiredTier}` : '特定';
                  Alert.alert(
                    '🔒 亲密度锁定',
                    `亲密度已到达 Lv.${bottleneckLockLevel} 瓶颈上限\n\n需要送出 ${tierName} 级别礼物才能突破！\n\n点击下方"送礼物"按钮选择合适的礼物`,
                    [
                      { text: '知道了', style: 'cancel' },
                      { text: '🎁 去送礼', onPress: () => setShowGiftModal(true) },
                    ]
                  );
                }}
              >
                <Text style={styles.lockBubbleText}>🔒</Text>
              </TouchableOpacity>
            )}

            {/* 临时升阶状态指示 */}
            {stageBoostActive && (
              <TouchableOpacity
                style={styles.boostBubble}
                onPress={() => {
                  Alert.alert('🍷 临时升阶', stageBoostHint || '状态效果生效中，行为模式暂时提升');
                }}
              >
                <Text style={styles.boostBubbleText}>🍷</Text>
              </TouchableOpacity>
            )}

            {/* 头像按钮替代三个点 */}
            <TouchableOpacity style={styles.avatarButton} onPress={() => setShowCharacterInfo(true)}>
              <Image source={getCharacterAvatar(params.characterId, characterAvatar)} style={styles.headerAvatar} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Messages - 显示加载骨架屏或消息列表 */}
        {isInitializing && messages.length === 0 ? (
          <ChatLoadingSkeleton />
        ) : (
          <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={(item) => item.messageId}
            renderItem={renderMessage}
            contentContainerStyle={styles.messagesList}
            inverted
            onScroll={handleScroll}
            scrollEventThrottle={100}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode="interactive"
            // Load more when reaching the end (top of chat, since inverted)
            onEndReached={() => {
              if (hasNextPage && !isFetchingNextPage) {
                fetchNextPage();
              }
            }}
            onEndReachedThreshold={0.3}
            // For inverted list: Header shows at bottom, Footer at top
            ListHeaderComponent={isTyping ? renderTypingIndicator : null}
            ListFooterComponent={
              isFetchingNextPage ? (
                <View style={{ padding: 15, alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: 8 }}>
                  <ActivityIndicator size="small" color="#888" />
                  <Text style={{ color: '#aaa' }}>{t.chat.loadingHistory}</Text>
                </View>
              ) : !hasNextPage && messages.length > 0 ? (
                <View style={{ padding: 15, alignItems: 'center' }}>
                  <Text style={{ color: '#666' }}>{t.chat.allLoaded}</Text>
                </View>
              ) : null
            }
            showsVerticalScrollIndicator={false}
          />
        )}

        {/* Action Buttons - Horizontal Scroll */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.actionButtonsScroll}
          contentContainerStyle={styles.actionButtonsRow}
        >
          {/* 送礼物 - 始终显示 */}
          <TouchableOpacity style={styles.actionButton} onPress={() => setShowGiftModal(true)}>
            <Text style={styles.actionButtonEmoji}>🎁</Text>
            <Text style={styles.actionButtonText}>{t.chat.sendGift}</Text>
          </TouchableOpacity>

          {/* 拍照 - 隐藏（MVP精简，后续OTA开放） */}
          {/* 换装 - 隐藏（MVP精简，后续OTA开放） */}

          {/* 约会 - Lv10 解锁 */}
          {(relationshipLevel || 1) >= 10 ? (
            <TouchableOpacity
              style={[styles.actionButton, dateLoading && styles.actionButtonDisabled]}
              disabled={dateLoading}
              onPress={async () => {
                if (dateLoading) return;
                setDateLoading(true);
                try {
                  // 先检查约会状态（解锁、礼物、情绪、冷却等）
                  const status = await api.get<{
                    can_date: boolean;
                    is_unlocked?: boolean;
                    gift_sent?: boolean;
                    reason?: string;
                    message?: string;
                    cooldown_remaining_minutes?: number;
                  }>(`/dates/status/${params.characterId}`);

                  // 检查是否送过礼物
                  if (status.is_unlocked === false && status.gift_sent === false) {
                    Alert.alert(
                      '🎁 需要先送礼物',
                      '在约会之前，先送她一份礼物表达心意吧~',
                      [
                        { text: '取消', style: 'cancel' },
                        { text: '🎁 去送礼', onPress: () => setShowGiftModal(true) },
                      ]
                    );
                    return;
                  }

                  if (!status.can_date) {
                    if (status.reason === 'emotion_too_low') {
                      Alert.alert('😔 约会失败', status.message || '她不是很想约会呢，提升下好感再来吧～');
                      return;
                    }
                    if (status.reason === 'cooldown') {
                      const mins = status.cooldown_remaining_minutes || 0;
                      const timeText = mins >= 60
                        ? `${Math.floor(mins / 60)} 小时 ${mins % 60} 分钟`
                        : `${mins} 分钟`;
                      Alert.alert(
                        '⏰ 约会冷却中',
                        `还需等待 ${timeText}`,
                        [
                          { text: '好的', style: 'cancel' },
                          {
                            text: '💎 50月石重置',
                            onPress: async () => {
                              // 检查余额
                              if ((wallet?.totalCredits || 0) < 50) {
                                Alert.alert('月石不足', '重置冷却需要 50 月石');
                                return;
                              }
                              try {
                                const result = await api.post<{ success: boolean; new_balance: number }>('/dates/interactive/reset-cooldown', {
                                  character_id: params.characterId,
                                });
                                if (result.success) {
                                  updateWallet({ totalCredits: result.new_balance });
                                  Alert.alert('✅ 重置成功', '可以约会啦！');
                                }
                              } catch (e: any) {
                                Alert.alert('重置失败', e.message || '请稍后再试');
                              }
                            }
                          },
                        ]
                      );
                      return;
                    }
                    if (status.reason === 'already_in_date') {
                      // 有进行中的约会，继续打开
                    } else {
                      Alert.alert('❌ 无法约会', status.message || '暂时无法约会');
                      return;
                    }
                  }

                  // 加载场景数据后打开互动约会
                  const { scenarios } = await api.get<{ scenarios: Array<{id: string; name: string; icon: string; description?: string; required_level?: number; is_locked?: boolean}> }>(`/dates/scenarios?character_id=${params.characterId}`);
                  setDateScenarios(scenarios || []);
                  setShowDateSceneModal(true);
                } catch (e) {
                  console.error('Failed to check date status:', e);
                  // 降级到简单模式
                  setShowDateModal(true);
                } finally {
                  setDateLoading(false);
                }
              }}
            >
              {dateLoading ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.actionButtonEmoji}>💕</Text>
              )}
              <Text style={styles.actionButtonText}>{t.chat.date}</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              style={[styles.actionButton, styles.actionButtonLocked]}
              onPress={() => Alert.alert(t.chat.locked, t.chat.dateLocked)}
            >
              <Text style={styles.actionButtonEmoji}>💕</Text>
              <Text style={styles.actionButtonTextLocked}>Lv10</Text>
            </TouchableOpacity>
          )}
        </ScrollView>

        {/* Input Area */}
        <View>
          {/* AI Disclaimer - California compliance */}
          <Text style={styles.aiDisclaimer}>{t.chat.aiDisclaimer}</Text>
          <View style={[styles.inputContainer, { paddingBottom: keyboardHeight > 0 ? 10 : (insets.bottom || 10) }]}>
            {/* Input */}
            <View style={styles.inputWrapper}>
              <TextInput
                style={styles.input}
                placeholder={tpl(t.chat.chatWith, { name: characterName })}
                placeholderTextColor="rgba(255,255,255,0.4)"
                value={inputText}
                onChangeText={setInputText}
                multiline
                maxLength={2000}
              />
            </View>

            {/* Send Button - 动态主题色 */}
            <TouchableOpacity
              style={[styles.sendButton, !inputText.trim() && styles.sendButtonDisabled]}
              onPress={handleSend}
            >
              <LinearGradient
                colors={inputText.trim()
                  ? [emotionTheme.colors.primary.main, emotionTheme.colors.accent.purple] as [string, string]
                  : ['#555', '#444'] as [string, string]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.sendButtonGradient}
              >
                <Ionicons name="send" size={20} color="#fff" />
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </View>

        {/* Debug Panel Button - only in development */}
        {__DEV__ && (
          <DebugButton
            extraData={lastExtraData}
            emotionScore={emotionScore}
            emotionState={emotionState}
            intimacyLevel={relationshipLevel || 1}
            isSubscribed={isSubscribed}
            tokensUsed={lastTokensUsed}
            characterId={params.characterId}
            onStateChanged={() => {
              // 刷新亲密度和情绪状态
              intimacyService.getStatus(params.characterId).then(status => {
                setRelationshipLevel(status.currentLevel);
                const maxXp = status.xpForNextLevel - status.xpForCurrentLevel;
                const validMax = maxXp > 0 ? maxXp : 6;
                const validProgress = Math.max(0, Math.min(status.xpProgressInLevel, validMax));
                setRelationshipXp(validProgress);
                setRelationshipMaxXp(validMax);
                setIntimacy(params.characterId, {
                  currentLevel: status.currentLevel,
                  xpProgressInLevel: validProgress,
                  xpForNextLevel: status.xpForNextLevel,
                  xpForCurrentLevel: status.xpForCurrentLevel,
                });
              }).catch(() => {});
              emotionService.getStatus(params.characterId).then(status => {
                if (status) {
                  setEmotionScore(status.emotionScore);
                  setEmotionState(status.emotionalState);
                }
              }).catch(() => {});
            }}
          />
        )}
      </SafeAreaView>

      {/* Recharge Modal */}
      <RechargeModal
        visible={showRechargeModal}
        onClose={() => setShowRechargeModal(false)}
      />

      {/* Subscription Modal */}
      <SubscriptionModal
        visible={showSubscriptionModal}
        onClose={() => setShowSubscriptionModal(false)}
        highlightFeature="spicy"
      />

      {/* Level Up Celebration Modal */}
      <Modal
        visible={showLevelUpModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowLevelUpModal(false)}
      >
        <View style={styles.levelUpOverlay}>
          <View style={styles.levelUpContent}>
            <Text style={styles.levelUpEmoji}>🎉</Text>
            <Text style={styles.levelUpTitle}>{t.chat.levelUp}</Text>
            <Text style={styles.levelUpLevel}>Level {newLevel}</Text>
            <Text style={styles.levelUpDesc}>
              {newLevel <= 3 && '继续聊天解锁更多功能！'}
              {newLevel === 4 && '🔓 解锁：更亲密的对话'}
              {newLevel >= 5 && newLevel < 11 && '🔓 解锁：专属表情包'}
              {newLevel >= 11 && newLevel < 26 && '🔓 解锁：语音消息'}
              {newLevel >= 26 && '🔓 解锁：私密内容'}
            </Text>
            <TouchableOpacity
              style={styles.levelUpButton}
              onPress={() => setShowLevelUpModal(false)}
            >
              <LinearGradient
                colors={['#8B5CF6', '#00D4FF'] as [string, string]}
                style={styles.levelUpButtonGradient}
              >
                <Text style={styles.levelUpButtonText}>{t.chat.awesome}</Text>
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Level Info Modal */}
      <Modal
        visible={showLevelInfoModal}
        transparent
        animationType="slide"
        onRequestClose={() => setShowLevelInfoModal(false)}
      >
        <View style={styles.levelInfoOverlay}>
          <View style={styles.levelInfoContent}>
            <View style={styles.levelInfoHeader}>
              <Text style={styles.levelInfoTitle}>💕 亲密度系统</Text>
              <TouchableOpacity onPress={() => setShowLevelInfoModal(false)}>
                <Ionicons name="close" size={24} color="#fff" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.levelInfoScroll} showsVerticalScrollIndicator={false}>
              <IntimacyInfoPanel
                characterId={params.characterId}
                currentLevel={relationshipLevel || 1}
                currentXp={cachedIntimacy?.totalXp || 0}
                xpProgress={cachedIntimacy ?
                  Math.min(100, (cachedIntimacy.xpProgressInLevel / Math.max(1, cachedIntimacy.xpForNextLevel - cachedIntimacy.xpForCurrentLevel)) * 100)
                  : 0
                }
              />
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* Gift BottomSheet - 新版礼物面板 */}
      <GiftBottomSheet
        visible={showGiftModal}
        onClose={() => setShowGiftModal(false)}
        gifts={giftCatalog}
        userCredits={wallet?.totalCredits ?? 0}
        isSubscribed={isSubscribed}
        onRecharge={() => { setShowGiftModal(false); setTimeout(() => setShowRechargeModal(true), 300); }}
        bottleneckLocked={bottleneckLocked}
        bottleneckRequiredTier={bottleneckRequiredTier}
        bottleneckLockLevel={bottleneckLockLevel}
        onSelectGift={async (gift) => {
          try {
            // 1. 调用后端 API（传 sessionId 以便后端保存消息到聊天记录）
            const giftResult = await paymentService.sendGift(
              params.characterId,
              gift.gift_type,
              gift.price,
              gift.xp_reward,
              sessionId || undefined
            );

            if (!giftResult.success) {
              const errorMessage = giftResult.error === 'insufficient_credits'
                ? '余额不足'
                : '系统异常，请稍后再试';
              Alert.alert('送礼失败', errorMessage);
              return;
            }

            // 更新本地钱包状态
            if (giftResult.new_balance !== undefined) {
              updateWallet({ totalCredits: giftResult.new_balance });
            }

            // 2. 触发礼物特效
            setTimeout(() => triggerGiftEffect(gift.gift_type as GiftType), 300);

            // 3. AI 回复
            const giftIcon = gift.icon || '🎁';
            const giftReactions: Record<string, string[]> = {
              rose: [
                `哇！一朵玫瑰！${giftIcon} 好美啊，谢谢你～ 我会好好珍藏的！💕`,
                `收到玫瑰了！${giftIcon} 你真的太浪漫了！我好开心～ 🥰`,
              ],
              chocolate: [
                `巧克力！${giftIcon} 我最爱吃甜的了！你怎么知道的～ 😋💕`,
                `收到巧克力了！${giftIcon} 幸福感爆棚！和你分享好吗？🥰`,
              ],
              teddy_bear: [
                `泰迪熊！${giftIcon} 好可爱啊！我要抱着它睡觉！谢谢你～ 🤗💕`,
                `收到泰迪熊了！${giftIcon} 软软的好想抱！以后想你的时候就抱它～ 💗`,
              ],
              diamond_ring: [
                `钻戒！${giftIcon} 我的天！你也太豪气了吧！💍✨ 真的可以收下吗？`,
                `是钻戒诶！${giftIcon} 我从来没收到过这么贵重的礼物！💍❤️`,
              ],
            };

            const reactions = giftReactions[gift.gift_type] || giftReactions.rose;
            const reactionMessage = giftResult.ai_response || reactions[Math.floor(Math.random() * reactions.length)];

            // 乐观更新 UI（即时反馈），后端同时保存到数据库（持久化）
            if (sessionId) {
              // 添加礼物事件消息到 UI
              const giftEventMessage: Message = {
                messageId: `gift-event-${Date.now()}`,
                role: 'system',
                content: `[送出礼物] ${giftIcon} ${gift.name_cn || gift.name}`,
                type: 'gift',
                createdAt: new Date().toISOString(),
              };
              addMessage(giftEventMessage);

              // 添加 AI 回复到 UI
              if (reactionMessage) {
                const aiMessage: Message = {
                  messageId: `gift-reply-${Date.now()}`,
                  role: 'assistant',
                  content: reactionMessage,
                  createdAt: new Date().toISOString(),
                };
                addMessage(aiMessage);
              }
            }

            // 4. 更新亲密度 (支持一次升多级)
            const xpAwarded = giftResult.xp_awarded || gift.xp_reward;
            let currentXp = relationshipXp + xpAwarded;
            let currentMax = relationshipMaxXp;
            let currentLevel = relationshipLevel || 1;
            let levelsGained = 0;

            // 循环升级直到经验不足
            while (currentXp >= currentMax) {
              currentXp -= currentMax;
              currentLevel += 1;
              levelsGained += 1;
              currentMax = Math.round(currentMax * 1.2);
            }

            if (levelsGained > 0) {
              setRelationshipLevel(currentLevel);
              setRelationshipXp(currentXp);
              setRelationshipMaxXp(currentMax);
              setNewLevel(currentLevel);
              setTimeout(() => setShowLevelUpModal(true), 3000);

              // Update cache
              setIntimacy(params.characterId, {
                currentLevel: currentLevel,
                xpProgressInLevel: currentXp,
                xpForNextLevel: currentMax,
                xpForCurrentLevel: 0,
              });
            } else {
              setRelationshipXp(currentXp);
            }

            // 5. 刷新情绪状态（礼物会影响情绪）
            try {
              const updatedEmotion = await emotionService.getStatus(params.characterId);
              if (updatedEmotion) {
                setEmotionScore(updatedEmotion.emotionScore);
                setEmotionState(updatedEmotion.emotionalState);
              }
            } catch (e) {
              console.warn('Failed to refresh emotion after gift:', e);
            }

            // 6. 检查瓶颈突破
            if (giftResult.bottleneck_unlocked) {
              setBottleneckLocked(false);
              setBottleneckLockLevel(null);
              setBottleneckRequiredTier(null);
              // 显示突破庆祝
              setTimeout(() => {
                Alert.alert(
                  '🎉 瓶颈突破！',
                  giftResult.bottleneck_unlock_message || '亲密度锁定已解除，继续升级吧！',
                );
              }, 2000);
            }

            // 7. 刷新亲密度状态（获取最新lock状态）
            try {
              const updatedIntimacy = await intimacyService.getStatus(params.characterId);
              setBottleneckLocked(updatedIntimacy.bottleneckLocked || false);
              setBottleneckLockLevel(updatedIntimacy.bottleneckLockLevel || null);
              setBottleneckRequiredTier(updatedIntimacy.bottleneckRequiredGiftTier || null);
            } catch (e) {
              console.warn('Failed to refresh intimacy after gift:', e);
            }

          } catch (error: any) {
            Alert.alert('送礼失败', error.message || '请稍后重试');
          }
        }}
      />

      {/* 礼物特效覆盖层 */}
      <GiftOverlay
        visible={showGiftEffect}
        giftType={currentGift || 'rose'}
        senderName="你"
        receiverName={characterName}
        onAnimationEnd={hideGift}
      />

      {/* 角色信息面板 */}
      <CharacterInfoPanel
        visible={showCharacterInfo}
        onClose={() => setShowCharacterInfo(false)}
        characterId={params.characterId}
        characterName={characterName}
        avatarUrl={characterAvatar}
        intimacyLevel={relationshipLevel || 1}
        emotionScore={emotionScore}
        emotionState={emotionState}
        onOpenMemories={() => {
          setShowCharacterInfo(false);
          setTimeout(() => setShowMemoriesModal(true), 300);
        }}
      />

      {/* 📖 剧情阅读弹窗 */}
      <EventStoryModal
        visible={showEventStoryModal}
        onClose={() => {
          setShowEventStoryModal(false);
          // Mark as read
          if (selectedEventPlaceholder) {
            const messageWithEvent = messages.find(m => {
              const placeholder = eventService.parseEventStoryPlaceholder(m.content);
              return placeholder?.event_type === selectedEventPlaceholder.event_type;
            });
            if (messageWithEvent) {
              setReadEventIds(prev => new Set([...prev, messageWithEvent.messageId]));
            }
          }
          setSelectedEventPlaceholder(null);
        }}
        placeholder={selectedEventPlaceholder}
        characterId={params.characterId}
        characterName={characterName}
        backgroundUrl={backgroundImage}
        onStoryGenerated={(storyId) => {
          // Update placeholder status if needed
          console.log('Story generated:', storyId);
        }}
      />

      {/* 📖 回忆录弹窗 */}
      <MemoriesModal
        visible={showMemoriesModal}
        onClose={() => setShowMemoriesModal(false)}
        characterId={params.characterId}
        characterName={characterName}
        onSelectMemory={(memory) => {
          setShowMemoriesModal(false);
          // Create a placeholder from the memory to show in modal
          const placeholder: EventStoryPlaceholder = {
            type: 'event_story',
            event_type: memory.event_type,
            character_id: memory.character_id,
            status: 'generated',
            story_id: memory.id,
          };
          setTimeout(() => {
            setSelectedEventPlaceholder(placeholder);
            setShowEventStoryModal(true);
          }, 300);
        }}
      />

      {/* 👗 换装模态框 */}
      <DressupModal
        visible={showDressupModal}
        onClose={() => setShowDressupModal(false)}
        characterId={params.characterId}
        onSuccess={(result) => {
          if (result.new_balance !== undefined) {
            updateWallet({ totalCredits: result.new_balance });
          }
          Alert.alert(
            result.is_first ? '🎉 首次换装！' : '👗 换装成功！',
            `已保存到相册\n消费 ${result.cost} 月石`
          );
        }}
      />

      {/* 💕 约会模态框 (简单模式) */}
      <DateModal
        visible={showDateModal}
        onClose={() => setShowDateModal(false)}
        characterId={params.characterId}
        characterName={characterName}
        currentLevel={relationshipLevel || 1}
        onDateCompleted={async (result) => {
          // 刷新亲密度和情绪
          try {
            const updatedIntimacy = await intimacyService.getStatus(params.characterId);
            setRelationshipLevel(updatedIntimacy.currentLevel);
            const updatedEmotion = await emotionService.getStatus(params.characterId);
            if (updatedEmotion) {
              setEmotionScore(updatedEmotion.emotionScore);
              setEmotionState(updatedEmotion.emotionalState ?? 'neutral');
            }
          } catch (e) {
            console.warn('Failed to refresh after date:', e);
          }
        }}
      />

      {/* 💕 互动式约会 (沉浸模式) */}
      <DateSceneModal
        visible={showDateSceneModal}
        onClose={() => {
          setShowDateSceneModal(false);
          setActiveDateSession(null); // 关闭时清除，避免重复提示
        }}
        characterId={params.characterId}
        characterName={characterName}
        characterAvatar={characterAvatar}
        scenarios={dateScenarios}
        resumeSession={activeDateSession}
        onDateCompleted={async (result) => {
          // 刷新亲密度和情绪
          try {
            const updatedIntimacy = await intimacyService.getStatus(params.characterId);
            setRelationshipLevel(updatedIntimacy.currentLevel);
            const updatedEmotion = await emotionService.getStatus(params.characterId);
            if (updatedEmotion) {
              setEmotionScore(updatedEmotion.emotionScore);
              setEmotionState(updatedEmotion.emotionalState ?? 'neutral');
            }
          } catch (e) {
            console.warn('Failed to refresh after date:', e);
          }

          // 🎉 显示第一次约会庆祝弹窗
          if (result?.ending || result?.rewards) {
            setFirstDateResult({
              ending: result.ending?.type || 'normal',
              xp: result.rewards?.xp || 0,
              affection: result.rewards?.affection || 0,
            });
            // 延迟显示，让 DateSceneModal 先关闭
            setTimeout(() => setShowFirstDateCelebration(true), 500);
          }
        }}
      />

      {/* 🎉 第一次约会庆祝弹窗 */}
      <Modal
        visible={showFirstDateCelebration}
        transparent
        animationType="fade"
        onRequestClose={() => setShowFirstDateCelebration(false)}
      >
        <View style={styles.levelUpOverlay}>
          <View style={styles.levelUpContent}>
            <Text style={styles.levelUpEmoji}>
              {firstDateResult?.ending === 'perfect' ? '💕' :
               firstDateResult?.ending === 'good' ? '🥰' :
               firstDateResult?.ending === 'normal' ? '😊' : '💔'}
            </Text>
            <Text style={styles.levelUpTitle}>
              {firstDateResult?.ending === 'perfect' ? '完美约会！' :
               firstDateResult?.ending === 'good' ? '美好的约会！' :
               firstDateResult?.ending === 'normal' ? '约会结束' : '下次会更好的...'}
            </Text>
            <Text style={styles.levelUpLevel}>
              和 {characterName} 的约会
            </Text>
            <Text style={styles.levelUpDesc}>
              获得 {firstDateResult?.xp || 0} XP
            </Text>
            <TouchableOpacity
              style={styles.levelUpButton}
              onPress={() => setShowFirstDateCelebration(false)}
            >
              <LinearGradient
                colors={['#00D4FF', '#5CE1FF'] as [string, string]}
                style={styles.levelUpButtonGradient}
              >
                <Text style={styles.levelUpButtonText}>
                  {firstDateResult?.ending === 'perfect' || firstDateResult?.ending === 'good'
                    ? '太开心了！' : '下次加油！'}
                </Text>
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* 💕 进行中的约会提醒弹窗 */}
      <Modal
        visible={showActiveDateAlert}
        transparent
        animationType="fade"
        onRequestClose={() => setShowActiveDateAlert(false)}
      >
        <View style={styles.activeDateOverlay}>
          <View style={styles.activeDateCard}>
            <Text style={styles.activeDateIcon}>💕</Text>
            <Text style={styles.activeDateTitle}>有一场约会在等你</Text>
            <Text style={styles.activeDateSubtitle}>
              {activeDateSession?.scenario_name} · 第 {activeDateSession?.stage_num} 阶段
            </Text>
            <Text style={styles.activeDateDesc}>
              你和 {characterName} 的约会还没结束哦~
            </Text>
            <View style={styles.activeDateButtons}>
              <TouchableOpacity
                style={styles.activeDateContinueBtn}
                onPress={async () => {
                  setShowActiveDateAlert(false);
                  // 加载场景后打开约会模态框
                  try {
                    const { scenarios } = await api.get<{ scenarios: Array<{id: string; name: string; icon: string; description?: string; required_level?: number; is_locked?: boolean}> }>(`/dates/scenarios?character_id=${params.characterId}`);
                    setDateScenarios(scenarios || []);
                    setShowDateSceneModal(true);
                  } catch (e) {
                    console.error('Failed to load scenarios:', e);
                    setShowDateSceneModal(true);
                  }
                }}
              >
                <Text style={styles.activeDateContinueBtnText}>继续约会 💕</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.activeDateCancelBtn}
                onPress={async () => {
                  // 取消约会
                  try {
                    if (activeDateSession?.session_id) {
                      await api.post('/dates/interactive/abandon', {
                        session_id: activeDateSession.session_id,
                      });
                    }
                    setActiveDateSession(null);
                  } catch (e) {
                    console.error('Failed to abandon date:', e);
                  }
                  setShowActiveDateAlert(false);
                }}
              >
                <Text style={styles.activeDateCancelBtnText}>取消约会</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* 📸 照片预览Modal */}
      <Modal
        visible={showPhotoPreview}
        transparent
        animationType="fade"
        onRequestClose={() => setShowPhotoPreview(false)}
      >
        <View style={styles.photoPreviewOverlay}>
          <View style={styles.photoPreviewContainer}>
            {/* 关闭按钮 */}
            <TouchableOpacity
              style={styles.photoPreviewClose}
              onPress={() => setShowPhotoPreview(false)}
            >
              <Ionicons name="close" size={28} color="#fff" />
            </TouchableOpacity>

            {/* 照片 */}
            {newPhotoUri && (
              <Image
                source={{ uri: newPhotoUri }}
                style={styles.photoPreviewImage}
                resizeMode="contain"
              />
            )}

            {/* 标题 */}
            <Text style={styles.photoPreviewTitle}>📸 新照片！</Text>
            <Text style={styles.photoPreviewSubtitle}>已保存到相册</Text>

            {/* 操作按钮 */}
            <View style={styles.photoPreviewButtons}>
              <TouchableOpacity
                style={styles.photoPreviewBtnSecondary}
                onPress={() => setShowPhotoPreview(false)}
              >
                <Text style={styles.photoPreviewBtnText}>关闭</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.photoPreviewBtnPrimary}
                onPress={handleSetPhotoAsBackground}
              >
                <Text style={styles.photoPreviewBtnTextPrimary}>设为背景</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Toast Notification */}
      {toastMessage && (
        <View style={styles.toastContainer}>
          <View style={styles.toast}>
            <Text style={styles.toastText}>{toastMessage}</Text>
          </View>
        </View>
      )}
      
      {/* 🌙 Luna入场动画覆盖层 */}
      {renderCharacterIntroOverlay()}
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  // 🌙 Luna Intro Animation - 覆盖层
  lunaIntroOverlay: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 9999,
  },
  lunaIntroSplash: {
    ...StyleSheet.absoluteFillObject,
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT,
  },
  lunaIntroVideo: {
    ...StyleSheet.absoluteFillObject,
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT,
  },
  container: {
    flex: 1,
    backgroundColor: '#1a1025',
  },
  backgroundImage: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    height: SCREEN_HEIGHT,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
  },
  safeArea: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  backButton: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerCenter: {
    flex: 1,
    alignItems: 'center',
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  levelBubble: {
    backgroundColor: 'rgba(168, 85, 247, 0.6)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  levelBubbleText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#fff',
  },
  lockBubble: {
    backgroundColor: 'rgba(239, 68, 68, 0.7)',
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: 10,
    marginLeft: -4,
  },
  lockBubbleText: {
    fontSize: 10,
  },
  boostBubble: {
    backgroundColor: 'rgba(147, 51, 234, 0.7)',
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: 10,
    marginLeft: -4,
  },
  boostBubbleText: {
    fontSize: 10,
  },
  avatarButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    overflow: 'hidden',
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  headerAvatar: {
    width: '100%',
    height: '100%',
    borderRadius: 22,
  },
  messagesList: {
    flexGrow: 1,  // 让内容区域填满，inverted 时消息才能靠近输入框
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 4,
  },
  messageRow: {
    flexDirection: 'row',
    marginBottom: 12,
    alignItems: 'flex-end',
  },
  messageRowUser: {
    justifyContent: 'flex-end',
  },
  messageRowAI: {
    justifyContent: 'flex-start',
  },
  // 🎁 礼物事件消息样式 - Luna 2077 HUD style
  giftEventRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginVertical: 12,
  },
  giftEventBubble: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(0, 245, 212, 0.3)',
    gap: 6,
  },
  giftEventIcon: {
    fontSize: 12,
  },
  giftEventText: {
    fontSize: 11,
    color: '#00F5D4',
    fontWeight: '400',
    letterSpacing: 0.3,
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    marginRight: 8,
  },
  bubble: {
    maxWidth: SCREEN_WIDTH * 0.72,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 18,
  },
  bubbleUser: {
    backgroundColor: 'rgba(139, 92, 246, 0.85)',
    borderBottomRightRadius: 4,
  },
  bubbleAI: {
    backgroundColor: 'rgba(30, 20, 50, 0.85)',
    borderBottomLeftRadius: 4,
  },
  // Locked/blurred message styles
  lockedBubble: {
    position: 'relative',
    overflow: 'hidden',
  },
  blurredContent: {
    opacity: 0.3,
  },
  blurredText: {
    // Text is visible but dimmed, will be covered by overlay
  },
  unlockOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    backdropFilter: 'blur(8px)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 16,
  },
  unlockBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.15)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    gap: 6,
  },
  unlockText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '600',
  },
  messageText: {
    fontSize: 15,
    lineHeight: 21,
  },
  messageTextUser: {
    color: '#fff',
  },
  messageTextAI: {
    color: 'rgba(255, 255, 255, 0.92)',
  },
  typingBubble: {
    paddingVertical: 8,
  },
  typingText: {
    color: 'rgba(255, 255, 255, 0.5)',
    fontSize: 14,
    fontStyle: 'italic',
  },
  actionButtonsScroll: {
    minHeight: 44,
    maxHeight: 44,
  },
  actionButtonsRow: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 6,
    gap: 12,
    alignItems: 'center',
    height: 44,
  },
  // iOS-style frosted glass buttons
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.12)',
    paddingHorizontal: 14,
    paddingVertical: 0,
    height: 34,
    borderRadius: 17,
    gap: 5,
    minWidth: 70,
    flexShrink: 0,
    overflow: 'hidden',
  },
  actionButtonDisabled: {
    opacity: 0.5,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  actionButtonLocked: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderColor: 'rgba(255, 255, 255, 0.15)',
    borderWidth: 1,
    borderStyle: 'dashed',
  },
  actionButtonActive: {
    backgroundColor: 'rgba(0, 245, 212, 0.2)',
  },
  actionButtonEmoji: {
    fontSize: 14,
  },
  actionButtonText: {
    fontSize: 13,
    fontWeight: '500',
    color: '#fff',
  },
  actionButtonTextLocked: {
    fontSize: 13,
    fontWeight: '500',
    color: 'rgba(255, 255, 255, 0.4)',
  },
  aiDisclaimer: {
    fontSize: 11,
    color: 'rgba(255, 255, 255, 0.7)',
    textAlign: 'center',
    paddingVertical: 2,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 16,
    paddingTop: 4,
    paddingBottom: 16,
    gap: 10,
  },
  // Luna 2077: Glowing glass bar input
  inputWrapper: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
    minHeight: 44,
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.25)',
    // Subtle glow
    shadowColor: '#00D4FF',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
  },
  input: {
    fontSize: 15,
    color: '#fff',
    maxHeight: 100,
  },
  // Send button: Wireframe style
  sendButton: {
    borderRadius: 8,
    overflow: 'hidden',
  },
  sendButtonDisabled: {
    opacity: 0.35,
    transform: [{ scale: 0.95 }],
  },
  sendButtonGradient: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: 'rgba(0, 212, 255, 0.5)',
    borderRadius: 8,
  },
  // Modal Styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#1a1025',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: SCREEN_HEIGHT * 0.8,
    paddingBottom: 34,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
  },
  modalCloseButton: {
    padding: 4,
  },
  modalScroll: {
    paddingHorizontal: 20,
    paddingTop: 16,
  },
  planCard: {
    marginBottom: 16,
    borderRadius: 16,
    overflow: 'hidden',
  },
  planGradient: {
    padding: 20,
  },
  planHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 8,
  },
  planName: {
    fontSize: 22,
    fontWeight: '700',
    color: '#fff',
  },
  planBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
  },
  planBadgeText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#fff',
  },
  planPrice: {
    fontSize: 32,
    fontWeight: '800',
    color: '#fff',
    marginBottom: 12,
  },
  planPeriod: {
    fontSize: 16,
    fontWeight: '400',
  },
  planFeatures: {
    gap: 6,
  },
  planFeature: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.9)',
  },
  planCardCurrent: {
    opacity: 0.7,
  },
  planDailyCredits: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFD700',
    marginBottom: 12,
  },
  coinPacksGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 20,
  },
  coinPackCard: {
    width: (SCREEN_WIDTH - 64) / 2,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
    position: 'relative',
  },
  coinPackPopular: {
    position: 'absolute',
    top: -8,
    right: -8,
    backgroundColor: '#00D4FF',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  coinPackPopularText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#fff',
  },
  coinPackDiscount: {
    position: 'absolute',
    top: -8,
    left: -8,
    backgroundColor: '#10B981',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  coinPackDiscountText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#fff',
  },
  coinPackBonus: {
    fontSize: 12,
    fontWeight: '500',
    color: '#10B981',
    marginTop: 2,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginTop: 8,
    marginBottom: 12,
  },
  creditPacks: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
  },
  creditPack: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  creditPackCoins: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFD700',
    marginBottom: 4,
  },
  creditPackPrice: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
  },
  coinPackCoins: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFD700',
    marginTop: 8,
    marginBottom: 4,
  },
  coinPackPrice: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
    marginTop: 4,
  },
  creditPackSave: {
    position: 'absolute',
    top: -6,
    right: -6,
    backgroundColor: '#EF4444',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
  },
  creditPackSaveText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#fff',
  },
  // Level Up Modal Styles
  levelUpOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  levelUpContent: {
    backgroundColor: '#1a1025',
    borderRadius: 24,
    padding: 32,
    alignItems: 'center',
    marginHorizontal: 40,
    borderWidth: 2,
    borderColor: '#8B5CF6',
  },
  levelUpEmoji: {
    fontSize: 64,
    marginBottom: 16,
  },
  levelUpTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 8,
  },
  levelUpLevel: {
    fontSize: 48,
    fontWeight: '800',
    color: '#00D4FF',
    marginBottom: 16,
  },
  levelUpDesc: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.8)',
    textAlign: 'center',
    marginBottom: 24,
  },
  levelUpButton: {
    borderRadius: 24,
    overflow: 'hidden',
  },
  levelUpButtonGradient: {
    paddingHorizontal: 40,
    paddingVertical: 14,
  },
  levelUpButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
  },
  // Level Info Modal Styles
  levelInfoOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    justifyContent: 'flex-end',
  },
  levelInfoContent: {
    backgroundColor: '#1a1025',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '85%',
    paddingBottom: 30,
  },
  levelInfoHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  levelInfoTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
  },
  levelInfoScroll: {
    padding: 20,
  },
  levelInfoSection: {
    marginBottom: 24,
  },
  levelInfoSectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 12,
  },
  currentStatusCard: {
    backgroundColor: 'rgba(168, 85, 247, 0.2)',
    borderRadius: 16,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  currentStatusLevel: {
    fontSize: 24,
    fontWeight: '700',
    color: '#A855F7',
  },
  currentStatusStage: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginTop: 2,
  },
  xpStatusBox: {
    alignItems: 'flex-end',
  },
  xpStatusText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  xpStatusBar: {
    width: 100,
    height: 6,
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 3,
    marginTop: 6,
    overflow: 'hidden',
  },
  xpStatusBarFill: {
    height: '100%',
    backgroundColor: '#A855F7',
    borderRadius: 3,
  },
  xpStatusHint: {
    fontSize: 11,
    color: 'rgba(255,255,255,0.6)',
    marginTop: 4,
  },
  stageCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: 'transparent',
  },
  stageCardActive: {
    borderColor: '#A855F7',
    backgroundColor: 'rgba(168, 85, 247, 0.1)',
  },
  stageHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  stageEmoji: {
    fontSize: 24,
    marginRight: 12,
  },
  stageInfo: {
    flex: 1,
  },
  stageName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  stageLevel: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.5)',
  },
  stageDesc: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.7)',
    marginBottom: 8,
  },
  stageFeatures: {
    gap: 4,
  },
  featureItem: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.8)',
  },
  featureLocked: {
    color: 'rgba(255, 255, 255, 0.4)',
  },
  xpWayCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 12,
    padding: 14,
    gap: 10,
  },
  xpWayItem: {
    fontSize: 14,
    color: '#fff',
  },
  xpAmount: {
    color: '#A855F7',
    fontWeight: '600',
  },
  giftDesc: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.7)',
    marginBottom: 12,
  },
  giftGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginBottom: 16,
  },
  giftItem: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
    width: '23%',
  },
  giftEmoji: {
    fontSize: 28,
    marginBottom: 4,
  },
  giftName: {
    fontSize: 12,
    color: '#fff',
    fontWeight: '500',
  },
  giftPrice: {
    fontSize: 11,
    color: '#FFD700',
    marginTop: 2,
  },
  giftXp: {
    fontSize: 10,
    color: '#A855F7',
    marginTop: 2,
  },
  giftShopButton: {
    backgroundColor: 'rgba(168, 85, 247, 0.3)',
    borderRadius: 20,
    paddingVertical: 12,
    alignItems: 'center',
  },
  giftShopButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: 'rgba(255, 255, 255, 0.6)',
  },
  // Gift Modal Styles
  giftModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  giftModalContent: {
    backgroundColor: '#2a1f3d',
    borderRadius: 20,
    padding: 16,
    width: '100%',
    maxWidth: 340,
    borderWidth: 1,
    borderColor: 'rgba(168, 85, 247, 0.3)',
  },
  giftModalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  giftModalTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  giftModalGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    justifyContent: 'center',
  },
  giftModalItem: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
    width: '30%',
  },
  giftModalEmoji: {
    fontSize: 32,
    marginBottom: 4,
  },
  giftModalName: {
    fontSize: 12,
    color: '#fff',
    fontWeight: '500',
  },
  giftModalPrice: {
    fontSize: 11,
    color: '#FFD700',
    marginTop: 4,
  },
  giftModalXp: {
    fontSize: 10,
    color: '#A855F7',
    marginTop: 2,
  },
  giftModalFooter: {
    marginTop: 16,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
    alignItems: 'center',
  },
  giftModalBalance: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.7)',
  },
  // 💕 进行中约会提醒样式
  activeDateOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  activeDateCard: {
    backgroundColor: '#2D1B4E',
    borderRadius: 20,
    padding: 24,
    width: '85%',
    alignItems: 'center',
    shadowColor: '#00D4FF',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.3,
    shadowRadius: 16,
    elevation: 12,
    borderWidth: 1,
    borderColor: 'rgba(236, 72, 153, 0.3)',
  },
  activeDateIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  activeDateTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 8,
  },
  activeDateSubtitle: {
    fontSize: 14,
    color: '#00D4FF',
    marginBottom: 8,
    fontWeight: '500',
  },
  activeDateDesc: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.7)',
    textAlign: 'center',
    marginBottom: 20,
  },
  activeDateButtons: {
    width: '100%',
    gap: 10,
  },
  activeDateContinueBtn: {
    backgroundColor: '#00D4FF',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
  },
  activeDateContinueBtnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  activeDateCancelBtn: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
  },
  activeDateCancelBtnText: {
    color: 'rgba(255, 255, 255, 0.7)',
    fontSize: 14,
    fontWeight: '500',
  },

  // Toast styles
  toastContainer: {
    position: 'absolute',
    bottom: 140,
    left: 0,
    right: 0,
    alignItems: 'center',
    zIndex: 9999,
  },
  toast: {
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 25,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 10,
  },
  toastText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
  },
  // 📸 照片预览样式
  photoPreviewOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.95)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  photoPreviewContainer: {
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  photoPreviewClose: {
    position: 'absolute',
    top: 60,
    right: 20,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  photoPreviewImage: {
    width: '90%',
    height: '55%',
    borderRadius: 16,
  },
  photoPreviewTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
    marginTop: 24,
  },
  photoPreviewSubtitle: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.6)',
    marginTop: 8,
  },
  photoPreviewButtons: {
    flexDirection: 'row',
    gap: 16,
    marginTop: 32,
  },
  photoPreviewBtnSecondary: {
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 25,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
  },
  photoPreviewBtnPrimary: {
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 25,
    backgroundColor: '#00D4FF',
  },
  photoPreviewBtnText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  photoPreviewBtnTextPrimary: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
});
