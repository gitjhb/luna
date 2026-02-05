/**
 * Age Verification Modal
 * 
 * 18+ 年龄确认弹窗，首次使用时弹出。
 * 确认后写入 AsyncStorage，不再重复弹出。
 */

import React, { useEffect, useState } from 'react';
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  BackHandler,
  Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';

const STORAGE_KEY = '@luna_age_verified';
const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface AgeVerificationModalProps {
  /** Called when user confirms they are 18+ */
  onConfirm: () => void;
  /** Called when user declines (exits app) */
  onDecline: () => void;
}

export default function AgeVerificationModal({ onConfirm, onDecline }: AgeVerificationModalProps) {
  const [visible, setVisible] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    checkVerification();
  }, []);

  // Block Android back button while modal is visible
  useEffect(() => {
    if (!visible) return;
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      onDecline();
      return true;
    });
    return () => sub.remove();
  }, [visible]);

  const checkVerification = async () => {
    try {
      const verified = await AsyncStorage.getItem(STORAGE_KEY);
      if (verified === 'true') {
        onConfirm();
      } else {
        setVisible(true);
      }
    } catch {
      setVisible(true);
    } finally {
      setChecking(false);
    }
  };

  const handleConfirm = async () => {
    try {
      await AsyncStorage.setItem(STORAGE_KEY, 'true');
    } catch {}
    setVisible(false);
    onConfirm();
  };

  const handleDecline = () => {
    setVisible(false);
    onDecline();
  };

  if (checking || !visible) return null;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      statusBarTranslucent
      onRequestClose={handleDecline}
    >
      <View style={styles.overlay}>
        {/* Card */}
        <View style={styles.card}>
          {/* Glow ring */}
          <LinearGradient
            colors={['#8B5CF6', '#EC4899']}
            style={styles.iconRing}
          >
            <View style={styles.iconInner}>
              <Ionicons name="shield-checkmark" size={32} color="#8B5CF6" />
            </View>
          </LinearGradient>

          <Text style={styles.title}>年龄确认</Text>

          <Text style={styles.body}>
            本应用包含虚拟角色互动内容{'\n'}
            仅限<Text style={styles.highlight}> 18 岁以上</Text>用户使用
          </Text>

          {/* Confirm */}
          <TouchableOpacity style={styles.confirmBtn} onPress={handleConfirm} activeOpacity={0.85}>
            <LinearGradient
              colors={['#8B5CF6', '#EC4899']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.confirmGradient}
            >
              <Text style={styles.confirmText}>我已满 18 岁，继续</Text>
            </LinearGradient>
          </TouchableOpacity>

          {/* Decline */}
          <TouchableOpacity style={styles.declineBtn} onPress={handleDecline} activeOpacity={0.7}>
            <Text style={styles.declineText}>退出</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(10, 6, 18, 0.92)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
  },
  card: {
    width: '100%',
    maxWidth: 340,
    backgroundColor: '#1a1025',
    borderRadius: 24,
    paddingHorizontal: 28,
    paddingTop: 36,
    paddingBottom: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.25)',
    // Glow shadow
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.25,
    shadowRadius: 24,
    elevation: 20,
  },
  iconRing: {
    width: 68,
    height: 68,
    borderRadius: 34,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 18,
  },
  iconInner: {
    width: 58,
    height: 58,
    borderRadius: 29,
    backgroundColor: '#1a1025',
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 12,
  },
  body: {
    fontSize: 15,
    color: 'rgba(255,255,255,0.7)',
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 28,
  },
  highlight: {
    color: '#EC4899',
    fontWeight: '600',
  },
  confirmBtn: {
    width: '100%',
    borderRadius: 16,
    overflow: 'hidden',
    marginBottom: 12,
  },
  confirmGradient: {
    paddingVertical: 15,
    alignItems: 'center',
  },
  confirmText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  declineBtn: {
    paddingVertical: 10,
  },
  declineText: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: 14,
  },
});
