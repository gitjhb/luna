/**
 * Push Notification Service
 * 
 * 轮询后端获取角色主动推送的消息
 */

import { api } from './api';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

// ============================================================================
// Types
// ============================================================================

export interface PushMessage {
  character_id: string;
  character_name: string;
  message: string;
  stage: string;
  timestamp: string;
}

export interface PendingPushesResponse {
  success: boolean;
  pushes: PushMessage[];
  count: number;
}

// ============================================================================
// Configuration
// ============================================================================

// 轮询间隔（毫秒）
const POLL_INTERVAL = 5 * 60 * 1000; // 5 分钟

// 存储回调
let onPushReceived: ((push: PushMessage) => void) | null = null;
let pollTimer: NodeJS.Timeout | null = null;
let isPolling = false;

// ============================================================================
// Notification Setup
// ============================================================================

async function setupNotifications(): Promise<boolean> {
  try {
    // 设置通知处理
    Notifications.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowAlert: true,
        shouldPlaySound: true,
        shouldSetBadge: true,
        shouldShowBanner: true,
        shouldShowList: true,
      }),
    });

    // 请求权限
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== 'granted') {
      console.log('[Push] Notification permission not granted');
      return false;
    }

    console.log('[Push] Notifications setup complete');
    return true;
  } catch (error) {
    console.error('[Push] Setup error:', error);
    return false;
  }
}

/**
 * 单独请求通知权限（可在 app 启动时调用）
 */
export async function requestNotificationPermission(): Promise<boolean> {
  try {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    
    if (existingStatus === 'granted') {
      return true;
    }
    
    const { status } = await Notifications.requestPermissionsAsync();
    return status === 'granted';
  } catch (error) {
    console.error('[Push] Permission request error:', error);
    return false;
  }
}

// ============================================================================
// Local Notification
// ============================================================================

async function showLocalNotification(push: PushMessage): Promise<void> {
  try {
    await Notifications.scheduleNotificationAsync({
      content: {
        title: `💌 ${push.character_name}`,
        body: push.message,
        data: {
          character_id: push.character_id,
          type: 'character_push',
        },
        sound: true,
      },
      trigger: null, // 立即显示
    });
    
    console.log(`[Push] Notification shown for ${push.character_name}`);
  } catch (error) {
    console.error('[Push] Failed to show notification:', error);
  }
}

// ============================================================================
// Polling
// ============================================================================

async function checkForPushes(): Promise<void> {
  if (isPolling) return;
  
  isPolling = true;
  
  try {
    const response = await api.get<PendingPushesResponse>('/push/pending');
    
    if (response.success && response.pushes.length > 0) {
      console.log(`[Push] Received ${response.pushes.length} push(es)`);
      
      for (const push of response.pushes) {
        // 显示本地通知
        await showLocalNotification(push);
        
        // 触发回调
        if (onPushReceived) {
          onPushReceived(push);
        }
      }
    }
  } catch (error) {
    console.error('[Push] Poll error:', error);
  } finally {
    isPolling = false;
  }
}

// ============================================================================
// Service
// ============================================================================

export const pushService = {
  /**
   * 初始化推送服务
   */
  init: async (): Promise<boolean> => {
    const hasPermission = await setupNotifications();
    
    if (hasPermission) {
      // 立即检查一次
      await checkForPushes();
      
      // 启动定时轮询
      pushService.startPolling();
    }
    
    return hasPermission;
  },

  /**
   * 启动轮询
   */
  startPolling: (): void => {
    if (pollTimer) {
      clearInterval(pollTimer);
    }
    
    pollTimer = setInterval(checkForPushes, POLL_INTERVAL);
    console.log(`[Push] Polling started (interval: ${POLL_INTERVAL / 1000}s)`);
  },

  /**
   * 停止轮询
   */
  stopPolling: (): void => {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
      console.log('[Push] Polling stopped');
    }
  },

  /**
   * 手动检查推送
   */
  checkNow: async (): Promise<PushMessage[]> => {
    try {
      const response = await api.get<PendingPushesResponse>('/push/pending');
      return response.pushes || [];
    } catch (error) {
      console.error('[Push] Check error:', error);
      return [];
    }
  },

  /**
   * 设置推送接收回调
   */
  onPush: (callback: (push: PushMessage) => void): void => {
    onPushReceived = callback;
  },

  /**
   * 清除回调
   */
  clearCallback: (): void => {
    onPushReceived = null;
  },

  /**
   * 获取角色推送配置
   */
  getCharacterConfig: async (characterId: string): Promise<any> => {
    try {
      const response = await api.get<any>(`/push/config/${characterId}`);
      return response.config;
    } catch (error) {
      console.error('[Push] Get config error:', error);
      return null;
    }
  },

  /**
   * 测试推送（忽略时间和频率限制）
   */
  testPush: async (): Promise<PushMessage[]> => {
    try {
      const response = await api.get<any>('/push/test');
      
      if (response.success && response.test_messages?.length > 0) {
        console.log(`[Push] Test: ${response.test_messages.length} messages`);
        
        // 显示第一条作为通知
        const firstPush = response.test_messages[0];
        await showLocalNotification(firstPush);
        
        return response.test_messages;
      }
      
      return [];
    } catch (error) {
      console.error('[Push] Test error:', error);
      return [];
    }
  },
};

export default pushService;
