/**
 * Tabs Layout - Purple Pink Theme
 */

import React, { useEffect, useState } from 'react';
import { View, StyleSheet, Platform } from 'react-native';
import { Tabs, useRouter, useSegments } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { theme } from '../../theme/config';
import { useChatStore } from '../../store/chatStore';

const GRADIENT_COLORS: [string, string] = ['#EC4899', '#8B5CF6'];

export default function TabsLayout() {
  const router = useRouter();
  const segments = useSegments();
  const { sessions } = useChatStore();
  const [hasInitialized, setHasInitialized] = useState(false);

  // Redirect to appropriate tab based on whether user has chats
  useEffect(() => {
    if (hasInitialized) return;
    
    // Only redirect on initial load when on index (discover) page
    const currentTab = segments[segments.length - 1];
    if (currentTab === 'index' || currentTab === '(tabs)') {
      if (sessions.length > 0) {
        // Has chats -> go to messages
        router.replace('/(tabs)/chats');
      }
      // No chats -> stay on discover (index)
    }
    setHasInitialized(true);
  }, [sessions, hasInitialized]);

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: theme.colors.primary.main,
        tabBarInactiveTintColor: theme.colors.text.tertiary,
        tabBarStyle: styles.tabBar,
        tabBarLabelStyle: styles.tabBarLabel,
        tabBarItemStyle: styles.tabBarItem,
      }}
    >
      {/* Order: 消息 -> 发现 -> 我的 */}
      <Tabs.Screen
        name="chats"
        options={{
          title: '消息',
          tabBarIcon: ({ color, focused }) => (
            focused ? (
              <LinearGradient colors={GRADIENT_COLORS} style={styles.activeIcon}>
                <Ionicons name="chatbubbles" size={22} color="#fff" />
              </LinearGradient>
            ) : (
              <Ionicons name="chatbubbles-outline" size={24} color={color} />
            )
          ),
        }}
      />
      
      <Tabs.Screen
        name="index"
        options={{
          title: '发现',
          tabBarIcon: ({ color, focused }) => (
            focused ? (
              <LinearGradient colors={GRADIENT_COLORS} style={styles.activeIcon}>
                <Ionicons name="heart" size={22} color="#fff" />
              </LinearGradient>
            ) : (
              <Ionicons name="heart-outline" size={24} color={color} />
            )
          ),
        }}
      />
      
      <Tabs.Screen
        name="profile"
        options={{
          title: '我的',
          tabBarIcon: ({ color, focused }) => (
            focused ? (
              <LinearGradient colors={GRADIENT_COLORS} style={styles.activeIcon}>
                <Ionicons name="person" size={22} color="#fff" />
              </LinearGradient>
            ) : (
              <Ionicons name="person-outline" size={24} color={color} />
            )
          ),
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: theme.colors.background.secondary,
    borderTopWidth: 1,
    borderTopColor: theme.colors.border,
    height: Platform.OS === 'ios' ? 88 : 64,
    paddingTop: 8,
    paddingBottom: Platform.OS === 'ios' ? 28 : 8,
  },
  tabBarLabel: {
    fontSize: 11,
    fontWeight: '500',
    marginTop: 4,
  },
  tabBarItem: {
    paddingTop: 4,
  },
  activeIcon: {
    width: 42,
    height: 42,
    borderRadius: 21,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
