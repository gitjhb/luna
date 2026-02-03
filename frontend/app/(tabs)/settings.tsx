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
import { useTheme, themeList, ThemeConfig } from '../../theme/config';
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
  theme: ThemeConfig;
}

const SettingItem = ({ icon, title, subtitle, onPress, rightElement, danger, theme }: SettingItemProps) => (
  <TouchableOpacity 
    style={[
      styles.settingItem,
      { borderBottomColor: theme.colors.border }
    ]} 
    onPress={onPress}
    disabled={!onPress}
    activeOpacity={onPress ? 0.7 : 1}
  >
    <View style={[
      styles.settingIcon, 
      danger && styles.settingIconDanger,
      { backgroundColor: danger ? 'rgba(239, 68, 68, 0.15)' : `${theme.colors.primary.main}20` }
    ]}>
      <Ionicons name={icon} size={20} color={danger ? theme.colors.error : theme.colors.primary.main} />
    </View>
    <View style={styles.settingContent}>
      <Text style={[styles.settingTitle, danger && { color: theme.colors.error }]}>{title}</Text>
      {subtitle && <Text style={[styles.settingSubtitle, { color: theme.colors.text.tertiary }]}>{subtitle}</Text>}
    </View>
    {rightElement || (onPress && (
      <Ionicons name="chevron-forward" size={20} color={theme.colors.text.tertiary} />
    ))}
  </TouchableOpacity>
);

const SettingSection = ({ title, children, theme }: { title: string; children: React.ReactNode; theme: ThemeConfig }) => (
  <View style={styles.section}>
    <Text style={[styles.sectionTitle, { color: theme.colors.text.tertiary }]}>{title}</Text>
    <View style={styles.sectionContent}>{children}</View>
  </View>
);

