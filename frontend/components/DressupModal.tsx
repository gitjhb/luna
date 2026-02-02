/**
 * Dressup Modal - 换装选择界面
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { interactionsService, DressupOption, PhotoResponse } from '../services/interactionsService';

interface DressupModalProps {
  visible: boolean;
  onClose: () => void;
  characterId: string;
  onSuccess: (result: PhotoResponse) => void;
}

export const DressupModal: React.FC<DressupModalProps> = ({
  visible,
  onClose,
  characterId,
  onSuccess,
}) => {
  const [tops, setTops] = useState<DressupOption[]>([]);
  const [bottoms, setBottoms] = useState<DressupOption[]>([]);
  const [selectedTop, setSelectedTop] = useState<string>('');
  const [selectedBottom, setSelectedBottom] = useState<string>('');
  const [cost, setCost] = useState(50);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // 加载换装选项
  useEffect(() => {
    if (visible) {
      loadOptions();
    }
  }, [visible]);

  const loadOptions = async () => {
    setLoading(true);
    try {
      const options = await interactionsService.getDressupOptions();
      setTops(options.tops);
      setBottoms(options.bottoms);
      setCost(options.cost);
      // 默认选中第一个
      if (options.tops.length > 0) setSelectedTop(options.tops[0].id);
      if (options.bottoms.length > 0) setSelectedBottom(options.bottoms[0].id);
    } catch (e) {
      console.error('Failed to load dressup options:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!selectedTop || !selectedBottom) {
      Alert.alert('请选择', '请选择上衣和下装');
      return;
    }

    setSubmitting(true);
    try {
      const result = await interactionsService.dressup(characterId, selectedTop, selectedBottom);
      onSuccess(result);
      onClose();
    } catch (e: any) {
      Alert.alert('换装失败', e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const renderOption = (
    option: DressupOption,
    isSelected: boolean,
    onSelect: () => void
  ) => (
    <TouchableOpacity
      key={option.id}
      style={[styles.optionItem, isSelected && styles.optionItemSelected]}
      onPress={onSelect}
    >
      <Text style={styles.optionIcon}>{option.icon}</Text>
      <Text style={[styles.optionName, isSelected && styles.optionNameSelected]}>
        {option.name}
      </Text>
      {isSelected && (
        <Ionicons name="checkmark-circle" size={20} color="#A855F7" />
      )}
    </TouchableOpacity>
  );

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
          <View style={styles.header}>
            <Text style={styles.title}>👗 换装</Text>
            <TouchableOpacity onPress={onClose}>
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>
          </View>

          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#A855F7" />
            </View>
          ) : (
            <ScrollView style={styles.content}>
              {/* 上衣选择 */}
              <Text style={styles.sectionTitle}>👕 上衣</Text>
              <View style={styles.optionsGrid}>
                {tops.map((top) =>
                  renderOption(top, selectedTop === top.id, () => setSelectedTop(top.id))
                )}
              </View>

              {/* 下装选择 */}
              <Text style={styles.sectionTitle}>👖 下装</Text>
              <View style={styles.optionsGrid}>
                {bottoms.map((bottom) =>
                  renderOption(bottom, selectedBottom === bottom.id, () => setSelectedBottom(bottom.id))
                )}
              </View>
            </ScrollView>
          )}

          {/* Footer */}
          <View style={styles.footer}>
            <Text style={styles.costText}>消费: {cost} 月石</Text>
            <TouchableOpacity
              style={[styles.confirmButton, submitting && styles.confirmButtonDisabled]}
              onPress={handleConfirm}
              disabled={submitting || loading}
            >
              {submitting ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.confirmButtonText}>确认换装</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'flex-end',
  },
  container: {
    backgroundColor: '#1A1025',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '70%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  loadingContainer: {
    padding: 60,
    alignItems: 'center',
  },
  content: {
    padding: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#A855F7',
    marginBottom: 12,
    marginTop: 8,
  },
  optionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginBottom: 16,
  },
  optionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    gap: 8,
  },
  optionItemSelected: {
    backgroundColor: 'rgba(168, 85, 247, 0.2)',
    borderColor: '#A855F7',
  },
  optionIcon: {
    fontSize: 20,
  },
  optionName: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.7)',
  },
  optionNameSelected: {
    color: '#fff',
    fontWeight: '600',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
  },
  costText: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.6)',
  },
  confirmButton: {
    backgroundColor: '#A855F7',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 20,
  },
  confirmButtonDisabled: {
    opacity: 0.5,
  },
  confirmButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default DressupModal;
