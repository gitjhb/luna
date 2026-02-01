/**
 * Toast Component
 * 
 * Lightweight toast notification with animation.
 * Provides global hook for easy usage.
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withSequence,
  withDelay,
  runOnJS,
  Easing,
} from 'react-native-reanimated';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface ToastContextType {
  showToast: (message: string, duration?: number) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

interface ToastMessage {
  id: number;
  message: string;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  let toastId = 0;
  
  const showToast = useCallback((message: string, duration: number = 2000) => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, message }]);
    
    // Auto remove
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, duration);
  }, []);
  
  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <View style={styles.toastContainer} pointerEvents="none">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} message={toast.message} />
        ))}
      </View>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    // Return a no-op if not in provider (for safety)
    return { showToast: (msg: string) => console.log('Toast:', msg) };
  }
  return context;
}

function ToastItem({ message }: { message: string }) {
  const translateY = useSharedValue(50);
  const opacity = useSharedValue(0);
  
  useEffect(() => {
    // Animate in
    translateY.value = withTiming(0, { duration: 200, easing: Easing.out(Easing.ease) });
    opacity.value = withTiming(1, { duration: 200 });
    
    // Animate out after delay
    translateY.value = withDelay(1500, withTiming(50, { duration: 200 }));
    opacity.value = withDelay(1500, withTiming(0, { duration: 200 }));
  }, []);
  
  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: translateY.value }],
    opacity: opacity.value,
  }));
  
  return (
    <Animated.View style={[styles.toast, animatedStyle]}>
      <Text style={styles.toastText}>{message}</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  toastContainer: {
    position: 'absolute',
    bottom: 120,
    left: 0,
    right: 0,
    alignItems: 'center',
    zIndex: 9999,
  },
  toast: {
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 25,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 10,
    maxWidth: SCREEN_WIDTH * 0.8,
  },
  toastText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
  },
});

export default ToastProvider;
