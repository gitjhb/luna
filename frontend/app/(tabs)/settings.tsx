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
  Platform,
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import * as StoreReview from 'expo-store-review';
import { useTheme, ThemeConfig } from '../../theme/config';
import { useUserStore } from '../../store/userStore';
import { useChatStore } from '../../store/chatStore';
import { SubscriptionModal } from '../../components/SubscriptionModal';
import { InterestsSelector } from '../../components/InterestsSelector';
import { settingsService } from '../../services/settingsService';
import { paymentService } from '../../services/paymentService';
import { pushService } from '../../services/pushService';

// Notification preferences storage key
const NOTIFICATION_PREFS_KEY = '@luna_notification_prefs';

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

// Notification Settings types
interface NotificationPrefs {
  messageNotifications: boolean;
  dateReminders: boolean;
  activityNotifications: boolean;
}

const defaultNotificationPrefs: NotificationPrefs = {
  messageNotifications: true,
  dateReminders: true,
  activityNotifications: true,
};

// Notification Settings Component
const NotificationSettings = ({ theme }: { theme: ThemeConfig }) => {
  const [prefs, setPrefs] = useState<NotificationPrefs>(defaultNotificationPrefs);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadNotificationPrefs();
    checkPermission();
  }, []);

  const loadNotificationPrefs = async () => {
    try {
      const stored = await AsyncStorage.getItem(NOTIFICATION_PREFS_KEY);
      if (stored) {
        setPrefs(JSON.parse(stored));
      }
    } catch (e) {
      console.log('Failed to load notification prefs:', e);
    } finally {
      setLoading(false);
    }
  };

  const checkPermission = async () => {
    const { status } = await Notifications.getPermissionsAsync();
    setHasPermission(status === 'granted');
  };

  const requestPermission = async () => {
    if (!Device.isDevice) {
      Alert.alert('提示', '通知功能需要在真实设备上使用');
      return false;
    }

    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== 'granted') {
      Alert.alert(
        '需要通知权限',
        '请在系统设置中启用通知权限，以便接收消息提醒。',
        [
          { text: '取消', style: 'cancel' },
          { 
            text: '去设置', 
            onPress: () => {
              if (Platform.OS === 'ios') {
                Linking.openURL('app-settings:');
              } else {
                Linking.openSettings();
              }
            }
          },
        ]
      );
      return false;
    }

    setHasPermission(true);
    return true;
  };

  const savePrefs = async (newPrefs: NotificationPrefs) => {
    try {
      await AsyncStorage.setItem(NOTIFICATION_PREFS_KEY, JSON.stringify(newPrefs));
      setPrefs(newPrefs);
    } catch (e) {
      console.log('Failed to save notification prefs:', e);
    }
  };

  const handleToggle = async (key: keyof NotificationPrefs, value: boolean) => {
    if (value && !hasPermission) {
      const granted = await requestPermission();
      if (!granted) return;
    }
    
    const newPrefs = { ...prefs, [key]: value };
    await savePrefs(newPrefs);
  };

  if (loading) {
    return (
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: theme.colors.text.tertiary }]}>通知设置</Text>
        <View style={[styles.sectionContent, { padding: 20, alignItems: 'center' }]}>
          <ActivityIndicator color={theme.colors.primary.main} />
        </View>
      </View>
    );
  }

  return (
    <View style={styles.section}>
      <Text style={[styles.sectionTitle, { color: theme.colors.text.tertiary }]}>通知设置</Text>
      <View style={styles.sectionContent}>
        {/* Permission warning */}
        {hasPermission === false && (
          <TouchableOpacity 
            style={[styles.permissionBanner, { backgroundColor: `${theme.colors.warning || '#F59E0B'}20` }]}
            onPress={requestPermission}
          >
            <Ionicons name="warning-outline" size={20} color={theme.colors.warning || '#F59E0B'} />
            <Text style={[styles.permissionText, { color: theme.colors.warning || '#F59E0B' }]}>
              点击授权通知权限
            </Text>
          </TouchableOpacity>
        )}
        
        {/* Message notifications */}
        <View style={[styles.settingItem, { borderBottomColor: theme.colors.border }]}>
          <View style={[styles.settingIcon, { backgroundColor: `${theme.colors.primary.main}20` }]}>
            <Ionicons name="chatbubble-outline" size={20} color={theme.colors.primary.main} />
          </View>
          <View style={styles.settingContent}>
            <Text style={styles.settingTitle}>消息通知</Text>
            <Text style={[styles.settingSubtitle, { color: theme.colors.text.tertiary }]}>
              收到新消息时提醒
            </Text>
          </View>
          <Switch
            value={prefs.messageNotifications}
            onValueChange={(v) => handleToggle('messageNotifications', v)}
            trackColor={{ false: 'rgba(255,255,255,0.2)', true: theme.colors.primary.main }}
            thumbColor="#fff"
          />
        </View>

        {/* Date reminders */}
        <View style={[styles.settingItem, { borderBottomColor: theme.colors.border }]}>
          <View style={[styles.settingIcon, { backgroundColor: `${theme.colors.primary.main}20` }]}>
            <Ionicons name="heart-outline" size={20} color={theme.colors.primary.main} />
          </View>
          <View style={styles.settingContent}>
            <Text style={styles.settingTitle}>约会提醒</Text>
            <Text style={[styles.settingSubtitle, { color: theme.colors.text.tertiary }]}>
              约会时间到时提醒
            </Text>
          </View>
          <Switch
            value={prefs.dateReminders}
            onValueChange={(v) => handleToggle('dateReminders', v)}
            trackColor={{ false: 'rgba(255,255,255,0.2)', true: theme.colors.primary.main }}
            thumbColor="#fff"
          />
        </View>

        {/* Activity notifications */}
        <View style={[styles.settingItem, { borderBottomWidth: 0 }]}>
          <View style={[styles.settingIcon, { backgroundColor: `${theme.colors.primary.main}20` }]}>
            <Ionicons name="sparkles-outline" size={20} color={theme.colors.primary.main} />
          </View>
          <View style={styles.settingContent}>
            <Text style={styles.settingTitle}>活动通知</Text>
            <Text style={[styles.settingSubtitle, { color: theme.colors.text.tertiary }]}>
              新活动和优惠提醒
            </Text>
          </View>
          <Switch
            value={prefs.activityNotifications}
            onValueChange={(v) => handleToggle('activityNotifications', v)}
            trackColor={{ false: 'rgba(255,255,255,0.2)', true: theme.colors.primary.main }}
            thumbColor="#fff"
          />
        </View>
      </View>
    </View>
  );
};

