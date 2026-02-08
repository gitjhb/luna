/**
 * Root Layout
 */

import React, { useEffect, useRef, useState } from 'react';
import { View, ActivityIndicator, Image, StyleSheet, Dimensions, Animated } from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as Notifications from 'expo-notifications';
import { theme, ThemeProvider, useTheme } from '../theme/config';
import { LocaleProvider } from '../i18n';
import { useChatStore } from '../store/chatStore';
import { useUserStore } from '../store/userStore';
import { useGiftStore } from '../store/giftStore';
import { revenueCatService } from '../services/revenueCatService';
import { pushService } from '../services/pushService';
import { initDatabase } from '../services/database';
import { migrateToSQLite, needsMigration } from '../services/database/migration';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const SPLASH_LOGO = require('../assets/images/splash-logo.jpg');

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 1000 * 60 * 5,
    },
  },
});

// Hydration wrapper to wait for stores to rehydrate
function HydrationGate({ children }: { children: React.ReactNode }) {
  const chatHydrated = useChatStore((s) => s._hasHydrated);
  const userHydrated = useUserStore((s) => s._hasHydrated);
  const giftHydrated = useGiftStore((s) => s._hasHydrated);
  const fetchGiftCatalog = useGiftStore((s) => s.fetchCatalog);
  const needsGiftRefresh = useGiftStore((s) => s.needsRefresh);
  
  // 初始化 RevenueCat
  const user = useUserStore((s) => s.user);
  
  useEffect(() => {
    const initRevenueCat = async () => {
      try {
        // Initialize with user ID if logged in
        const userId = user?.userId;
        const ok = await revenueCatService.init(userId);
        console.log('[App] RevenueCat initialized:', ok);
        
        // Only set attributes if RevenueCat initialized successfully
        if (ok && user?.email) {
          await revenueCatService.setUserAttributes({
            email: user.email,
            displayName: user.displayName,
          });
        }
      } catch (error) {
        // Silently log - don't crash app if RevenueCat fails
        console.warn('[App] RevenueCat init error (non-fatal):', error);
      }
    };
    
    initRevenueCat();
  }, [user?.userId]);
  
  // 初始化 SQLite 数据库
  useEffect(() => {
    const initDB = async () => {
      try {
        await initDatabase();
        console.log('[App] SQLite database initialized');
        
        // Run migration if needed (AsyncStorage → SQLite)
        if (await needsMigration()) {
          console.log('[App] Running data migration...');
          const result = await migrateToSQLite();
          console.log('[App] Migration result:', result);
        }
      } catch (error) {
        // Don't crash app if database init fails
        console.error('[App] Database init failed (non-fatal):', error);
      }
    };
    
    // Wrap in try-catch to prevent crash
    try {
      initDB();
    } catch (e) {
      console.error('[App] Database init threw:', e);
    }
  }, []);
  
  // 初始化推送服务
  useEffect(() => {
    pushService.init().then((ok) => {
      console.log('[App] Push service initialized:', ok);
    });
    
    return () => {
      pushService.stopPolling();
    };
  }, []);
  
  // 处理通知点击 - 导航到对应聊天
  useEffect(() => {
    // 处理 App 在后台时收到的通知点击
    const subscription = Notifications.addNotificationResponseReceivedListener(response => {
      console.log('[App] Notification clicked:', response);
      
      const data = response.notification.request.content.data;
      
      if (data?.character_id && data?.type === 'character_push') {
        // 导航到角色聊天页面
        console.log('[App] Navigating to chat:', data.character_id);
        
        // 使用延迟确保导航器已准备好
        setTimeout(() => {
          const router = require('expo-router').router;
          router.push({
            pathname: '/chat/[characterId]',
            params: { characterId: data.character_id }
          });
        }, 100);
      }
    });

    // 检查 App 是否从通知启动（冷启动）
    Notifications.getLastNotificationResponseAsync().then(response => {
      if (response) {
        console.log('[App] Launched from notification:', response);
        const data = response.notification.request.content.data;
        
        if (data?.character_id && data?.type === 'character_push') {
          setTimeout(() => {
            const router = require('expo-router').router;
            router.push({
              pathname: '/chat/[characterId]',
              params: { characterId: data.character_id }
            });
          }, 500); // 冷启动需要更长延迟
        }
      }
    });

    return () => subscription.remove();
  }, []);
  
  // 加载礼物目录（后端为准）
  useEffect(() => {
    if (giftHydrated && needsGiftRefresh()) {
      fetchGiftCatalog();
    }
  }, [giftHydrated]);
  
  // Show splash screen while hydrating
  if (!chatHydrated || !userHydrated || !giftHydrated) {
    return <SplashScreen />;
  }
  
  return <>{children}</>;
}

// Inner layout that can use theme context
function ThemedLayout() {
  const { theme } = useTheme();
  
  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background.primary }}>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: {
            backgroundColor: theme.colors.background.primary,
          },
          animation: 'slide_from_right',
        }}
      >
        <Stack.Screen name="index" />
        <Stack.Screen name="auth/login" />
        <Stack.Screen name="(tabs)" />
        <Stack.Screen 
          name="chat/[characterId]" 
          options={{ animation: 'slide_from_bottom' }}
        />
        <Stack.Screen 
          name="legal/terms" 
          options={{ animation: 'slide_from_bottom' }}
        />
        <Stack.Screen 
          name="legal/privacy" 
          options={{ animation: 'slide_from_bottom' }}
        />
      </Stack>
    </View>
  );
}

// Splash screen component with Luna logo
function SplashScreen() {
  const opacity = useRef(new Animated.Value(0)).current;
  const scale = useRef(new Animated.Value(0.8)).current;
  
  useEffect(() => {
    // Fade in and scale up animation
    Animated.parallel([
      Animated.timing(opacity, {
        toValue: 1,
        duration: 600,
        useNativeDriver: true,
      }),
      Animated.spring(scale, {
        toValue: 1,
        tension: 50,
        friction: 7,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);
  
  return (
    <View style={splashStyles.container}>
      <StatusBar style="light" />
      <Animated.View style={[splashStyles.logoContainer, { opacity, transform: [{ scale }] }]}>
        <Image 
          source={SPLASH_LOGO} 
          style={splashStyles.logo}
          resizeMode="cover"
        />
      </Animated.View>
    </View>
  );
}

const splashStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a12',
  },
  logoContainer: {
    ...StyleSheet.absoluteFillObject,
  },
  logo: {
    width: '100%',
    height: '100%',
  },
});

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <LocaleProvider>
          <HydrationGate>
            <ThemedLayout />
          </HydrationGate>
        </LocaleProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
