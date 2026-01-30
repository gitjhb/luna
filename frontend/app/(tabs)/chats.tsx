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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../theme/config';
import { useChatStore, ChatSession, Message } from '../../store/chatStore';
import { chatService } from '../../services/chatService';
import SettingsDrawer from '../../components/SettingsDrawer';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

export default function ChatsScreen() {
  const router = useRouter();
  const { sessions, setSessions, deleteSession, messagesBySession } = useChatStore();
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showSettingsDrawer, setShowSettingsDrawer] = useState(false);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      // Fetch latest sessions from backend
      const backendSessions = await chatService.getSessions();
      
      // Merge with local sessions to preserve any local-only data
      // but always use backend's avatar/name (they may have been updated)
      const mergedSessions = backendSessions.map(bs => {
        const localSession = sessions.find(ls => ls.sessionId === bs.sessionId);
        return {
          ...localSession,
          ...bs, // Backend data takes priority (updated avatars, names)
        };
      });
      
      setSessions(mergedSessions);
    } catch (error) {
      console.error('Failed to load sessions:', error);
      // Keep using cached sessions if backend fails
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

  const handleDeleteSession = (session: ChatSession) => {
    Alert.alert('删除对话', `确定删除与 ${session.characterName} 的对话吗？`, [
      { text: '取消', style: 'cancel' },
      {
        text: '删除',
        style: 'destructive',
        onPress: async () => {
          try {
            await chatService.deleteSession(session.sessionId);
            deleteSession(session.sessionId);
          } catch (error) {
            Alert.alert('错误', '删除失败');
          }
        },
      },
    ]);
  };

  const formatTime = (dateString: string) => {
    try {
      // Backend returns UTC time without timezone indicator, append Z to parse as UTC
      const utcDate = dateString.endsWith('Z') ? dateString : dateString + 'Z';
      return formatDistanceToNow(new Date(utcDate), { addSuffix: true, locale: zhCN });
    } catch {
      return '';
    }
  };

  const getLastMessage = (sessionId: string): string => {
    const messages = messagesBySession[sessionId];
    if (!messages || messages.length === 0) return '新对话';
    const lastMsg = messages[messages.length - 1];
    return lastMsg.content.slice(0, 50) + (lastMsg.content.length > 50 ? '...' : '');
  };

  const renderSession = ({ item }: { item: ChatSession }) => (
    <TouchableOpacity
      style={styles.sessionCard}
      onPress={() => handleSessionPress(item)}
      onLongPress={() => handleDeleteSession(item)}
      activeOpacity={0.8}
    >
      <Image
        source={{ uri: item.characterAvatar || 'https://i.pravatar.cc/100' }}
        style={styles.avatar}
      />
      <View style={styles.sessionInfo}>
        <View style={styles.sessionHeader}>
          <Text style={styles.characterName}>{item.characterName}</Text>
          <Text style={styles.timestamp}>{formatTime(item.lastMessageAt || item.createdAt)}</Text>
        </View>
        <Text style={styles.sessionTitle} numberOfLines={1}>
          {getLastMessage(item.sessionId)}
        </Text>
      </View>
    </TouchableOpacity>
  );

  const renderEmpty = () => (
    <View style={styles.emptyState}>
      <View style={styles.emptyIcon}>
        <Ionicons name="chatbubbles-outline" size={48} color={theme.colors.text.tertiary} />
      </View>
      <Text style={styles.emptyTitle}>暂无对话</Text>
      <Text style={styles.emptySubtext}>去发现页面开始聊天吧</Text>
      <TouchableOpacity style={styles.startButton} onPress={() => router.push('/(tabs)')}>
        <LinearGradient colors={theme.colors.primary.gradient} style={styles.startButtonGradient}>
          <Text style={styles.startButtonText}>去发现</Text>
        </LinearGradient>
      </TouchableOpacity>
    </View>
  );

  return (
    <LinearGradient colors={theme.colors.background.gradient} style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <View style={styles.header}>
          <TouchableOpacity 
            style={styles.menuButton}
            onPress={() => setShowSettingsDrawer(true)}
          >
            <Ionicons name="menu-outline" size={26} color="#fff" />
          </TouchableOpacity>
          <View style={styles.headerCenter}>
            <Text style={styles.title}>消息</Text>
            {sessions.length > 0 && (
              <Text style={styles.subtitle}>{sessions.length} 个对话</Text>
            )}
          </View>
          <View style={styles.headerRight} />
        </View>

        <FlatList
          data={sessions}
          keyExtractor={(item) => item.sessionId}
          renderItem={renderSession}
          contentContainerStyle={sessions.length === 0 ? styles.emptyContainer : styles.listContainer}
          ListEmptyComponent={!loading ? renderEmpty : null}
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
    color: theme.colors.text.secondary,
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
  avatar: {
    width: 50,
    height: 50,
    borderRadius: 25,
    marginRight: 14,
    backgroundColor: theme.colors.background.tertiary,
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
    color: theme.colors.text.tertiary,
  },
  sessionTitle: {
    fontSize: 14,
    color: theme.colors.text.secondary,
    marginTop: 4,
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
    color: theme.colors.text.secondary,
  },
  emptySubtext: {
    fontSize: 14,
    color: theme.colors.text.tertiary,
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
