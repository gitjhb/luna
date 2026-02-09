/**
 * Authentication Service
 * 
 * Supports:
 * - Guest login (instant, no account)
 * - Apple Sign In (via expo-apple-authentication + Firebase)
 * - Google Sign In (via @react-native-google-signin + Firebase)
 */

import { Platform } from 'react-native';
import Constants from 'expo-constants';
import * as AppleAuthentication from 'expo-apple-authentication';

import { api } from './api';
import { User, Wallet } from '../store/userStore';

// 检测是否在 Expo Go 中运行
const isExpoGo = Constants.appOwnership === 'expo';

// 动态导入原生模块（只在 dev build 中可用）
let GoogleSignin: any = null;
let statusCodes: any = {};
let firebaseAuth: any = null;
let nativeFirebaseAuth: any = null;

if (!isExpoGo) {
  try {
    const googleModule = require('@react-native-google-signin/google-signin');
    GoogleSignin = googleModule.GoogleSignin;
    statusCodes = googleModule.statusCodes;
  } catch (e) {
    console.warn('[Auth] Google Sign-In not available');
  }
  
  // 优先使用 Native Firebase Auth (推荐用于 React Native)
  try {
    nativeFirebaseAuth = require('@react-native-firebase/auth').default;
    console.log('[Auth] Native Firebase Auth loaded');
  } catch (e) {
    console.warn('[Auth] Native Firebase Auth not available, falling back to Web SDK');
    // Fallback to Web SDK
    try {
      firebaseAuth = require('firebase/auth');
      const { initFirebase } = require('./firebaseConfig');
      initFirebase();
    } catch (e2) {
      console.warn('[Auth] Firebase not available');
    }
  }
}

// Configure Google Sign In (call this once on app start)
// Web Client ID from Firebase Console (luna-f0af5)
const GOOGLE_WEB_CLIENT_ID = '1081215078404-tv6fpf9ui8b9uucepahp4a9v8100cc0t.apps.googleusercontent.com';

let googleConfigured = false;

function configureGoogleSignIn() {
  if (googleConfigured || !GoogleSignin) return;
  
  try {
    GoogleSignin.configure({
      webClientId: GOOGLE_WEB_CLIENT_ID,
      offlineAccess: true,
    });
    googleConfigured = true;
    console.log('[Auth] Google Sign In configured');
  } catch (err) {
    console.warn('[Auth] Google Sign In config failed:', err);
  }
}

// ============================================================================
// Types
// ============================================================================

interface LoginResponse {
  user: User;
  wallet: Wallet;
  accessToken: string;
}

interface LoginRequest {
  provider: 'google' | 'apple' | 'guest';
  idToken?: string;
}

// ============================================================================
// Service
// ============================================================================

