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
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useUserStore } from '../../store/userStore';
import { useChatStore, selectActiveMessages, Message } from '../../store/chatStore';
import { useGiftStore, GiftCatalogItem } from '../../store/giftStore';

// NSFW mode costs 2 extra credits per message
const NSFW_MODE_CREDIT_COST = 2;
import { chatService } from '../../services/chatService';
import { intimacyService } from '../../services/intimacyService';
import { characterService } from '../../services/characterService';
import { emotionService } from '../../services/emotionService';
import { GiftOverlay, useGiftEffect, GiftType } from '../../components/GiftEffects';
import { paymentService } from '../../services/paymentService';
import { RechargeModal } from '../../components/RechargeModal';
import { SubscriptionModal } from '../../components/SubscriptionModal';
import { getCharacterAvatar, getCharacterBackground } from '../../assets/characters';
import CharacterInfoPanel from '../../components/CharacterInfoPanel';
import GiftBottomSheet from '../../components/GiftBottomSheet';
import MockModeBanner from '../../components/MockModeBanner';
import MessageBubble from '../../components/MessageBubble';
import { ToastProvider, useToast } from '../../components/Toast';
import { useEmotionTheme } from '../../hooks/useEmotionTheme';
import { EmotionEffectsLayer, EmotionIndicator } from '../../components/EmotionEffects';
import { DebugButton } from '../../components/DebugPanel';
import { ExtraData } from '../../store/chatStore';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

const DEFAULT_BACKGROUND = 'https://i.imgur.com/vB5HQXQ.jpg';

