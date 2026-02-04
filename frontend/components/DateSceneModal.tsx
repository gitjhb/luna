/**
 * DateSceneModal - 互动式约会场景
 * 
 * 布局参考心跳回忆风格：
 * - 顶部：状态栏（好感度 + 角色头像 + 阶段进度）
 * - 中间：大面积背景
 * - 底部：对话框 + 选项
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  Modal,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Dimensions,
  Animated,
  Image,
  TextInput,
  Keyboard,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import BottomSheet, { BottomSheetScrollView } from '@gorhom/bottom-sheet';
import { api } from '../services/api';
import { getCharacterAvatar } from '../assets/characters';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// Sakura 场景图片映射
const SAKURA_SCENE_IMAGES: Record<string, any> = {
  bedroom: require('../assets/characters/sakura/scenes/bedroom.jpeg'),
  beach: require('../assets/characters/sakura/scenes/beach.jpeg'),
  ocean: require('../assets/characters/sakura/scenes/ocean.jpeg'),
  school: require('../assets/characters/sakura/scenes/school.jpeg'),
};

// 获取场景图片
const getSceneImage = (characterId: string, sceneId: string): any | null => {
  // 目前只有 Sakura 有场景图片
  if (characterId === 'e3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e') {
    return SAKURA_SCENE_IMAGES[sceneId] || null;
  }
  return null;
};

// 场景背景渐变颜色
const SCENARIO_GRADIENTS: Record<string, string[]> = {
  cafe_paris: ['#2D1B00', '#5C3D2E', '#B85C38'],
  beach_sunset: ['#1A1A2E', '#FF6B6B', '#FFE66D'],
  rooftop_city: ['#0D1B2A', '#1B263B', '#415A77'],
  forest_walk: ['#1B4332', '#2D6A4F', '#52B788'],
  stargazing: ['#0D0D1A', '#1A1A3E', '#2E1A47'],
  default: ['#1A1025', '#2D1B4E', '#0D0815'],
};

// 角色表情映射（emoji 作为占位，后续可换成图片）
const EXPRESSIONS: Record<string, string> = {
  happy: '😊',
  shy: '😳',
  surprised: '😲',
  sad: '😢',
  neutral: '🙂',
  excited: '🥰',
  angry: '😠',
  thinking: '🤔',
};

interface DateOption {
  id: number;
  text: string;
  is_special?: boolean;
  is_locked?: boolean;
  requirement?: string;
}

interface DateStage {
  stage_num: number;
  narrative: string;
  character_expression: string;
  options: DateOption[];
  user_choice?: number;
  affection_change?: number;
  supports_free_input?: boolean;
}

interface DateScenario {
  id: string;
  name: string;
  icon: string;
  description?: string;
}

interface DateEnding {
  type: string;
  title: string;
  description: string;
}

interface DateRewards {
  xp: number;
  affection: number;
}

interface DateSceneModalProps {
  visible: boolean;
  onClose: () => void;
  characterId: string;
  characterName: string;
  characterAvatar?: string;
  scenarios: DateScenario[];
  onDateCompleted?: (result: any) => void;
}

// API helpers
const dateApi = {
  getStatus: async (characterId: string) => {
    return api.get(`/dates/status/${characterId}`);
  },
  
  startInteractive: async (characterId: string, scenarioId: string) => {
    return api.post('/dates/interactive/start', {
      character_id: characterId,
      scenario_id: scenarioId,
    });
  },
  
  makeChoice: async (sessionId: string, choiceId: number) => {
    return api.post('/dates/interactive/choose', {
      session_id: sessionId,
      choice_id: choiceId,
    });
  },
  
  sendFreeInput: async (sessionId: string, userInput: string) => {
    return api.post('/dates/interactive/free-input', {
      session_id: sessionId,
      user_input: userInput,
    });
  },
  
  abandonDate: async (sessionId: string) => {
    return api.post('/dates/interactive/abandon', {
      session_id: sessionId,
    });
  },
  
  getSession: async (sessionId: string) => {
    return api.get(`/dates/interactive/session/${sessionId}`);
  },
  
  resetCooldown: async (characterId: string) => {
    return api.post('/dates/interactive/reset-cooldown', {
      character_id: characterId,
    });
  },
  
  extendDate: async (sessionId: string) => {
    return api.post('/dates/interactive/extend', {
      session_id: sessionId,
    });
  },
  
  finishDate: async (sessionId: string) => {
    return api.post('/dates/interactive/finish', {
      session_id: sessionId,
    });
  },
};

type Phase = 'select' | 'playing' | 'checkpoint' | 'finale' | 'ending';

export default function DateSceneModal({
  visible,
  onClose,
  characterId,
  characterName,
  characterAvatar,
  scenarios,
  onDateCompleted,
}: DateSceneModalProps) {
  // State
  const [phase, setPhase] = useState<Phase>('select');
  const [selectedScenario, setSelectedScenario] = useState<DateScenario | null>(null);
  const [activeSceneId, setActiveSceneId] = useState<string | null>(null); // 保存当前场景ID
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<DateStage | null>(null);
  const [progress, setProgress] = useState({ current: 0, total: 5 });
  const [loading, setLoading] = useState(false);
  const [ending, setEnding] = useState<DateEnding | null>(null);
  const [rewards, setRewards] = useState<DateRewards | null>(null);
  const [storySummary, setStorySummary] = useState<string | null>(null);
  const [unlockedPhoto, setUnlockedPhoto] = useState<{scene: string; photo_type: string; is_new: boolean} | null>(null);
  const [finaleNarrative, setFinaleNarrative] = useState<string | null>(null); // 结局剧情
  const [pendingEndingResult, setPendingEndingResult] = useState<any>(null); // 暂存的结局数据
  const [canExtend, setCanExtend] = useState(true); // 是否可以继续延长剧情
  const [remainingExtends, setRemainingExtends] = useState(3); // 剩余可延长次数
  const [isExtended, setIsExtended] = useState(false); // 是否已经延长过（一次性30月石）
  const [extendLoading, setExtendLoading] = useState(false); // 延长加载状态
  const [affectionScore, setAffectionScore] = useState(50); // 起始好感度
  const [affectionFeedback, setAffectionFeedback] = useState<number | null>(null);
  const [showFreeInput, setShowFreeInput] = useState(false);
  const [shuffledOptions, setShuffledOptions] = useState<DateOption[]>([]);
  const [freeInputText, setFreeInputText] = useState('');
  const [judgeComment, setJudgeComment] = useState<string | null>(null);
  
  // 打字机效果状态
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showOptions, setShowOptions] = useState(false);
  const optionsOpacity = useRef(new Animated.Value(0)).current;
  const typingSpeed = 25; // ms per character
  const typingTimerRef = useRef<NodeJS.Timeout | null>(null); // 用于跳过时清除定时器
  
  const [cooldownInfo, setCooldownInfo] = useState<{
    inCooldown: boolean;
    remainingMinutes: number;
  } | null>(null);
  const [resettingCooldown, setResettingCooldown] = useState(false);
  const [activeSession, setActiveSession] = useState<{
    session_id: string;
    stage_num: number;
    scenario_name: string;
  } | null>(null);
  
  // Animations
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;
  const affectionAnim = useRef(new Animated.Value(0)).current;
  const finaleAnim = useRef(new Animated.Value(0)).current; // finale 淡入动画
  
  // Bottom sheet ref and snap points
  const bottomSheetRef = useRef<BottomSheet>(null);
  const snapPoints = useMemo(() => ['15%', '50%', '85%'], []);
  
  // TextInput ref for free input focus
  const freeInputRef = useRef<TextInput>(null);
  
  // Auto focus free input when opened and expand sheet
  useEffect(() => {
    if (showFreeInput) {
      // Expand sheet to max and focus input
      bottomSheetRef.current?.snapToIndex(2); // 85%
      setTimeout(() => {
        freeInputRef.current?.focus();
      }, 150);
    }
  }, [showFreeInput]);
  
  // Reset when modal opens and check cooldown
  useEffect(() => {
    if (visible) {
      setPhase('select');
      setSelectedScenario(null);
      setActiveSceneId(null);
      setSessionId(null);
      setCurrentStage(null);
      setEnding(null);
      setRewards(null);
      setStorySummary(null);
      setAffectionScore(50);
      setAffectionFeedback(null);
      setCooldownInfo(null);
      
      // Check cooldown status
      checkCooldown();
    }
  }, [visible]);
  
  // 情绪太低不能约会
  const [emotionTooLow, setEmotionTooLow] = useState<{
    currentEmotion: number;
    message: string;
  } | null>(null);

  // Check cooldown status and active session
  const checkCooldown = async () => {
    try {
      const status = await dateApi.getStatus(characterId);
      
      // Check for active session
      if (status.active_session) {
        setActiveSession(status.active_session);
      } else {
        setActiveSession(null);
      }
      
      // Check emotion (太生气不能约会)
      if (!status.can_date && status.reason === 'emotion_too_low') {
        setEmotionTooLow({
          currentEmotion: status.current_emotion,
          message: status.message || '她现在心情不好，不想和你约会',
        });
        setCooldownInfo(null);
        return;
      } else {
        setEmotionTooLow(null);
      }
      
      // Check cooldown
      if (!status.can_date && status.cooldown_remaining_minutes > 0 && !status.active_session) {
        setCooldownInfo({
          inCooldown: true,
          remainingMinutes: status.cooldown_remaining_minutes,
        });
      } else {
        setCooldownInfo(null);
      }
    } catch (e) {
      console.error('Failed to check cooldown:', e);
    }
  };
  
  // Reset cooldown with 月石
  const handleResetCooldown = async () => {
    setResettingCooldown(true);
    try {
      const result = await dateApi.resetCooldown(characterId);
      if (result.success) {
        setCooldownInfo(null);
        // Show success message
        setJudgeComment(`冷却已重置！消费 50 月石`);
        setTimeout(() => setJudgeComment(null), 2000);
      }
    } catch (e: any) {
      // 从错误响应中提取具体信息
      const errorMsg = e.response?.data?.detail || e.message || '重置失败';
      setJudgeComment(`💎 ${errorMsg}`);
      setTimeout(() => setJudgeComment(null), 3000);
    } finally {
      setResettingCooldown(false);
    }
  };
  
  // Animate stage transitions
  useEffect(() => {
    if (currentStage || ending) {
      fadeAnim.setValue(0);
      slideAnim.setValue(30);
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 400,
          useNativeDriver: true,
        }),
        Animated.timing(slideAnim, {
          toValue: 0,
          duration: 400,
          useNativeDriver: true,
        }),
      ]).start();
    }
  }, [currentStage, ending]);
  
  // Animate finale phase (淡入效果)
  useEffect(() => {
    if (phase === 'finale') {
      finaleAnim.setValue(0);
      Animated.timing(finaleAnim, {
        toValue: 1,
        duration: 800, // 较慢的淡入，更有仪式感
        useNativeDriver: true,
      }).start();
    }
  }, [phase]);
  
  // 打乱选项顺序（避免用户猜出好坏选项）
  useEffect(() => {
    if (currentStage?.options && currentStage.options.length > 0) {
      // Fisher-Yates shuffle
      const shuffled = [...currentStage.options];
      for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
      }
      setShuffledOptions(shuffled);
    } else {
      setShuffledOptions([]);
    }
  }, [currentStage?.stage_num]); // 只在阶段变化时重新打乱
  
  // 打字机效果
  useEffect(() => {
    if (currentStage?.narrative && phase === 'playing') {
      const fullText = currentStage.narrative;
      setDisplayedText('');
      setShowOptions(false);
      optionsOpacity.setValue(0);
      setIsTyping(true);
      
      // 清除之前的定时器
      if (typingTimerRef.current) {
        clearInterval(typingTimerRef.current);
      }
      
      let index = 0;
      typingTimerRef.current = setInterval(() => {
        if (index < fullText.length) {
          setDisplayedText(fullText.substring(0, index + 1));
          index++;
        } else {
          if (typingTimerRef.current) {
            clearInterval(typingTimerRef.current);
            typingTimerRef.current = null;
          }
          setIsTyping(false);
          // 延迟显示选项并淡入
          setTimeout(() => {
            setShowOptions(true);
            Animated.timing(optionsOpacity, {
              toValue: 1,
              duration: 400,
              useNativeDriver: true,
            }).start();
          }, 200);
        }
      }, typingSpeed);
      
      return () => {
        if (typingTimerRef.current) {
          clearInterval(typingTimerRef.current);
          typingTimerRef.current = null;
        }
      };
    }
  }, [currentStage?.narrative, currentStage?.stage_num]);
  
  // 点击跳过打字机效果
  const handleSkipTyping = () => {
    if (isTyping && currentStage?.narrative) {
      // 立即清除定时器，停止打字
      if (typingTimerRef.current) {
        clearInterval(typingTimerRef.current);
        typingTimerRef.current = null;
      }
      // 直接显示完整文字
      setDisplayedText(currentStage.narrative);
      setIsTyping(false);
      // 立即显示选项（不延迟）
      setShowOptions(true);
      Animated.timing(optionsOpacity, {
        toValue: 1,
        duration: 200,
        useNativeDriver: true,
      }).start();
    }
  };
  
  // Animate affection feedback
  useEffect(() => {
    if (affectionFeedback !== null) {
      affectionAnim.setValue(1);
      Animated.sequence([
        Animated.delay(1200),
        Animated.timing(affectionAnim, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start(() => setAffectionFeedback(null));
    }
  }, [affectionFeedback]);
  
  // Start date
  const handleStartDate = async () => {
    if (!selectedScenario) return;
    
    // 保存选中的场景ID（用于显示场景图片）
    const sceneIdToUse = selectedScenario.id;
    setActiveSceneId(sceneIdToUse);
    
    setLoading(true);
    try {
      const result = await dateApi.startInteractive(characterId, sceneIdToUse);
      if (result.success) {
        setSessionId(result.session_id);
        setCurrentStage(result.stage);
        setProgress(result.progress);
        setSelectedScenario(result.scenario);
        setIsExtended(false); // 重置延长状态
        setPhase('playing');
      }
    } catch (e: any) {
      console.error('Failed to start date:', e);
    } finally {
      setLoading(false);
    }
  };
  
  // Continue existing date
  const handleContinueDate = async () => {
    if (!activeSession) return;
    
    setLoading(true);
    try {
      const session = await dateApi.getSession(activeSession.session_id);
      if (session) {
        setSessionId(session.id);
        setAffectionScore(50 + (session.affection_score || 0));
        
        // 根据是否延长设置 total
        const extended = session.is_extended || false;
        setIsExtended(extended);
        setProgress({ 
          current: session.current_stage, 
          total: extended ? 8 : 5 
        });
        
        // Get last stage
        const lastStage = session.stages?.[session.stages.length - 1];
        if (lastStage) {
          setCurrentStage(lastStage);
        }
        
        setSelectedScenario({ 
          id: session.scenario_id, 
          name: session.scenario_name, 
          icon: '☕' 
        });
        setActiveSceneId(session.scenario_id); // 设置场景ID用于显示图片
        
        // 清除 activeSession 提示，避免重复显示
        setActiveSession(null);
        setPhase('playing');
      }
    } catch (e: any) {
      console.error('Failed to continue date:', e);
    } finally {
      setLoading(false);
    }
  };
  
  // Make choice
  const handleChoice = async (choiceId: number, option?: DateOption) => {
    if (!sessionId || loading) return;
    
    // 检查是否是锁定的特殊选项
    if (option?.is_locked) {
      // 显示提示
      setJudgeComment(option.requirement || '需要更高好感度');
      setTimeout(() => setJudgeComment(null), 2000);
      return;
    }
    
    setLoading(true);
    setShowFreeInput(false);
    
    try {
      const result = await dateApi.makeChoice(sessionId, choiceId);
      
      if (result.success) {
        // Show affection feedback
        if (result.affection_change !== undefined) {
          setAffectionFeedback(result.affection_change);
          setAffectionScore(prev => Math.max(0, Math.min(100, prev + result.affection_change)));
        }
        
        if (result.at_checkpoint) {
          // 到达检查点 - 让用户选择是否继续
          setCanExtend(result.can_extend);
          setRemainingExtends(result.remaining_extends);
          setProgress(result.progress);
          setPhase('checkpoint');
        } else if (result.completed) {
          // Date completed - first show finale, then ending
          // Store result for later
          setPendingEndingResult(result);
          setEnding(result.ending);
          setRewards(result.rewards);
          setStorySummary(result.story_summary);
          setUnlockedPhoto(result.unlocked_photo || null);
          
          // 生成结局叙述：使用 story_summary 的最后部分，或者 ending.description
          const finaleText = result.finale_narrative || 
            result.ending?.description ||
            '约会结束了，你们依依不舍地告别...';
          setFinaleNarrative(finaleText);
          
          // 先进入 finale 阶段，不是直接 ending
          setPhase('finale');
          // 注意：不在这里调用 onDateCompleted，等用户看完结局后再调用
        } else {
          // Next stage
          setCurrentStage(result.stage);
          setProgress(result.progress);
        }
      }
    } catch (e: any) {
      console.error('Failed to make choice:', e);
    } finally {
      setLoading(false);
    }
  };
  
  // Handle free input
  const handleFreeInput = async () => {
    if (!sessionId || loading || !freeInputText.trim()) return;
    
    Keyboard.dismiss();
    setLoading(true);
    setShowFreeInput(false);
    
    try {
      const result = await dateApi.sendFreeInput(sessionId, freeInputText.trim());
      
      if (result.success) {
        // Show judge comment
        if (result.judge_comment) {
          setJudgeComment(result.judge_comment);
          setTimeout(() => setJudgeComment(null), 2000);
        }
        
        // Show affection feedback
        if (result.affection_change !== undefined) {
          setAffectionFeedback(result.affection_change);
          setAffectionScore(prev => Math.max(0, Math.min(100, prev + result.affection_change)));
        }
        
        if (result.at_checkpoint) {
          // 到达检查点
          setCanExtend(result.can_extend);
          setRemainingExtends(result.remaining_extends);
          setProgress(result.progress);
          setPhase('checkpoint');
        } else if (result.completed) {
          // Date completed - first show finale, then ending
          setPendingEndingResult(result);
          setEnding(result.ending);
          setRewards(result.rewards);
          setStorySummary(result.story_summary);
          setUnlockedPhoto(result.unlocked_photo || null);
          
          const finaleText = result.finale_narrative || 
            result.ending?.description ||
            '约会结束了，你们依依不舍地告别...';
          setFinaleNarrative(finaleText);
          
          setPhase('finale');
        } else {
          setCurrentStage(result.stage);
          setProgress(result.progress);
        }
        
        setFreeInputText('');
      }
    } catch (e: any) {
      console.error('Failed to send free input:', e);
      setJudgeComment('发送失败，请重试');
      setTimeout(() => setJudgeComment(null), 2000);
    } finally {
      setLoading(false);
    }
  };
  
  // 暂时退出（保持约会进行中，可以继续）
  const handlePause = () => {
    onClose();
  };
  
  // 放弃约会（彻底结束，不可继续）
  const handleAbandon = async () => {
    if (!sessionId) {
      onClose();
      return;
    }
    
    try {
      await dateApi.abandonDate(sessionId);
    } catch (e) {
      console.error('Failed to abandon date:', e);
    }
    onClose();
  };
  
  // 付费延长剧情
  const handleExtend = async () => {
    if (!sessionId || extendLoading) return;
    
    setExtendLoading(true);
    try {
      const result = await dateApi.extendDate(sessionId);
      
      if (result.success) {
        // 标记已延长（一次性解锁3阶段）
        setIsExtended(true);
        setCanExtend(false); // 已延长，不能再次延长
        setRemainingExtends(0);
        
        // 回到 playing 阶段，显示新剧情
        setCurrentStage(result.stage);
        setProgress(result.progress); // 后端返回 x/8
        setPhase('playing');
        
        // 显示扣费提示
        const cost = result.credits_deducted || 30;
        setJudgeComment(`💎 -${cost} 月石，解锁后续3章剧情！`);
        setTimeout(() => setJudgeComment(null), 2500);
      }
    } catch (e: any) {
      const errorMsg = e.response?.data?.detail || e.message || '延长失败';
      setJudgeComment(`❌ ${errorMsg}`);
      setTimeout(() => setJudgeComment(null), 3000);
    } finally {
      setExtendLoading(false);
    }
  };
  
  // 结束约会（在 checkpoint 阶段选择不延长）
  const handleFinish = async () => {
    if (!sessionId || loading) return;
    
    setLoading(true);
    try {
      const result = await dateApi.finishDate(sessionId);
      
      if (result.success && result.completed) {
        // 进入结局
        setPendingEndingResult(result);
        setEnding(result.ending);
        setRewards(result.rewards);
        setStorySummary(result.story_summary);
        setUnlockedPhoto(result.unlocked_photo || null);
        
        const finaleText = result.finale_narrative || 
          result.ending?.description ||
          '约会结束了，你们依依不舍地告别...';
        setFinaleNarrative(finaleText);
        
        setPhase('finale');
      }
    } catch (e: any) {
      console.error('Failed to finish date:', e);
      const errorMsg = e.response?.data?.detail || '结束失败';
      setJudgeComment(`❌ ${errorMsg}`);
      setTimeout(() => setJudgeComment(null), 3000);
    } finally {
      setLoading(false);
    }
  };
  
  // Get background gradient
  const getBackgroundGradient = (): string[] => {
    if (selectedScenario?.id && SCENARIO_GRADIENTS[selectedScenario.id]) {
      return SCENARIO_GRADIENTS[selectedScenario.id];
    }
    return SCENARIO_GRADIENTS.default;
  };
  
  // Get expression emoji
  const getExpression = (): string => {
    return EXPRESSIONS[currentStage?.character_expression || 'neutral'] || '🙂';
  };
  
  // Render scenario selection
  const renderScenarioSelect = () => (
    <View style={styles.selectContainer}>
      {/* 顶部栏：返回按钮 */}
      <View style={styles.selectHeader}>
        <TouchableOpacity style={styles.cancelBtn} onPress={onClose}>
          <Ionicons name="chevron-back" size={24} color="#fff" />
          <Text style={styles.cancelBtnText}>返回</Text>
        </TouchableOpacity>
      </View>
      
      <Text style={styles.selectTitle}>选择约会地点</Text>
      <Text style={styles.selectSubtitle}>和 {characterName} 去哪里？</Text>
      
      {/* 情绪太低提示 */}
      {emotionTooLow && !activeSession && (
        <View style={styles.emotionWarningBox}>
          <Text style={styles.emotionWarningIcon}>😤</Text>
          <Text style={styles.emotionWarningText}>
            {emotionTooLow.message}
          </Text>
          <Text style={styles.emotionWarningHint}>
            💡 送她一份礼物来改善心情吧
          </Text>
        </View>
      )}
      
      {/* Cooldown 提示 */}
      {cooldownInfo?.inCooldown && !activeSession && !emotionTooLow && (
        <View style={styles.cooldownBox}>
          <Text style={styles.cooldownIcon}>⏰</Text>
          <Text style={styles.cooldownText}>
            约会冷却中，还需等待 {cooldownInfo.remainingMinutes} 分钟
          </Text>
          <TouchableOpacity 
            style={styles.resetCooldownBtn}
            onPress={handleResetCooldown}
            disabled={resettingCooldown}
          >
            {resettingCooldown ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <>
                <Text style={styles.resetCooldownText}>立即重置</Text>
                <Text style={styles.resetCooldownPrice}>💎 50</Text>
              </>
            )}
          </TouchableOpacity>
        </View>
      )}
      
      <ScrollView style={styles.scenarioList} showsVerticalScrollIndicator={false}>
        {scenarios.map((scenario) => {
          const isLocked = (scenario as any).is_locked;
          const requiredLevel = (scenario as any).required_level;
          
          return (
            <TouchableOpacity
              key={scenario.id}
              style={[
                styles.scenarioItem,
                selectedScenario?.id === scenario.id && styles.scenarioItemSelected,
                isLocked && styles.scenarioItemLocked,
              ]}
              onPress={() => {
                if (isLocked) {
                  setJudgeComment(`🔒 需要 Lv.${requiredLevel} 解锁`);
                  setTimeout(() => setJudgeComment(null), 2000);
                } else {
                  setSelectedScenario(scenario);
                }
              }}
            >
              <Text style={[styles.scenarioIcon, isLocked && styles.scenarioIconLocked]}>
                {isLocked ? '🔒' : scenario.icon}
              </Text>
              <View style={styles.scenarioInfo}>
                <View style={styles.scenarioNameRow}>
                  <Text style={[styles.scenarioName, isLocked && styles.scenarioNameLocked]}>
                    {scenario.name}
                  </Text>
                  {isLocked && requiredLevel && (
                    <Text style={styles.scenarioLevelBadge}>Lv.{requiredLevel}</Text>
                  )}
                </View>
                {scenario.description && (
                  <Text style={[styles.scenarioDesc, isLocked && styles.scenarioDescLocked]} numberOfLines={1}>
                    {scenario.description}
                  </Text>
                )}
              </View>
              {!isLocked && selectedScenario?.id === scenario.id && (
                <Ionicons name="checkmark-circle" size={24} color="#FF6B9D" />
              )}
            </TouchableOpacity>
          );
        })}
      </ScrollView>
      
      <TouchableOpacity
        style={[styles.startButton, (!selectedScenario || cooldownInfo?.inCooldown || emotionTooLow || activeSession) && styles.startButtonDisabled]}
        onPress={handleStartDate}
        disabled={!selectedScenario || loading || cooldownInfo?.inCooldown || !!emotionTooLow || !!activeSession}
      >
        <LinearGradient
          colors={selectedScenario && !activeSession ? ['#FF6B9D', '#C44569'] : ['#666', '#444']}
          style={styles.startButtonGradient}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.startButtonText}>💕 开始约会</Text>
          )}
        </LinearGradient>
      </TouchableOpacity>
      
      {/* 未完成约会遮罩 - 居中覆盖 */}
      {activeSession && (
        <View style={styles.activeSessionOverlay}>
          <View style={styles.activeSessionCard}>
            <Text style={styles.activeSessionIcon}>💕</Text>
            <Text style={styles.activeSessionText}>
              有一场未完成的约会
            </Text>
            <Text style={styles.activeSessionDetail}>
              {activeSession.scenario_name} · 第 {activeSession.stage_num} 阶段
            </Text>
            <View style={styles.activeSessionButtons}>
              <TouchableOpacity 
                style={styles.continueBtn}
                onPress={handleContinueDate}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text style={styles.continueBtnText}>继续约会</Text>
                )}
              </TouchableOpacity>
              <TouchableOpacity 
                style={styles.abandonBtn}
                onPress={async () => {
                  try {
                    await dateApi.abandonDate(activeSession.session_id);
                    setActiveSession(null);
                    checkCooldown();
                  } catch (e) {
                    console.error('Failed to abandon:', e);
                  }
                }}
              >
                <Text style={styles.abandonBtnText}>放弃</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}
    </View>
  );
  
  // Render playing phase (新布局)
  const renderPlaying = () => (
    <LinearGradient colors={getBackgroundGradient()} style={styles.playingContainer}>
      {/* === 顶部状态栏 === */}
      <View style={styles.topBar}>
        {/* 返回按钮 */}
        <TouchableOpacity onPress={handlePause} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={24} color="#fff" />
        </TouchableOpacity>
        
        {/* 好感度 */}
        <View style={styles.affectionContainer}>
          <Text style={styles.heartIcon}>❤️</Text>
          <View style={styles.affectionBarBg}>
            <View style={[styles.affectionBarFill, { width: `${affectionScore}%` }]} />
          </View>
          <Text style={styles.affectionText}>{affectionScore}</Text>
        </View>
        
        {/* 阶段进度 + 延长按钮 */}
        <View style={styles.phaseContainer}>
          <Text style={styles.phaseText}>PHASE {progress.current} / {progress.total}</Text>
          {/* ➕ 延长按钮：未延长且未结束时显示 */}
          {!isExtended && !ending && progress.total === 5 && (
            <TouchableOpacity
              style={styles.extendPlusButton}
              onPress={handleExtend}
              disabled={extendLoading}
            >
              {extendLoading ? (
                <ActivityIndicator size="small" color="#FFD700" />
              ) : (
                <Text style={styles.extendPlusText}>➕</Text>
              )}
            </TouchableOpacity>
          )}
        </View>
      </View>
      
      {/* === 好感度变化反馈 === */}
      {affectionFeedback !== null && (
        <Animated.View style={[styles.affectionFeedback, { opacity: affectionAnim }]}>
          <Text style={[
            styles.affectionFeedbackText,
            affectionFeedback > 0 ? styles.affectionPositive : 
            affectionFeedback < 0 ? styles.affectionNegative : styles.affectionNeutral
          ]}>
            {affectionFeedback > 0 ? `+${affectionFeedback}` : affectionFeedback}
            {affectionFeedback > 0 ? ' ❤️' : affectionFeedback < 0 ? ' 💔' : ''}
          </Text>
        </Animated.View>
      )}
      
      {/* === 中间区域 - 场景图片或角色立绘 === */}
      <View style={styles.middleArea}>
        {(() => {
          // 优先使用 activeSceneId（约会进行中），否则用 selectedScenario
          const sceneId = activeSceneId || selectedScenario?.id;
          const sceneImage = sceneId ? getSceneImage(characterId, sceneId) : null;
          
          if (sceneImage) {
            return (
              <Image 
                source={sceneImage} 
                style={styles.sceneImage}
                resizeMode="cover"
              />
            );
          } else if (characterId) {
            return (
              <Image 
                source={getCharacterAvatar(characterId, characterAvatar)} 
                style={styles.backgroundAvatar}
                resizeMode="contain"
              />
            );
          } else {
            return <Text style={styles.scenarioEmoji}>{selectedScenario?.icon || '✨'}</Text>;
          }
        })()}
      </View>
      
      {/* === 底部对话框 - 使用 BottomSheet === */}
      <BottomSheet
        ref={bottomSheetRef}
        index={1}
        snapPoints={snapPoints}
        backgroundStyle={styles.bottomSheetBackground}
        handleIndicatorStyle={styles.bottomSheetIndicator}
        keyboardBehavior="interactive"
        keyboardBlurBehavior="restore"
        android_keyboardInputMode="adjustResize"
      >
        <BottomSheetScrollView 
          contentContainerStyle={styles.bottomSheetContent}
          keyboardShouldPersistTaps="handled"
        >
          {/* 角色名 */}
          <Text style={styles.dialogCharacterName}>{characterName}</Text>
          
          {/* 剧情文字 */}
          <Text style={styles.narrativeText}>
            {displayedText || '...'}
            {isTyping && <Text style={styles.typingCursor}>▌</Text>}
          </Text>
          
          {/* 跳过按钮 */}
          {isTyping && (
            <TouchableOpacity style={styles.skipButton} onPress={handleSkipTyping}>
              <Text style={styles.skipHint}>跳过 →</Text>
            </TouchableOpacity>
          )}
          
          {/* 评判评论 */}
          {judgeComment && (
            <View style={styles.judgeCommentBox}>
              <Text style={styles.judgeCommentText}>{judgeComment}</Text>
            </View>
          )}
          
          {/* 选项/输入 - 打字完成后淡入 */}
          <Animated.View style={[styles.optionsContainer, { opacity: optionsOpacity }]}>
            {loading ? (
              <ActivityIndicator size="large" color="#FF6B9D" style={{ marginVertical: 20 }} />
            ) : !showOptions ? null : showFreeInput ? (
              /* 自由输入模式 */
              <View style={styles.freeInputContainer}>
                <TextInput
                  ref={freeInputRef}
                  style={styles.freeInputField}
                  placeholder="说点什么..."
                  placeholderTextColor="rgba(255,255,255,0.4)"
                  value={freeInputText}
                  onChangeText={setFreeInputText}
                  multiline
                  maxLength={200}
                />
                <View style={styles.freeInputButtons}>
                  <TouchableOpacity 
                    style={styles.freeInputCancel}
                    onPress={() => {
                      Keyboard.dismiss();
                      setShowFreeInput(false);
                      setFreeInputText('');
                      bottomSheetRef.current?.snapToIndex(1); // 恢复到 50%
                    }}
                  >
                    <Text style={styles.freeInputCancelText}>取消</Text>
                  </TouchableOpacity>
                  <TouchableOpacity 
                    style={[styles.freeInputSend, !freeInputText.trim() && styles.freeInputSendDisabled]}
                    onPress={handleFreeInput}
                    disabled={!freeInputText.trim()}
                  >
                    <Text style={styles.freeInputSendText}>发送</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ) : (
              /* 选项模式 */
              <>
                {shuffledOptions.map((option) => (
                  <TouchableOpacity
                    key={option.id}
                    style={[
                      styles.optionButton,
                      option.is_special && styles.optionSpecial,
                      option.is_locked && styles.optionLocked,
                    ]}
                    onPress={() => handleChoice(option.id, option)}
                    disabled={loading}
                  >
                    <Text style={[
                      styles.optionText,
                      option.is_special && styles.optionTextSpecial,
                      option.is_locked && styles.optionTextLocked,
                    ]}>
                      {option.is_special && '✨ '}
                      {option.text}
                      {option.is_locked && ` 🔒`}
                    </Text>
                  </TouchableOpacity>
                ))}
                
                {/* 自由输入入口 */}
                <TouchableOpacity
                  style={styles.freeInputTrigger}
                  onPress={() => setShowFreeInput(true)}
                >
                  <Ionicons name="chatbubble-ellipses-outline" size={16} color="rgba(255,255,255,0.5)" />
                  <Text style={styles.freeInputTriggerText}>我想自己说点什么...</Text>
                </TouchableOpacity>
              </>
            )}
          </Animated.View>
        </BottomSheetScrollView>
      </BottomSheet>
    </LinearGradient>
  );
  
  // Render checkpoint phase (选择是否继续约会)
  const renderCheckpoint = () => (
    <LinearGradient colors={getBackgroundGradient()} style={styles.playingContainer}>
      {/* 顶部状态栏 */}
      <View style={styles.topBar}>
        <View style={styles.backBtn} />
        
        {/* 好感度 */}
        <View style={styles.affectionContainer}>
          <Text style={styles.heartIcon}>❤️</Text>
          <View style={styles.affectionBarBg}>
            <View style={[styles.affectionBarFill, { width: `${affectionScore}%` }]} />
          </View>
          <Text style={styles.affectionText}>{affectionScore}</Text>
        </View>
        
        {/* 阶段进度 */}
        <View style={styles.phaseContainer}>
          <Text style={styles.phaseText}>PHASE {progress.current} / {progress.total}</Text>
        </View>
      </View>
      
      {/* 中间区域 - 场景图片 */}
      <View style={styles.middleArea}>
        {(() => {
          const sceneId = activeSceneId || selectedScenario?.id;
          const sceneImage = sceneId ? getSceneImage(characterId, sceneId) : null;
          
          if (sceneImage) {
            return (
              <Image 
                source={sceneImage} 
                style={styles.sceneImage}
                resizeMode="cover"
              />
            );
          } else if (characterId) {
            return (
              <Image 
                source={getCharacterAvatar(characterId, characterAvatar)} 
                style={styles.backgroundAvatar}
                resizeMode="contain"
              />
            );
          } else {
            return <Text style={styles.scenarioEmoji}>{selectedScenario?.icon || '✨'}</Text>;
          }
        })()}
      </View>
      
      {/* 底部选择区域 */}
      <BottomSheet
        ref={bottomSheetRef}
        index={1}
        snapPoints={snapPoints}
        backgroundStyle={styles.bottomSheetBackground}
        handleIndicatorStyle={styles.bottomSheetIndicator}
      >
        <BottomSheetScrollView contentContainerStyle={styles.bottomSheetContent}>
          {/* 标题 */}
          <View style={styles.checkpointHeader}>
            <Text style={styles.checkpointIcon}>✨</Text>
            <Text style={styles.checkpointTitle}>约会进行得很顺利...</Text>
          </View>
          
          <Text style={styles.checkpointText}>
            基础章节已完成！要继续享受更多甜蜜时光吗？
          </Text>
          
          {/* 选择按钮 */}
          <View style={styles.checkpointButtons}>
            {/* 继续剧情按钮 */}
            {canExtend && remainingExtends > 0 && (
              <TouchableOpacity
                style={styles.extendButton}
                onPress={handleExtend}
                disabled={extendLoading || loading}
              >
                <LinearGradient
                  colors={['#FFD700', '#FFA500']}
                  style={styles.extendButtonGradient}
                >
                  {extendLoading ? (
                    <ActivityIndicator size="small" color="#fff" />
                  ) : (
                    <>
                      <Text style={styles.extendButtonText}>💎 继续剧情</Text>
                      <Text style={styles.extendButtonPrice}>10 月石 · 还能延长{remainingExtends}次</Text>
                    </>
                  )}
                </LinearGradient>
              </TouchableOpacity>
            )}
            
            {/* 结束约会按钮 */}
            <TouchableOpacity
              style={styles.finishButton}
              onPress={handleFinish}
              disabled={loading || extendLoading}
            >
              {loading ? (
                <ActivityIndicator size="small" color="#FF6B9D" />
              ) : (
                <Text style={styles.finishButtonText}>结束约会，查看结局 →</Text>
              )}
            </TouchableOpacity>
          </View>
        </BottomSheetScrollView>
      </BottomSheet>
    </LinearGradient>
  );
  
  // Render finale phase (结局剧情展示，无选项)
  const renderFinale = () => (
    <LinearGradient colors={getBackgroundGradient()} style={styles.playingContainer}>
      {/* 顶部状态栏 */}
      <View style={styles.topBar}>
        <View style={styles.backBtn} />
        
        {/* 好感度 */}
        <View style={styles.affectionContainer}>
          <Text style={styles.heartIcon}>❤️</Text>
          <View style={styles.affectionBarBg}>
            <View style={[styles.affectionBarFill, { width: `${affectionScore}%` }]} />
          </View>
          <Text style={styles.affectionText}>{affectionScore}</Text>
        </View>
        
        {/* 完结标记 */}
        <View style={styles.phaseContainer}>
          <Text style={styles.phaseText}>~ THE END ~</Text>
        </View>
      </View>
      
      {/* 中间区域 - 场景图片 */}
      <View style={styles.middleArea}>
        {(() => {
          const sceneId = activeSceneId || selectedScenario?.id;
          const sceneImage = sceneId ? getSceneImage(characterId, sceneId) : null;
          
          if (sceneImage) {
            return (
              <Image 
                source={sceneImage} 
                style={styles.sceneImage}
                resizeMode="cover"
              />
            );
          } else if (characterId) {
            return (
              <Image 
                source={getCharacterAvatar(characterId, characterAvatar)} 
                style={styles.backgroundAvatar}
                resizeMode="contain"
              />
            );
          } else {
            return <Text style={styles.scenarioEmoji}>{selectedScenario?.icon || '✨'}</Text>;
          }
        })()}
      </View>
      
      {/* 底部结局剧情 */}
      <BottomSheet
        ref={bottomSheetRef}
        index={1}
        snapPoints={snapPoints}
        backgroundStyle={styles.bottomSheetBackground}
        handleIndicatorStyle={styles.bottomSheetIndicator}
      >
        <BottomSheetScrollView contentContainerStyle={styles.bottomSheetContent}>
          <Animated.View style={{ opacity: finaleAnim }}>
            {/* 结局标题 */}
            <View style={styles.finaleHeader}>
              <Text style={styles.finaleIcon}>
                {ending?.type === 'perfect' ? '💕' :
                 ending?.type === 'good' ? '😊' :
                 ending?.type === 'normal' ? '🙂' : '😅'}
              </Text>
              <Text style={styles.finaleTitle}>{ending?.title || '约会结束'}</Text>
            </View>
            
            {/* 结局剧情文字 */}
            <Text style={styles.finaleNarrativeText}>
              {finaleNarrative}
            </Text>
            
            {/* 查看结算按钮 */}
            <TouchableOpacity
              style={styles.finaleContinueButton}
              onPress={() => {
                // 切换到 ending 结算页面
                setPhase('ending');
                // 现在才通知父组件完成（如果需要的话）
                if (pendingEndingResult) {
                  onDateCompleted?.(pendingEndingResult);
                }
              }}
            >
              <LinearGradient
                colors={['#FF6B9D', '#C44569']}
                style={styles.finaleContinueGradient}
              >
                <Text style={styles.finaleContinueText}>查看结算 →</Text>
              </LinearGradient>
            </TouchableOpacity>
          </Animated.View>
        </BottomSheetScrollView>
      </BottomSheet>
    </LinearGradient>
  );
  
  // Render ending phase
  const renderEnding = () => (
    <LinearGradient colors={['#1A1025', '#2D1B4E']} style={styles.endingContainer}>
      <Animated.View
        style={[
          styles.endingContent,
          { opacity: fadeAnim, transform: [{ translateY: slideAnim }] },
        ]}
      >
        {/* Ending Icon */}
        <Text style={styles.endingIcon}>
          {ending?.type === 'perfect' ? '💕' :
           ending?.type === 'good' ? '😊' :
           ending?.type === 'normal' ? '🙂' : '😅'}
        </Text>
        
        {/* Title */}
        <Text style={styles.endingTitle}>{ending?.title}</Text>
        <Text style={styles.endingDescription}>{ending?.description}</Text>
        
        {/* Rewards */}
        {rewards && (
          <View style={styles.rewardsBox}>
            <Text style={styles.rewardsTitle}>🎁 获得奖励</Text>
            <Text style={styles.rewardsText}>
              +{rewards.xp} XP
            </Text>
          </View>
        )}
        
        {/* Unlocked Photo */}
        {unlockedPhoto?.is_new && (
          <View style={[styles.rewardsBox, { backgroundColor: 'rgba(236, 72, 153, 0.15)', borderColor: 'rgba(236, 72, 153, 0.3)' }]}>
            <Text style={styles.rewardsTitle}>📸 解锁新照片</Text>
            <Text style={[styles.rewardsText, { color: '#EC4899' }]}>
              {unlockedPhoto.photo_type === 'perfect' ? '💕 特别版照片' : '📷 普通照片'}
            </Text>
            <Text style={{ color: '#888', fontSize: 12, marginTop: 4 }}>
              前往相册查看
            </Text>
          </View>
        )}
        
        {/* Story Summary Saved Notice */}
        {storySummary && (
          <View style={styles.summaryBox}>
            <Text style={styles.summaryTitle}>📖 回忆已保存</Text>
          </View>
        )}
        
        {/* Done Button */}
        <TouchableOpacity style={styles.doneButton} onPress={onClose}>
          <LinearGradient
            colors={['#FF6B9D', '#C44569']}
            style={styles.doneButtonGradient}
          >
            <Text style={styles.doneButtonText}>完成</Text>
          </LinearGradient>
        </TouchableOpacity>
      </Animated.View>
    </LinearGradient>
  );
  
  return (
    <Modal
      visible={visible}
      animationType="fade"
      statusBarTranslucent
      onRequestClose={handlePause}
    >
      <View style={styles.container}>
        {phase === 'select' && renderScenarioSelect()}
        {phase === 'playing' && renderPlaying()}
        {phase === 'checkpoint' && renderCheckpoint()}
        {phase === 'finale' && renderFinale()}
        {phase === 'ending' && renderEnding()}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1A1025',
  },
  
  // === Scenario Selection ===
  selectContainer: {
    flex: 1,
    padding: 20,
    paddingTop: 50,
  },
  selectHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  cancelBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingRight: 12,
  },
  cancelBtnText: {
    color: '#fff',
    fontSize: 16,
    marginLeft: 4,
  },
  selectTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#fff',
    textAlign: 'center',
    marginBottom: 8,
    marginTop: 20,
  },
  selectSubtitle: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.6)',
    textAlign: 'center',
    marginBottom: 20,
  },
  
  // 继续约会遮罩
  activeSessionOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 100,
  },
  activeSessionCard: {
    backgroundColor: 'rgba(30,20,40,0.98)',
    borderRadius: 20,
    padding: 24,
    marginHorizontal: 30,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,107,157,0.3)',
  },
  // 旧样式保留兼容
  activeSessionBox: {
    backgroundColor: 'rgba(255,107,157,0.15)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 20,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,107,157,0.3)',
  },
  activeSessionIcon: {
    fontSize: 28,
    marginBottom: 8,
  },
  activeSessionText: {
    color: '#FF6B9D',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  activeSessionDetail: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: 14,
    marginBottom: 12,
  },
  activeSessionButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  continueBtn: {
    backgroundColor: '#FF6B9D',
    paddingVertical: 10,
    paddingHorizontal: 24,
    borderRadius: 20,
  },
  continueBtnText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  abandonBtn: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 20,
  },
  abandonBtnText: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 14,
  },
  
  // 情绪太低提示
  emotionWarningBox: {
    backgroundColor: 'rgba(255,100,100,0.15)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 20,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,100,100,0.3)',
  },
  emotionWarningIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  emotionWarningText: {
    color: '#FF6B6B',
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 8,
  },
  emotionWarningHint: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: 12,
    textAlign: 'center',
  },
  
  // Cooldown 提示
  cooldownBox: {
    backgroundColor: 'rgba(255,165,0,0.15)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 20,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,165,0,0.3)',
  },
  cooldownIcon: {
    fontSize: 28,
    marginBottom: 8,
  },
  cooldownText: {
    color: '#FFA500',
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 12,
  },
  resetCooldownBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FF6B9D',
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 20,
    gap: 8,
  },
  resetCooldownText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  resetCooldownPrice: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
  },
  
  scenarioList: {
    flex: 1,
  },
  scenarioItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  scenarioItemSelected: {
    borderColor: '#FF6B9D',
    backgroundColor: 'rgba(255,107,157,0.1)',
  },
  scenarioIcon: {
    fontSize: 36,
    marginRight: 16,
  },
  scenarioInfo: {
    flex: 1,
  },
  scenarioName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  scenarioDesc: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.5)',
    marginTop: 4,
  },
  // 锁定状态样式
  scenarioItemLocked: {
    opacity: 0.6,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  scenarioIconLocked: {
    opacity: 0.7,
  },
  scenarioNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  scenarioNameLocked: {
    color: 'rgba(255,255,255,0.5)',
  },
  scenarioLevelBadge: {
    marginLeft: 8,
    paddingHorizontal: 8,
    paddingVertical: 2,
    backgroundColor: 'rgba(255,107,157,0.3)',
    borderRadius: 8,
    fontSize: 12,
    color: '#FF6B9D',
    fontWeight: '600',
  },
  scenarioDescLocked: {
    color: 'rgba(255,255,255,0.3)',
  },
  startButton: {
    marginTop: 20,
    marginBottom: 40,
  },
  startButtonDisabled: {
    opacity: 0.5,
  },
  startButtonGradient: {
    paddingVertical: 18,
    borderRadius: 16,
    alignItems: 'center',
  },
  startButtonText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  
  // === Playing Phase (新布局) ===
  playingContainer: {
    flex: 1,
  },
  
  // 顶部状态栏
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 50,
    paddingHorizontal: 16,
    paddingBottom: 10,
    zIndex: 10, // 确保在场景图片之上
  },
  backBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(0,0,0,0.3)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  
  // 好感度
  affectionContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    marginLeft: 10,
  },
  heartIcon: {
    fontSize: 16,
    marginRight: 6,
  },
  affectionBarBg: {
    flex: 1,
    maxWidth: 80,
    height: 6,
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 3,
    overflow: 'hidden',
  },
  affectionBarFill: {
    height: '100%',
    backgroundColor: '#FF6B9D',
    borderRadius: 3,
  },
  affectionText: {
    color: '#fff',
    fontSize: 12,
    marginLeft: 6,
    fontWeight: '600',
  },
  
  // 角色头像
  characterAvatarContainer: {
    alignItems: 'center',
    marginHorizontal: 15,
  },
  characterAvatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
    borderWidth: 3,
    borderColor: '#FF6B9D',
  },
  characterAvatarPlaceholder: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: 'rgba(255,107,157,0.3)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#FF6B9D',
  },
  expressionEmoji: {
    fontSize: 32,
  },
  
  // 阶段进度
  phaseContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.4)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    gap: 6,
  },
  phaseText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 1,
  },
  extendPlusButton: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: 'rgba(255, 215, 0, 0.3)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 215, 0, 0.5)',
  },
  extendPlusText: {
    fontSize: 12,
  },
  
  // 好感度反馈
  affectionFeedback: {
    position: 'absolute',
    top: 120,
    alignSelf: 'center',
    backgroundColor: 'rgba(0,0,0,0.7)',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
    zIndex: 100,
  },
  affectionFeedbackText: {
    fontSize: 18,
    fontWeight: '700',
  },
  affectionPositive: {
    color: '#6BCB77',
  },
  affectionNegative: {
    color: '#FF6B6B',
  },
  affectionNeutral: {
    color: '#FFD93D',
  },
  
  // 中间区域 - 场景图片/角色立绘展示（背景层）
  middleArea: {
    position: 'absolute',
    top: 0, // 从顶部开始
    left: 0,
    right: 0,
    height: SCREEN_HEIGHT * 0.55, // 占屏幕 55%，给 BottomSheet 留空间
    justifyContent: 'flex-start',
    alignItems: 'center',
    overflow: 'hidden',
    zIndex: -1, // 放在最底层，不覆盖任何 UI
  },
  backgroundAvatar: {
    width: SCREEN_WIDTH * 0.85,
    height: SCREEN_HEIGHT * 0.55,
    marginTop: 60, // 给顶部状态栏留空间
    opacity: 1,
  },
  sceneImage: {
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT * 0.55,
  },
  scenarioEmoji: {
    fontSize: 64,
    opacity: 0.25,
  },
  
  // 底部对话框 - BottomSheet
  bottomSheetBackground: {
    backgroundColor: 'rgba(20, 15, 30, 0.98)',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
  },
  bottomSheetIndicator: {
    backgroundColor: 'rgba(255, 255, 255, 0.4)',
    width: 40,
  },
  bottomSheetContent: {
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
  typingCursor: {
    color: '#FF6B9D',
    fontWeight: '300',
  },
  skipButton: {
    alignSelf: 'flex-end',
    backgroundColor: 'rgba(255,107,157,0.4)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 16,
    marginBottom: 12,
  },
  skipHint: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '500',
  },
  dialogCharacterName: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FF6B9D',
    marginBottom: 12,
  },
  narrativeText: {
    fontSize: 16,
    color: '#fff',
    lineHeight: 26,
    letterSpacing: 0.3,
    marginBottom: 16,
  },
  
  // 评判评论
  judgeCommentBox: {
    backgroundColor: 'rgba(255,107,157,0.2)',
    borderRadius: 8,
    padding: 10,
    marginBottom: 12,
  },
  judgeCommentText: {
    color: '#FF6B9D',
    fontSize: 14,
    textAlign: 'center',
    fontStyle: 'italic',
  },
  
  // 选项
  optionsContainer: {
    gap: 8,
    marginTop: 8,
  },
  optionButton: {
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  optionSpecial: {
    backgroundColor: 'rgba(255,215,0,0.1)',
    borderColor: 'rgba(255,215,0,0.3)',
  },
  optionLocked: {
    backgroundColor: 'rgba(100,100,100,0.2)',
    borderColor: 'rgba(100,100,100,0.3)',
  },
  optionText: {
    fontSize: 14,
    color: '#fff',
    textAlign: 'center',
    lineHeight: 20,
  },
  optionTextSpecial: {
    color: '#FFD700',
  },
  optionTextLocked: {
    color: 'rgba(255,255,255,0.4)',
  },
  
  // 自由输入入口
  freeInputTrigger: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    gap: 6,
  },
  freeInputTriggerText: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 14,
  },
  
  // 自由输入框
  freeInputContainer: {
    gap: 12,
  },
  freeInputField: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 12,
    padding: 14,
    color: '#fff',
    fontSize: 15,
    minHeight: 80,
    textAlignVertical: 'top',
  },
  freeInputButtons: {
    flexDirection: 'row',
    gap: 10,
  },
  freeInputCancel: {
    flex: 1,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
  },
  freeInputCancelText: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 15,
  },
  freeInputSend: {
    flex: 1,
    backgroundColor: '#FF6B9D',
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
  },
  freeInputSendDisabled: {
    backgroundColor: 'rgba(255,107,157,0.3)',
  },
  freeInputSendText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
  },
  
  // === Ending Phase ===
  endingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 30,
  },
  endingContent: {
    alignItems: 'center',
    width: '100%',
  },
  endingIcon: {
    fontSize: 80,
    marginBottom: 20,
  },
  endingTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 12,
    textAlign: 'center',
  },
  endingDescription: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.7)',
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 30,
  },
  rewardsBox: {
    backgroundColor: 'rgba(107,203,119,0.1)',
    borderRadius: 16,
    padding: 20,
    width: '100%',
    alignItems: 'center',
    marginBottom: 20,
  },
  rewardsTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#6BCB77',
    marginBottom: 8,
  },
  rewardsText: {
    fontSize: 16,
    color: '#fff',
  },
  summaryBox: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 16,
    padding: 16,
    width: '100%',
    marginBottom: 30,
  },
  summaryTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FF6B9D',
    marginBottom: 8,
  },
  summaryText: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.6)',
    lineHeight: 20,
  },
  doneButton: {
    width: '100%',
  },
  doneButtonGradient: {
    paddingVertical: 18,
    borderRadius: 16,
    alignItems: 'center',
  },
  doneButtonText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  
  // === Finale Phase (结局剧情展示) ===
  finaleHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 12,
  },
  finaleIcon: {
    fontSize: 32,
  },
  finaleTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#FF6B9D',
  },
  finaleNarrativeText: {
    fontSize: 16,
    color: '#fff',
    lineHeight: 28,
    letterSpacing: 0.3,
    marginBottom: 24,
  },
  finaleContinueButton: {
    marginTop: 16,
  },
  finaleContinueGradient: {
    paddingVertical: 16,
    borderRadius: 14,
    alignItems: 'center',
  },
  finaleContinueText: {
    fontSize: 17,
    fontWeight: '700',
    color: '#fff',
  },
  
  // 按钮容器
  finaleButtonsContainer: {
    gap: 12,
    marginTop: 16,
  },
  
  // 付费延长按钮
  extendButton: {
    borderRadius: 14,
    overflow: 'hidden',
  },
  extendButtonGradient: {
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 14,
    alignItems: 'center',
  },
  extendButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
  },
  extendButtonPrice: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.8)',
    marginTop: 2,
  },
  
  // Checkpoint phase styles
  checkpointHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 10,
  },
  checkpointIcon: {
    fontSize: 28,
  },
  checkpointTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
  },
  checkpointText: {
    fontSize: 15,
    color: 'rgba(255,255,255,0.7)',
    lineHeight: 24,
    marginBottom: 24,
  },
  checkpointButtons: {
    gap: 12,
  },
  finishButton: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,107,157,0.3)',
  },
  finishButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FF6B9D',
  },
});