// Rate App Card Component
const RateAppCard = ({ theme }: { theme: ThemeConfig }) => {
  const [canReview, setCanReview] = useState(false);

  useEffect(() => {
    checkReviewAvailability();
  }, []);

  const checkReviewAvailability = async () => {
    const isAvailable = await StoreReview.isAvailableAsync();
    setCanReview(isAvailable);
  };

  const handleRateApp = async () => {
    if (await StoreReview.hasAction()) {
      try {
        await StoreReview.requestReview();
      } catch (e) {
        console.log('Failed to request review:', e);
        Alert.alert('提示', '暂时无法打开评分页面，请稍后再试');
      }
    } else {
      Alert.alert('提示', '此功能在当前设备上不可用');
    }
  };

  return (
    <View style={styles.section}>
      <Text style={[styles.sectionTitle, { color: theme.colors.text.tertiary }]}>支持我们</Text>
      <TouchableOpacity 
        style={[
          styles.rateCard,
          { 
            backgroundColor: 'rgba(255, 255, 255, 0.06)',
            borderColor: theme.colors.primary.main,
          }
        ]}
        onPress={handleRateApp}
        activeOpacity={0.8}
      >
        <LinearGradient
          colors={[`${theme.colors.primary.main}30`, 'transparent']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.rateCardGradient}
        >
          <View style={styles.rateCardContent}>
            <View style={styles.rateStars}>
              {[1, 2, 3, 4, 5].map((star) => (
                <Ionicons 
                  key={star} 
                  name="star" 
                  size={24} 
                  color="#FFD700" 
                  style={styles.starIcon}
                />
              ))}
            </View>
            <Text style={styles.rateTitle}>喜欢 Luna 吗？</Text>
            <Text style={[styles.rateSubtitle, { color: theme.colors.text.secondary }]}>
              给我们一个五星好评，帮助更多人发现 Luna ✨
            </Text>
            <View style={[styles.rateButton, { backgroundColor: theme.colors.primary.main }]}>
              <Ionicons name="heart" size={16} color="#fff" />
              <Text style={styles.rateButtonText}>给我们评分</Text>
            </View>
          </View>
        </LinearGradient>
      </TouchableOpacity>
    </View>
  );
};

