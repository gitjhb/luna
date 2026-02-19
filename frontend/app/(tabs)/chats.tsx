/**
 * Chats Screen - Purple Pink Theme
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  Image,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useQueryClient } from '@tanstack/react-query';
import { useTheme } from '../../theme/config';
import { useChatStore, ChatSession, Message } from '../../store/chatStore';
import { chatService } from '../../services/chatService';
import SettingsDrawer from '../../components/SettingsDrawer';
import { useLocale, tpl } from '../../i18n';
import { getCharacterAvatar } from '../../assets/characters';
import { formatDistanceToNow } from 'date-fns';
import { zhCN, enUS } from 'date-fns/locale';

export default function ChatsScreen() {
  const router = useRouter();
  const { theme } = useTheme();
  const { t, locale } = useLocale();
  const queryClient = useQueryClient();
  const { sessions, setSessions, deleteSession, messagesBySession } = useChatStore();
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showSettingsDrawer, setShowSettingsDrawer] = useState(false);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      // 批量获取 sessions + messages（一次 API 调用）
      const { sessions: backendSessions, messages } = await chatService.getSessionsWithMessages(20);
      
      if (backendSessions && backendSessions.length > 0) {
        // Merge with local sessions to preserve any local-only data
        const mergedSessions = backendSessions.map(bs => {
          const localSession = sessions.find(ls => ls.sessionId === bs.sessionId);
          return {
            ...localSession,
            ...bs,
          };
        });
        setSessions(mergedSessions);
        
        // 预填充 React Query 缓存，避免进入聊天页时再次请求
        if (messages) {
          for (const [sessionId, msgs] of Object.entries(messages)) {
            const session = backendSessions.find(s => s.sessionId === sessionId);
            if (session && msgs.length > 0) {
              // 预填充 useMessages 的缓存
              queryClient.setQueryData(
                ['messages', session.characterId, sessionId],
                {
                  pages: [{
                    messages: msgs,
                    nextCursor: msgs.length >= 20 ? msgs[0]?.messageId : null,
                    hasMore: msgs.length >= 20,
                  }],
                  pageParams: [null],
                }
              );
            }
          }
          console.log('[Chats] Pre-cached messages for', Object.keys(messages).length, 'sessions');
        }
      } else {
        // Backend returned empty - try SQLite fallback
        try {
          const { SessionRepository } = await import('../../services/database/repositories');
          const sqliteSessions = await SessionRepository.getAll();
          if (sqliteSessions && sqliteSessions.length > 0) {
            const mappedSessions = sqliteSessions.map(s => ({
              sessionId: s.id,
              characterId: s.character_id,
              characterName: s.character_name || 'Unknown',
              characterAvatar: s.character_avatar,
              lastMessage: s.last_message,
              lastMessageAt: s.last_message_at || s.updated_at || s.created_at,
              createdAt: s.created_at,
            }));
            setSessions(mappedSessions as any);
            console.log('[Chats] Loaded sessions from SQLite:', mappedSessions.length);
          }
        } catch (sqliteError) {
          console.log('[Chats] SQLite not available:', sqliteError);
        }
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadSessions();
  }, []);

  const handleSessionPress = (session: ChatSession) => {
    router.push({
      pathname: '/chat/[characterId]',
      params: {
        characterId: session.characterId,
        sessionId: session.sessionId,
        characterName: session.characterName,
      },
    });
  };

  const handleClearMessages = (session: ChatSession) => {
    Alert.alert(
      t.chats.clearHistory,
      tpl(t.chats.clearHistoryConfirm, { name: session.characterName }),
      [
        { text: t.common.cancel, style: 'cancel' },
        {
          text: t.chats.clearHistory,
          style: 'destructive',
          onPress: async () => {
            try {
              await chatService.deleteSession(session.sessionId);
              deleteSession(session.sessionId);
              Alert.alert(t.chats.cleared, t.chats.clearedMessage);
            } catch (error) {
              console.error('Clear messages failed:', error);
              Alert.alert(t.chats.error, t.chats.clearFailed);
            }
          },
        },
      ]
    );
  };

  const formatTime = (dateString: string) => {
    try {
      // Backend returns UTC time without timezone indicator, append Z to parse as UTC
      const utcDate = dateString.endsWith('Z') ? dateString : dateString + 'Z';
      return formatDistanceToNow(new Date(utcDate), { addSuffix: true, locale: locale === 'zh' ? zhCN : enUS });
    } catch {
      return '';
    }
  };

  const formatMessagePreview = (msg: string): string => {
    if (!msg) return t.chats.newConversation;
    
    // Handle event/date messages - parse JSON and show friendly text
    if (msg.startsWith('[date]') || msg.startsWith('[event]')) {
      try {
        const jsonStr = msg.replace(/^\[(date|event)\]\s*/, '');
        const data = JSON.parse(jsonStr);
        if (data.type === 'event' && data.event_type === 'date_complete') {
          const scenarioName = data.scenario_name || '约会';
          return `🎉 完成了一次${scenarioName}`;
        }
        if (data.type === 'event') {
          return `🎉 完成了一个特殊事件`;
        }
      } catch (e) {
        // Not valid JSON, fall through
      }
    }
    
    // Handle system messages
    if (msg.startsWith('[system]') || msg.startsWith('[event]')) {
      return '📍 发生了一些事情...';
    }
    
    // Normal message
    const preview = msg.slice(0, 50);
    return preview + (msg.length > 50 ? '...' : '');
  };

  const getLastMessage = (session: ChatSession): string => {
    // 优先使用session自带的lastMessage（后端返回或SQLite存储）
    if ((session as any).lastMessage) {
      return formatMessagePreview((session as any).lastMessage);
    }
    // 检查SQLite存的last_message
    if ((session as any).last_message) {
      return formatMessagePreview((session as any).last_message);
    }
    // 回退到本地内存缓存
    const messages = messagesBySession[session.sessionId];
    if (!messages || messages.length === 0) return t.chats.newConversation;
    const lastMsg = messages[messages.length - 1];
    return formatMessagePreview(lastMsg.content);
  };

  const renderSession = ({ item }: { item: ChatSession }) => (
    <TouchableOpacity
      style={styles.sessionCard}
      onPress={() => handleSessionPress(item)}
      onLongPress={() => handleClearMessages(item)}
      activeOpacity={0.8}
    >
      <View style={styles.avatarContainer}>
        <Text style={styles.avatarPlaceholder}>?</Text>
        <Image
          source={getCharacterAvatar(item.characterId, item.characterAvatar)}
          style={styles.avatar}
          fadeDuration={0}
        />
      </View>
      <View style={styles.sessionInfo}>
        <View style={styles.sessionHeader}>
          <Text style={styles.characterName}>{item.characterName}</Text>
          <Text style={styles.timestamp}>{formatTime(item.lastMessageAt || item.createdAt)}</Text>
        </View>
        <Text style={styles.sessionTitle} numberOfLines={1}>
          {getLastMessage(item)}
        </Text>
      </View>
    </TouchableOpacity>
  );

  const renderEmpty = () => (
    <View style={styles.emptyState}>
      <View style={styles.emptyIcon}>
        <Ionicons name="chatbubbles-outline" size={48} color={theme.colors.text.tertiary} />
      </View>
      <Text style={styles.emptyTitle}>{t.chats.noChats}</Text>
      <Text style={styles.emptySubtext}>{t.chats.noChatsHint}</Text>
      <TouchableOpacity style={styles.startButton} onPress={() => router.push('/(tabs)')}>
        <LinearGradient colors={[...theme.colors.primary.gradient]} style={styles.startButtonGradient}>
          <Text style={styles.startButtonText}>{t.chats.goDiscover}</Text>
        </LinearGradient>
      </TouchableOpacity>
    </View>
  );

  return (
    <LinearGradient colors={[...theme.colors.background.gradient]} style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <View style={styles.header}>
          <TouchableOpacity 
            style={styles.menuButton}
            onPress={() => setShowSettingsDrawer(true)}
          >
            <Ionicons name="menu-outline" size={26} color="#fff" />
          </TouchableOpacity>
          <View style={styles.headerCenter}>
            <Text style={styles.title}>{t.chats.title}</Text>
            {sessions.length > 0 && (
              <Text style={styles.subtitle}>{tpl(t.chats.conversations, { count: sessions.length })}</Text>
            )}
          </View>
          <View style={styles.headerRight} />
        </View>

        <FlatList
          data={sessions}
          keyExtractor={(item) => item.sessionId}
          renderItem={renderSession}
          contentContainerStyle={sessions.length === 0 ? styles.emptyContainer : styles.listContainer}
          ListEmptyComponent={
            loading ? (
              <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color={theme.colors.primary.main} />
                <Text style={styles.loadingText}>{t.common?.loading || '加载中...'}</Text>
              </View>
            ) : renderEmpty()
          }
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.primary.main} />
          }
          showsVerticalScrollIndicator={false}
        />
      </SafeAreaView>

      <SettingsDrawer visible={showSettingsDrawer} onClose={() => setShowSettingsDrawer(false)} />
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safeArea: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  menuButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerCenter: {
    flex: 1,
    marginLeft: 8,
  },
  headerRight: {
    width: 40,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
  },
  subtitle: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.7)',
    marginTop: 2,
  },
  listContainer: {
    paddingHorizontal: 20,
    paddingBottom: 100,
  },
  emptyContainer: { flex: 1 },
  sessionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 18,
    padding: 14,
    marginBottom: 10,
  },
  avatarContainer: {
    width: 50,
    height: 50,
    borderRadius: 25,
    marginRight: 14,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'hidden',
  },
  avatarPlaceholder: {
    position: 'absolute',
    fontSize: 20,
    color: 'rgba(255, 255, 255, 0.5)',
    fontWeight: '600',
  },
  avatar: {
    width: 50,
    height: 50,
    borderRadius: 25,
  },
  sessionInfo: { flex: 1 },
  sessionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  characterName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  timestamp: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.4)',
  },
  sessionTitle: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.7)',
    marginTop: 4,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.6)',
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
  },
  emptyIcon: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: 'rgba(255, 255, 255, 0.7)',
  },
  emptySubtext: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.4)',
    marginTop: 6,
    marginBottom: 24,
  },
  startButton: {
    borderRadius: 24,
    overflow: 'hidden',
  },
  startButtonGradient: {
    paddingHorizontal: 28,
    paddingVertical: 13,
  },
  startButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
  },
});
