/**
 * Date Modal - 约会场景选择和进行
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

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface DateScenario {
  id: string;
  name: string;
  description: string;
  icon: string;
}

interface DateInfo {
  is_active: boolean;
  scenario_name?: string;
  scenario_icon?: string;
  message_count?: number;
  required_messages?: number;
  status?: string;
}

interface DateModalProps {
  visible: boolean;
  onClose: () => void;
  characterId: string;
  characterName: string;
  currentLevel: number;
  onDateStarted?: (dateInfo: any) => void;
  onDateCompleted?: (result: any) => void;
  activeDateInfo?: DateInfo | null;
}

// API helpers (using api service for auth)
const dateApi = {
  getScenarios: async (): Promise<DateScenario[]> => {
    const data = await api.get<{ scenarios: DateScenario[] }>('/dates/scenarios');
    return data.scenarios;
  },
  
  checkUnlock: async (characterId: string): Promise<{ is_unlocked: boolean; reason: string }> => {
    return api.get(`/dates/unlock-status/${characterId}`);
  },
  
  startDate: async (characterId: string, scenarioId: string): Promise<any> => {
    return api.post('/dates/start', { character_id: characterId, scenario_id: scenarioId });
  },
  
  completeDate: async (characterId: string): Promise<any> => {
    return api.post('/dates/complete', { character_id: characterId });
  },
};

export default function DateModal({
  visible,
  onClose,
  characterId,
  characterName,
  currentLevel,
  onDateStarted,
  onDateCompleted,
  activeDateInfo,
}: DateModalProps) {
  const [scenarios, setScenarios] = useState<DateScenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [unlockStatus, setUnlockStatus] = useState<{ is_unlocked: boolean; reason: string } | null>(null);

  // Load scenarios and unlock status
  useEffect(() => {
    if (visible) {
      loadData();
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
    
    setLoading(true);
    try {
      const result = await dateApi.startDate(characterId, selectedScenario);
      if (result.success) {
        onDateStarted?.(result.date);
        Alert.alert(
          '💕 约会开始！',
          `你和${characterName}在${result.date.scenario_name}开始约会了！\n\n好好聊天，享受约会时光吧～`,
          [{ text: '开始约会', onPress: onClose }]
        );
      }
    } catch (e: any) {
      Alert.alert('约会失败', e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCompleteDate = async () => {
    setLoading(true);
    try {
      const result = await dateApi.completeDate(characterId);
      if (result.success) {
        onDateCompleted?.(result);
        Alert.alert(
          '🎉 约会成功！',
          `和${characterName}度过了美好的时光！\n\n+${result.xp_reward} XP\n关系更近了一步 💕`,
          [{ text: '太棒了！', onPress: onClose }]
        );
      }
    } catch (e: any) {
      Alert.alert('完成失败', e.message);
    } finally {
      setLoading(false);
    }
  };

  const isUnlocked = unlockStatus?.is_unlocked ?? false;
  const isDateActive = activeDateInfo?.is_active ?? false;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <View style={styles.container}>
          {/* Header */}
          <LinearGradient
            colors={['#FF6B9D', '#C44569']}
            style={styles.header}
          >
            <Text style={styles.headerTitle}>
              {isDateActive ? '💕 约会进行中' : '💕 邀请约会'}
            </Text>
            <TouchableOpacity style={styles.closeButton} onPress={onClose}>
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>
          </LinearGradient>

          <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
            {loading ? (
              <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#FF6B9D" />
                <Text style={styles.loadingText}>加载中...</Text>
              </View>
            ) : isDateActive ? (
              /* 约会进行中 */
              <View style={styles.activeDateContainer}>
                <Text style={styles.activeDateIcon}>
                  {activeDateInfo?.scenario_icon || '💑'}
                </Text>
                <Text style={styles.activeDateTitle}>
                  {activeDateInfo?.scenario_name || '约会中'}
                </Text>
                <Text style={styles.activeDateDesc}>
                  和{characterName}的约会正在进行中...
                </Text>
                
                {/* Progress */}
                <View style={styles.progressContainer}>
                  <View style={styles.progressBar}>
                    <View 
                      style={[
                        styles.progressFill,
                        { 
                          width: `${((activeDateInfo?.message_count || 0) / (activeDateInfo?.required_messages || 5)) * 100}%` 
                        }
                      ]} 
                    />
                  </View>
                  <Text style={styles.progressText}>
                    {activeDateInfo?.message_count || 0} / {activeDateInfo?.required_messages || 5} 条对话
                  </Text>
                </View>
                
                <Text style={styles.activeDateHint}>
                  继续聊天，享受约会时光～{'\n'}
                  完成后会自动解锁新阶段！
                </Text>

                {/* Manual complete button (for testing) */}
                {__DEV__ && (
                  <TouchableOpacity
                    style={styles.completeButton}
                    onPress={handleCompleteDate}
                  >
                    <Text style={styles.completeButtonText}>🧪 手动完成约会</Text>
                  </TouchableOpacity>
                )}
              </View>
            ) : !isUnlocked ? (
              /* 未解锁 */
              <View style={styles.lockedContainer}>
                <Text style={styles.lockedIcon}>🔒</Text>
                <Text style={styles.lockedTitle}>约会功能未解锁</Text>
                <Text style={styles.lockedReason}>{unlockStatus?.reason}</Text>
                <View style={styles.unlockRequirements}>
                  <Text style={styles.reqTitle}>解锁条件：</Text>
                  <Text style={[styles.reqItem, currentLevel >= 10 && styles.reqItemDone]}>
                    {currentLevel >= 10 ? '✅' : '⬜'} 达到 LV 10 (当前 LV {currentLevel})
                  </Text>
                  <Text style={styles.reqItem}>
                    ⬜ 送出过礼物
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
                      <Text style={styles.scenarioIcon}>{scenario.icon}</Text>
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
                  style={[styles.startButton, loading && styles.startButtonDisabled]}
                  onPress={handleStartDate}
                  disabled={loading}
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
    maxHeight: '85%',
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
  
  // Active date
  activeDateContainer: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  activeDateIcon: {
    fontSize: 64,
    marginBottom: 12,
  },
  activeDateTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 8,
  },
  activeDateDesc: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.7)',
    marginBottom: 20,
  },
  progressContainer: {
    width: '100%',
    alignItems: 'center',
    marginBottom: 20,
  },
  progressBar: {
    width: '80%',
    height: 8,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#FF6B9D',
    borderRadius: 4,
  },
  progressText: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.5)',
    marginTop: 8,
  },
  activeDateHint: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.6)',
    textAlign: 'center',
    lineHeight: 22,
  },
  completeButton: {
    marginTop: 20,
    paddingVertical: 10,
    paddingHorizontal: 20,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 8,
  },
  completeButtonText: {
    color: '#FF6B9D',
    fontSize: 14,
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
  scenarioIcon: {
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
    marginBottom: 20,
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
});
