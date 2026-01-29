/**
 * App Entry Point
 * 
 * Redirects to appropriate screen based on auth state.
 */

import { Redirect } from 'expo-router';
import { useUserStore } from '../store/userStore';

export default function Index() {
  const isAuthenticated = useUserStore((state) => state.isAuthenticated);

  if (isAuthenticated) {
    return <Redirect href="/(tabs)" />;
  }
  
  return <Redirect href="/auth/login" />;
}
