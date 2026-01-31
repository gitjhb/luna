/**
 * Login Screen - Purple Pink Theme
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ImageBackground,
  Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../theme/config';
import { useUserStore } from '../../store/userStore';

const { height: SCREEN_HEIGHT } = Dimensions.get('window');

const BG_IMAGE = 'https://i.pinimg.com/originals/8b/1c/a0/8b1ca08def61220dc83e5c3d91e55cde.jpg';

export default function LoginScreen() {
  const router = useRouter();
  const { login } = useUserStore();
  const [loading, setLoading] = useState(false);

  const handleLogin = async (provider: 'apple' | 'google') => {
    setLoading(true);
    try {
      const mockUser = {
        userId: 'user-001',
        email: provider === 'apple' ? 'user@icloud.com' : 'user@gmail.com',
        displayName: 'User',
        subscriptionTier: 'free' as const,
        createdAt: new Date().toISOString(),
      };
      
      const mockWallet = {
        totalCredits: 1000,  // 给新用户 1000 金币测试
        dailyFreeCredits: 10,
        purchedCredits: 990,
        bonusCredits: 0,
        dailyCreditsLimit: 10,
      };
      
      await new Promise(r => setTimeout(r, 800));
      login(mockUser, 'mock-token', mockWallet);
      router.replace('/(tabs)');
    } catch (error) {
      console.error('Login failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      {/* Background Image */}
      <ImageBackground
        source={{ uri: BG_IMAGE }}
        style={styles.backgroundImage}
        resizeMode="cover"
      >
        <LinearGradient
          colors={['rgba(26,16,37,0.2)', 'rgba(26,16,37,0.6)', 'rgba(26,16,37,0.98)'] as [string, string, string]}
          style={styles.overlay}
        />
      </ImageBackground>

      <SafeAreaView style={styles.safeArea}>
        {/* Spacer to push content down */}
        <View style={styles.spacer} />

        {/* Content */}
        <View style={styles.content}>
          {/* Logo */}
          <View style={styles.logoContainer}>
            <LinearGradient
              colors={theme.colors.primary.gradient}
              style={styles.logoGradient}
            >
              <Ionicons name="heart" size={36} color="#fff" />
            </LinearGradient>
          </View>
          
          <Text style={styles.appName}>{theme.appName}</Text>
          <Text style={styles.tagline}>遇见你的专属AI伴侣 💕</Text>

          {/* Features */}
          <View style={styles.features}>
            <FeatureItem icon="chatbubble-ellipses" text="深度情感交流" />
            <FeatureItem icon="shield-checkmark" text="私密安全对话" />
            <FeatureItem icon="sparkles" text="独特个性体验" />
          </View>

          {/* Auth Buttons */}
          <View style={styles.authSection}>
            <TouchableOpacity
              style={styles.appleButton}
              onPress={() => handleLogin('apple')}
              disabled={loading}
              activeOpacity={0.85}
            >
              <Ionicons name="logo-apple" size={22} color="#fff" />
              <Text style={styles.appleButtonText}>Apple 登录</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.googleButton}
              onPress={() => handleLogin('google')}
              disabled={loading}
              activeOpacity={0.85}
            >
              <Ionicons name="logo-google" size={20} color="#fff" />
              <Text style={styles.googleButtonText}>Google 登录</Text>
            </TouchableOpacity>

            {loading && (
              <View style={styles.loadingOverlay}>
                <ActivityIndicator size="large" color={theme.colors.primary.main} />
              </View>
            )}
          </View>

          {/* Terms */}
          <Text style={styles.termsText}>
            继续即表示同意 <Text style={styles.termsLink}>服务条款</Text> 和 <Text style={styles.termsLink}>隐私政策</Text>
          </Text>
        </View>
      </SafeAreaView>
    </View>
  );
}

const FeatureItem: React.FC<{ icon: any; text: string }> = ({ icon, text }) => (
  <View style={styles.featureItem}>
    <View style={styles.featureIcon}>
      <Ionicons name={icon} size={18} color={theme.colors.primary.main} />
    </View>
    <Text style={styles.featureText}>{text}</Text>
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background.primary,
  },
  backgroundImage: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: SCREEN_HEIGHT * 0.55,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
  },
  safeArea: {
    flex: 1,
  },
  spacer: {
    flex: 1,
  },
  content: {
    paddingHorizontal: 28,
    paddingBottom: 24,
  },
  logoContainer: {
    alignSelf: 'center',
    marginBottom: 16,
  },
  logoGradient: {
    width: 72,
    height: 72,
    borderRadius: 36,
    justifyContent: 'center',
    alignItems: 'center',
  },
  appName: {
    fontSize: 32,
    fontWeight: '700',
    color: '#fff',
    textAlign: 'center',
  },
  tagline: {
    fontSize: 16,
    color: theme.colors.text.secondary,
    textAlign: 'center',
    marginTop: 6,
    marginBottom: 28,
  },
  features: {
    marginBottom: 28,
    gap: 12,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  featureIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(236, 72, 153, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  featureText: {
    fontSize: 15,
    color: theme.colors.text.secondary,
    fontWeight: '500',
  },
  authSection: {
    gap: 12,
    marginBottom: 20,
  },
  appleButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#000',
    paddingVertical: 15,
    borderRadius: 28,
    gap: 10,
  },
  appleButtonText: {
    color: '#fff',
    fontSize: 17,
    fontWeight: '600',
  },
  googleButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    paddingVertical: 15,
    borderRadius: 28,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
    gap: 10,
  },
  googleButtonText: {
    color: '#fff',
    fontSize: 17,
    fontWeight: '600',
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(26, 16, 37, 0.8)',
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
  },
  termsText: {
    fontSize: 12,
    color: theme.colors.text.tertiary,
    textAlign: 'center',
    lineHeight: 18,
  },
  termsLink: {
    color: theme.colors.primary.main,
  },
});
