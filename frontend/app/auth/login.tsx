/**
 * Login Screen - Immersive Design
 * 
 * 少即是多：让 Sakura 的脸说话
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ImageBackground,
  Dimensions,
  Alert,
} from 'react-native';
import { Video, ResizeMode } from 'expo-av';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../theme/config';
import { useUserStore } from '../../store/userStore';
import { authService } from '../../services/authService';
import { ReferralCodeModal } from '../../components/ReferralCodeModal';
import AgeVerificationModal from '../../components/AgeVerificationModal';
import { useLocale } from '../../i18n';
import { requestNotificationPermission } from '../../services/pushService';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// 背景配置：切换视频/图片
const USE_VIDEO_BACKGROUND = true;
const BG_IMAGE = 'https://i.pinimg.com/originals/8b/1c/a0/8b1ca08def61220dc83e5c3d91e55cde.jpg';
const BG_VIDEO = require('../../assets/characters/sakura/videos/profile_bg.mp4');

export default function LoginScreen() {
  const router = useRouter();
  const { t } = useLocale();
  const { login, updateWallet } = useUserStore();
  const [loading, setLoading] = useState(false);
  const [showReferralModal, setShowReferralModal] = useState(false);
  const [pendingNavigation, setPendingNavigation] = useState(false);
  const [showAgeVerification, setShowAgeVerification] = useState(false);
  const [pendingLoginProvider, setPendingLoginProvider] = useState<'apple' | 'google' | 'guest' | null>(null);

  // 进入登录页时请求通知权限
  useEffect(() => {
    requestNotificationPermission().then((granted) => {
      console.log('[Login] Notification permission:', granted ? 'granted' : 'denied');
    });
  }, []);

  const handleLogin = async (provider: 'apple' | 'google' | 'guest') => {
    // First show age verification
    setPendingLoginProvider(provider);
    setShowAgeVerification(true);
  };

  const handleAgeVerified = async () => {
    setShowAgeVerification(false);
    const provider = pendingLoginProvider;
    if (!provider) return;
    
    setLoading(true);
    try {
      // Call real API
      const result = await authService.login({ provider });
      
      login(result.user, result.accessToken, result.wallet);
      
      // MVP: Skip referral modal, go directly to main app
      router.replace('/(tabs)');
    } catch (error: any) {
      // Silently ignore user cancellation - this is normal flow
      if (error.message === 'Sign in cancelled') {
        console.log('[Login] User cancelled sign in');
        return;
      }
      console.error('Login failed:', error);
      Alert.alert(t.login.loginFailed, error.message || t.login.checkNetwork);
    } finally {
      setLoading(false);
      setPendingLoginProvider(null);
    }
  };

  const handleAgeDeclined = () => {
    setShowAgeVerification(false);
    setPendingLoginProvider(null);
    Alert.alert(
      t.login.ageRestricted || 'Age Restricted',
      t.login.mustBe18 || 'You must be 18 or older to use this app.'
    );
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
      {/* Full-screen Background */}
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
          {/* Subtle gradient only at bottom for readability */}
          <LinearGradient
            colors={['transparent', 'rgba(0,0,0,0.3)', 'rgba(0,0,0,0.7)'] as const}
            locations={[0, 0.6, 1]}
            style={styles.bottomGradient}
          />
        </View>
      ) : (
        <ImageBackground
          source={{ uri: BG_IMAGE }}
          style={StyleSheet.absoluteFillObject}
          resizeMode="cover"
        >
          <LinearGradient
            colors={['transparent', 'rgba(0,0,0,0.3)', 'rgba(0,0,0,0.7)'] as const}
            locations={[0, 0.6, 1]}
            style={styles.bottomGradient}
          />
        </ImageBackground>
      )}

      <SafeAreaView style={styles.safeArea}>
        {/* Top: Empty - app name is already known */}
        <View style={styles.topSection} />

        {/* Middle: Empty - Let Sakura shine */}
        <View style={styles.middleSection} />

        {/* Bottom: Ultra-transparent auth area */}
        <View style={styles.bottomArea}>
          {/* Main auth buttons - unified frosted white style */}
          <View style={styles.authButtons}>
            <TouchableOpacity
              style={styles.authButton}
              onPress={() => handleLogin('apple')}
              disabled={loading}
              activeOpacity={0.8}
            >
              <BlurView intensity={80} tint="light" style={styles.authButtonBlur}>
                <Ionicons name="logo-apple" size={24} color="#000" />
              </BlurView>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.authButton}
              onPress={() => handleLogin('google')}
              disabled={loading}
              activeOpacity={0.8}
            >
              <BlurView intensity={80} tint="light" style={styles.authButtonBlur}>
                <Ionicons name="logo-google" size={22} color="#000" />
              </BlurView>
            </TouchableOpacity>
          </View>

          {/* Guest login as small text link - dev only */}
          {__DEV__ && (
            <TouchableOpacity
              onPress={() => handleLogin('guest')}
              disabled={loading}
              activeOpacity={0.6}
              style={styles.guestLink}
            >
              <Text style={styles.guestLinkText}>{t.login.guestLogin}</Text>
            </TouchableOpacity>
          )}

          {loading && (
            <ActivityIndicator 
              size="small" 
              color="#fff" 
              style={styles.loadingIndicator}
            />
          )}

          {/* Tiny terms text */}
          <Text style={styles.termsText}>
            {t.login.termsPrefix}
            <Text style={styles.termsLink} onPress={() => router.push('/legal/terms')}>
              {t.login.termsOfService}
            </Text>
            {t.login.and}
            <Text style={styles.termsLink} onPress={() => router.push('/legal/privacy')}>
              {t.login.privacyPolicy}
            </Text>
          </Text>
        </View>
      </SafeAreaView>

      {/* Age Verification Modal */}
      {showAgeVerification && (
        <AgeVerificationModal
          onConfirm={handleAgeVerified}
          onDecline={handleAgeDeclined}
        />
      )}

      {/* MVP: Referral Code Modal hidden */}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  backgroundVideo: {
    ...StyleSheet.absoluteFillObject,
    overflow: 'hidden',
  },
  bottomGradient: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    height: SCREEN_HEIGHT * 0.35,
  },
  safeArea: {
    flex: 1,
  },
  topSection: {
    // Empty spacer at top
  },
  middleSection: {
    flex: 1,
  },
  bottomArea: {
    paddingHorizontal: 24,
    paddingBottom: 16,
    alignItems: 'center',
  },
  authButtons: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 20,
    marginBottom: 12,
  },
  authButton: {
    width: 60,
    height: 60,
    borderRadius: 30,
    overflow: 'hidden',
  },
  authButtonBlur: {
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.85)',
  },
  guestLink: {
    marginBottom: 12,
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  guestLinkText: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.6)',
    textDecorationLine: 'underline',
  },
  loadingIndicator: {
    marginBottom: 12,
  },
  termsText: {
    fontSize: 10,
    color: 'rgba(255,255,255,0.35)',
    textAlign: 'center',
    lineHeight: 14,
  },
  termsLink: {
    color: 'rgba(255,255,255,0.5)',
  },
});
