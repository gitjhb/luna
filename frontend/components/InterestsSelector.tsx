/**
 * Interests Selector Component
 * 
 * A multi-select chip-style UI for user interests/hobbies
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  ScrollView,
  Alert,
} from 'react-native';
import { theme } from '../theme/config';
import { interestsService, InterestItem } from '../services/interestsService';

interface InterestsSelectorProps {
  /** Called when interests are successfully saved */
  onSave?: (interestIds: number[]) => void;
  /** Show inline or as a standalone section */
  inline?: boolean;
}

export const InterestsSelector: React.FC<InterestsSelectorProps> = ({
  onSave,
  inline = false,
}) => {
  const [allInterests, setAllInterests] = useState<InterestItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [originalIds, setOriginalIds] = useState<number[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      // Load both interest list and user's selections in parallel
      const [listResponse, userResponse] = await Promise.all([
        interestsService.getInterestList(),
        interestsService.getUserInterests(),
      ]);
      
      setAllInterests(listResponse.interests);
      setCategories(listResponse.categories);
      setSelectedIds(userResponse.interestIds);
      setOriginalIds(userResponse.interestIds);
    } catch (e) {
      console.error('Failed to load interests:', e);
      Alert.alert('加载失败', '无法加载兴趣列表，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const toggleInterest = (id: number) => {
    setSelectedIds(prev => {
      const newIds = prev.includes(id)
        ? prev.filter(i => i !== id)
        : [...prev, id];
      
      // Check if there are changes
      const changed = JSON.stringify(newIds.sort()) !== JSON.stringify(originalIds.sort());
      setHasChanges(changed);
      
      return newIds;
    });
  };

  const handleSave = async () => {
    if (!hasChanges) return;
    
    try {
      setSaving(true);
      const response = await interestsService.updateUserInterests(selectedIds);
      setOriginalIds(response.interestIds);
      setHasChanges(false);
      
      if (onSave) {
        onSave(response.interestIds);
      }
      
      Alert.alert('保存成功', '你的兴趣爱好已更新');
    } catch (e: any) {
      console.error('Failed to save interests:', e);
      Alert.alert('保存失败', e.message || '请稍后重试');
    } finally {
      setSaving(false);
    }
  };

  const getCategoryLabel = (category: string): string => {
    const labels: Record<string, string> = {
      entertainment: '🎯 娱乐',
      sports: '🏃 运动健身',
      creative: '🎨 创意爱好',
      social: '🌟 生活社交',
      tech: '💡 科技学习',
    };
    return labels[category] || category;
  };

  const getInterestsByCategory = (category: string): InterestItem[] => {
    return allInterests.filter(i => i.category === category);
  };

  if (loading) {
    return (
      <View style={[styles.container, inline && styles.containerInline]}>
        <ActivityIndicator size="large" color={theme.colors.primary.main} />
        <Text style={styles.loadingText}>加载中...</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, inline && styles.containerInline]}>
      {!inline && (
        <View style={styles.header}>
          <Text style={styles.title}>选择你的兴趣</Text>
          <Text style={styles.subtitle}>让 AI 更好地了解你，提供个性化的对话体验</Text>
        </View>
      )}

      <ScrollView 
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
        nestedScrollEnabled={true}
      >
        {categories.map(category => (
          <View key={category} style={styles.categorySection}>
            <Text style={styles.categoryTitle}>{getCategoryLabel(category)}</Text>
            <View style={styles.chipsContainer}>
              {getInterestsByCategory(category).map(interest => {
                const isSelected = selectedIds.includes(interest.id);
                return (
                  <TouchableOpacity
                    key={interest.id}
                    style={[
                      styles.chip,
                      isSelected && styles.chipSelected,
                    ]}
                    onPress={() => toggleInterest(interest.id)}
                    activeOpacity={0.7}
                  >
                    <Text style={[
                      styles.chipText,
                      isSelected && styles.chipTextSelected,
                    ]}>
                      {interest.displayName}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>
        ))}

        {/* Selected count & Save button */}
        <View style={styles.footer}>
          <Text style={styles.selectedCount}>
            已选择 {selectedIds.length} 个兴趣
          </Text>
          
          {hasChanges && (
            <TouchableOpacity
              style={[styles.saveButton, saving && styles.saveButtonDisabled]}
              onPress={handleSave}
              disabled={saving}
            >
              {saving ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.saveButtonText}>保存</Text>
              )}
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 16,
    padding: 16,
    marginVertical: 8,
  },
  containerInline: {
    flex: 0,
    maxHeight: 400,
  },
  header: {
    marginBottom: 20,
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: theme.colors.text.tertiary,
  },
  scrollView: {
    flex: 1,
  },
  categorySection: {
    marginBottom: 16,
  },
  categoryTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.text.secondary,
    marginBottom: 10,
  },
  chipsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  chipSelected: {
    backgroundColor: 'rgba(139, 92, 246, 0.25)',
    borderColor: theme.colors.primary.main,
  },
  chipText: {
    fontSize: 14,
    color: theme.colors.text.secondary,
  },
  chipTextSelected: {
    color: '#fff',
    fontWeight: '500',
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
  },
  selectedCount: {
    fontSize: 13,
    color: theme.colors.text.tertiary,
  },
  saveButton: {
    backgroundColor: theme.colors.primary.main,
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
    minWidth: 70,
    alignItems: 'center',
  },
  saveButtonDisabled: {
    opacity: 0.6,
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  loadingText: {
    color: theme.colors.text.tertiary,
    marginTop: 12,
    textAlign: 'center',
  },
});
