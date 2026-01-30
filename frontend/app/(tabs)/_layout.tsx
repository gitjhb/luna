/**
 * Tabs Layout - WeChat Style Bottom Navigation
 */

import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Platform } from 'react-native';
import { Tabs, useRouter, useSegments } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../theme/config';
import { useChatStore } from '../../store/chatStore';

export default function TabsLayout() {
  const router = useRouter();
  const segments = useSegments();
  const { sessions, messagesBySession } = useChatStore();
  const [hasInitialized, setHasInitialized] = useState(false);

  // Calculate unread messages (simplified - can be enhanced with proper unread tracking)
  const unreadCount = sessions.reduce((count, session) => {
    // For now, just check if there are any messages from assistant that might be "new"
    // In production, you'd track read/unread status properly
    return count;
  }, 0);

  // Redirect to appropriate tab based on whether user has chats
  useEffect(() => {
    if (hasInitialized) return;
    
    // Only redirect on initial load when on discover page
    const currentTab = segments[segments.length - 1];
    if (currentTab === 'chats' || currentTab === '(tabs)') {
      if (sessions.length > 0) {
        // Has chats -> go to messages
        router.replace('/(tabs)/chats');
      }
      // No chats -> stay on current tab (discover)
    }
    setHasInitialized(true);
  }, [sessions, hasInitialized]);

  // Tab icon component with optional badge
  const TabIcon = ({ 
    name, 
    focused, 
    color, 
    badge 
  }: { 
    name: keyof typeof Ionicons.glyphMap; 
    focused: boolean; 
    color: string;
    badge?: number;
  }) => (
    <View style={styles.iconContainer}>
      <Ionicons name={name} size={24} color={focused ? theme.colors.primary.main : color} />
      {badge !== undefined && badge > 0 && (
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{badge > 99 ? '99+' : badge}</Text>
        </View>
      )}
    </View>
  );

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
      {/* Order: 消息 -> 发现 -> 我 */}
      <Tabs.Screen
        name="chats"
        options={{
          title: '消息',
          tabBarIcon: ({ color, focused }) => (
            <TabIcon 
              name={focused ? 'chatbubbles' : 'chatbubbles-outline'} 
              focused={focused} 
              color={color}
              badge={unreadCount}
            />
          ),
        }}
      />
      
      <Tabs.Screen
        name="index"
        options={{
          title: '发现',
          tabBarIcon: ({ color, focused }) => (
            <TabIcon 
              name={focused ? 'search' : 'search-outline'} 
              focused={focused} 
              color={color}
            />
          ),
        }}
      />
      
      <Tabs.Screen
        name="profile"
        options={{
          title: '我',
          tabBarIcon: ({ color, focused }) => (
            <TabIcon 
              name={focused ? 'person' : 'person-outline'} 
              focused={focused} 
              color={color}
            />
          ),
        }}
      />

      {/* Settings - hidden from tab bar, accessed via menu */}
      <Tabs.Screen
        name="settings"
        options={{
          href: null, // Hide from tab bar
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: theme.colors.background.secondary,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
    height: Platform.OS === 'ios' ? 83 : 60,
    paddingTop: 6,
    paddingBottom: Platform.OS === 'ios' ? 28 : 6,
  },
  tabBarLabel: {
    fontSize: 10,
    fontWeight: '400',
    marginTop: 2,
  },
  tabBarItem: {
    paddingTop: 2,
    gap: 2,
  },
  iconContainer: {
    position: 'relative',
    width: 28,
    height: 28,
    justifyContent: 'center',
    alignItems: 'center',
  },
  badge: {
    position: 'absolute',
    top: -4,
    right: -10,
    backgroundColor: '#EF4444',
    minWidth: 16,
    height: 16,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 4,
  },
  badgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '600',
  },
});
