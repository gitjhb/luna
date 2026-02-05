/**
 * Root Layout
 */

import React, { useEffect } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { theme, ThemeProvider, useTheme } from '../theme/config';
import { LocaleProvider } from '../i18n';
import { useChatStore } from '../store/chatStore';
import { useUserStore } from '../store/userStore';
import { useGiftStore } from '../store/giftStore';

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
