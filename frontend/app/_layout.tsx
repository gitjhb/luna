/**
 * Root Layout
 */

import React, { useEffect, useRef } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as Notifications from 'expo-notifications';
import { theme, ThemeProvider, useTheme } from '../theme/config';
import { LocaleProvider } from '../i18n';
import { useChatStore } from '../store/chatStore';
import { useUserStore } from '../store/userStore';
import { useGiftStore } from '../store/giftStore';
import { iapService } from '../services/iapService';
import { pushService } from '../services/pushService';

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
  
  // 初始化 IAP 连接
  useEffect(() => {
    iapService.init().then((ok) => {
      console.log('[App] IAP initialized:', ok);
    });
    
    return () => {
      iapService.cleanup();
    };
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
  
  if (!chatHydrated || !userHydrated || !giftHydrated) {
    return (
      <View style={{ 
        flex: 1, 
        backgroundColor: theme.colors.background.primary,
        justifyContent: 'center',
        alignItems: 'center',
      }}>
        <ActivityIndicator size="large" color={theme.colors.primary.main} />
      </View>
    );
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
