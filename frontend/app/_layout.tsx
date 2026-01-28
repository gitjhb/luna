/**
 * Root Layout
 * 
 * Main app layout with navigation structure.
 */

import React, { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useUserStore } from '../store/userStore';
import { theme } from '../theme/config';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 1000 * 60 * 5, // 5 minutes
    },
  },
});

export default function RootLayout() {
  const isAuthenticated = useUserStore((state) => state.isAuthenticated);

  return (
    <QueryClientProvider client={queryClient}>
      <GestureHandlerRootView style={{ flex: 1 }}>
        <StatusBar style="light" />
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: {
              backgroundColor: theme.colors.background.primary,
            },
          }}
        >
          {!isAuthenticated ? (
            <Stack.Screen name="auth/login" />
          ) : (
            <>
              <Stack.Screen name="(tabs)" />
              <Stack.Screen name="chat/[characterId]" />
            </>
          )}
        </Stack>
      </GestureHandlerRootView>
    </QueryClientProvider>
  );
}
