/**
 * Age Verification Modal
 * 
 * 18+ 年龄确认弹窗，首次使用时弹出。
 * 用户需要选择生日日期来验证年龄。
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
  Platform,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import DateTimePicker, { DateTimePickerEvent } from '@react-native-community/datetimepicker';

const STORAGE_KEY = '@luna_age_verified';
const BIRTHDAY_KEY = '@luna_user_birthday';
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
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Default to 18 years ago for picker initial value
  const defaultDate = new Date();
  defaultDate.setFullYear(defaultDate.getFullYear() - 18);

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

  const calculateAge = (birthday: Date): number => {
    const today = new Date();
    let age = today.getFullYear() - birthday.getFullYear();
    const monthDiff = today.getMonth() - birthday.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthday.getDate())) {
      age--;
    }
    
    return age;
  };

  const handleDateChange = (event: DateTimePickerEvent, date?: Date) => {
    if (Platform.OS === 'android') {
      setShowDatePicker(false);
    }
    
    if (event.type === 'set' && date) {
      setSelectedDate(date);
      setError(null);
    }
  };

  const handleConfirm = async () => {
    if (!selectedDate) {
      setError('请选择您的生日');
      return;
    }

    const age = calculateAge(selectedDate);
    
    if (age < 18) {
      setError('抱歉，本应用仅限18岁以上用户使用');
      // Delay exit to show error
      setTimeout(() => {
        onDecline();
      }, 2000);
      return;
    }

    try {
      await AsyncStorage.setItem(STORAGE_KEY, 'true');
      await AsyncStorage.setItem(BIRTHDAY_KEY, selectedDate.toISOString());
    } catch {}
    
    setVisible(false);
    onConfirm();
  };

  const handleDecline = () => {
    setVisible(false);
    onDecline();
  };

  const formatDate = (date: Date): string => {
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
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

          <Text style={styles.title}>年龄验证</Text>

          <Text style={styles.body}>
            本应用包含虚拟角色互动内容{'\n'}
            仅限<Text style={styles.highlight}> 18 岁以上</Text>用户使用
          </Text>

          {/* Birthday picker */}
          <Text style={styles.label}>请选择您的生日</Text>
          
          <TouchableOpacity 
            style={styles.dateButton}
            onPress={() => setShowDatePicker(true)}
          >
            <Ionicons name="calendar-outline" size={20} color="#8B5CF6" />
            <Text style={styles.dateText}>
              {selectedDate ? formatDate(selectedDate) : '点击选择日期'}
            </Text>
          </TouchableOpacity>

          {/* Date Picker */}
          {(showDatePicker || Platform.OS === 'ios') && (
            <View style={styles.pickerContainer}>
              <DateTimePicker
                value={selectedDate || defaultDate}
                mode="date"
                display={Platform.OS === 'ios' ? 'spinner' : 'default'}
                onChange={handleDateChange}
                maximumDate={new Date()}
                minimumDate={new Date(1920, 0, 1)}
                textColor="#fff"
                themeVariant="dark"
                style={styles.picker}
              />
              {Platform.OS === 'ios' && (
                <TouchableOpacity 
                  style={styles.pickerDone}
                  onPress={() => setShowDatePicker(false)}
                >
                  <Text style={styles.pickerDoneText}>完成</Text>
                </TouchableOpacity>
              )}
            </View>
          )}

          {/* Error message */}
          {error && (
            <View style={styles.errorContainer}>
              <Ionicons name="warning" size={16} color="#EF4444" />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          {/* Confirm */}
          <TouchableOpacity 
            style={[styles.confirmBtn, !selectedDate && styles.confirmBtnDisabled]} 
            onPress={handleConfirm} 
            activeOpacity={0.85}
            disabled={!selectedDate}
          >
            <LinearGradient
              colors={selectedDate ? ['#8B5CF6', '#EC4899'] : ['#4B5563', '#374151']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.confirmGradient}
            >
              <Text style={styles.confirmText}>确认并继续</Text>
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
    backgroundColor: 'rgba(10, 6, 18, 0.95)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  card: {
    width: '100%',
    maxWidth: 360,
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
    marginBottom: 24,
  },
  highlight: {
    color: '#EC4899',
    fontWeight: '600',
  },
  label: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginBottom: 12,
    alignSelf: 'flex-start',
  },
  dateButton: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(139, 92, 246, 0.15)',
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 16,
    marginBottom: 16,
    gap: 10,
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.3)',
  },
  dateText: {
    fontSize: 16,
    color: '#fff',
  },
  pickerContainer: {
    width: '100%',
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 12,
    marginBottom: 16,
    overflow: 'hidden',
  },
  picker: {
    height: 150,
  },
  pickerDone: {
    alignItems: 'center',
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.1)',
  },
  pickerDoneText: {
    color: '#8B5CF6',
    fontSize: 16,
    fontWeight: '600',
  },
  errorContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 14,
    marginBottom: 16,
    gap: 8,
  },
  errorText: {
    color: '#EF4444',
    fontSize: 14,
  },
  confirmBtn: {
    width: '100%',
    borderRadius: 16,
    overflow: 'hidden',
    marginBottom: 12,
  },
  confirmBtnDisabled: {
    opacity: 0.7,
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
