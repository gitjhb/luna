/**
 * Root Layout
 */

import React from 'react';
import { View, ActivityIndicator } from 'react-native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { theme } from '../theme/config';
import { useChatStore } from '../store/chatStore';
import { useUserStore } from '../store/userStore';

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
  
  if (!chatHydrated || !userHydrated) {
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

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <HydrationGate>
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
          </Stack>
        </View>
      </HydrationGate>
    </QueryClientProvider>
  );
}