// Theme Selector Component
const ThemeSelector = () => {
  const { themeId, setTheme, theme: currentTheme } = useTheme();
  
  return (
    <View style={styles.section}>
      <Text style={[styles.sectionTitle, { color: currentTheme.colors.text.tertiary }]}>主题风格</Text>
      <View style={styles.themeGrid}>
        {themeList.map((t) => {
          const isActive = themeId === t.id;
          const isCyberpunk = t.id === 'cyberpunk-2077';
          
          return (
            <TouchableOpacity
              key={t.id}
              style={[
                styles.themeCard,
                isActive && styles.themeCardActive,
                { 
                  borderColor: isActive ? currentTheme.colors.primary.main : 'rgba(255,255,255,0.1)',
                  backgroundColor: isActive 
                    ? `${currentTheme.colors.primary.main}15` 
                    : 'rgba(255, 255, 255, 0.06)',
                  borderRadius: isCyberpunk ? 4 : 16,
                },
                // Cyberpunk glow effect when active
                isActive && isCyberpunk && {
                  shadowColor: '#00F0FF',
                  shadowOffset: { width: 0, height: 0 },
                  shadowOpacity: 0.5,
                  shadowRadius: 10,
                  elevation: 10,
                }
              ]}
              onPress={() => setTheme(t.id)}
            >
              <Text style={styles.themeIcon}>{t.icon}</Text>
              <Text style={[
                styles.themeName,
                isCyberpunk && isActive && { 
                  color: '#00F0FF',
                  textShadowColor: '#00F0FF',
                  textShadowOffset: { width: 0, height: 0 },
                  textShadowRadius: 8,
                }
              ]}>{t.nameCn}</Text>
              {isActive && (
                <View style={[styles.themeCheck, { backgroundColor: currentTheme.colors.primary.main }]}>
                  <Ionicons name="checkmark" size={12} color="#fff" />
                </View>
              )}
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
};

export default function SettingsScreen() {
  const router = useRouter();
  const { theme } = useTheme();
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
    <LinearGradient colors={[...theme.colors.background.gradient]} style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={[
            styles.title,
            theme.effects?.borderGlow && {
              textShadowColor: theme.colors.glow,
              textShadowOffset: { width: 0, height: 0 },
              textShadowRadius: 10,
            }
          ]}>设置</Text>
        </View>

        <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
          {/* Account Section */}
          <SettingSection title="Account" theme={theme}>
            <SettingItem
              icon="person-circle-outline"
              title="Profile"
              subtitle={user?.email || 'Not logged in'}
              onPress={() => router.push('/(tabs)/profile')}
              theme={theme}
            />
            <SettingItem
              icon="diamond-outline"
              title="Subscription"
              subtitle={isSubscribed ? 'Premium Member' : 'Free Plan - 点击升级'}
              onPress={() => setShowSubscriptionModal(true)}
              theme={theme}
            />
            {isSubscribed && (
              <SettingItem
                icon="close-circle-outline"
                title="取消订阅"
                subtitle="降级为免费用户，金币保留"
                onPress={handleCancelSubscription}
                danger
                theme={theme}
              />
            )}
          </SettingSection>

          {/* Interests Section */}
          <SettingSection title="我的兴趣" theme={theme}>
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
          <SettingSection title="Preferences" theme={theme}>
            {/* NSFW toggle removed - only available on web version for App Store compliance */}
            <SettingItem
              icon="notifications-outline"
              title="Notifications"
              subtitle="Push notifications"
              onPress={() => {}}
              theme={theme}
            />
            <SettingItem
              icon="language-outline"
              title="Language"
              subtitle="简体中文"
              onPress={() => {}}
              theme={theme}
            />
          </SettingSection>

          {/* Theme Section */}
          <ThemeSelector />

          {/* Storage Section */}
          <SettingSection title="Storage" theme={theme}>
            <SettingItem
              icon="folder-outline"
              title="Clear Cache"
              subtitle="Free up space"
              onPress={handleClearCache}
              theme={theme}
            />
          </SettingSection>

          {/* Support Section */}
          <SettingSection title="Support" theme={theme}>
            <SettingItem
              icon="help-circle-outline"
              title="Help Center"
              onPress={() => {}}
              theme={theme}
            />
            <SettingItem
              icon="chatbox-ellipses-outline"
              title="Contact Us"
              onPress={() => {}}
              theme={theme}
            />
            <SettingItem
              icon="star-outline"
              title="Rate App"
              onPress={() => {}}
              theme={theme}
            />
          </SettingSection>

          {/* Legal Section */}
          <SettingSection title="Legal" theme={theme}>
            <SettingItem
              icon="document-text-outline"
              title="Terms of Service"
              onPress={() => {}}
              theme={theme}
            />
            <SettingItem
              icon="shield-checkmark-outline"
              title="Privacy Policy"
              onPress={() => {}}
              theme={theme}
            />
          </SettingSection>

          {/* Danger Zone */}
          <SettingSection title="Account Actions" theme={theme}>
            <SettingItem
              icon="log-out-outline"
              title="Log Out"
              onPress={handleLogout}
              danger
              theme={theme}
            />
            <SettingItem
              icon="trash-outline"
              title="Delete Account"
              onPress={handleDeleteAccount}
              danger
              theme={theme}
            />
          </SettingSection>

          {/* App Version */}
          <View style={styles.versionContainer}>
            <Text style={[styles.versionText, { color: theme.colors.text.tertiary }]}>Luna v1.0.0</Text>
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
  },
  settingIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  settingIconDanger: {
    // Handled by inline style
  },
  settingContent: {
    flex: 1,
  },
  settingTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#fff',
  },
  settingSubtitle: {
    fontSize: 13,
    marginTop: 2,
  },
  versionContainer: {
    alignItems: 'center',
    paddingVertical: 24,
    marginBottom: 100,
  },
  versionText: {
    fontSize: 13,
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
    padding: 16,
    alignItems: 'center',
    borderWidth: 2,
    position: 'relative',
  },
  themeCardActive: {
    // Handled by inline style
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