export const authService = {
  /**
   * Login with specified provider
   */
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    switch (data.provider) {
      case 'apple':
        return await authService.loginWithApple();
      case 'google':
        return await authService.loginWithGoogle();
      case 'guest':
      default:
        return await authService.loginAsGuest();
    }
  },

  /**
   * Guest login - instant access, no account required
   * In dev mode, uses demo account with persistent data
   */
  loginAsGuest: async (): Promise<LoginResponse> => {
    // In Expo Go / dev mode, use demo login for persistent session
    // Demo secret is only for JHB's testing
    const isDev = __DEV__ || isExpoGo;
    const DEMO_SECRET = 'jhb-luna-2024';
    
    let response: any;
    
    if (isDev) {
      // Use demo login for persistent user ID
      console.log('[Auth] Using demo login for dev mode');
      response = await api.post<any>('/auth/demo', { secret: DEMO_SECRET });
    } else {
      // Production: regular guest login
      response = await api.post<any>('/auth/guest');
    }
    
    return {
      user: {
        userId: response.user_id,
        email: response.email || (isDev ? 'jhb@luna.app' : 'guest@luna.app'),
        displayName: response.display_name || (isDev ? 'JHB' : 'Guest'),
        subscriptionTier: response.subscription_tier || 'free',
        createdAt: new Date().toISOString(),
      },
      wallet: {
        totalCredits: response.wallet?.total_credits || 100,
        dailyFreeCredits: response.wallet?.daily_free_credits || 10,
        purchedCredits: response.wallet?.purchased_credits || 0,
        bonusCredits: response.wallet?.bonus_credits || 0,
        dailyCreditsLimit: response.wallet?.daily_credits_limit || 50,
      },
      accessToken: response.access_token,
    };
  },

  /**
   * Apple Sign In
   */
  loginWithApple: async (): Promise<LoginResponse> => {
    // Check availability
    const isAvailable = await AppleAuthentication.isAvailableAsync();
    if (!isAvailable) {
      throw new Error('Apple Sign In is not available on this device');
    }

    try {
      // Request Apple credential
      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
      });

      console.log('[Auth] Apple credential received');

      // 优先使用 Native Firebase Auth (推荐用于 dev build)
      if (nativeFirebaseAuth && !isExpoGo) {
        console.log('[Auth] Using Native Firebase Auth');
        
        // Create Apple credential for Firebase
        const appleCredential = nativeFirebaseAuth.AppleAuthProvider.credential(
          credential.identityToken!,
          credential.authorizationCode!
        );
        
        // Sign in to Firebase
        const userCredential = await nativeFirebaseAuth().signInWithCredential(appleCredential);
        const firebaseUser = userCredential.user;
        const idToken = await firebaseUser.getIdToken();

        console.log('[Auth] Native Firebase sign in successful:', firebaseUser.uid);

        const response = await api.post<any>('/auth/firebase', {
          id_token: idToken,
          provider: 'apple',
          display_name: credential.fullName
            ? `${credential.fullName.givenName || ''} ${credential.fullName.familyName || ''}`.trim()
            : undefined,
        });

        return {
          user: {
            userId: response.user_id,
            email: firebaseUser.email || credential.email || undefined,
            displayName: response.display_name || firebaseUser.displayName || 'User',
            subscriptionTier: response.subscription_tier || 'free',
            createdAt: response.created_at || new Date().toISOString(),
          },
          wallet: {
            totalCredits: response.wallet?.total_credits || 100,
            dailyFreeCredits: response.wallet?.daily_free_credits || 10,
            purchedCredits: response.wallet?.purchased_credits || 0,
            bonusCredits: response.wallet?.bonus_credits || 0,
            dailyCreditsLimit: response.wallet?.daily_credits_limit || 50,
          },
          accessToken: response.access_token,
        };
      }
      
      // Fallback: 使用 Web Firebase SDK
      if (firebaseAuth && !isExpoGo) {
        console.log('[Auth] Using Web Firebase SDK');
        const { getFirebaseAuth } = require('./firebaseConfig');
        const { signInWithCredential, OAuthProvider } = firebaseAuth;
        
        const auth = getFirebaseAuth();
        const provider = new OAuthProvider('apple.com');
        const oauthCredential = provider.credential({
          idToken: credential.identityToken!,
          rawNonce: undefined,
        });

        const userCredential = await signInWithCredential(auth, oauthCredential);
        const firebaseUser = userCredential.user;
        const idToken = await firebaseUser.getIdToken();

        console.log('[Auth] Web Firebase sign in successful:', firebaseUser.uid);

        const response = await api.post<any>('/auth/firebase', {
          id_token: idToken,
          provider: 'apple',
          display_name: credential.fullName
            ? `${credential.fullName.givenName || ''} ${credential.fullName.familyName || ''}`.trim()
            : undefined,
        });

        return {
          user: {
            userId: response.user_id,
            email: firebaseUser.email || credential.email || undefined,
            displayName: response.display_name || firebaseUser.displayName || 'User',
            subscriptionTier: response.subscription_tier || 'free',
            createdAt: response.created_at || new Date().toISOString(),
          },
          wallet: {
            totalCredits: response.wallet?.total_credits || 100,
            dailyFreeCredits: response.wallet?.daily_free_credits || 10,
            purchedCredits: response.wallet?.purchased_credits || 0,
            bonusCredits: response.wallet?.bonus_credits || 0,
            dailyCreditsLimit: response.wallet?.daily_credits_limit || 50,
          },
          accessToken: response.access_token,
        };
      }
      
      // Expo Go fallback: 直接发送 Apple 凭据到后端（mock 模式）
      console.log('[Auth] Using direct Apple auth (Expo Go mode)');
      const response = await api.post<any>('/auth/firebase', {
        id_token: credential.identityToken || 'expo-go-mock',
        provider: 'apple',
        display_name: credential.fullName
          ? `${credential.fullName.givenName || ''} ${credential.fullName.familyName || ''}`.trim()
          : undefined,
        email: credential.email,
      });

      return {
        user: {
          userId: response.user_id,
          email: credential.email || undefined,
          displayName: response.display_name || 'User',
          subscriptionTier: response.subscription_tier || 'free',
          createdAt: response.created_at || new Date().toISOString(),
        },
        wallet: {
          totalCredits: response.wallet?.total_credits || 100,
          dailyFreeCredits: response.wallet?.daily_free_credits || 10,
          purchedCredits: response.wallet?.purchased_credits || 0,
          bonusCredits: response.wallet?.bonus_credits || 0,
          dailyCreditsLimit: response.wallet?.daily_credits_limit || 50,
        },
        accessToken: response.access_token,
      };
    } catch (error: any) {
      if (error.code === 'ERR_REQUEST_CANCELED') {
        throw new Error('Sign in cancelled');
      }
      console.error('[Auth] Apple Sign In error:', error);
      throw new Error(error.message || 'Apple Sign In failed');
    }
  },

  /**
   * Google Sign In
   */
  loginWithGoogle: async (): Promise<LoginResponse> => {
    // Expo Go 不支持 Google Sign In
    if (isExpoGo || !GoogleSignin) {
      throw new Error('Google 登录在 Expo Go 中不可用，请使用 Guest 登录或 dev build');
    }
    
    configureGoogleSignIn();

    try {
      // Check Play Services (Android only)
      await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });

      // Sign in with Google
      const userInfo = await GoogleSignin.signIn();
      console.log('[Auth] Google credential received');

      // Get ID token
      const tokens = await GoogleSignin.getTokens();
      const googleIdToken = tokens.idToken;

      if (!googleIdToken) {
        throw new Error('Failed to get Google ID token');
      }

      // 如果 Firebase 可用
      if (firebaseAuth) {
        const { getFirebaseAuth } = require('./firebaseConfig');
        const { signInWithCredential, GoogleAuthProvider } = firebaseAuth;
        
        const auth = getFirebaseAuth();
        const googleCredential = GoogleAuthProvider.credential(googleIdToken);
        const userCredential = await signInWithCredential(auth, googleCredential);
        const firebaseUser = userCredential.user;
        const idToken = await firebaseUser.getIdToken();

        console.log('[Auth] Firebase sign in successful:', firebaseUser.uid);

        const response = await api.post<any>('/auth/firebase', {
          id_token: idToken,
          provider: 'google',
          display_name: firebaseUser.displayName || userInfo.data?.user?.name,
          email: firebaseUser.email || userInfo.data?.user?.email,
          photo_url: firebaseUser.photoURL || userInfo.data?.user?.photo,
        });

        return {
          user: {
            userId: response.user_id,
            email: firebaseUser.email || userInfo.data?.user?.email || undefined,
            displayName: response.display_name || firebaseUser.displayName || 'User',
            avatarUrl: firebaseUser.photoURL || userInfo.data?.user?.photo || undefined,
            subscriptionTier: response.subscription_tier || 'free',
            createdAt: response.created_at || new Date().toISOString(),
          },
          wallet: {
            totalCredits: response.wallet?.total_credits || 100,
            dailyFreeCredits: response.wallet?.daily_free_credits || 10,
            purchedCredits: response.wallet?.purchased_credits || 0,
            bonusCredits: response.wallet?.bonus_credits || 0,
            dailyCreditsLimit: response.wallet?.daily_credits_limit || 50,
          },
          accessToken: response.access_token,
        };
      }
      
      throw new Error('Firebase not available');
    } catch (error: any) {
      if (error.code === statusCodes?.SIGN_IN_CANCELLED) {
        throw new Error('Sign in cancelled');
      } else if (error.code === statusCodes?.IN_PROGRESS) {
        throw new Error('Sign in already in progress');
      } else if (error.code === statusCodes?.PLAY_SERVICES_NOT_AVAILABLE) {
        throw new Error('Google Play Services not available');
      }
      console.error('[Auth] Google Sign In error:', error);
      throw new Error(error.message || 'Google Sign In failed');
    }
  },

  /**
   * Sign out from all providers
   */
  signOut: async (): Promise<void> => {
    try {
      // Sign out from Firebase
      if (firebaseAuth && !isExpoGo) {
        const { getFirebaseAuth } = require('./firebaseConfig');
        const { signOut: firebaseSignOut } = firebaseAuth;
        const auth = getFirebaseAuth();
        await firebaseSignOut(auth);
      }

      // Sign out from Google (if signed in)
      if (GoogleSignin) {
        try {
          await GoogleSignin.signOut();
        } catch (e) {
          // Ignore - might not be signed in with Google
        }
      }

      console.log('[Auth] Signed out');
    } catch (error) {
      console.error('[Auth] Sign out error:', error);
    }
  },

  /**
   * Get current user profile from backend
   */
  getProfile: async (): Promise<User> => {
    const response = await api.get<any>('/auth/me');
    return {
      userId: response.user_id,
      email: response.email || undefined,
      displayName: response.display_name || 'User',
      avatarUrl: response.avatar_url || undefined,
      subscriptionTier: response.subscription_tier || 'free',
      createdAt: response.created_at || new Date().toISOString(),
    };
  },

  /**
   * Refresh access token
   */
  refreshToken: async (): Promise<{ accessToken: string }> => {
    const response = await api.post<any>('/auth/refresh');
    return { accessToken: response.access_token };
  },

  /**
   * Check if Apple Sign In is available
   */
  isAppleAuthAvailable: async (): Promise<boolean> => {
    if (Platform.OS !== 'ios') return false;
    return await AppleAuthentication.isAvailableAsync();
  },
};