// Theme Selector removed - Luna 2077 is the only theme for MVP

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
      '确定要取消订阅吗？\n\n• 将立即降级为免费用户\n• 月光碎片余额保留\n• 不退款',
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
                subtitle="降级为免费用户，碎片余额保留"
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

          {/* Notification Settings Section */}
          <NotificationSettings theme={theme} />

          {/* Preferences Section */}
          <SettingSection title="Preferences" theme={theme}>
            {/* NSFW toggle removed - only available on web version for App Store compliance */}
            <SettingItem
              icon="language-outline"
              title="Language"
              subtitle="简体中文"
              onPress={() => {}}
              theme={theme}
            />
          </SettingSection>

          {/* Theme Section - Hidden for now, TODO: implement properly */}
          {/* <ThemeSelector /> */}

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

          {/* Rate App Card */}
          <RateAppCard theme={theme} />

          {/* Support Section */}
          <SettingSection title="Support" theme={theme}>
            <SettingItem
              icon="help-circle-outline"
              title="帮助中心"
              subtitle="常见问题解答"
              onPress={() => {
                Alert.alert(
                  '常见问题',
                  '1. 如何获得更多月光碎片？\n订阅 Premium 或 VIP 每日获得更多碎片，或直接购买。\n\n2. 如何解锁更多角色？\n提升与角色的亲密度，达到特定等级后解锁新内容。\n\n3. 约会功能怎么玩？\n点击角色页面的约会按钮，选择场景开始互动约会。\n\n更多问题请联系客服。',
                  [{ text: '我知道了' }]
                );
              }}
              theme={theme}
            />
            <SettingItem
              icon="chatbox-ellipses-outline"
              title="联系客服"
              subtitle="support@luna.app"
              onPress={() => {
                Linking.openURL('mailto:support@luna.app?subject=Luna App 反馈');
              }}
              theme={theme}
            />
          </SettingSection>

          {/* Developer Section */}
          <SettingSection title="Developer" theme={theme}>
            <SettingItem
              icon="notifications-outline"
              title="测试推送通知"
              subtitle="发送一条角色消息通知"
              onPress={async () => {
                try {
                  const messages = await pushService.testPush();
                  if (messages.length > 0) {
                    Alert.alert(
                      '推送测试',
                      `已发送 ${messages.length} 条测试通知\n\n${messages[0].character_name}: "${messages[0].message.slice(0, 50)}..."`
                    );
                  } else {
                    Alert.alert('推送测试', '没有可发送的消息');
                  }
                } catch (e: any) {
                  Alert.alert('测试失败', e.message);
                }
              }}
              theme={theme}
            />
          </SettingSection>

          {/* Legal Section */}
          <SettingSection title="Legal" theme={theme}>
            <SettingItem
              icon="document-text-outline"
              title="服务条款"
              onPress={() => router.push('/legal/terms')}
              theme={theme}
            />
            <SettingItem
              icon="shield-checkmark-outline"
              title="隐私政策"
              onPress={() => router.push('/legal/privacy')}
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
  // Notification settings styles
  permissionBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    marginHorizontal: 12,
    marginTop: 12,
    borderRadius: 8,
    gap: 8,
  },
  permissionText: {
    fontSize: 14,
    fontWeight: '500',
  },
  // Rate app card styles
  rateCard: {
    borderRadius: 20,
    borderWidth: 1,
    overflow: 'hidden',
  },
  rateCardGradient: {
    padding: 24,
  },
  rateCardContent: {
    alignItems: 'center',
  },
  rateStars: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  starIcon: {
    marginHorizontal: 2,
  },
  rateTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 8,
  },
  rateSubtitle: {
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 16,
    lineHeight: 20,
  },
  rateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 25,
    gap: 8,
  },
  rateButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
});
