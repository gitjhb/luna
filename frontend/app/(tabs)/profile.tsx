/**
 * Profile Screen
 * 
 * User profile and settings.
 */

import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../theme/config';
import { useUserStore } from '../../store/userStore';

export default function ProfileScreen() {
  const router = useRouter();
  const { user, wallet, logout } = useUserStore();

  const handleLogout = () => {
    logout();
    router.replace('/auth/login');
  };

  return (
    <LinearGradient colors={theme.colors.background.gradient} style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <View style={styles.header}>
          <Text style={styles.title}>Profile</Text>
        </View>
        
        <View style={styles.content}>
          {/* User Info */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Account</Text>
            <View style={styles.infoCard}>
              <Text style={styles.label}>Name</Text>
              <Text style={styles.value}>{user?.displayName || 'Guest'}</Text>
            </View>
            <View style={styles.infoCard}>
              <Text style={styles.label}>Email</Text>
              <Text style={styles.value}>{user?.email || 'N/A'}</Text>
            </View>
            <View style={styles.infoCard}>
              <Text style={styles.label}>Subscription</Text>
              <Text style={styles.value}>{user?.subscriptionTier || 'free'}</Text>
            </View>
          </View>

          {/* Credits */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Credits</Text>
            <View style={styles.creditsCard}>
              <Ionicons name="diamond" size={32} color={theme.colors.primary.main} />
              <Text style={styles.creditsAmount}>{wallet?.totalCredits?.toFixed(2) || '0.00'}</Text>
              <Text style={styles.creditsLabel}>Total Credits</Text>
            </View>
          </View>

          {/* Logout */}
          <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
            <Text style={styles.logoutText}>Logout</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
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
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.md,
  },
  title: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize['2xl'],
    color: theme.colors.text.primary,
  },
  content: {
    flex: 1,
    paddingHorizontal: theme.spacing.lg,
  },
  section: {
    marginBottom: theme.spacing.xl,
  },
  sectionTitle: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize.lg,
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.md,
  },
  infoCard: {
    backgroundColor: theme.colors.background.secondary,
    padding: theme.spacing.md,
    borderRadius: theme.borderRadius.lg,
    marginBottom: theme.spacing.sm,
  },
  label: {
    fontFamily: theme.typography.fontFamily.medium,
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.secondary,
    marginBottom: theme.spacing.xs,
  },
  value: {
    fontFamily: theme.typography.fontFamily.regular,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.primary,
  },
  creditsCard: {
    backgroundColor: theme.colors.background.secondary,
    padding: theme.spacing.xl,
    borderRadius: theme.borderRadius.xl,
    alignItems: 'center',
  },
  creditsAmount: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize['3xl'],
    color: theme.colors.primary.main,
    marginTop: theme.spacing.sm,
  },
  creditsLabel: {
    fontFamily: theme.typography.fontFamily.medium,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
    marginTop: theme.spacing.xs,
  },
  logoutButton: {
    backgroundColor: theme.colors.error,
    padding: theme.spacing.md,
    borderRadius: theme.borderRadius.lg,
    alignItems: 'center',
    marginTop: 'auto',
    marginBottom: theme.spacing.lg,
  },
  logoutText: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize.lg,
    color: theme.colors.text.primary,
  },
});
