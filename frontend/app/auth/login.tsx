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
  Alert,
  BackHandler,
} from 'react-native';
import { Video, ResizeMode } from 'expo-av';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../theme/config';
import { useUserStore } from '../../store/userStore';
import { authService } from '../../services/authService';
import { ReferralCodeModal } from '../../components/ReferralCodeModal';
import AgeVerificationModal from '../../components/AgeVerificationModal';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// 背景配置：切换视频/图片
const USE_VIDEO_BACKGROUND = true;
const BG_IMAGE = 'https://i.pinimg.com/originals/8b/1c/a0/8b1ca08def61220dc83e5c3d91e55cde.jpg';
const BG_VIDEO = require('../../assets/characters/sakura/videos/profile_bg.mp4');

export default function LoginScreen() {
  const router = useRouter();
  const { login, updateWallet } = useUserStore();
  const [loading, setLoading] = useState(false);
  const [showReferralModal, setShowReferralModal] = useState(false);
  const [pendingNavigation, setPendingNavigation] = useState(false);
  const [ageVerified, setAgeVerified] = useState(false);

  const handleLogin = async (provider: 'apple' | 'google' | 'guest') => {
    setLoading(true);
    try {
      // Call real API
      const result = await authService.login({ provider });
      
      login(result.user, result.accessToken, result.wallet);
      
      // Check if this is a new user (could be based on result.isNewUser flag from backend)
      // For now, show referral modal for all guest logins as they're likely new users
      if (provider === 'guest') {
        setShowReferralModal(true);
        setPendingNavigation(true);
      } else {
        router.replace('/(tabs)');
      }
    } catch (error: any) {
      console.error('Login failed:', error);
      Alert.alert('登录失败', error.message || '请检查网络连接');
    } finally {
      setLoading(false);
    }
  };

  const handleReferralModalClose = () => {
    setShowReferralModal(false);
    if (pendingNavigation) {
      setPendingNavigation(false);
      router.replace('/(tabs)');
    }
  };

  const handleReferralSuccess = (bonus: number, newBalance: number) => {
    // Update wallet with new balance
    updateWallet({ totalCredits: newBalance });
    
    // Close modal and navigate after short delay
    setTimeout(() => {
      handleReferralModalClose();
    }, 500);
  };

  return (
    <View style={styles.container}>
      {/* Background Video/Image */}
      {USE_VIDEO_BACKGROUND ? (
        <View style={styles.backgroundVideo}>
          <Video
            source={BG_VIDEO}
            style={StyleSheet.absoluteFillObject}
            resizeMode={ResizeMode.COVER}
            shouldPlay
            isLooping
            isMuted
          />
          <LinearGradient
            colors={['rgba(26,16,37,0.1)', 'rgba(26,16,37,0.5)', 'rgba(26,16,37,0.98)'] as [string, string, string]}
            style={styles.overlay}
          />
        </View>
      ) : (
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
      )}

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
            {/* Guest Login - Primary for testing */}
            <TouchableOpacity
              style={styles.guestButton}
              onPress={() => handleLogin('guest')}
              disabled={loading}
              activeOpacity={0.85}
            >
              <LinearGradient
                colors={theme.colors.primary.gradient}
                style={styles.guestButtonGradient}
              >
                <Ionicons name="person" size={22} color="#fff" />
                <Text style={styles.guestButtonText}>访客登录</Text>
              </LinearGradient>
            </TouchableOpacity>

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

          {/* AI Disclaimer */}
          <Text style={styles.aiDisclaimer}>
            🤖 本应用角色对话内容由 AI 生成，不代表真实人物观点
          </Text>

          {/* Terms */}
          <Text style={styles.termsText}>
            注册即表示同意{' '}
            <Text style={styles.termsLink} onPress={() => router.push('/legal/terms')}>
              《服务条款》
            </Text>
            {' '}和{' '}
            <Text style={styles.termsLink} onPress={() => router.push('/legal/privacy')}>
              《隐私政策》
            </Text>
          </Text>
        </View>
      </SafeAreaView>

      {/* Age Verification - first-time gate */}
      {!ageVerified && (
        <AgeVerificationModal
          onConfirm={() => setAgeVerified(true)}
          onDecline={() => BackHandler.exitApp()}
        />
      )}

      {/* Referral Code Modal */}
      <ReferralCodeModal
        visible={showReferralModal}
        onClose={handleReferralModalClose}
        onSuccess={handleReferralSuccess}
      />
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
  backgroundVideo: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    overflow: 'hidden',
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
  guestButton: {
    borderRadius: 28,
    overflow: 'hidden',
  },
  guestButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 15,
    gap: 10,
  },
  guestButtonText: {
    color: '#fff',
    fontSize: 17,
    fontWeight: '600',
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
  aiDisclaimer: {
    fontSize: 11,
    color: 'rgba(255,255,255,0.4)',
    textAlign: 'center',
    marginBottom: 8,
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
