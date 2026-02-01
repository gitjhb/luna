/**
 * Debug Panel - Shows L1/GameEngine state for development
 * 
 * Displays:
 * - L1 Perception: safety, intent, sentiment, nsfw detection
 * - Game Engine: emotion, intimacy, events, check status
 * - Last message stats
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Modal,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { ExtraData, GameDebugInfo } from '../store/chatStore';

interface DebugPanelProps {
  extraData?: ExtraData | null;
  emotionScore: number;
  emotionState: string;
  intimacyLevel: number;
  isSubscribed: boolean;
  tokensUsed?: number;
}

// Compact floating button that expands to full panel
export const DebugButton: React.FC<DebugPanelProps> = (props) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const hasData = props.extraData?.game || props.extraData?.l1;
  const emotion = props.extraData?.game?.emotion || props.emotionState;
  
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
        style={[styles.floatingButton, { backgroundColor: getEmotionColor(emotion) }]}
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
              {/* Current State */}
              <View style={styles.section}>
                <Text style={styles.sectionTitle}>📊 Current State</Text>
                <View style={styles.row}>
                  <Text style={styles.label}>Emotion:</Text>
                  <View style={[styles.badge, { backgroundColor: getEmotionColor(emotion) }]}>
                    <Text style={styles.badgeText}>{emotion}</Text>
                  </View>
                  <Text style={styles.value}>{props.emotionScore}</Text>
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
                  <View style={styles.row}>
                    <Text style={styles.label}>Intent:</Text>
                    <Text style={styles.value}>{props.extraData.game.intent}</Text>
                  </View>
                  <View style={styles.row}>
                    <Text style={styles.label}>Emotion:</Text>
                    <View style={[styles.badge, { backgroundColor: getEmotionColor(props.extraData.game.emotion) }]}>
                      <Text style={styles.badgeText}>{props.extraData.game.emotion}</Text>
                    </View>
                  </View>
                  <View style={styles.row}>
                    <Text style={styles.label}>Intimacy:</Text>
                    <Text style={styles.value}>LV {props.extraData.game.intimacy}</Text>
                  </View>
                  {props.extraData.game.events.length > 0 && (
                    <View style={styles.row}>
                      <Text style={styles.label}>Events:</Text>
                      <Text style={styles.value}>{props.extraData.game.events.join(', ')}</Text>
                    </View>
                  )}
                  {props.extraData.game.new_event && (
                    <View style={styles.row}>
                      <Text style={styles.label}>New Event:</Text>
                      <Text style={[styles.value, styles.yellowText]}>
                        🎉 {props.extraData.game.new_event}
                      </Text>
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
                    <Text style={styles.value}>{props.extraData.l1.difficulty_rating}/5</Text>
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
  noDataText: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.4)',
    textAlign: 'center',
    paddingVertical: 20,
  },
});

export default DebugButton;
