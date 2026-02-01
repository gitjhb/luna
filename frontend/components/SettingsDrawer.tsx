/**
 * Settings Drawer Component
 * Slides in from the left side with animation
 */

import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Switch,
  ScrollView,
  Animated,
  Dimensions,
  Modal,
  TouchableWithoutFeedback,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme, themeList } from '../theme/config';
import { useUserStore } from '../store/userStore';
import { useChatStore } from '../store/chatStore';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const DRAWER_WIDTH = SCREEN_WIDTH * 0.8;

interface SettingsDrawerProps {
  visible: boolean;
  onClose: () => void;
}

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
      <Ionicons name={icon} size={18} color={danger ? '#EF4444' : '#EC4899'} />
    </View>
    <View style={styles.settingContent}>
      <Text style={[styles.settingTitle, danger && styles.settingTitleDanger]}>{title}</Text>
      {subtitle && <Text style={styles.settingSubtitle}>{subtitle}</Text>}
    </View>
    {rightElement || (onPress && (
      <Ionicons name="chevron-forward" size={18} color="rgba(255, 255, 255, 0.4)" />
    ))}
  </TouchableOpacity>
);

export default function SettingsDrawer({ visible, onClose }: SettingsDrawerProps) {
  const router = useRouter();
  const { theme, setTheme, themeId } = useTheme();
  const insets = useSafeAreaInsets();
  const slideAnim = useRef(new Animated.Value(-DRAWER_WIDTH)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;
  
  const { user, logout, isSubscribed } = useUserStore();
  const { isSpicyMode, setSpicyMode } = useChatStore();

  useEffect(() => {
    if (visible) {
      // Reset position before animating in
      slideAnim.setValue(-DRAWER_WIDTH);
      fadeAnim.setValue(0);
      
      Animated.parallel([
        Animated.spring(slideAnim, {
          toValue: 0,
          useNativeDriver: true,
          tension: 50,
          friction: 8,
          velocity: 3,
        }),
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start();
    } else {
      Animated.parallel([
        Animated.spring(slideAnim, {
          toValue: -DRAWER_WIDTH,
          useNativeDriver: true,
          tension: 80,
          friction: 10,
        }),
        Animated.timing(fadeAnim, {
          toValue: 0,
          duration: 250,
          useNativeDriver: true,
        }),
      ]).start();
    }
  }, [visible]);

  const handleLogout = () => {
    Alert.alert('Log Out', 'Are you sure you want to log out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log Out',
        style: 'destructive',
        onPress: () => {
          onClose();
          logout();
          router.replace('/auth/login');
        },
      },
    ]);
  };

  if (!visible) return null;

  return (
    <Modal transparent visible={visible} onRequestClose={onClose}>
      {/* Backdrop */}
      <TouchableWithoutFeedback onPress={onClose}>
        <Animated.View style={[styles.backdrop, { opacity: fadeAnim }]} />
      </TouchableWithoutFeedback>

      {/* Drawer */}
      <Animated.View 
        style={[
          styles.drawer, 
          { 
            transform: [{ translateX: slideAnim }],
            paddingTop: insets.top,
            paddingBottom: insets.bottom,
            backgroundColor: theme.colors.background.secondary,
            ...(theme.effects?.borderGlow && {
              borderRightWidth: 1,
              borderRightColor: theme.colors.glow,
              shadowColor: theme.colors.glow,
            })
          }
        ]}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>设置</Text>
          <TouchableOpacity style={styles.closeButton} onPress={onClose}>
            <Ionicons name="close" size={24} color="#fff" />
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
          {/* User Info */}
          <TouchableOpacity 
            style={styles.userCard}
            onPress={() => { onClose(); router.push('/(tabs)/profile'); }}
          >
            <View style={[styles.userAvatar, { backgroundColor: theme.colors.primary.main }]}>
              <Text style={styles.userAvatarText}>
                {user?.displayName?.charAt(0).toUpperCase() || 'U'}
              </Text>
            </View>
            <View style={styles.userInfo}>
              <Text style={styles.userName}>{user?.displayName || 'Guest'}</Text>
              <Text style={styles.userEmail}>{user?.email || ''}</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={theme.colors.text.tertiary} />
          </TouchableOpacity>

          {/* Preferences */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Preferences</Text>
            <View style={styles.sectionContent}>
              <SettingItem
                icon="flame-outline"
                title="Spicy Mode"
                subtitle={isSubscribed ? 'Unlock intimate content' : 'Premium only'}
                rightElement={
                  <Switch
                    value={isSpicyMode}
                    onValueChange={setSpicyMode}
                    disabled={!isSubscribed}
                    trackColor={{ false: '#3e3e3e', true: theme.colors.primary.main }}
                    thumbColor={isSpicyMode ? '#fff' : '#f4f3f4'}
                  />
                }
              />
              <SettingItem
                icon="notifications-outline"
                title="Notifications"
                onPress={() => {}}
              />
              <SettingItem
                icon="language-outline"
                title="Language"
                subtitle="简体中文"
                onPress={() => {}}
              />
            </View>
          </View>

          {/* Theme Selection */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>主题风格</Text>
            <View style={[styles.sectionContent, { flexDirection: 'row', flexWrap: 'wrap', gap: 12, paddingVertical: 8 }]}>
              {themeList.map((t) => {
                const isActive = themeId === t.id;
                const isCyberpunk = t.id === 'cyberpunk-2077';
                return (
                  <TouchableOpacity
                    key={t.id}
                    style={[
                      styles.themeCard,
                      isActive && { borderColor: theme.colors.primary.main, borderWidth: 2 },
                      { borderRadius: isCyberpunk ? 4 : 12 },
                      isActive && isCyberpunk && {
                        shadowColor: '#00F0FF',
                        shadowOffset: { width: 0, height: 0 },
                        shadowOpacity: 0.5,
                        shadowRadius: 8,
                      }
                    ]}
                    onPress={() => setTheme(t.id)}
                  >
                    <Text style={styles.themeIcon}>{t.icon}</Text>
                    <Text style={[
                      styles.themeName,
                      isActive && isCyberpunk && { color: '#00F0FF' }
                    ]}>{t.nameCn}</Text>
                    {isActive && (
                      <Ionicons name="checkmark-circle" size={16} color={theme.colors.primary.main} style={{ position: 'absolute', top: 4, right: 4 }} />
                    )}
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>

          {/* Support */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Support</Text>
            <View style={styles.sectionContent}>
              <SettingItem
                icon="help-circle-outline"
                title="Help Center"
                onPress={() => {}}
              />
              <SettingItem
                icon="star-outline"
                title="Rate App"
                onPress={() => {}}
              />
              <SettingItem
                icon="document-text-outline"
                title="Terms & Privacy"
                onPress={() => {}}
              />
            </View>
          </View>

          {/* Account */}
          <View style={styles.section}>
            <View style={styles.sectionContent}>
              <SettingItem
                icon="log-out-outline"
                title="Log Out"
                onPress={handleLogout}
                danger
              />
            </View>
          </View>

          {/* Version */}
          <Text style={styles.version}>Luna v1.0.0</Text>
        </ScrollView>
      </Animated.View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
  },
  drawer: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    width: DRAWER_WIDTH,
    // backgroundColor set via inline style for theme support
    // Shadow for depth effect
    shadowColor: '#000',
    shadowOffset: { width: 8, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 20,
    elevation: 20,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
  },
  closeButton: {
    width: 36,
    height: 36,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    flex: 1,
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  userCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: 16,
    padding: 14,
    marginBottom: 24,
  },
  userAvatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    // backgroundColor set via inline style for theme support
    justifyContent: 'center',
    alignItems: 'center',
  },
  userAvatarText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  userInfo: {
    flex: 1,
    marginLeft: 12,
  },
  userName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  userEmail: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.4)',
    marginTop: 2,
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '600',
    color: 'rgba(255, 255, 255, 0.4)',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
    marginLeft: 4,
  },
  sectionContent: {
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: 14,
    overflow: 'hidden',
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(255, 255, 255, 0.06)',
  },
  settingIcon: {
    width: 32,
    height: 32,
    borderRadius: 8,
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
    fontSize: 15,
    fontWeight: '500',
    color: '#fff',
  },
  settingTitleDanger: {
    color: '#EF4444',
  },
  settingSubtitle: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.4)',
    marginTop: 2,
  },
  version: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.4)',
    textAlign: 'center',
    marginTop: 20,
    marginBottom: 40,
  },
  themeCard: {
    width: '45%',
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    paddingVertical: 16,
    paddingHorizontal: 12,
    alignItems: 'center',
    position: 'relative',
  },
  themeIcon: {
    fontSize: 24,
    marginBottom: 8,
  },
  themeName: {
    fontSize: 13,
    fontWeight: '500',
    color: '#fff',
  },
});
