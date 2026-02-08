/**
 * VideoMessageBubble Component
 * 
 * 视频消息气泡，点击全屏播放
 */

import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  Dimensions,
  ActivityIndicator,
  Image,
} from 'react-native';
import { Video, ResizeMode, AVPlaybackStatus } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// 视频资源映射
const VIDEO_ASSETS: Record<string, any> = {
  'sakura_beach_reward': require('../assets/characters/sakura/videos/beach_reward.mp4'),
  'vera_intro': require('../assets/characters/vera/videos/intro.mp4'),
  // 后续添加更多视频
};

interface VideoMessageBubbleProps {
  videoId?: string;        // 本地视频资源 ID
  videoUrl?: string;       // 远程视频 URL
  thumbnailUrl?: string;   // 封面图
  caption?: string;        // 消息文字
  characterName?: string;
}

export default function VideoMessageBubble({
  videoId,
  videoUrl,
  thumbnailUrl,
  caption,
  characterName = '角色',
}: VideoMessageBubbleProps) {
  const [showFullscreen, setShowFullscreen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [videoFillMode, setVideoFillMode] = useState<'cover' | 'contain'>('cover');
  const videoRef = useRef<Video>(null);

  // 获取视频源
  const getVideoSource = () => {
    if (videoId && VIDEO_ASSETS[videoId]) {
      return VIDEO_ASSETS[videoId];
    }
    if (videoUrl) {
      return { uri: videoUrl };
    }
    return null;
  };

  const videoSource = getVideoSource();

  const handlePlaybackStatusUpdate = (status: AVPlaybackStatus) => {
    if (status.isLoaded) {
      setIsLoading(false);
      setIsPlaying(status.isPlaying);
      
      // 播放结束后自动重播
      if (status.didJustFinish) {
        videoRef.current?.replayAsync();
      }
    }
  };

  const handlePress = () => {
    setShowFullscreen(true);
  };

  const handleCloseFullscreen = async () => {
    await videoRef.current?.pauseAsync();
    setShowFullscreen(false);
    setVideoFillMode('cover');
  };

  if (!videoSource) {
    return (
      <View style={styles.errorContainer}>
        <Ionicons name="videocam-off" size={24} color="#666" />
        <Text style={styles.errorText}>视频不可用</Text>
      </View>
    );
  }

  return (
    <>
      {/* 聊天气泡内的视频预览 */}
      <View style={styles.bubbleContainer}>
        {/* 消息文字 */}
        {caption && (
          <Text style={styles.captionText}>{caption}</Text>
        )}
        
        {/* 视频预览卡片 */}
        <TouchableOpacity 
          style={styles.videoPreview}
          onPress={handlePress}
          activeOpacity={0.9}
        >
          <LinearGradient
            colors={['rgba(236, 72, 153, 0.2)', 'rgba(139, 92, 246, 0.2)']}
            style={styles.previewGradient}
          >
            {/* 播放图标 */}
            <View style={styles.playIconContainer}>
              <LinearGradient
                colors={['#00D4FF', '#8B5CF6']}
                style={styles.playIconGradient}
              >
                <Ionicons name="play" size={28} color="#fff" style={{ marginLeft: 3 }} />
              </LinearGradient>
            </View>
            
            {/* 视频标签 */}
            <View style={styles.videoLabel}>
              <Ionicons name="videocam" size={12} color="#fff" />
              <Text style={styles.videoLabelText}>专属视频</Text>
            </View>
          </LinearGradient>
        </TouchableOpacity>
      </View>

      {/* 全屏视频播放 Modal */}
      <Modal
        visible={showFullscreen}
        transparent={false}
        animationType="fade"
        onRequestClose={handleCloseFullscreen}
        statusBarTranslucent
      >
        <View style={styles.fullscreenContainer}>
          {/* 关闭按钮 */}
          <TouchableOpacity 
            style={styles.closeButton}
            onPress={handleCloseFullscreen}
          >
            <Ionicons name="close-circle" size={36} color="rgba(255,255,255,0.7)" />
          </TouchableOpacity>

          {/* 缩放切换按钮 */}
          <TouchableOpacity 
            style={styles.scaleButton}
            onPress={() => setVideoFillMode(prev => prev === 'cover' ? 'contain' : 'cover')}
          >
            <Ionicons 
              name={videoFillMode === 'cover' ? 'contract-outline' : 'expand-outline'} 
              size={28} 
              color="rgba(255,255,255,0.7)" 
            />
          </TouchableOpacity>

          {/* 加载指示器 */}
          {isLoading && (
            <ActivityIndicator 
              size="large" 
              color="#00D4FF" 
              style={styles.loadingIndicator}
            />
          )}

          {/* 视频播放器 */}
          <Video
            ref={videoRef}
            source={videoSource}
            style={styles.fullscreenVideo}
            resizeMode={videoFillMode === 'cover' ? ResizeMode.COVER : ResizeMode.CONTAIN}
            shouldPlay={showFullscreen}
            isLooping
            useNativeControls
            onPlaybackStatusUpdate={handlePlaybackStatusUpdate}
          />
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  bubbleContainer: {
    maxWidth: SCREEN_WIDTH * 0.7,
  },
  captionText: {
    fontSize: 15,
    color: 'rgba(255, 255, 255, 0.92)',
    lineHeight: 22,
    marginBottom: 10,
  },
  videoPreview: {
    width: 200,
    height: 120,
    borderRadius: 16,
    overflow: 'hidden',
  },
  previewGradient: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  playIconContainer: {
    width: 56,
    height: 56,
    borderRadius: 28,
    overflow: 'hidden',
  },
  playIconGradient: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  videoLabel: {
    position: 'absolute',
    bottom: 8,
    right: 8,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 10,
    gap: 4,
  },
  videoLabelText: {
    fontSize: 11,
    color: '#fff',
    fontWeight: '500',
  },
  errorContainer: {
    padding: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  errorText: {
    color: '#666',
    marginTop: 8,
  },
  
  // Fullscreen styles
  fullscreenContainer: {
    flex: 1,
    backgroundColor: '#000',
    justifyContent: 'center',
    alignItems: 'center',
  },
  closeButton: {
    position: 'absolute',
    top: 50,
    right: 16,
    zIndex: 100,
    padding: 8,
  },
  scaleButton: {
    position: 'absolute',
    top: 50,
    left: 16,
    zIndex: 100,
    padding: 8,
  },
  loadingIndicator: {
    position: 'absolute',
    zIndex: 5,
  },
  fullscreenVideo: {
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT,
  },
});
