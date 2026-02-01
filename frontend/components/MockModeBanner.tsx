/**
 * Backend Status Banner
 * 
 * Shows a warning banner when backend is not connected.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useBackendStatus } from '../hooks/useBackendStatus';

interface Props {
  compact?: boolean;
}

export const MockModeBanner: React.FC<Props> = ({ compact = false }) => {
  const { isConnected, refresh, error } = useBackendStatus();

  if (isConnected) {
    return null;
  }

  if (compact) {
    return (
      <TouchableOpacity style={styles.compactBanner} onPress={refresh}>
        <Ionicons name="cloud-offline" size={14} color="#FF6B6B" />
        <Text style={styles.compactText}>离线</Text>
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity style={styles.banner} onPress={refresh} activeOpacity={0.8}>
      <Ionicons name="cloud-offline" size={16} color="#FF6B6B" />
      <Text style={styles.text}>后端未连接</Text>
      <Ionicons name="refresh" size={14} color="#FF6B6B" style={styles.refreshIcon} />
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255, 107, 107, 0.15)',
    paddingVertical: 8,
    paddingHorizontal: 16,
    marginHorizontal: 16,
    marginVertical: 8,
    borderRadius: 8,
    gap: 8,
  },
  text: {
    fontSize: 13,
    fontWeight: '500',
    color: '#FF6B6B',
  },
  refreshIcon: {
    marginLeft: 4,
  },
  compactBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 107, 107, 0.2)',
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 12,
    gap: 4,
  },
  compactText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#FF6B6B',
  },
});

export default MockModeBanner;
