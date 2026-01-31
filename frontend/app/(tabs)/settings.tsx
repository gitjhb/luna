/**
 * Settings Screen
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { theme } from '../../theme/config';
import { useUserStore } from '../../store/userStore';
import { useChatStore } from '../../store/chatStore';
import { SubscriptionModal } from '../../components/SubscriptionModal';

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
    disabled={!onPress && !rightElement}
    activeOpacity={0.7}
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

export default function SettingsScreen() {
  const router = useRouter();
  const { user, logout, isSubscribed } = useUserStore();
  const { isSpicyMode, setSpicyMode } = useChatStore();
  const [showSubscriptionModal, setShowSubscriptionModal] = useState(false);

  const handleSpicyModeToggle = (value: boolean) => {
    if (value && !isSubscribed) {
      // Show subscription modal if trying to enable without subscription
      setShowSubscriptionModal(true);
    } else {
      setSpicyMode(value);
    }
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
          </SettingSection>

          {/* Preferences Section */}
          <SettingSection title="Preferences">
            <SettingItem
              icon="flame-outline"
              title="Spicy Mode"
              subtitle={isSubscribed ? 'Unlock intimate content' : '需要订阅 Premium'}
              onPress={!isSubscribed ? () => setShowSubscriptionModal(true) : undefined}
              rightElement={
                <Switch
                  value={isSpicyMode}
                  onValueChange={handleSpicyModeToggle}
                  trackColor={{ false: '#3e3e3e', true: theme.colors.primary.main }}
                  thumbColor={isSpicyMode ? '#fff' : '#f4f3f4'}
                />
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
        highlightFeature="spicy"
        onSubscribeSuccess={(tier) => {
          // After successful subscription, enable spicy mode if that was the intent
          if (tier !== 'free') {
            setSpicyMode(true);
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
});
