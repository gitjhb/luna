/**
 * Intimacy Info Panel
 * 
 * 亲密度系统面板 - 从后端获取配置
 */

import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { getIntimacyConfig, StageInfo, getStageEmoji } from '../services/intimacyConfigService';

interface IntimacyInfoPanelProps {
  characterId?: string;
  currentLevel: number;
}

export const IntimacyInfoPanel: React.FC<IntimacyInfoPanelProps> = ({
  characterId,
  currentLevel,
}) => {
  const [stages, setStages] = useState<StageInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentStage, setCurrentStage] = useState<string>('');

  useEffect(() => {
    loadConfig();
  }, [characterId]);

  const loadConfig = async () => {
    setLoading(true);
    const config = await getIntimacyConfig(characterId);
    if (config) {
      setStages(config.stages);
      setCurrentStage(config.current_stage || '');
    }
    setLoading(false);
  };

  const isStageActive = (stage: StageInfo) => {
    return currentLevel >= stage.min_level && currentLevel <= stage.max_level;
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="small" color="#A855F7" />
        <Text style={styles.loadingText}>加载中...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* 当前等级显示 */}
      <View style={styles.currentLevelSection}>
        <Text style={styles.currentLevelLabel}>当前等级</Text>
        <View style={styles.currentLevelRow}>
          <Text style={styles.currentLevelNumber}>LV {currentLevel}</Text>
          <Text style={styles.currentStageName}>
            {stages.find(s => isStageActive(s))?.stage_name_cn || ''}
          </Text>
        </View>
      </View>

      {/* 阶段列表 */}
      <View style={styles.stagesSection}>
        <Text style={styles.sectionTitle}>亲密阶段</Text>
        
        {stages.map((stage) => (
          <View 
            key={stage.stage_id} 
            style={[
              styles.stageCard, 
              isStageActive(stage) && styles.stageCardActive
            ]}
          >
            <View style={styles.stageHeader}>
              <Text style={styles.stageEmoji}>{getStageEmoji(stage.stage_id)}</Text>
              <View style={styles.stageInfo}>
                <Text style={styles.stageName}>{stage.stage_name_cn}</Text>
                <Text style={styles.stageLevel}>LV {stage.level_range}</Text>
              </View>
            </View>
            <Text style={styles.stageDesc}>{stage.description}</Text>
            {stage.key_unlocks && stage.key_unlocks.length > 0 && (
              <View style={styles.stageFeatures}>
                {stage.key_unlocks.map((unlock, idx) => (
                  <Text key={idx} style={styles.featureItem}>✓ {unlock}</Text>
                ))}
              </View>
            )}
          </View>
        ))}
      </View>

      {/* 如何提升亲密度 */}
      <View style={styles.xpSection}>
        <Text style={styles.sectionTitle}>如何提升亲密度</Text>
        <View style={styles.xpWayCard}>
          <Text style={styles.xpWayItem}>💬 发送消息 <Text style={styles.xpAmount}>+2 XP</Text></Text>
          <Text style={styles.xpWayItem}>📅 每日签到 <Text style={styles.xpAmount}>+20 XP</Text></Text>
          <Text style={styles.xpWayItem}>🔥 连续聊天 <Text style={styles.xpAmount}>+5 XP</Text></Text>
          <Text style={styles.xpWayItem}>💝 表达情感 <Text style={styles.xpAmount}>+10 XP</Text></Text>
          <Text style={styles.xpWayItem}>🎁 送礼物 <Text style={styles.xpAmount}>+10~1500 XP</Text></Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    padding: 40,
    alignItems: 'center',
  },
  loadingText: {
    color: 'rgba(255,255,255,0.6)',
    marginTop: 8,
  },
  currentLevelSection: {
    marginBottom: 20,
  },
  currentLevelLabel: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.6)',
    marginBottom: 4,
  },
  currentLevelRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 12,
  },
  currentLevelNumber: {
    fontSize: 32,
    fontWeight: '700',
    color: '#fff',
  },
  currentStageName: {
    fontSize: 18,
    color: '#A855F7',
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 12,
  },
  stagesSection: {
    marginBottom: 20,
  },
  stageCard: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: 'transparent',
  },
  stageCardActive: {
    borderColor: '#A855F7',
    backgroundColor: 'rgba(168,85,247,0.1)',
  },
  stageHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  stageEmoji: {
    fontSize: 24,
    marginRight: 10,
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
    color: 'rgba(255,255,255,0.5)',
  },
  stageDesc: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.7)',
    marginBottom: 8,
  },
  stageFeatures: {
    marginTop: 4,
  },
  featureItem: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.6)',
    marginBottom: 2,
  },
  xpSection: {
    marginBottom: 20,
  },
  xpWayCard: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 12,
    padding: 12,
  },
  xpWayItem: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginBottom: 8,
  },
  xpAmount: {
    color: '#A855F7',
    fontWeight: '600',
  },
});

export default IntimacyInfoPanel;
