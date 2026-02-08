/**
 * Moon Shard Icon Component
 * 月石图标组件 - 可复用
 */

import React from 'react';
import { Image, StyleSheet, ImageStyle, StyleProp } from 'react-native';

interface MoonShardIconProps {
  size?: number;
  style?: StyleProp<ImageStyle>;
}

export default function MoonShardIcon({ size = 24, style }: MoonShardIconProps) {
  return (
    <Image
      source={require('../assets/images/moon-shard.png')}
      style={[
        styles.icon,
        { width: size, height: size },
        style,
      ]}
      resizeMode="contain"
    />
  );
}

const styles = StyleSheet.create({
  icon: {
    // 默认样式
  },
});
