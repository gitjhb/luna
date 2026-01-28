/**
 * Login Screen
 * 
 * High-conversion login screen with:
 * - Continue with Apple
 * - Continue with Google
 * - Compelling value proposition
 * - Terms and privacy links
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Image,
  Alert,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme, getShadow } from '../../theme/config';
import { useUserStore } from '../../store/userStore';
import { authService } from '../../services/authService';

export default function LoginScreen() {
  const router = useRouter();
  const { login } = useUserStore();
  const [loading, setLoading] = useState(false);

  const handleAppleLogin = async () => {
    setLoading(true);
    try {
      // Mock Apple Sign-In
      // In production, use expo-apple-authentication
      const mockUser = {
        userId: 'mock-user-id',
        email: 'user@example.com',
        displayName: 'John Doe',
        subscriptionTier: 'free' as const,
        createdAt: new Date().toISOString(),
      };
      
      const mockWallet = {
        totalCredits: 10,
        dailyFreeCredits: 10,
        purchedCredits: 0,
        bonusCredits: 0,
        dailyCreditsLimit: 10,
      };
      
      login(mockUser, 'mock-token', mockWallet);
      router.replace('/(tabs)');
    } catch (error) {
      console.error('Apple login failed:', error);
      Alert.alert('Error', 'Failed to sign in with Apple');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setLoading(true);
    try {
      // Mock Google Sign-In
      // In production, use expo-auth-session or @react-native-google-signin/google-signin
      const mockUser = {
        userId: 'mock-user-id',
        email: 'user@gmail.com',
        displayName: 'John Doe',
        subscriptionTier: 'free' as const,
        createdAt: new Date().toISOString(),
      };
      
      const mockWallet = {
        totalCredits: 10,
        dailyFreeCredits: 10,
        purchedCredits: 0,
        bonusCredits: 0,
        dailyCreditsLimit: 10,
      };
      
      login(mockUser, 'mock-token', mockWallet);
      router.replace('/(tabs)');
    } catch (error) {
      console.error('Google login failed:', error);
      Alert.alert('Error', 'Failed to sign in with Google');
    } finally {
      setLoading(false);
    }
  };

  return (
    <LinearGradient
      colors={theme.colors.background.gradient}
      style={styles.container}
    >
      <SafeAreaView style={styles.safeArea}>
        {/* Logo & Branding */}
        <View style={styles.header}>
          <View style={styles.logoContainer}>
            <LinearGradient
              colors={theme.colors.primary.gradient}
              style={styles.logoGradient}
            >
              <Ionicons name="chatbubble-ellipses" size={40} color={theme.colors.text.inverse} />
            </LinearGradient>
          </View>
          
          <Text style={styles.appName}>{theme.appName}</Text>
          <Text style={styles.tagline}>{theme.appTagline}</Text>
        </View>

        {/* Value Proposition */}
        <View style={styles.features}>
          <FeatureItem
            icon="diamond"
            text="Premium AI companions tailored to you"
          />
          <FeatureItem
            icon="lock-closed"
            text="Private & secure conversations"
          />
          <FeatureItem
            icon="flame"
            text="Exclusive spicy content for subscribers"
          />
        </View>

        {/* Auth Buttons */}
        <View style={styles.authContainer}>
          {/* Apple Sign-In */}
          <TouchableOpacity
            style={styles.authButton}
            onPress={handleAppleLogin}
            disabled={loading}
            activeOpacity={0.8}
          >
            <View style={[styles.authButtonContent, styles.appleButton]}>
              <Ionicons name="logo-apple" size={24} color={theme.colors.text.primary} />
              <Text style={styles.authButtonText}>Continue with Apple</Text>
            </View>
          </TouchableOpacity>

          {/* Google Sign-In */}
          <TouchableOpacity
            style={styles.authButton}
            onPress={handleGoogleLogin}
            disabled={loading}
            activeOpacity={0.8}
          >
            <View style={[styles.authButtonContent, styles.googleButton]}>
              <Ionicons name="logo-google" size={24} color={theme.colors.text.primary} />
              <Text style={styles.authButtonText}>Continue with Google</Text>
            </View>
          </TouchableOpacity>
        </View>

        {/* Terms */}
        <View style={styles.footer}>
          <Text style={styles.termsText}>
            By continuing, you agree to our{' '}
            <Text style={styles.termsLink}>Terms of Service</Text>
            {' '}and{' '}
            <Text style={styles.termsLink}>Privacy Policy</Text>
          </Text>
        </View>
      </SafeAreaView>
    </LinearGradient>
  );
}

const FeatureItem: React.FC<{ icon: any; text: string }> = ({ icon, text }) => (
  <View style={styles.featureItem}>
    <View style={styles.featureIconContainer}>
      <Ionicons name={icon} size={20} color={theme.colors.primary.main} />
    </View>
    <Text style={styles.featureText}>{text}</Text>
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  safeArea: {
    flex: 1,
    paddingHorizontal: theme.spacing.lg,
  },
  header: {
    alignItems: 'center',
    marginTop: theme.spacing['3xl'],
    marginBottom: theme.spacing.xl,
  },
  logoContainer: {
    marginBottom: theme.spacing.lg,
  },
  logoGradient: {
    width: 100,
    height: 100,
    borderRadius: theme.borderRadius.full,
    justifyContent: 'center',
    alignItems: 'center',
    ...getShadow('xl'),
  },
  appName: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize['3xl'],
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.xs,
  },
  tagline: {
    fontFamily: theme.typography.fontFamily.regular,
    fontSize: theme.typography.fontSize.lg,
    color: theme.colors.text.secondary,
  },
  features: {
    marginBottom: theme.spacing['2xl'],
    gap: theme.spacing.md,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.md,
  },
  featureIconContainer: {
    width: 40,
    height: 40,
    borderRadius: theme.borderRadius.full,
    backgroundColor: 'rgba(255, 215, 0, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  featureText: {
    flex: 1,
    fontFamily: theme.typography.fontFamily.medium,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
    lineHeight: theme.typography.fontSize.base * theme.typography.lineHeight.normal,
  },
  authContainer: {
    gap: theme.spacing.md,
    marginBottom: theme.spacing.xl,
  },
  authButton: {
    borderRadius: theme.borderRadius.lg,
    overflow: 'hidden',
    ...getShadow('md'),
  },
  authButtonContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: theme.spacing.md,
    gap: theme.spacing.sm,
  },
  appleButton: {
    backgroundColor: theme.colors.text.primary,
  },
  googleButton: {
    backgroundColor: theme.colors.background.secondary,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  authButtonText: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize.lg,
    color: theme.colors.text.primary,
  },
  footer: {
    marginTop: 'auto',
    paddingBottom: theme.spacing.lg,
  },
  termsText: {
    fontFamily: theme.typography.fontFamily.regular,
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.tertiary,
    textAlign: 'center',
    lineHeight: theme.typography.fontSize.sm * theme.typography.lineHeight.relaxed,
  },
  termsLink: {
    color: theme.colors.primary.main,
    textDecorationLine: 'underline',
  },
});
