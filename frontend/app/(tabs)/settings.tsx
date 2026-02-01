/**
 * Settings Screen
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { theme, useTheme, themeList } from '../../theme/config';
import { useUserStore } from '../../store/userStore';
import { useChatStore } from '../../store/chatStore';
import { SubscriptionModal } from '../../components/SubscriptionModal';
import { InterestsSelector } from '../../components/InterestsSelector';
import { settingsService } from '../../services/settingsService';
import { paymentService } from '../../services/paymentService';

interface SettingItemProps {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle?: string;
  onPress?: () => void;
  rightElement?: React.ReactNode;
  danger?: boolean;
}

const SettingItem = ({ icon, title, subtitle, onPress, rightElement, danger }: SettingItemProps) => (
  <TouchableOpacity 
    style={styles.settingItem} 
    onPress={onPress}
    disabled={!onPress}
    activeOpacity={onPress ? 0.7 : 1}
  >
    <View style={[styles.settingIcon, danger && styles.settingIconDanger]}>
      <Ionicons name={icon} size={20} color={danger ? '#EF4444' : theme.colors.primary.main} />
    </View>
    <View style={styles.settingContent}>
      <Text style={[styles.settingTitle, danger && styles.settingTitleDanger]}>{title}</Text>
      {subtitle && <Text style={styles.settingSubtitle}>{subtitle}</Text>}
    </View>
    {rightElement || (onPress && (
      <Ionicons name="chevron-forward" size={20} color={theme.colors.text.tertiary} />
    ))}
  </TouchableOpacity>
);

const SettingSection = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <View style={styles.section}>
    <Text style={styles.sectionTitle}>{title}</Text>
    <View style={styles.sectionContent}>{children}</View>
  </View>
);

// Theme Selector Component
const ThemeSelector = () => {
  const { themeId, setTheme, theme: currentTheme } = useTheme();
  
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>主题风格</Text>
      <View style={styles.themeGrid}>
        {themeList.map((t) => (
          <TouchableOpacity
            key={t.id}
            style={[
              styles.themeCard,
              themeId === t.id && styles.themeCardActive,
              { borderColor: themeId === t.id ? currentTheme.colors.primary.main : 'rgba(255,255,255,0.1)' }
            ]}
            onPress={() => setTheme(t.id)}
          >
            <Text style={styles.themeIcon}>{t.icon}</Text>
            <Text style={styles.themeName}>{t.nameCn}</Text>
            {themeId === t.id && (
              <View style={[styles.themeCheck, { backgroundColor: currentTheme.colors.primary.main }]}>
                <Ionicons name="checkmark" size={12} color="#fff" />
              </View>
            )}
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
};

export default function SettingsScreen() {
  const router = useRouter();
  const { user, logout, isSubscribed, preferences, setPreferences } = useUserStore();
  const [showSubscriptionModal, setShowSubscriptionModal] = useState(false);
  const [nsfwLoading, setNsfwLoading] = useState(false);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const settings = await settingsService.getSettings();
      setPreferences({
        nsfwEnabled: settings.nsfwEnabled,
        language: settings.language,
        notificationsEnabled: settings.notificationsEnabled,
      });
    } catch (e) {
      console.log('Failed to load settings:', e);
    }
  };

  const handleNsfwToggle = async (value: boolean) => {
    if (value && !isSubscribed) {
      // Show subscription modal if trying to enable without subscription
      setShowSubscriptionModal(true);
      return;
    }
    
    setNsfwLoading(true);
    try {
      const updated = await settingsService.toggleNsfw(value);
      setPreferences({ nsfwEnabled: updated.nsfwEnabled });
      
      if (value) {
        Alert.alert(
          '🔞 成人内容已开启',
          '角色现在可以使用更加露骨的语言和描写。请确保你已年满18岁。',
          [{ text: '我知道了' }]
        );
      }
    } catch (e: any) {
      Alert.alert('设置失败', e.message || '请稍后重试');
    } finally {
      setNsfwLoading(false);
    }
  };

  const handleCancelSubscription = () => {
    Alert.alert(
      '取消订阅',
      '确定要取消订阅吗？\n\n• 将立即降级为免费用户\n• 金币余额保留\n• 不退款',
      [
        { text: '再想想', style: 'cancel' },
        {
          text: '确定取消',
          style: 'destructive',
          onPress: async () => {
            try {
              const result = await paymentService.cancelSubscription();
              if (result.success) {
                // Update local state - set tier to free
                useUserStore.getState().updateUser({ subscriptionTier: 'free' });
                Alert.alert('已取消', result.message || '订阅已取消，已降级为免费用户。');
              } else {
                Alert.alert('取消失败', result.message || '请稍后重试');
              }
            } catch (e: any) {
              Alert.alert('取消失败', e.message || '请稍后重试');
            }
          },
        },
      ]
    );
  };

  const handleLogout = () => {
    Alert.alert('Log Out', 'Are you sure you want to log out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log Out',
        style: 'destructive',
        onPress: () => {
          logout();
          router.replace('/auth/login');
        },
      },
    ]);
  };

  const handleClearCache = () => {
    Alert.alert('Clear Cache', 'This will clear cached images and data. Your conversations will not be affected.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Clear',
        style: 'destructive',
        onPress: () => {
          // Clear cache logic here
          Alert.alert('Done', 'Cache cleared successfully');
        },
      },
    ]);
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      'Delete Account',
      'This action cannot be undone. All your data, conversations, and purchases will be permanently deleted.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            // Delete account logic here
            Alert.alert('Contact Support', 'Please contact support@luna.app to delete your account.');
          },
        },
      ]
    );
  };

  return (
    <LinearGradient colors={theme.colors.background.gradient} style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>设置</Text>
        </View>

        <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
          {/* Account Section */}
          <SettingSection title="Account">
            <SettingItem
              icon="person-circle-outline"
              title="Profile"
              subtitle={user?.email || 'Not logged in'}
              onPress={() => router.push('/(tabs)/profile')}
            />
            <SettingItem
              icon="diamond-outline"
              title="Subscription"
              subtitle={isSubscribed ? 'Premium Member' : 'Free Plan - 点击升级'}
              onPress={() => setShowSubscriptionModal(true)}
            />
            {isSubscribed && (
              <SettingItem
                icon="close-circle-outline"
                title="取消订阅"
                subtitle="降级为免费用户，金币保留"
                onPress={handleCancelSubscription}
                danger
              />
            )}
          </SettingSection>

          {/* Interests Section */}
          <SettingSection title="我的兴趣">
            <View style={styles.interestsContainer}>
              <InterestsSelector 
                inline={true}
                onSave={(ids) => {
                  console.log('Interests saved:', ids);
                }}
              />
            </View>
          </SettingSection>

          {/* Preferences Section */}
          <SettingSection title="Preferences">
            <SettingItem
              icon="warning-outline"
              title="成人内容 (NSFW)"
              subtitle={isSubscribed ? '开启后角色可以说更露骨的话' : '需要订阅 Premium 才能开启'}
              onPress={!isSubscribed ? () => setShowSubscriptionModal(true) : undefined}
              rightElement={
                nsfwLoading ? (
                  <ActivityIndicator size="small" color={theme.colors.primary.main} />
                ) : (
                  <Switch
                    value={preferences.nsfwEnabled}
                    onValueChange={handleNsfwToggle}
                    disabled={!isSubscribed}
                    trackColor={{ false: '#3e3e3e', true: '#EF4444' }}
                    thumbColor={preferences.nsfwEnabled ? '#fff' : '#f4f3f4'}
                    ios_backgroundColor={!isSubscribed ? '#2a2a2a' : '#3e3e3e'}
                  />
                )
              }
            />
            <SettingItem
              icon="notifications-outline"
              title="Notifications"
              subtitle="Push notifications"
              onPress={() => {}}
            />
            <SettingItem
              icon="language-outline"
              title="Language"
              subtitle="简体中文"
              onPress={() => {}}
            />
          </SettingSection>

          {/* Theme Section */}
          <ThemeSelector />

          {/* Storage Section */}
          <SettingSection title="Storage">
            <SettingItem
              icon="folder-outline"
              title="Clear Cache"
              subtitle="Free up space"
              onPress={handleClearCache}
            />
          </SettingSection>

          {/* Support Section */}
          <SettingSection title="Support">
            <SettingItem
              icon="help-circle-outline"
              title="Help Center"
              onPress={() => {}}
            />
            <SettingItem
              icon="chatbox-ellipses-outline"
              title="Contact Us"
              onPress={() => {}}
            />
            <SettingItem
              icon="star-outline"
              title="Rate App"
              onPress={() => {}}
            />
          </SettingSection>

          {/* Legal Section */}
          <SettingSection title="Legal">
            <SettingItem
              icon="document-text-outline"
              title="Terms of Service"
              onPress={() => {}}
            />
            <SettingItem
              icon="shield-checkmark-outline"
              title="Privacy Policy"
              onPress={() => {}}
            />
          </SettingSection>

          {/* Danger Zone */}
          <SettingSection title="Account Actions">
            <SettingItem
              icon="log-out-outline"
              title="Log Out"
              onPress={handleLogout}
              danger
            />
            <SettingItem
              icon="trash-outline"
              title="Delete Account"
              onPress={handleDeleteAccount}
              danger
            />
          </SettingSection>

          {/* App Version */}
          <View style={styles.versionContainer}>
            <Text style={styles.versionText}>Luna v1.0.0</Text>
          </View>
        </ScrollView>
      </SafeAreaView>

      {/* Subscription Modal */}
      <SubscriptionModal
        visible={showSubscriptionModal}
        onClose={() => setShowSubscriptionModal(false)}
        highlightFeature="nsfw"
        onSubscribeSuccess={async (tier) => {
          // After successful subscription, enable NSFW if that was the intent
          if (tier !== 'free') {
            try {
              const updated = await settingsService.toggleNsfw(true);
              setPreferences({ nsfwEnabled: updated.nsfwEnabled });
            } catch (e) {
              console.log('Failed to enable NSFW after subscription:', e);
            }
          }
        }}
      />
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  safeArea: {
    flex: 1,
  },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
  },
  scrollView: {
    flex: 1,
    paddingHorizontal: 20,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: theme.colors.text.tertiary,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
    marginLeft: 4,
  },
  sectionContent: {
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: 16,
    overflow: 'hidden',
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(255, 255, 255, 0.08)',
  },
  settingIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: 'rgba(139, 92, 246, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  settingIconDanger: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
  },
  settingContent: {
    flex: 1,
  },
  settingTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#fff',
  },
  settingTitleDanger: {
    color: '#EF4444',
  },
  settingSubtitle: {
    fontSize: 13,
    color: theme.colors.text.tertiary,
    marginTop: 2,
  },
  versionContainer: {
    alignItems: 'center',
    paddingVertical: 24,
    marginBottom: 100,
  },
  versionText: {
    fontSize: 13,
    color: theme.colors.text.tertiary,
  },
  interestsContainer: {
    padding: 0,
    margin: 0,
  },
  // Theme selector styles
  themeGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  themeCard: {
    flex: 1,
    minWidth: 140,
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    position: 'relative',
  },
  themeCardActive: {
    backgroundColor: 'rgba(139, 92, 246, 0.15)',
  },
  themeIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  themeName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
  },
  themeCheck: {
    position: 'absolute',
    top: 8,
    right: 8,
    width: 20,
    height: 20,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