export default function ChatScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ characterId: string; characterName: string; sessionId?: string; backgroundUrl?: string; avatarUrl?: string }>();
  
  const { wallet, deductCredits, updateWallet, isSubscribed } = useUserStore();
  const isSpicyMode = useChatStore((s) => s.isSpicyMode);
  const giftCatalog = useGiftStore((s) => s.catalog);
  const fetchGiftCatalog = useGiftStore((s) => s.fetchCatalog);
  const {
    isTyping,
    setActiveSession,
    addMessage,
    setMessages,
    setTyping,
    getIntimacy,
    setIntimacy,
    updateSession,
  } = useChatStore();
  
  const messages = useChatStore(selectActiveMessages);
  const cachedIntimacy = useChatStore((s) => s.intimacyByCharacter[params.characterId]);
  
  const [inputText, setInputText] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(params.sessionId || null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [characterAvatar, setCharacterAvatar] = useState(params.avatarUrl || 'https://i.pravatar.cc/100?img=5');
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
  const [showSubscriptionModal, setShowSubscriptionModal] = useState(false);
  const [showCharacterInfo, setShowCharacterInfo] = useState(false);
  const [emotionScore, setEmotionScore] = useState(0);
  const [emotionState, setEmotionState] = useState('neutral');
  const [lastExtraData, setLastExtraData] = useState<ExtraData | null>(null);  // Debug info
  const [lastTokensUsed, setLastTokensUsed] = useState<number>(0);
  
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

  // Scroll to bottom when keyboard opens
  useEffect(() => {
    const keyboardShowListener = Keyboard.addListener(
      Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow',
      () => {
        // Multiple attempts to ensure scroll completes after layout
        setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 150);
        setTimeout(() => flatListRef.current?.scrollToEnd({ animated: false }), 400);
      }
    );
    return () => keyboardShowListener.remove();
  }, []);

  // Scroll to bottom when messages load (initial load)
  useEffect(() => {
    if (messages.length > 0 && !isInitializing) {
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: false }), 100);
    }
  }, [messages.length, isInitializing]);

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
      
      // Step 1: Check for cached session first (instant load)
      const cachedSession = useChatStore.getState().getSessionByCharacterId(params.characterId);
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
          // Convert emotionIntensity (0-100) to score (-100 to 100)
          // negative emotions have negative score
          const negativeStates = ['annoyed', 'angry', 'hurt', 'cold', 'silent'];
          const isNegative = negativeStates.includes(emotionStatus.emotionalState);
          const score = isNegative ? -emotionStatus.emotionIntensity : emotionStatus.emotionIntensity;
          setEmotionScore(score);
          setEmotionState(emotionStatus.emotionalState);
        }
      } catch (e) {
        console.log('Emotion status not available:', e);
      }
      
      // Step 3: Sync with backend - get or create session
      const session = await chatService.getOrCreateSession(params.characterId);
      setSessionId(session.sessionId);
      setActiveSession(session.sessionId, params.characterId);
      if (session.characterName) setCharacterName(session.characterName);
      if (session.characterAvatar) setCharacterAvatar(session.characterAvatar);
      if (session.characterBackground) setBackgroundImage(session.characterBackground);
      
      // Update session in store
      const existingSession = useChatStore.getState().getSessionByCharacterId(params.characterId);
      if (existingSession) {
        useChatStore.getState().updateSession(session.sessionId, session);
      } else {
        useChatStore.getState().addSession(session);
      }
      
      // Step 4: Load message history from backend (only if newer than cache)
      try {
        const cachedMessages = useChatStore.getState().messagesBySession[session.sessionId] || [];
        const history = await chatService.getSessionHistory(session.sessionId);
        // Only update if backend has more messages or cache is empty
        if (history.length > 0 && history.length >= cachedMessages.length) {
          setMessages(session.sessionId, history);
        }
        
        // Step 5: If no messages yet, show character's greeting
        const finalMessages = useChatStore.getState().messagesBySession[session.sessionId] || [];
        if (finalMessages.length === 0) {
          try {
            const character = await characterService.getCharacter(params.characterId);
            if (character.greeting) {
              const greetingMessage: Message = {
                messageId: `greeting-${Date.now()}`,
                role: 'assistant',
                content: character.greeting,
                createdAt: new Date().toISOString(),
                tokensUsed: 0,
              };
              addMessage(session.sessionId, greetingMessage);
            }
          } catch (e) {
            console.log('Could not load character greeting:', e);
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
      // Scroll to bottom after loading completes
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: false }), 200);
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: false }), 500);
    }
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
    addMessage(sessionId, userMessage);
    
    setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    setTyping(true, params.characterId);
    
    try {
      // Check if user is subscribed for NSFW mode
      if (isSpicyMode && !isSubscribed) {
        setTyping(false);
        setShowSubscriptionModal(true);
        return;
      }
      
      // Check if user has enough credits for NSFW mode
      if (isSpicyMode && (wallet?.totalCredits || 0) < NSFW_MODE_CREDIT_COST) {
        Alert.alert('金币不足', 'NSFW 模式每条消息需要 2 金币，请先充值。');
        setTyping(false);
        return;
      }
      
      const response = await chatService.sendMessage({ 
        sessionId, 
        message: text,
        spicyMode: isSpicyMode,
        intimacyLevel: relationshipLevel || 1,
      });
      
      addMessage(sessionId, {
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
      }
      if (response.tokensUsed) {
        setLastTokensUsed(response.tokensUsed);
      }
      
      // Update session's lastMessageAt for accurate time display in chat list
      updateSession(sessionId, { lastMessageAt: new Date().toISOString() });
      
      if (response.creditsDeducted) {
        deductCredits(response.creditsDeducted);
      }
      
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
      } catch (e) {
        // Silently fail if intimacy update fails
      }
      
      // Update emotion after chat
      try {
        const updatedEmotion = await emotionService.getStatus(params.characterId);
        if (updatedEmotion) {
          const negativeStates = ['annoyed', 'angry', 'hurt', 'cold', 'silent'];
          const isNegative = negativeStates.includes(updatedEmotion.emotionalState);
          const score = isNegative ? -updatedEmotion.emotionIntensity : updatedEmotion.emotionIntensity;
          setEmotionScore(score);
          setEmotionState(updatedEmotion.emotionalState);
        }
      } catch (e) {
        // Silently fail if emotion update fails
      }
      
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    } catch (error: any) {
      console.error('Send message error:', error);
      Alert.alert('Error', 'Failed to send message');
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
    addMessage(sessionId, userMessage);
    
    setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    setTyping(true, params.characterId);
    
    try {
      const response = await chatService.sendMessage({ 
        sessionId, 
        message: photoRequest,
        requestType: 'photo',  // Tell backend this is a photo request
        spicyMode: isSpicyMode,
        intimacyLevel: relationshipLevel || 1,
      });
      
      addMessage(sessionId, {
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
      
      if (response.creditsDeducted) {
        deductCredits(response.creditsDeducted);
      }
      
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
      
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    } catch (error: any) {
      console.error('Photo request error:', error);
      Alert.alert('Error', 'Failed to request photo');
    } finally {
      setTyping(false);
    }
  };

  // Toast state for copy feedback
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  
  // Show toast helper
  const showToast = useCallback((message: string) => {
    setToastMessage(message);
    setTimeout(() => setToastMessage(null), 2000);
  }, []);
  
  // Handle emoji reaction - awards XP bonus
  const handleReaction = useCallback(async (reactionName: string, xpBonus: number) => {
    // Award XP for reaction
    const newXp = relationshipXp + xpBonus;
    const newMax = relationshipMaxXp;
    
    if (newXp >= newMax) {
      // Level up!
      const newLevelValue = (relationshipLevel || 1) + 1;
      setRelationshipLevel(newLevelValue);
      setRelationshipXp(newXp - newMax);
      setRelationshipMaxXp(Math.round(newMax * 1.15));
      setNewLevel(newLevelValue);
      setTimeout(() => setShowLevelUpModal(true), 500);
      
      // Update cache
      setIntimacy(params.characterId, {
        currentLevel: newLevelValue,
        xpProgressInLevel: newXp - newMax,
        xpForNextLevel: Math.round(newMax * 1.15),
        xpForCurrentLevel: 0,
      });
    } else {
      setRelationshipXp(newXp);
      
      // Update cache
      setIntimacy(params.characterId, {
        currentLevel: relationshipLevel || 1,
        xpProgressInLevel: newXp,
        xpForNextLevel: relationshipMaxXp,
        xpForCurrentLevel: 0,
      });
    }
    
    showToast(`+${xpBonus} 亲密度 💕`);
  }, [relationshipXp, relationshipMaxXp, relationshipLevel, params.characterId, setIntimacy, showToast]);
  
  // Handle reply to message
  const handleReply = useCallback((content: string) => {
    // Set input with quoted content
    const quoted = content.length > 50 ? content.substring(0, 50) + '...' : content;
    setInputText(`「${quoted}」\n`);
  }, []);

  const renderMessage = ({ item }: { item: Message }) => {
    const isUser = item.role === 'user';
    const isLocked = item.isLocked && !isSubscribed;
    
    // Handle unlock tap - show subscription modal
    const handleUnlock = () => {
      setShowSubscriptionModal(true);
    };
    
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
          onReaction={!isUser ? handleReaction : undefined}
          onReply={!isUser ? handleReply : undefined}
          showToast={showToast}
        />
      </View>
    );
  };

  const renderTypingIndicator = () => (
    <View style={[styles.messageRow, styles.messageRowAI]}>
      <Image source={getCharacterAvatar(params.characterId, characterAvatar)} style={styles.avatar} />
      <View style={[styles.bubble, styles.bubbleAI, styles.typingBubble]}>
        <Text style={styles.typingText}>正在输入...</Text>
      </View>
    </View>
  );

  // Get background source (local or remote)
  const backgroundSource = getCharacterBackground(params.characterId, backgroundImage);

  return (
    <GestureHandlerRootView style={styles.container}>
      {/* Full screen background image */}
      <ImageBackground
        source={backgroundSource || { uri: backgroundImage }}
        style={styles.backgroundImage}
        resizeMode="cover"
      >
        {/* Gradient overlay for readability - 动态主题色 */}
        <LinearGradient
          colors={overlayColors as unknown as [string, string, string]}
          style={styles.overlay}
        />
      </ImageBackground>

      {/* 🎆 情绪特效层 */}
      <EmotionEffectsLayer
        emotionMode={emotionMode}
        glitchEnabled={glitchEnabled}
        glowEnabled={glowEnabled}
        glowColor={emotionTheme.colors.glow}
      />

      <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
        {/* 情绪指示器 */}
        {emotionMode !== 'neutral' && (
          <EmotionIndicator
            mode={emotionMode}
            score={emotionScore}
            style={{ position: 'absolute', top: 60, zIndex: 100 }}
          />
        )}
        
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="close" size={28} color="#fff" />
          </TouchableOpacity>
          
          <View style={styles.headerCenter}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <Text style={styles.characterName}>{characterName}</Text>
              <MockModeBanner compact />
            </View>
          </View>
          
          <TouchableOpacity style={styles.menuButton} onPress={() => setShowCharacterInfo(true)}>
            <Ionicons name="ellipsis-horizontal" size={24} color="#fff" />
          </TouchableOpacity>
        </View>

        {/* Status Bar - Level, Credits, Upgrade */}
        <View style={styles.statusBar}>
          {/* Level Badge */}
          <TouchableOpacity style={styles.levelContainer} onPress={() => setShowLevelInfoModal(true)}>
            {relationshipLevel === null ? (
              <Text style={styles.levelText}>加载中...</Text>
            ) : (
              <>
                <View style={styles.levelRow}>
                  <Ionicons name="information-circle-outline" size={14} color="rgba(255,255,255,0.7)" style={{ marginRight: 4 }} />
                  <Text style={styles.levelText}>LV {relationshipLevel}</Text>
                </View>
                <View style={styles.xpBarContainer}>
                  <Animated.View 
                    style={[
                      styles.xpBar, 
                      { 
                        width: xpProgressAnim.interpolate({
                          inputRange: [0, 100],
                          outputRange: ['0%', '100%'],
                        })
                      }
                    ]} 
                  />
                </View>
              </>
            )}
          </TouchableOpacity>
          
          {/* Credits */}
          <TouchableOpacity style={styles.creditsContainer} onPress={() => setShowRechargeModal(true)}>
            <Text style={styles.coinEmoji}>🪙</Text>
            <Text style={styles.creditsText}>{wallet?.totalCredits ?? 0}</Text>
            <View style={styles.addCreditsButton}>
              <Ionicons name="add" size={14} color="#FFD700" />
            </View>
          </TouchableOpacity>
          
          {/* Upgrade Button */}
          {!isSubscribed && (
            <TouchableOpacity style={styles.upgradeButton} onPress={() => setShowSubscriptionModal(true)}>
              <LinearGradient
                colors={['#FF6B35', '#F7931E'] as [string, string]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.upgradeGradient}
              >
                <Text style={styles.upgradeIcon}>🔥</Text>
                <Text style={styles.upgradeText}>UPGRADE</Text>
              </LinearGradient>
            </TouchableOpacity>
          )}
        </View>

        {/* Messages */}
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(item) => item.messageId}
          renderItem={renderMessage}
          contentContainerStyle={styles.messagesList}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: false })}
          ListFooterComponent={isTyping ? renderTypingIndicator : null}
          showsVerticalScrollIndicator={false}
        />

        {/* Action Buttons */}
        <View style={styles.actionButtonsRow}>
          <TouchableOpacity style={styles.actionButton} onPress={handleAskForPhoto}>
            <Text style={styles.actionButtonEmoji}>📸</Text>
            <Text style={styles.actionButtonText}>Ask for Photo</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionButton} onPress={() => setShowGiftModal(true)}>
            <Text style={styles.actionButtonEmoji}>🎁</Text>
            <Text style={styles.actionButtonText}>送礼物</Text>
          </TouchableOpacity>
        </View>

        {/* Input Area - moved up */}
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          keyboardVerticalOffset={0}
        >
          <View style={styles.inputContainer}>
            {/* Input */}
            <View style={styles.inputWrapper}>
              <TextInput
                style={styles.input}
                placeholder={`与 ${characterName} 聊天`}
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
              disabled={!inputText.trim()}
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
        </KeyboardAvoidingView>
        
        {/* Debug Panel Button - only in development */}
        {__DEV__ && (
          <DebugButton
            extraData={lastExtraData}
            emotionScore={emotionScore}
            emotionState={emotionState}
            intimacyLevel={relationshipLevel || 1}
            isSubscribed={isSubscribed}
            tokensUsed={lastTokensUsed}
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
            <Text style={styles.levelUpTitle}>恭喜升级！</Text>
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
                colors={['#8B5CF6', '#EC4899'] as [string, string]}
                style={styles.levelUpButtonGradient}
              >
                <Text style={styles.levelUpButtonText}>太棒了！</Text>
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
              {/* Current Status */}
              <View style={styles.levelInfoSection}>
                <Text style={styles.levelInfoSectionTitle}>当前状态</Text>
                <View style={styles.currentStatusCard}>
                  <View>
                    <Text style={styles.currentStatusLevel}>LV {relationshipLevel || 1}</Text>
                    <Text style={styles.currentStatusStage}>
                      {(relationshipLevel || 1) <= 3 ? '👋 初识' : 
                       (relationshipLevel || 1) <= 10 ? '😊 熟悉' :
                       (relationshipLevel || 1) <= 25 ? '💛 好友' :
                       (relationshipLevel || 1) <= 40 ? '💕 亲密' : '❤️ 挚爱'}
                    </Text>
                  </View>
                  <View style={styles.xpStatusBox}>
                    <Text style={styles.xpStatusText}>
                      {Math.round(relationshipXp)} / {Math.round(relationshipMaxXp)} XP
                    </Text>
                    <View style={styles.xpStatusBar}>
                      <View style={[styles.xpStatusBarFill, { width: `${Math.min(100, (relationshipXp / relationshipMaxXp) * 100)}%` }]} />
                    </View>
                    <Text style={styles.xpStatusHint}>
                      还需 {Math.round(relationshipMaxXp - relationshipXp)} XP 升级
                    </Text>
                  </View>
                </View>
              </View>

              {/* Stages */}
              <View style={styles.levelInfoSection}>
                <Text style={styles.levelInfoSectionTitle}>亲密阶段</Text>
                
                <View style={[styles.stageCard, (relationshipLevel || 1) <= 3 && styles.stageCardActive]}>
                  <View style={styles.stageHeader}>
                    <Text style={styles.stageEmoji}>👋</Text>
                    <View style={styles.stageInfo}>
                      <Text style={styles.stageName}>初识</Text>
                      <Text style={styles.stageLevel}>LV 1-3</Text>
                    </View>
                  </View>
                  <Text style={styles.stageDesc}>刚认识，保持礼貌距离</Text>
                  <View style={styles.stageFeatures}>
                    <Text style={styles.featureItem}>✓ 基础文字聊天</Text>
                    <Text style={styles.featureItem}>✓ 基础表情回复</Text>
                    <Text style={[styles.featureItem, styles.featureLocked]}>✗ 发送图片</Text>
                  </View>
                </View>

                <View style={[styles.stageCard, (relationshipLevel || 1) > 3 && (relationshipLevel || 1) <= 10 && styles.stageCardActive]}>
                  <View style={styles.stageHeader}>
                    <Text style={styles.stageEmoji}>😊</Text>
                    <View style={styles.stageInfo}>
                      <Text style={styles.stageName}>熟悉</Text>
                      <Text style={styles.stageLevel}>LV 4-10</Text>
                    </View>
                  </View>
                  <Text style={styles.stageDesc}>开始熟络，可以开玩笑</Text>
                  <View style={styles.stageFeatures}>
                    <Text style={styles.featureItem}>✓ 专属表情包</Text>
                    <Text style={styles.featureItem}>✓ 发送图片</Text>
                    <Text style={styles.featureItem}>✓ 更俏皮的回复</Text>
                  </View>
                </View>

                <View style={[styles.stageCard, (relationshipLevel || 1) > 10 && (relationshipLevel || 1) <= 25 && styles.stageCardActive]}>
                  <View style={styles.stageHeader}>
                    <Text style={styles.stageEmoji}>💛</Text>
                    <View style={styles.stageInfo}>
                      <Text style={styles.stageName}>好友</Text>
                      <Text style={styles.stageLevel}>LV 11-25</Text>
                    </View>
                  </View>
                  <Text style={styles.stageDesc}>无话不谈的好朋友</Text>
                  <View style={styles.stageFeatures}>
                    <Text style={styles.featureItem}>✓ 语音消息</Text>
                    <Text style={styles.featureItem}>✓ 更多话题解锁</Text>
                    <Text style={styles.featureItem}>✓ 送礼物</Text>
                  </View>
                </View>

                <View style={[styles.stageCard, (relationshipLevel || 1) > 25 && (relationshipLevel || 1) <= 40 && styles.stageCardActive]}>
                  <View style={styles.stageHeader}>
                    <Text style={styles.stageEmoji}>💕</Text>
                    <View style={styles.stageInfo}>
                      <Text style={styles.stageName}>亲密</Text>
                      <Text style={styles.stageLevel}>LV 26-40</Text>
                    </View>
                  </View>
                  <Text style={styles.stageDesc}>特别的存在，独特的羁绊</Text>
                  <View style={styles.stageFeatures}>
                    <Text style={styles.featureItem}>✓ 私密话题</Text>
                    <Text style={styles.featureItem}>✓ 专属称呼</Text>
                    <Text style={styles.featureItem}>✓ Spicy 模式</Text>
                  </View>
                </View>

                <View style={[styles.stageCard, (relationshipLevel || 1) > 40 && styles.stageCardActive]}>
                  <View style={styles.stageHeader}>
                    <Text style={styles.stageEmoji}>❤️</Text>
                    <View style={styles.stageInfo}>
                      <Text style={styles.stageName}>挚爱</Text>
                      <Text style={styles.stageLevel}>LV 41+</Text>
                    </View>
                  </View>
                  <Text style={styles.stageDesc}>灵魂伴侣，心有灵犀</Text>
                  <View style={styles.stageFeatures}>
                    <Text style={styles.featureItem}>✓ 全部功能解锁</Text>
                    <Text style={styles.featureItem}>✓ 专属剧情</Text>
                    <Text style={styles.featureItem}>✓ 优先回复</Text>
                  </View>
                </View>
              </View>

              {/* How to earn XP */}
              <View style={styles.levelInfoSection}>
                <Text style={styles.levelInfoSectionTitle}>如何提升亲密度</Text>
                <View style={styles.xpWayCard}>
                  <Text style={styles.xpWayItem}>💬 发送消息 <Text style={styles.xpAmount}>+2 XP</Text></Text>
                  <Text style={styles.xpWayItem}>📅 每日签到 <Text style={styles.xpAmount}>+20 XP</Text></Text>
                  <Text style={styles.xpWayItem}>🔥 连续聊天（10条） <Text style={styles.xpAmount}>+5 XP</Text></Text>
                  <Text style={styles.xpWayItem}>💝 表达情感 <Text style={styles.xpAmount}>+10 XP</Text></Text>
                  <Text style={styles.xpWayItem}>🎁 送礼物 <Text style={styles.xpAmount}>+50~500 XP</Text></Text>
                </View>
              </View>

              {/* Gifts */}
              <View style={styles.levelInfoSection}>
                <Text style={styles.levelInfoSectionTitle}>🎁 礼物商城</Text>
                <Text style={styles.giftDesc}>用金币给 TA 送礼物，快速提升亲密度！</Text>
                <View style={styles.giftGrid}>
                  <View style={styles.giftItem}>
                    <Text style={styles.giftEmoji}>🌹</Text>
                    <Text style={styles.giftName}>玫瑰</Text>
                    <Text style={styles.giftPrice}>10 🪙</Text>
                    <Text style={styles.giftXp}>+50 XP</Text>
                  </View>
                  <View style={styles.giftItem}>
                    <Text style={styles.giftEmoji}>🧸</Text>
                    <Text style={styles.giftName}>小熊</Text>
                    <Text style={styles.giftPrice}>50 🪙</Text>
                    <Text style={styles.giftXp}>+150 XP</Text>
                  </View>
                  <View style={styles.giftItem}>
                    <Text style={styles.giftEmoji}>💎</Text>
                    <Text style={styles.giftName}>钻石</Text>
                    <Text style={styles.giftPrice}>100 🪙</Text>
                    <Text style={styles.giftXp}>+300 XP</Text>
                  </View>
                  <View style={styles.giftItem}>
                    <Text style={styles.giftEmoji}>👑</Text>
                    <Text style={styles.giftName}>皇冠</Text>
                    <Text style={styles.giftPrice}>200 🪙</Text>
                    <Text style={styles.giftXp}>+500 XP</Text>
                  </View>
                </View>
                <TouchableOpacity style={styles.giftShopButton}>
                  <Text style={styles.giftShopButtonText}>即将开放</Text>
                </TouchableOpacity>
              </View>

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
        onSelectGift={async (gift) => {
          try {
            // 1. 调用后端 API
            const giftResult = await paymentService.sendGift(
              params.characterId,
              gift.gift_type,
              gift.price,
              gift.xp_reward
            );
            
            if (!giftResult.success) {
              const errorMessage = giftResult.error === 'insufficient_credits' 
                ? '金币不足' 
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
            
            // 添加 AI 回复到聊天
            if (sessionId && reactionMessage) {
              const aiMessage: Message = {
                messageId: `gift-${Date.now()}`,
                role: 'assistant',
                content: reactionMessage,
                createdAt: new Date().toISOString(),
              };
              addMessage(sessionId, aiMessage);
              setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
            }
            
            // 4. 更新亲密度
            const xpAwarded = giftResult.xp_awarded || gift.xp_reward;
            const newXp = relationshipXp + xpAwarded;
            const newMax = relationshipMaxXp;
            
            if (newXp >= newMax) {
              const newLevel = (relationshipLevel || 1) + 1;
              setRelationshipLevel(newLevel);
              setRelationshipXp(newXp - newMax);
              setRelationshipMaxXp(Math.round(newMax * 1.2));
              setNewLevel(newLevel);
              setTimeout(() => setShowLevelUpModal(true), 3000);
            } else {
              setRelationshipXp(newXp);
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
      />
      
      {/* Toast Notification */}
      {toastMessage && (
        <View style={styles.toastContainer}>
          <View style={styles.toast}>
            <Text style={styles.toastText}>{toastMessage}</Text>
          </View>
        </View>
      )}
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
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
  characterName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  menuButton: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  statusBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    borderRadius: 12,
    marginHorizontal: 16,
    marginBottom: 8,
  },
  levelContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  levelRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  levelText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#fff',
  },
  xpBarContainer: {
    width: 50,
    height: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 3,
    overflow: 'hidden',
  },
  xpBar: {
    height: '100%',
    backgroundColor: '#A855F7',
    borderRadius: 3,
  },
  creditsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 215, 0, 0.15)',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 16,
    gap: 4,
  },
  coinEmoji: {
    fontSize: 14,
  },
  creditsText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFD700',
  },
  addCreditsButton: {
    marginLeft: 2,
  },
  upgradeButton: {
    borderRadius: 16,
    overflow: 'hidden',
  },
  upgradeGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    gap: 4,
  },
  upgradeIcon: {
    fontSize: 12,
  },
  upgradeText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#fff',
  },
  messagesList: {
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 8,
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
    backgroundColor: 'rgba(255, 255, 255, 0.18)',
    borderBottomRightRadius: 4,
  },
  bubbleAI: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
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
  actionButtonsRow: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingBottom: 8,
    gap: 10,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(139, 92, 246, 0.3)',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.5)',
    gap: 6,
  },
  actionButtonEmoji: {
    fontSize: 16,
  },
  actionButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 16,
    gap: 10,
  },
  inputWrapper: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.12)',
    borderRadius: 24,
    paddingHorizontal: 18,
    paddingVertical: Platform.OS === 'ios' ? 12 : 8,
    minHeight: 48,
    justifyContent: 'center',
  },
  input: {
    fontSize: 16,
    color: '#fff',
    maxHeight: 100,
  },
  sendButton: {
    borderRadius: 24,
    overflow: 'hidden',
  },
  sendButtonDisabled: {
    opacity: 0.5,
  },
  sendButtonGradient: {
    width: 48,
    height: 48,
    justifyContent: 'center',
    alignItems: 'center',
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
    backgroundColor: '#EC4899',
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
    color: '#EC4899',
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
});
