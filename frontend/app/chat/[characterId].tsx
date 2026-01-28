/**
 * Chat Screen
 * 
 * Main chat interface with:
 * - Spicy mode toggle (requires subscription)
 * - Message list with optimized rendering
 * - Input field with send button
 * - Credit header
 * - Typing indicator
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
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { theme, getSpicyTheme } from '../../theme/config';
import { useUserStore } from '../../store/userStore';
import { useChatStore, selectActiveMessages, selectIsSpicyMode } from '../../store/chatStore';
import { ChatBubble } from '../../components/molecules/ChatBubble';
import { CreditHeader } from '../../components/molecules/CreditHeader';
import { TypingIndicator } from '../../components/atoms/TypingIndicator';
import { PaywallModal } from '../../components/organisms/PaywallModal';
import { chatService } from '../../services/chatService';

export default function ChatScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ characterId: string; characterName: string }>();
  
  // Store state
  const { isSubscribed, wallet, deductCredits } = useUserStore();
  const {
    activeSessionId,
    isSpicyMode,
    isTyping,
    setActiveSession,
    addMessage,
    toggleSpicyMode,
    setTyping,
    unlockMessage,
  } = useChatStore();
  
  const messages = useChatStore(selectActiveMessages);
  
  // Local state
  const [inputText, setInputText] = useState('');
  const [showPaywall, setShowPaywall] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  
  const flatListRef = useRef<FlatList>(null);
  
  // Initialize session
  useEffect(() => {
    initializeSession();
  }, [params.characterId]);
  
  const initializeSession = async () => {
    try {
      // Create or get existing session
      const session = await chatService.createSession(params.characterId);
      setSessionId(session.sessionId);
      setActiveSession(session.sessionId, params.characterId);
      
      // Load message history
      const history = await chatService.getSessionHistory(session.sessionId);
      // Set messages in store
    } catch (error) {
      console.error('Failed to initialize session:', error);
      Alert.alert('Error', 'Failed to start chat session');
    }
  };
  
  // Handle spicy mode toggle
  const handleSpicyToggle = () => {
    if (!isSubscribed) {
      setShowPaywall(true);
      return;
    }
    toggleSpicyMode();
  };
  
  // Send message
  const handleSend = async () => {
    if (!inputText.trim() || !sessionId) return;
    
    const userMessage = {
      messageId: `temp-${Date.now()}`,
      role: 'user' as const,
      content: inputText.trim(),
      createdAt: new Date().toISOString(),
    };
    
    // Add user message immediately
    addMessage(sessionId, userMessage);
    setInputText('');
    
    // Scroll to bottom
    setTimeout(() => {
      flatListRef.current?.scrollToEnd({ animated: true });
    }, 100);
    
    // Show typing indicator
    setTyping(true, params.characterId);
    
    try {
      // Call API
      const response = await chatService.sendMessage({
        sessionId,
        message: userMessage.content,
      });
      
      // Add assistant message
      addMessage(sessionId, {
        messageId: response.messageId,
        role: 'assistant',
        content: response.content,
        type: response.type,
        isLocked: response.isLocked,
        imageUrl: response.imageUrl,
        createdAt: response.createdAt,
      });
      
      // Deduct credits
      if (response.creditsDeducted) {
        deductCredits(response.creditsDeducted);
      }
      
      // Scroll to bottom
      setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
      }, 100);
    } catch (error: any) {
      console.error('Failed to send message:', error);
      
      if (error.error === 'insufficient_credits') {
        Alert.alert(
          'Insufficient Credits',
          `You need ${error.required} credits. Current balance: ${error.currentBalance}`,
          [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Buy Credits', onPress: () => router.push('/profile/credits') },
          ]
        );
      } else if (error.error === 'rate_limit_exceeded') {
        Alert.alert(
          'Rate Limit Exceeded',
          `Please wait ${error.retryAfter} seconds before sending another message.`
        );
      } else {
        Alert.alert('Error', 'Failed to send message. Please try again.');
      }
    } finally {
      setTyping(false);
    }
  };
  
  // Handle unlock message
  const handleUnlock = async (messageId: string) => {
    if (!sessionId) return;
    
    try {
      await chatService.unlockMessage(sessionId, messageId);
      unlockMessage(sessionId, messageId);
      deductCredits(5); // Unlock cost
    } catch (error) {
      console.error('Failed to unlock message:', error);
      Alert.alert('Error', 'Failed to unlock content');
    }
  };
  
  // Apply spicy theme
  const activeTheme = isSpicyMode ? getSpicyTheme() : theme;
  const accentColor = isSpicyMode ? theme.colors.spicy.main : theme.colors.primary.main;
  
  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      {/* Credit Header */}
      <CreditHeader
        credits={wallet?.totalCredits || 0}
        onBuyCredits={() => router.push('/profile/credits')}
        isSpicyMode={isSpicyMode}
      />
      
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color={theme.colors.text.primary} />
        </TouchableOpacity>
        
        <View style={styles.headerInfo}>
          <Text style={styles.characterName}>{params.characterName}</Text>
          {isTyping && (
            <Text style={styles.typingText}>typing...</Text>
          )}
        </View>
        
        {/* Spicy Mode Toggle */}
        <TouchableOpacity
          style={[styles.spicyToggle, isSpicyMode && styles.spicyToggleActive]}
          onPress={handleSpicyToggle}
        >
          <Ionicons
            name="flame"
            size={20}
            color={isSpicyMode ? theme.colors.text.inverse : theme.colors.text.secondary}
          />
          {!isSubscribed && (
            <View style={styles.lockBadge}>
              <Ionicons name="lock-closed" size={10} color={theme.colors.text.inverse} />
            </View>
          )}
        </TouchableOpacity>
      </View>
      
      {/* Messages List */}
      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(item) => item.messageId}
        renderItem={({ item }) => (
          <ChatBubble
            message={item}
            onUnlock={handleUnlock}
            isSpicyMode={isSpicyMode}
          />
        )}
        contentContainerStyle={styles.messagesList}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
        ListFooterComponent={isTyping ? <TypingIndicator isSpicyMode={isSpicyMode} /> : null}
      />
      
      {/* Input Area */}
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            placeholder="Type a message..."
            placeholderTextColor={theme.colors.text.tertiary}
            value={inputText}
            onChangeText={setInputText}
            multiline
            maxLength={2000}
          />
          
          <TouchableOpacity
            style={[styles.sendButton, !inputText.trim() && styles.sendButtonDisabled]}
            onPress={handleSend}
            disabled={!inputText.trim()}
          >
            <LinearGradient
              colors={isSpicyMode ? theme.colors.spicy.gradient : theme.colors.primary.gradient}
              style={styles.sendButtonGradient}
            >
              <Ionicons name="send" size={20} color={theme.colors.text.inverse} />
            </LinearGradient>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
      
      {/* Paywall Modal */}
      <PaywallModal
        visible={showPaywall}
        onClose={() => setShowPaywall(false)}
        onSubscribe={(plan) => {
          // Handle subscription
          console.log('Subscribe to:', plan);
          setShowPaywall(false);
        }}
        feature="Spicy Mode"
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background.primary,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  backButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerInfo: {
    flex: 1,
    marginLeft: theme.spacing.sm,
  },
  characterName: {
    fontFamily: theme.typography.fontFamily.bold,
    fontSize: theme.typography.fontSize.lg,
    color: theme.colors.text.primary,
  },
  typingText: {
    fontFamily: theme.typography.fontFamily.regular,
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.secondary,
    fontStyle: 'italic',
  },
  spicyToggle: {
    width: 44,
    height: 44,
    borderRadius: theme.borderRadius.full,
    backgroundColor: theme.colors.background.secondary,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  spicyToggleActive: {
    backgroundColor: theme.colors.spicy.main,
  },
  lockBadge: {
    position: 'absolute',
    top: -4,
    right: -4,
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: theme.colors.primary.main,
    justifyContent: 'center',
    alignItems: 'center',
  },
  messagesList: {
    paddingVertical: theme.spacing.md,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    backgroundColor: theme.colors.background.secondary,
    borderTopWidth: 1,
    borderTopColor: theme.colors.border,
    gap: theme.spacing.sm,
  },
  input: {
    flex: 1,
    backgroundColor: theme.colors.background.tertiary,
    borderRadius: theme.borderRadius.lg,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    fontFamily: theme.typography.fontFamily.regular,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.primary,
    maxHeight: 100,
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: theme.borderRadius.full,
    overflow: 'hidden',
  },
  sendButtonDisabled: {
    opacity: 0.5,
  },
  sendButtonGradient: {
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
});
