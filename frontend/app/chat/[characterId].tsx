/**
 * Chat Screen - Intimate Style
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  FlatList,
  Alert,
  Keyboard,
  Image,
  Dimensions,
  ImageBackground,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useUserStore } from '../../store/userStore';
import { useChatStore, selectActiveMessages, Message } from '../../store/chatStore';
import { chatService } from '../../services/chatService';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

const DEFAULT_BACKGROUND = 'https://i.imgur.com/vB5HQXQ.jpg';

export default function ChatScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ characterId: string; characterName: string; sessionId?: string; backgroundUrl?: string; avatarUrl?: string }>();
  
  const { wallet, deductCredits, isSubscribed } = useUserStore();
  const {
    isTyping,
    setActiveSession,
    addMessage,
    setMessages,
    setTyping,
  } = useChatStore();
  
  const messages = useChatStore(selectActiveMessages);
  
  const [inputText, setInputText] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(params.sessionId || null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [characterAvatar, setCharacterAvatar] = useState(params.avatarUrl || 'https://i.pravatar.cc/100?img=5');
  const [backgroundImage, setBackgroundImage] = useState(params.backgroundUrl || DEFAULT_BACKGROUND);
  const [relationshipLevel, setRelationshipLevel] = useState(1);
  const [relationshipXp, setRelationshipXp] = useState(0);
  const [relationshipMaxXp, setRelationshipMaxXp] = useState(100);
  
  const flatListRef = useRef<FlatList>(null);
  const characterName = params.characterName || 'Companion';

  useEffect(() => {
    initializeSession();
  }, [params.characterId]);

  const initializeSession = async () => {
    try {
      setIsInitializing(true);
      
      if (params.sessionId) {
        setSessionId(params.sessionId);
        setActiveSession(params.sessionId, params.characterId);
        const history = await chatService.getSessionHistory(params.sessionId);
        setMessages(params.sessionId, history);
      } else {
        const session = await chatService.createSession(params.characterId);
        setSessionId(session.sessionId);
        setActiveSession(session.sessionId, params.characterId);
        if (session.characterAvatar) setCharacterAvatar(session.characterAvatar);
        if (session.characterBackground) setBackgroundImage(session.characterBackground);
      }
    } catch (error) {
      console.error('Failed to initialize session:', error);
    } finally {
      setIsInitializing(false);
    }
  };

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text || !sessionId) return;
    
    Keyboard.dismiss();
    setInputText('');
    
    const userMessage: Message = {
      messageId: `user-${Date.now()}`,
      role: 'user',
      content: text,
      createdAt: new Date().toISOString(),
    };
    addMessage(sessionId, userMessage);
    
    setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    setTyping(true, params.characterId);
    
    try {
      const response = await chatService.sendMessage({ sessionId, message: text });
      
      addMessage(sessionId, {
        messageId: response.messageId,
        role: 'assistant',
        content: response.content,
        type: response.type,
        isLocked: response.isLocked,
        imageUrl: response.imageUrl,
        createdAt: response.createdAt,
      });
      
      if (response.creditsDeducted) {
        deductCredits(response.creditsDeducted);
      }
      
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    } catch (error: any) {
      console.error('Send message error:', error);
      Alert.alert('Error', 'Failed to send message');
    } finally {
      setTyping(false);
    }
  };

  const renderMessage = ({ item }: { item: Message }) => {
    const isUser = item.role === 'user';
    
    return (
      <View style={[styles.messageRow, isUser ? styles.messageRowUser : styles.messageRowAI]}>
        {/* AI Avatar */}
        {!isUser && (
          <Image source={{ uri: characterAvatar }} style={styles.avatar} />
        )}
        
        {/* Message Bubble */}
        <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAI]}>
          <Text style={[styles.messageText, isUser ? styles.messageTextUser : styles.messageTextAI]}>
            {item.content}
          </Text>
        </View>
      </View>
    );
  };

  const renderTypingIndicator = () => (
    <View style={[styles.messageRow, styles.messageRowAI]}>
      <Image source={{ uri: characterAvatar }} style={styles.avatar} />
      <View style={[styles.bubble, styles.bubbleAI, styles.typingBubble]}>
        <Text style={styles.typingText}>正在输入...</Text>
      </View>
    </View>
  );

  return (
    <View style={styles.container}>
      {/* Full screen background image */}
      <ImageBackground
        source={{ uri: backgroundImage }}
        style={styles.backgroundImage}
        resizeMode="cover"
      >
        {/* Gradient overlay for readability */}
        <LinearGradient
          colors={['rgba(26,16,37,0.3)', 'rgba(26,16,37,0.7)', 'rgba(26,16,37,0.95)'] as [string, string, string]}
          style={styles.overlay}
        />
      </ImageBackground>

      <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="close" size={28} color="#fff" />
          </TouchableOpacity>
          
          <View style={styles.headerCenter}>
            <Text style={styles.characterName}>{characterName}</Text>
          </View>
          
          <TouchableOpacity style={styles.menuButton}>
            <Ionicons name="ellipsis-horizontal" size={24} color="#fff" />
          </TouchableOpacity>
        </View>

        {/* Status Bar - Level, Credits, Upgrade */}
        <View style={styles.statusBar}>
          {/* Level Badge */}
          <View style={styles.levelContainer}>
            <Text style={styles.levelText}>LV {relationshipLevel}</Text>
            <View style={styles.xpBarContainer}>
              <View style={[styles.xpBar, { width: `${(relationshipXp / relationshipMaxXp) * 100}%` }]} />
            </View>
          </View>
          
          {/* Credits */}
          <View style={styles.creditsContainer}>
            <Text style={styles.coinEmoji}>🪙</Text>
            <Text style={styles.creditsText}>{wallet?.totalCredits ?? 0}</Text>
            <TouchableOpacity style={styles.addCreditsButton}>
              <Ionicons name="add" size={14} color="#FFD700" />
            </TouchableOpacity>
          </View>
          
          {/* Upgrade Button */}
          {!isSubscribed && (
            <TouchableOpacity style={styles.upgradeButton} onPress={() => router.push('/subscription')}>
              <LinearGradient
                colors={['#FF6B35', '#F7931E'] as [string, string]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.upgradeGradient}
              >
                <Text style={styles.upgradeIcon}>🔥</Text>
                <Text style={styles.upgradeText}>UPGRADE</Text>
              </LinearGradient>
            </TouchableOpacity>
          )}
        </View>

        {/* Messages */}
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(item) => item.messageId}
          renderItem={renderMessage}
          contentContainerStyle={styles.messagesList}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: false })}
          ListFooterComponent={isTyping ? renderTypingIndicator : null}
          showsVerticalScrollIndicator={false}
        />

        {/* Input Area - moved up */}
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          keyboardVerticalOffset={0}
        >
          <View style={styles.inputContainer}>
            {/* Input */}
            <View style={styles.inputWrapper}>
              <TextInput
                style={styles.input}
                placeholder={`与 ${characterName} 聊天`}
                placeholderTextColor="rgba(255,255,255,0.4)"
                value={inputText}
                onChangeText={setInputText}
                multiline
                maxLength={2000}
              />
            </View>
            
            {/* Send Button */}
            <TouchableOpacity 
              style={[styles.sendButton, !inputText.trim() && styles.sendButtonDisabled]} 
              onPress={handleSend}
              disabled={!inputText.trim()}
            >
              <LinearGradient
                colors={inputText.trim() ? ['#EC4899', '#8B5CF6'] as [string, string] : ['#555', '#444'] as [string, string]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.sendButtonGradient}
              >
                <Ionicons name="send" size={20} color="#fff" />
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1025',
  },
  backgroundImage: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: SCREEN_HEIGHT * 0.6,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
  },
  safeArea: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  backButton: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerCenter: {
    flex: 1,
    alignItems: 'center',
  },
  characterName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  menuButton: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  statusBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    borderRadius: 12,
    marginHorizontal: 16,
    marginBottom: 8,
  },
  levelContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  levelText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#fff',
  },
  xpBarContainer: {
    width: 50,
    height: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 3,
    overflow: 'hidden',
  },
  xpBar: {
    height: '100%',
    backgroundColor: '#A855F7',
    borderRadius: 3,
  },
  creditsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 215, 0, 0.15)',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 16,
    gap: 4,
  },
  coinEmoji: {
    fontSize: 14,
  },
  creditsText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFD700',
  },
  addCreditsButton: {
    marginLeft: 2,
  },
  upgradeButton: {
    borderRadius: 16,
    overflow: 'hidden',
  },
  upgradeGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    gap: 4,
  },
  upgradeIcon: {
    fontSize: 12,
  },
  upgradeText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#fff',
  },
  messagesList: {
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 8,
  },
  messageRow: {
    flexDirection: 'row',
    marginBottom: 12,
    alignItems: 'flex-end',
  },
  messageRowUser: {
    justifyContent: 'flex-end',
  },
  messageRowAI: {
    justifyContent: 'flex-start',
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    marginRight: 8,
  },
  bubble: {
    maxWidth: SCREEN_WIDTH * 0.72,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 18,
  },
  bubbleUser: {
    backgroundColor: 'rgba(255, 255, 255, 0.18)',
    borderBottomRightRadius: 4,
  },
  bubbleAI: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderBottomLeftRadius: 4,
  },
  messageText: {
    fontSize: 15,
    lineHeight: 21,
  },
  messageTextUser: {
    color: '#fff',
  },
  messageTextAI: {
    color: 'rgba(255, 255, 255, 0.92)',
  },
  typingBubble: {
    paddingVertical: 8,
  },
  typingText: {
    color: 'rgba(255, 255, 255, 0.5)',
    fontSize: 14,
    fontStyle: 'italic',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 16,
    gap: 10,
  },
  inputWrapper: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.12)',
    borderRadius: 24,
    paddingHorizontal: 18,
    paddingVertical: Platform.OS === 'ios' ? 12 : 8,
    minHeight: 48,
    justifyContent: 'center',
  },
  input: {
    fontSize: 16,
    color: '#fff',
    maxHeight: 100,
  },
  sendButton: {
    borderRadius: 24,
    overflow: 'hidden',
  },
  sendButtonDisabled: {
    opacity: 0.5,
  },
  sendButtonGradient: {
    width: 48,
    height: 48,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
