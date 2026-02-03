/**
 * Date Modal - 约会场景选择和故事生成
 * 
 * 新版流程：选择场景 → 一键生成约会故事 → 故事保存到回忆录
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  Modal,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
  Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../services/api';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

interface DateScenario {
  id: string;
  name: string;
  description: string;
  icon: string;
}

interface UnlockStatus {
  is_unlocked: boolean;
  reason: string;
  current_level: number;
  level_met: boolean;
  gift_sent: boolean;
  unlock_level: number;
}

interface DateResult {
  success: boolean;
  story?: string;
  scenario?: {
    id: string;
    name: string;
    icon: string;
  };
  rewards?: {
    xp: number;
    emotion_boost: number;
  };
  error?: string;
}

interface DateModalProps {
  visible: boolean;
  onClose: () => void;
  characterId: string;
  characterName: string;
  currentLevel: number;
  onDateCompleted?: (result: DateResult) => void;
}

// API helpers
const dateApi = {
  getScenarios: async (): Promise<DateScenario[]> => {
    const data = await api.get<{ scenarios: DateScenario[] }>('/dates/scenarios');
    return data.scenarios;
  },
  
  checkUnlock: async (characterId: string): Promise<UnlockStatus> => {
    return api.get(`/dates/unlock-status/${characterId}`);
  },
  
  startDate: async (characterId: string, scenarioId: string): Promise<DateResult> => {
    return api.post('/dates/start', { character_id: characterId, scenario_id: scenarioId });
  },
};

export default function DateModal({
  visible,
  onClose,
  characterId,
  characterName,
  currentLevel,
  onDateCompleted,
}: DateModalProps) {
  const [scenarios, setScenarios] = useState<DateScenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [unlockStatus, setUnlockStatus] = useState<UnlockStatus | null>(null);
  const [generatedStory, setGeneratedStory] = useState<string | null>(null);
  const [dateResult, setDateResult] = useState<DateResult | null>(null);

  // Load scenarios and unlock status
  useEffect(() => {
    if (visible) {
      loadData();
      // Reset story when modal opens
      setGeneratedStory(null);
      setDateResult(null);
    }
  }, [visible, characterId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [scenariosData, unlockData] = await Promise.all([
        dateApi.getScenarios(),
        dateApi.checkUnlock(characterId),
      ]);
      setScenarios(scenariosData);
      setUnlockStatus(unlockData);
      if (scenariosData.length > 0 && !selectedScenario) {
        setSelectedScenario(scenariosData[0].id);
      }
    } catch (e: any) {
      console.error('Failed to load date data:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleStartDate = async () => {
    if (!selectedScenario) {
      Alert.alert('请选择场景', '请先选择一个约会场景');
      return;
    }
    
    setGenerating(true);
    try {
      const result = await dateApi.startDate(characterId, selectedScenario);
      if (result.success && result.story) {
        setGeneratedStory(result.story);
        setDateResult(result);
        onDateCompleted?.(result);
      } else {
        Alert.alert('约会失败', result.error || '生成故事时出错');
      }
    } catch (e: any) {
      Alert.alert('约会失败', e.message || '网络错误');
    } finally {
      setGenerating(false);
    }
  };

  const handleClose = () => {
    setGeneratedStory(null);
    setDateResult(null);
    onClose();
  };

  const isUnlocked = unlockStatus?.is_unlocked ?? false;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={handleClose}
    >
      <View style={styles.overlay}>
        <View style={styles.container}>
          {/* Header */}
          <LinearGradient
            colors={['#FF6B9D', '#C44569']}
            style={styles.header}
          >
            <Text style={styles.headerTitle}>
              {generatedStory ? '💕 约会回忆' : '💕 邀请约会'}
            </Text>
            <TouchableOpacity style={styles.closeButton} onPress={handleClose}>
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>
          </LinearGradient>

          <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
            {loading ? (
              <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#FF6B9D" />
                <Text style={styles.loadingText}>加载中...</Text>
              </View>
            ) : generating ? (
              /* 生成中 */
              <View style={styles.generatingContainer}>
                <ActivityIndicator size="large" color="#FF6B9D" />
                <Text style={styles.generatingTitle}>正在生成约会故事...</Text>
                <Text style={styles.generatingDesc}>
                  {characterName}正在准备和你的约会～{'\n'}
                  请稍等片刻...
                </Text>
              </View>
            ) : generatedStory ? (
              /* 显示生成的故事 */
              <View style={styles.storyContainer}>
                {dateResult?.scenario && (
                  <View style={styles.scenarioHeader}>
                    <Text style={styles.scenarioIcon}>{dateResult.scenario.icon}</Text>
                    <Text style={styles.scenarioTitle}>{dateResult.scenario.name}</Text>
                  </View>
                )}
                <Text style={styles.storyText}>{generatedStory}</Text>
                
                {dateResult?.rewards && (
                  <View style={styles.rewardsContainer}>
                    <Text style={styles.rewardsTitle}>🎉 约会完成！</Text>
                    <Text style={styles.rewardsText}>
                      +{dateResult.rewards.xp} XP | 好感度 +{dateResult.rewards.emotion_boost}
                    </Text>
                    <Text style={styles.rewardsHint}>
                      回忆已保存，可在回忆录中查看 💕
                    </Text>
                  </View>
                )}
                
                <TouchableOpacity style={styles.doneButton} onPress={handleClose}>
                  <LinearGradient
                    colors={['#FF6B9D', '#C44569']}
                    style={styles.doneButtonGradient}
                  >
                    <Text style={styles.doneButtonText}>完成</Text>
                  </LinearGradient>
                </TouchableOpacity>
              </View>
            ) : !isUnlocked ? (
              /* 未解锁 */
              <View style={styles.lockedContainer}>
                <Text style={styles.lockedIcon}>🔒</Text>
                <Text style={styles.lockedTitle}>约会功能未解锁</Text>
                <Text style={styles.lockedReason}>{unlockStatus?.reason}</Text>
                <View style={styles.unlockRequirements}>
                  <Text style={styles.reqTitle}>解锁条件：</Text>
                  <Text style={[styles.reqItem, unlockStatus?.level_met && styles.reqItemDone]}>
                    {unlockStatus?.level_met ? '✅' : '⬜'} 达到 LV {unlockStatus?.unlock_level || 10} (当前 LV {unlockStatus?.current_level || currentLevel})
                  </Text>
                  <Text style={[styles.reqItem, unlockStatus?.gift_sent && styles.reqItemDone]}>
                    {unlockStatus?.gift_sent ? '✅' : '⬜'} 送出过礼物
                  </Text>
                </View>
              </View>
            ) : (
              /* 场景选择 */
              <>
                <Text style={styles.sectionTitle}>选择约会场景</Text>
                <Text style={styles.sectionDesc}>
                  选一个浪漫的地方，邀请{characterName}约会吧！
                </Text>
                
                <View style={styles.scenarioGrid}>
                  {scenarios.map((scenario) => (
                    <TouchableOpacity
                      key={scenario.id}
                      style={[
                        styles.scenarioCard,
                        selectedScenario === scenario.id && styles.scenarioCardSelected,
                      ]}
                      onPress={() => setSelectedScenario(scenario.id)}
                    >
                      <Text style={styles.scenarioCardIcon}>{scenario.icon}</Text>
                      <Text style={styles.scenarioName}>{scenario.name}</Text>
                      <Text style={styles.scenarioDesc} numberOfLines={2}>
                        {scenario.description}
                      </Text>
                      {selectedScenario === scenario.id && (
                        <View style={styles.selectedBadge}>
                          <Ionicons name="checkmark-circle" size={20} color="#FF6B9D" />
                        </View>
                      )}
                    </TouchableOpacity>
                  ))}
                </View>

                {/* Start Date Button */}
                <TouchableOpacity
                  style={[styles.startButton, generating && styles.startButtonDisabled]}
                  onPress={handleStartDate}
                  disabled={generating}
                >
                  <LinearGradient
                    colors={['#FF6B9D', '#C44569']}
                    style={styles.startButtonGradient}
                  >
                    <Text style={styles.startButtonText}>
                      💕 开始约会
                    </Text>
                  </LinearGradient>
                </TouchableOpacity>
                
                <Text style={styles.hintText}>
                  约会将生成一段浪漫故事，保存到回忆录中
                </Text>
              </>
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'flex-end',
  },
  container: {
    backgroundColor: '#1A1025',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '90%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 20,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  closeButton: {
    position: 'absolute',
    right: 16,
    padding: 4,
  },
  content: {
    padding: 20,
    paddingBottom: 40,
  },
  loadingContainer: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  loadingText: {
    color: 'rgba(255,255,255,0.6)',
    marginTop: 12,
  },
  
  // Generating state
  generatingContainer: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  generatingTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
    marginTop: 20,
    marginBottom: 8,
  },
  generatingDesc: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.6)',
    textAlign: 'center',
    lineHeight: 22,
  },
  
  // Story display
  storyContainer: {
    paddingBottom: 20,
  },
  scenarioHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  scenarioIcon: {
    fontSize: 32,
    marginRight: 12,
  },
  scenarioTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
  },
  storyText: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.9)',
    lineHeight: 28,
    letterSpacing: 0.3,
  },
  rewardsContainer: {
    marginTop: 24,
    padding: 16,
    backgroundColor: 'rgba(255,107,157,0.1)',
    borderRadius: 12,
    alignItems: 'center',
  },
  rewardsTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FF6B9D',
    marginBottom: 8,
  },
  rewardsText: {
    fontSize: 14,
    color: '#6BCB77',
    marginBottom: 4,
  },
  rewardsHint: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.5)',
    marginTop: 4,
  },
  doneButton: {
    marginTop: 20,
  },
  doneButtonGradient: {
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  doneButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
  },
  
  // Locked state
  lockedContainer: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  lockedIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  lockedTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 8,
  },
  lockedReason: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.6)',
    textAlign: 'center',
    marginBottom: 20,
  },
  unlockRequirements: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 12,
    padding: 16,
    width: '100%',
  },
  reqTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FF6B9D',
    marginBottom: 8,
  },
  reqItem: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.7)',
    marginVertical: 4,
  },
  reqItemDone: {
    color: '#6BCB77',
  },
  
  // Scenario selection
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 8,
  },
  sectionDesc: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.6)',
    marginBottom: 20,
  },
  scenarioGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  scenarioCard: {
    width: (SCREEN_WIDTH - 60) / 2,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  scenarioCardSelected: {
    borderColor: '#FF6B9D',
    backgroundColor: 'rgba(255,107,157,0.1)',
  },
  scenarioCardIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  scenarioName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 4,
  },
  scenarioDesc: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.5)',
    lineHeight: 16,
  },
  selectedBadge: {
    position: 'absolute',
    top: 8,
    right: 8,
  },
  
  // Start button
  startButton: {
    marginTop: 10,
  },
  startButtonDisabled: {
    opacity: 0.5,
  },
  startButtonGradient: {
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  startButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
  },
  hintText: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.4)',
    textAlign: 'center',
    marginTop: 12,
    marginBottom: 20,
  },
});
