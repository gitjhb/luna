/**
 * EventStoryModal Component
 * 
 * Full-screen modal for reading event stories.
 * Visual novel style with title, story content, and close button.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  ScrollView,
  Dimensions,
  ActivityIndicator,
  ImageBackground,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import Animated, {
  FadeIn,
  FadeOut,
  SlideInDown,
  SlideOutDown,
} from 'react-native-reanimated';
import { eventService, EventStoryPlaceholder, EventMemory } from '../services/eventService';
import { useChatStore, selectActiveMessages } from '../store/chatStore';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

interface EventStoryModalProps {
  visible: boolean;
  onClose: () => void;
  placeholder: EventStoryPlaceholder | null;
  characterId: string;
  characterName: string;
  backgroundUrl?: string;
  onStoryGenerated?: (storyId: string) => void;
}

export default function EventStoryModal({
  visible,
  onClose,
  placeholder,
  characterId,
  characterName,
  backgroundUrl,
  onStoryGenerated,
}: EventStoryModalProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [story, setStory] = useState<EventMemory | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Get recent chat history for context
  const messages = useChatStore(selectActiveMessages);
  
  const eventInfo = placeholder ? eventService.getEventInfo(placeholder.event_type) : null;
  
  // Load or generate story when modal opens
  useEffect(() => {
    if (visible && placeholder) {
      loadOrGenerateStory();
    }
  }, [visible, placeholder]);
  
  const loadOrGenerateStory = async () => {
    if (!placeholder) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      // If we have a story_id (from MemoriesModal), fetch by ID directly
      if (placeholder.story_id) {
        const existingStory = await eventService.getEventMemoryById(
          characterId,
          placeholder.story_id
        );
        if (existingStory) {
          setStory(existingStory);
          setIsLoading(false);
          return;
        }
      }
      
      // Otherwise try to get existing story by event_type
      const existingStory = await eventService.getEventMemory(
        characterId,
        placeholder.event_type
      );
      
      if (existingStory) {
        setStory(existingStory);
        setIsLoading(false);
        return;
      }
      
      // Generate new story
      const chatHistory = messages.slice(-10).map(m => ({
        role: m.role,
        content: m.content,
      }));
      
      const result = await eventService.generateStory(
        characterId,
        placeholder.event_type,
        chatHistory
      );
      
      if (result.success && result.story_content) {
        setStory({
          id: result.event_memory_id || '',
          user_id: 'me',
          character_id: characterId,
          event_type: placeholder.event_type,
          story_content: result.story_content,
          generated_at: new Date().toISOString(),
        });
        
        if (result.event_memory_id) {
          onStoryGenerated?.(result.event_memory_id);
        }
      } else {
        setError(result.error || '生成剧情失败，请稍后重试');
      }
    } catch (err: any) {
      setError(err.message || '加载失败，请稍后重试');
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleClose = useCallback(() => {
    setStory(null);
    setError(null);
    onClose();
  }, [onClose]);
  
  if (!visible || !placeholder || !eventInfo) return null;
  
  return (
    <Modal
      visible={visible}
      transparent
      animationType="none"
      onRequestClose={handleClose}
      statusBarTranslucent
    >
      <View style={styles.container}>
        {/* Background */}
        <ImageBackground
          source={backgroundUrl ? { uri: backgroundUrl } : undefined}
          style={styles.background}
          resizeMode="cover"
        >
          {/* Dark overlay */}
          <LinearGradient
            colors={['rgba(0,0,0,0.7)', 'rgba(0,0,0,0.85)', 'rgba(0,0,0,0.95)']}
            style={StyleSheet.absoluteFillObject}
          />
        </ImageBackground>
        
        {/* Header */}
        <Animated.View 
          entering={FadeIn.delay(200)} 
          style={styles.header}
        >
          <View style={styles.headerContent}>
            <Text style={styles.eventIcon}>{eventInfo.icon}</Text>
            <Text style={styles.eventTitle}>{eventInfo.name_cn}</Text>
            <Text style={styles.characterLabel}>与 {characterName}</Text>
          </View>
          
          <TouchableOpacity style={styles.closeButton} onPress={handleClose}>
            <Ionicons name="close" size={28} color="#fff" />
          </TouchableOpacity>
        </Animated.View>
        
        {/* Content */}
        <Animated.View 
          entering={SlideInDown.delay(300).springify()} 
          style={styles.contentContainer}
        >
          {isLoading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#00D4FF" />
              <Text style={styles.loadingText}>正在为你创作专属剧情...</Text>
              <Text style={styles.loadingSubtext}>这可能需要 10-20 秒</Text>
            </View>
          ) : error ? (
            <View style={styles.errorContainer}>
              <Ionicons name="sad-outline" size={48} color="#F43F5E" />
              <Text style={styles.errorText}>{error}</Text>
              <TouchableOpacity style={styles.retryButton} onPress={loadOrGenerateStory}>
                <Text style={styles.retryButtonText}>重试</Text>
              </TouchableOpacity>
            </View>
          ) : story ? (
            <ScrollView 
              style={styles.storyScroll}
              contentContainerStyle={styles.storyContent}
              showsVerticalScrollIndicator={false}
            >
              {/* Story text with visual novel style */}
              <View style={styles.storyTextContainer}>
                <Text style={styles.storyText}>{story.story_content}</Text>
              </View>
              
              {/* Generated date */}
              {story.generated_at && (
                <Text style={styles.generatedDate}>
                  📅 {new Date(story.generated_at).toLocaleDateString('zh-CN', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </Text>
              )}
              
              {/* Bottom padding for safe area */}
              <View style={{ height: 100 }} />
            </ScrollView>
          ) : null}
        </Animated.View>
        
        {/* Bottom fade gradient */}
        <LinearGradient
          colors={['transparent', 'rgba(0,0,0,0.9)']}
          style={styles.bottomGradient}
          pointerEvents="none"
        />
        
        {/* Close button at bottom */}
        {story && !isLoading && (
          <Animated.View 
            entering={FadeIn.delay(500)} 
            style={styles.bottomButtonContainer}
          >
            <TouchableOpacity style={styles.bottomCloseButton} onPress={handleClose}>
              <LinearGradient
                colors={['#00D4FF', '#8B5CF6']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.bottomCloseGradient}
              >
                <Text style={styles.bottomCloseText}>关闭</Text>
              </LinearGradient>
            </TouchableOpacity>
          </Animated.View>
        )}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  background: {
    position: 'absolute',
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingTop: 60,
    paddingHorizontal: 20,
    paddingBottom: 16,
  },
  headerContent: {
    flex: 1,
  },
  eventIcon: {
    fontSize: 40,
    marginBottom: 8,
  },
  eventTitle: {
    fontSize: 28,
    fontWeight: '800',
    color: '#fff',
    marginBottom: 4,
  },
  characterLabel: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.7)',
  },
  closeButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  contentContainer: {
    flex: 1,
    paddingHorizontal: 20,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingBottom: 100,
  },
  loadingText: {
    marginTop: 20,
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  loadingSubtext: {
    marginTop: 8,
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.5)',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingBottom: 100,
  },
  errorText: {
    marginTop: 16,
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.7)',
    textAlign: 'center',
  },
  retryButton: {
    marginTop: 24,
    paddingHorizontal: 32,
    paddingVertical: 12,
    backgroundColor: 'rgba(244, 63, 94, 0.2)',
    borderRadius: 24,
    borderWidth: 1,
    borderColor: '#F43F5E',
  },
  retryButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#F43F5E',
  },
  storyScroll: {
    flex: 1,
  },
  storyContent: {
    paddingTop: 16,
    paddingBottom: 40,
  },
  storyTextContainer: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  storyText: {
    fontSize: 17,
    lineHeight: 30,
    color: 'rgba(255, 255, 255, 0.95)',
    fontFamily: Platform.select({ ios: 'PingFang SC', android: 'Noto Sans CJK SC' }),
  },
  generatedDate: {
    marginTop: 20,
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.4)',
    textAlign: 'center',
  },
  bottomGradient: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    height: 150,
  },
  bottomButtonContainer: {
    position: 'absolute',
    left: 20,
    right: 20,
    bottom: 40,
  },
  bottomCloseButton: {
    borderRadius: 28,
    overflow: 'hidden',
  },
  bottomCloseGradient: {
    paddingVertical: 16,
    alignItems: 'center',
  },
  bottomCloseText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
});

// Import Platform at the top
import { Platform } from 'react-native';
