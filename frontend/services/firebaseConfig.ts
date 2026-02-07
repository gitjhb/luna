/**
 * Firebase Configuration
 * 
 * Replace these values with your Firebase project config from:
 * Firebase Console → Project Settings → Your Apps → SDK setup and configuration
 */

import { initializeApp, getApps, FirebaseApp } from 'firebase/app';
import { getAuth, Auth } from 'firebase/auth';

// Firebase project configuration (from GoogleService-Info.plist)
const firebaseConfig = {
  apiKey: "AIzaSyBe0NZ3xuGZzORP4c6jetqNJObSNkSXxac",
  authDomain: "luna-f0af5.firebaseapp.com",
  projectId: "luna-f0af5",
  storageBucket: "luna-f0af5.firebasestorage.app",
  messagingSenderId: "1081215078404",
  appId: "1:1081215078404:ios:4dbfee5f31a1e9acabe551",
};

// Initialize Firebase (singleton)
let app: FirebaseApp;
let auth: Auth;

export function initFirebase(): { app: FirebaseApp; auth: Auth } {
  if (getApps().length === 0) {
    app = initializeApp(firebaseConfig);
    console.log('[Firebase] Initialized');
  } else {
    app = getApps()[0];
  }
  
  auth = getAuth(app);
  return { app, auth };
}

export function getFirebaseAuth(): Auth {
  if (!auth) {
    initFirebase();
  }
  return auth;
}

export { app, auth };
