/**
 * Referral Code Input Modal
 * 
 * Shows after new user registration to optionally enter a referral code.
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Modal,
  TextInput,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../theme/config';
import { referralService } from '../services/referralService';

interface Props {
  visible: boolean;
  onClose: () => void;
  onSuccess?: (bonus: number, newBalance: number) => void;
}

export const ReferralCodeModal: React.FC<Props> = ({ visible, onClose, onSuccess }) => {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [bonusAmount, setBonusAmount] = useState(0);

  const handleSubmit = async () => {
    if (!code.trim()) {
      setError('请输入邀请码');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await referralService.applyReferralCode(code.trim());
      
      if (result.success) {
        setSuccess(true);
        setBonusAmount(result.new_user_bonus || 20);
        
        // Notify parent after a short delay
        setTimeout(() => {
          onSuccess?.(result.new_user_bonus || 20, result.new_balance || 0);
        }, 2000);
      } else {
        setError(result.message);
      }
    } catch (e) {
      setError('网络错误，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setCode('');
    setError(null);
    setSuccess(false);
    onClose();
  };

  const handleSkip = () => {
    handleClose();
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={handleClose}
    >
      <KeyboardAvoidingView 
        style={styles.overlay}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={styles.container}>
          {/* Close button */}
          <TouchableOpacity style={styles.closeButton} onPress={handleClose}>
            <Ionicons name="close" size={24} color={theme.colors.text.secondary} />
          </TouchableOpacity>

          {success ? (
            // Success State
            <View style={styles.successContainer}>
              <View style={styles.successIcon}>
                <Text style={styles.successEmoji}>🎉</Text>
              </View>
              <Text style={styles.successTitle}>领取成功！</Text>
              <Text style={styles.successText}>
                你已获得 <Text style={styles.successAmount}>{bonusAmount}</Text> 月光碎片
              </Text>
            </View>
          ) : (
            // Input State
            <>
              <View style={styles.iconContainer}>
                <Text style={styles.icon}>🎁</Text>
              </View>
              
              <Text style={styles.title}>有邀请码？</Text>
              <Text style={styles.subtitle}>
                输入好友的邀请码，即可获得月光碎片
              </Text>

              <View style={styles.inputContainer}>
                <TextInput
                  style={styles.input}
                  value={code}
                  onChangeText={(text) => {
                    setCode(text.toUpperCase());
                    setError(null);
                  }}
                  placeholder="请输入邀请码"
                  placeholderTextColor={theme.colors.text.tertiary}
                  autoCapitalize="characters"
                  autoCorrect={false}
                  maxLength={16}
                  editable={!loading}
                />
              </View>

              {error && (
                <View style={styles.errorContainer}>
                  <Ionicons name="alert-circle" size={16} color="#EF4444" />
                  <Text style={styles.errorText}>{error}</Text>
                </View>
              )}

              <TouchableOpacity
                style={[styles.submitButton, loading && styles.submitButtonDisabled]}
                onPress={handleSubmit}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text style={styles.submitButtonText}>确认使用</Text>
                )}
              </TouchableOpacity>

              <TouchableOpacity style={styles.skipButton} onPress={handleSkip}>
                <Text style={styles.skipButtonText}>暂时跳过</Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  container: {
    width: '100%',
    maxWidth: 340,
    backgroundColor: theme.colors.background.secondary,
    borderRadius: 24,
    padding: 28,
    alignItems: 'center',
  },
  closeButton: {
    position: 'absolute',
    top: 16,
    right: 16,
    width: 32,
    height: 32,
    justifyContent: 'center',
    alignItems: 'center',
  },
  iconContainer: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: 'rgba(255, 215, 0, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  icon: {
    fontSize: 36,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: theme.colors.text.secondary,
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 20,
  },
  inputContainer: {
    width: '100%',
    marginBottom: 12,
  },
  input: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 14,
    paddingHorizontal: 18,
    paddingVertical: 14,
    fontSize: 18,
    color: '#fff',
    textAlign: 'center',
    letterSpacing: 2,
    fontWeight: '600',
  },
  errorContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 16,
  },
  errorText: {
    fontSize: 13,
    color: '#EF4444',
  },
  submitButton: {
    width: '100%',
    backgroundColor: theme.colors.primary.main,
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: 12,
  },
  submitButtonDisabled: {
    opacity: 0.6,
  },
  submitButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  skipButton: {
    paddingVertical: 8,
  },
  skipButtonText: {
    fontSize: 14,
    color: theme.colors.text.tertiary,
  },
  
  // Success state
  successContainer: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  successIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  successEmoji: {
    fontSize: 40,
  },
  successTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 12,
  },
  successText: {
    fontSize: 16,
    color: theme.colors.text.secondary,
    textAlign: 'center',
  },
  successAmount: {
    color: '#FFD700',
    fontWeight: '700',
  },
});

export default ReferralCodeModal;
