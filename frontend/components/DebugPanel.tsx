/**
 * Debug Panel - Shows L1/GameEngine state for development
 * 
 * Displays:
 * - L1 Perception: safety, intent, sentiment, nsfw detection
 * - Game Engine: emotion, intimacy, events, check status
 * - Last message stats
 * - Debug controls: set level, set emotion, view full status
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Modal,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { ExtraData, GameDebugInfo } from '../store/chatStore';
import { apiClient, API_BASE_URL } from '../services/api';

// Stage name mapping
const getStageNameCN = (stage: string): string => {
  const stageNames: Record<string, string> = {
    'stranger': '陌生人',
    'friend': '朋友',
    'crush': '暧昧',
    'lover': '恋人',
    'spouse': '挚爱',
  };
  return stageNames[stage?.toLowerCase()] || stage || '未知';
};

interface DebugPanelProps {
  extraData?: ExtraData | null;
  emotionScore: number;
  emotionState: string;
  intimacyLevel: number;
  isSubscribed: boolean;
  tokensUsed?: number;
  characterId?: string;
  onStateChanged?: () => void;  // 状态变更后的回调
}

// Debug API helpers - 使用 apiClient 自动带 token
const debugApi = {
  setLevel: async (characterId: string, level: number) => {
    const res = await apiClient.post('/debug/set_level', {
      character_id: characterId,
      level,
    });
    return res.data;
  },
  
  setEmotion: async (characterId: string, emotion: number) => {
    const res = await apiClient.post('/debug/set_emotion', {
      character_id: characterId,
      emotion,
    });
    return res.data;
  },
  
  getStatus: async (characterId: string) => {
    const res = await apiClient.get(`/debug/status/${characterId}`);
    return res.data;
  },
};

// Compact floating button that expands to full panel
export const DebugButton: React.FC<DebugPanelProps> = (props) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const hasData = props.extraData?.game || props.extraData?.l1;
  const emotionState = props.extraData?.game?.emotion_state || props.emotionState;
  
  // Compact indicator color based on emotion
  const getEmotionColor = (emotion: string): string => {
    const colors: Record<string, string> = {
      loving: '#FF6B9D',
      happy: '#FFD93D',
      neutral: '#6BCB77',
      curious: '#4ECDC4',
      annoyed: '#FFC93C',
      angry: '#FF6B6B',
      hurt: '#A8E6CF',
      cold: '#636E72',
      silent: '#2D3436',
    };
    return colors[emotion] || '#6BCB77';
  };
  
  return (
    <>
      {/* Floating Debug Button */}
      <TouchableOpacity
        style={[styles.floatingButton, { backgroundColor: getEmotionColor(emotionState) }]}
        onPress={() => setIsExpanded(true)}
      >
        <Ionicons name="bug" size={16} color="#fff" />
        {hasData && (
          <View style={styles.badgeDot} />
        )}
      </TouchableOpacity>
      
      {/* Expanded Debug Panel */}
      <Modal
        visible={isExpanded}
        transparent
        animationType="slide"
        onRequestClose={() => setIsExpanded(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.panelContainer}>
            <View style={styles.panelHeader}>
              <Text style={styles.panelTitle}>🔧 Debug Panel</Text>
              <TouchableOpacity onPress={() => setIsExpanded(false)}>
                <Ionicons name="close" size={24} color="#fff" />
              </TouchableOpacity>
            </View>
            
            <ScrollView style={styles.panelContent} showsVerticalScrollIndicator={false}>
              {/* Current State (Before This Message) */}
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>📊 Current State</Text>
                <View style={styles.row}>
                  <Text style={styles.label}>Server:</Text>
                  <Text style={[styles.value, styles.monoText]} numberOfLines={1}>
                    {API_BASE_URL.replace('/api/v1', '')}
                  </Text>
                </View>
                <View style={styles.row}>
                  <Text style={styles.label}>Emotion:</Text>
                  <View style={[styles.badge, { backgroundColor: getEmotionColor(emotionState) }]}>
                    <Text style={styles.badgeText}>
                      {props.extraData?.game?.emotion_before ?? props.emotionScore}
                    </Text>
                  </View>
                  <Text style={styles.grayText}>(before)</Text>
                </View>
                <View style={styles.row}>
                  <Text style={styles.label}>Intimacy:</Text>
                  <Text style={styles.value}>LV {props.intimacyLevel}</Text>
                </View>
                <View style={styles.row}>
                  <Text style={styles.label}>VIP:</Text>
                  <Text style={[styles.value, props.isSubscribed ? styles.greenText : styles.grayText]}>
                    {props.isSubscribed ? '✓ Yes' : '✗ No'}
                  </Text>
                </View>
              </View>
              
              {/* Game Engine State */}
              {props.extraData?.game && (
                <View style={styles.section}>
                  <Text style={styles.sectionTitle}>⚙️ Game Engine</Text>
                  
                  {/* Power vs Difficulty 判定 */}
                  <View style={styles.subsection}>
                    <Text style={styles.subsectionTitle}>🎯 判定结果</Text>
                    <View style={styles.row}>
                      <Text style={styles.label}>Check:</Text>
                      <Text style={[
                        styles.value,
                        props.extraData.game.check_passed ? styles.greenText : styles.redText
                      ]}>
                        {props.extraData.game.check_passed ? '✓ Passed' : '✗ Blocked'}
                      </Text>
                    </View>
                    {props.extraData.game.refusal_reason && (
                      <View style={styles.row}>
                        <Text style={styles.label}>Reason:</Text>
                        <Text style={[styles.value, styles.redText]}>
                          {props.extraData.game.refusal_reason}
                        </Text>
                      </View>
                    )}
                    {/* Power vs Difficulty 详细计算 */}
                    <View style={styles.row}>
                      <Text style={styles.label}>Power:</Text>
                      <Text style={[
                        styles.value,
                        (props.extraData.game.power || 0) >= (props.extraData.game.adjusted_difficulty || 0) 
                          ? styles.greenText : styles.yellowText
                      ]}>
                        {props.extraData.game.power?.toFixed(1) || '0'}
                      </Text>
                    </View>
                    {/* Power 计算明细 */}
                    {props.extraData.game.power_breakdown && (
                      <View style={styles.powerBreakdown}>
                        <Text style={styles.breakdownFormula}>
                          = ({props.extraData.game.power_breakdown.intimacy} 亲密)
                          + ({props.extraData.game.power_breakdown.emotion} 情绪)
                          + ({props.extraData.game.power_breakdown.chaos} chaos)
                          - ({props.extraData.game.power_breakdown.pure} pure)
                          + ({props.extraData.game.power_breakdown.buff} buff)
                          {props.extraData.game.power_breakdown.effect > 0 && (
                            <Text style={styles.effectBuffText}>
                              {` + (${props.extraData.game.power_breakdown.effect} 🍷道具)`}
                            </Text>
                          )}
                        </Text>
                      </View>
                    )}
                    <View style={styles.row}>
                      <Text style={styles.label}>Difficulty:</Text>
                      <Text style={styles.value}>
                        {props.extraData.game.adjusted_difficulty || 0}
                        {props.extraData.game.difficulty_modifier && props.extraData.game.difficulty_modifier !== 1.0 && (
                          <Text style={styles.grayText}>
                            {` (base×${props.extraData.game.difficulty_modifier})`}
                          </Text>
                        )}
                      </Text>
                    </View>
                    {/* Stage Override 提示 */}
                    {!props.extraData.game.check_passed && 
                     props.extraData.game.stage === 'spouse' && 
                     props.extraData.game.is_nsfw && (
                      <View style={[styles.row, styles.overrideRow]}>
                        <Text style={styles.overrideText}>
                          💕 Stage Override: S4挚爱阶段允许NSFW
                        </Text>
                      </View>
                    )}
                  </View>
                  
                  {/* 关系状态 */}
                  <View style={styles.subsection}>
                    <Text style={styles.subsectionTitle}>💑 关系状态</Text>
                    <View style={styles.row}>
                      <Text style={styles.label}>Stage:</Text>
                      <Text style={styles.value}>
                        {props.extraData.game.stage?.toUpperCase() || 'N/A'}
                        <Text style={styles.grayText}>
                          {` (${getStageNameCN(props.extraData.game.stage || '')})`}
                        </Text>
                      </Text>
                    </View>
                    <View style={styles.row}>
                      <Text style={styles.label}>Level:</Text>
                      <Text style={styles.value}>LV {props.extraData.game.level || props.intimacyLevel}</Text>
                    </View>
                    <View style={styles.row}>
                      <Text style={styles.label}>Intimacy_x:</Text>
                      <Text style={styles.value}>{props.extraData.game.intimacy}/100</Text>
                    </View>
                    <View style={styles.row}>
                      <Text style={styles.label}>Archetype:</Text>
                      <Text style={styles.value}>{props.extraData.game.archetype?.toUpperCase() || 'NORMAL'}</Text>
                    </View>
                  </View>
                  
                  {/* Intent & NSFW */}
                  <View style={styles.subsection}>
                    <Text style={styles.subsectionTitle}>📨 用户意图</Text>
                    <View style={styles.row}>
                      <Text style={styles.label}>Intent:</Text>
                      <Text style={styles.value}>{props.extraData.game.intent}</Text>
                    </View>
                    <View style={styles.row}>
                      <Text style={styles.label}>NSFW:</Text>
                      <Text style={[
                        styles.value,
                        props.extraData.game.is_nsfw ? styles.yellowText : styles.grayText
                      ]}>
                        {props.extraData.game.is_nsfw ? '🔥 Yes' : 'No'}
                      </Text>
                    </View>
                  </View>
                  
                  {/* 情绪状态 */}
                  <View style={styles.subsection}>
                    <Text style={styles.subsectionTitle}>😊 情绪变化</Text>
                    <View style={styles.row}>
                      <Text style={styles.label}>Emotion:</Text>
                      <View style={[styles.badge, { backgroundColor: getEmotionColor(props.extraData.game.emotion_state || '') }]}>
                        <Text style={styles.badgeText}>{props.extraData.game.emotion}</Text>
                      </View>
                      {props.extraData.game.emotion_delta !== undefined && (
                        <Text style={[
                          styles.deltaText,
                          props.extraData.game.emotion_delta > 0 ? styles.greenText : 
                          props.extraData.game.emotion_delta < 0 ? styles.redText : styles.grayText
                        ]}>
                          {props.extraData.game.emotion_delta > 0 ? '+' : ''}{props.extraData.game.emotion_delta}
                        </Text>
                      )}
                    </View>
                    {props.extraData.game.emotion_state && (
                      <View style={styles.row}>
                        <Text style={styles.label}>State:</Text>
                        <Text style={[
                          styles.value,
                          props.extraData.game.emotion_locked ? styles.redText : styles.value
                        ]}>
                          {props.extraData.game.emotion_state}
                          {props.extraData.game.emotion_locked ? ' 🔒' : ''}
                        </Text>
                      </View>
                    )}
                    {props.extraData.game.emotion_before !== undefined && (
                      <View style={styles.row}>
                        <Text style={styles.label}>Before:</Text>
                        <Text style={styles.grayText}>{props.extraData.game.emotion_before}</Text>
                      </View>
                    )}
                  </View>
                  
                  {/* 事件 */}
                  {(props.extraData.game.events?.length > 0 || props.extraData.game.new_event) && (
                    <View style={styles.subsection}>
                      <Text style={styles.subsectionTitle}>🎉 事件</Text>
                      {props.extraData.game.events && props.extraData.game.events.length > 0 && (
                        <View style={styles.row}>
                          <Text style={styles.label}>已解锁:</Text>
                          <Text style={styles.value}>{props.extraData.game.events.join(', ')}</Text>
                        </View>
                      )}
                      {props.extraData.game.new_event && (
                        <View style={styles.row}>
                          <Text style={styles.label}>New:</Text>
                          <Text style={[styles.value, styles.yellowText]}>
                            🎉 {props.extraData.game.new_event}
                          </Text>
                        </View>
                      )}
                    </View>
                  )}
                  
                  {/* 激活效果 (Tier 2 礼物) */}
                  {props.extraData.active_effects && props.extraData.active_effects.length > 0 && (
                    <View style={styles.subsection}>
                      <Text style={styles.subsectionTitle}>🎁 激活效果</Text>
                      {props.extraData.active_effects.map((effect, idx) => (
                        <View key={idx} style={styles.row}>
                          <Text style={styles.label}>{effect.icon}</Text>
                          <Text style={[styles.value, { color: effect.color }]}>
                            {effect.name}
                          </Text>
                          <Text style={styles.remainingBadge}>
                            剩余 {effect.remaining} 条
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}
                </View>
              )}
              
              {/* L1 Perception */}
              {props.extraData?.l1 && (
                <View style={styles.section}>
                  <Text style={styles.sectionTitle}>📡 L1 Perception</Text>
                  <View style={styles.row}>
                    <Text style={styles.label}>Safety:</Text>
                    <Text style={[
                      styles.value,
                      props.extraData.l1.safety_flag === 'SAFE' ? styles.greenText : styles.yellowText
                    ]}>
                      {props.extraData.l1.safety_flag}
                    </Text>
                  </View>
                  <View style={styles.row}>
                    <Text style={styles.label}>Intent:</Text>
                    <Text style={styles.value}>{props.extraData.l1.intent}</Text>
                  </View>
                  <View style={styles.row}>
                    <Text style={styles.label}>Difficulty:</Text>
                    <Text style={styles.value}>
                      {props.extraData.l1.difficulty_rating}
                      <Text style={styles.grayText}> (base)</Text>
                    </Text>
                  </View>
                  <View style={styles.row}>
                    <Text style={styles.label}>Sentiment:</Text>
                    <Text style={[
                      styles.value,
                      props.extraData.l1.sentiment > 0 ? styles.greenText : 
                      props.extraData.l1.sentiment < 0 ? styles.redText : styles.grayText
                    ]}>
                      {props.extraData.l1.sentiment.toFixed(2)}
                    </Text>
                  </View>
                  <View style={styles.row}>
                    <Text style={styles.label}>NSFW:</Text>
                    <Text style={[
                      styles.value,
                      props.extraData.l1.is_nsfw ? styles.yellowText : styles.grayText
                    ]}>
                      {props.extraData.l1.is_nsfw ? '🔥 Yes' : 'No'}
                    </Text>
                  </View>
                </View>
              )}
              
              {/* Token Usage */}
              {props.tokensUsed !== undefined && (
                <View style={styles.section}>
                  <Text style={styles.sectionTitle}>💰 Usage</Text>
                  <View style={styles.row}>
                    <Text style={styles.label}>Tokens:</Text>
                    <Text style={styles.value}>{props.tokensUsed}</Text>
                  </View>
                </View>
              )}
              
              {/* No Data Message */}
              {!props.extraData?.game && !props.extraData?.l1 && (
                <View style={styles.section}>
                  <Text style={styles.noDataText}>
                    No debug data yet. Send a message to see L1/GameEngine state.
                  </Text>
                </View>
              )}
              
              {/* Debug Controls */}
              {props.characterId && (
                <View style={styles.section}>
                  <Text style={styles.sectionTitle}>🎮 等级调整</Text>
                  
                  {/* Level Up/Down Buttons */}
                  <View style={styles.levelButtonsRow}>
                    <TouchableOpacity
                      style={[styles.levelButton, styles.levelDownButton, loading && styles.controlButtonDisabled]}
                      onPress={async () => {
                        const newLevel = Math.max(1, props.intimacyLevel - 1);
                        if (newLevel === props.intimacyLevel) return;
                        setLoading(true);
                        try {
                          await debugApi.setLevel(props.characterId!, newLevel);
                          props.onStateChanged?.();
                        } catch (e) {
                          console.log('降级失败');
                        } finally {
                          setLoading(false);
                        }
                      }}
                      disabled={loading || props.intimacyLevel <= 1}
                    >
                      <Ionicons name="remove" size={24} color="#fff" />
                      <Text style={styles.levelButtonText}>降级</Text>
                    </TouchableOpacity>
                    
                    <View style={styles.currentLevelDisplay}>
                      <Text style={styles.currentLevelText}>LV {props.intimacyLevel}</Text>
                    </View>
                    
                    <TouchableOpacity
                      style={[styles.levelButton, styles.levelUpButton, loading && styles.controlButtonDisabled]}
                      onPress={async () => {
                        const newLevel = Math.min(50, props.intimacyLevel + 1);
                        if (newLevel === props.intimacyLevel) return;
                        setLoading(true);
                        try {
                          await debugApi.setLevel(props.characterId!, newLevel);
                          props.onStateChanged?.();
                        } catch (e) {
                          console.log('升级失败');
                        } finally {
                          setLoading(false);
                        }
                      }}
                      disabled={loading || props.intimacyLevel >= 50}
                    >
                      <Ionicons name="add" size={24} color="#fff" />
                      <Text style={styles.levelButtonText}>升级</Text>
                    </TouchableOpacity>
                  </View>
                  
                  {loading && (
                    <ActivityIndicator size="small" color="#A855F7" style={{ marginTop: 10 }} />
                  )}
                </View>
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </>
  );
};

const styles = StyleSheet.create({
  floatingButton: {
    position: 'absolute',
    right: 16,
    bottom: 180,
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 5,
    zIndex: 100,
  },
  badgeDot: {
    position: 'absolute',
    top: 2,
    right: 2,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#FF6B6B',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'flex-end',
  },
  panelContainer: {
    backgroundColor: 'rgba(26, 16, 37, 0.98)',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '70%',
    paddingBottom: 30,
  },
  panelHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  panelTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  panelContent: {
    paddingHorizontal: 20,
    paddingTop: 16,
  },
  section: {
    marginBottom: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 12,
    padding: 12,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#A855F7',
    marginBottom: 10,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  label: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.6)',
    width: 80,
  },
  value: {
    fontSize: 13,
    color: '#fff',
    flex: 1,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
    marginRight: 8,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#fff',
  },
  greenText: {
    color: '#6BCB77',
  },
  redText: {
    color: '#FF6B6B',
  },
  yellowText: {
    color: '#FFD93D',
  },
  grayText: {
    color: 'rgba(255, 255, 255, 0.4)',
  },
  monoText: {
    fontFamily: 'monospace',
    fontSize: 11,
    color: '#00D4FF',
  },
  deltaText: {
    fontSize: 12,
    fontWeight: '600',
    marginLeft: 8,
  },
  noDataText: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.4)',
    textAlign: 'center',
    paddingVertical: 20,
  },
  controlButtonDisabled: {
    opacity: 0.5,
  },
  // Subsection styles
  subsection: {
    marginBottom: 12,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
  },
  subsectionTitle: {
    fontSize: 12,
    fontWeight: '600',
    color: 'rgba(168, 85, 247, 0.8)',
    marginBottom: 6,
  },
  overrideRow: {
    backgroundColor: 'rgba(107, 203, 119, 0.15)',
    borderRadius: 6,
    padding: 6,
    marginTop: 4,
  },
  overrideText: {
    fontSize: 11,
    color: '#6BCB77',
    fontWeight: '500',
  },
  // Power breakdown styles
  powerBreakdown: {
    marginLeft: 80,
    marginBottom: 6,
    paddingLeft: 8,
    borderLeftWidth: 2,
    borderLeftColor: 'rgba(168, 85, 247, 0.3)',
  },
  breakdownFormula: {
    fontSize: 11,
    color: 'rgba(255, 255, 255, 0.5)',
    fontFamily: 'monospace',
  },
  effectBuffText: {
    color: '#FF6B9D',
    fontWeight: '600',
  },
  remainingBadge: {
    fontSize: 10,
    color: 'rgba(255, 255, 255, 0.5)',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
    marginLeft: 'auto',
  },
  // Level Up/Down buttons
  levelButtonsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
  },
  levelButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 12,
    gap: 6,
  },
  levelDownButton: {
    backgroundColor: 'rgba(255, 107, 107, 0.3)',
  },
  levelUpButton: {
    backgroundColor: 'rgba(107, 203, 119, 0.3)',
  },
  levelButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  currentLevelDisplay: {
    backgroundColor: 'rgba(168, 85, 247, 0.3)',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 12,
  },
  currentLevelText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
});

export default DebugButton;
