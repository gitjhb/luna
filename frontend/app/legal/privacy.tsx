/**
 * Privacy Policy - Placeholder Page
 */

import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

export default function PrivacyScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safe}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
            <Ionicons name="chevron-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>隐私政策</Text>
          <View style={{ width: 32 }} />
        </View>

        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <Text style={styles.title}>Luna 隐私政策</Text>
          <Text style={styles.updated}>最后更新：2025 年 1 月</Text>

          <Text style={styles.sectionTitle}>1. 信息收集</Text>
          <Text style={styles.body}>
            我们收集的信息包括：设备信息、使用数据、您主动提供的文字内容。我们不会收集您的真实姓名、地址或其他不必要的个人信息。
          </Text>

          <Text style={styles.sectionTitle}>2. 信息使用</Text>
          <Text style={styles.body}>
            收集的信息仅用于提供和改善服务、生成 AI 回复、以及保障账户安全。
          </Text>

          <Text style={styles.sectionTitle}>3. 数据安全</Text>
          <Text style={styles.body}>
            我们采用行业标准的加密和安全措施保护您的数据。聊天内容经过加密存储。
          </Text>

          <Text style={styles.sectionTitle}>4. 数据删除</Text>
          <Text style={styles.body}>
            您可以随时通过设置页面请求删除账户及所有相关数据。删除请求将在 30 天内处理。
          </Text>

          <Text style={styles.sectionTitle}>5. 第三方服务</Text>
          <Text style={styles.body}>
            我们可能使用第三方服务（如支付处理、数据分析）。这些服务有各自的隐私政策。
          </Text>

          <Text style={styles.sectionTitle}>6. 联系我们</Text>
          <Text style={styles.body}>
            如有隐私相关问题，请联系：support@luna-app.com
          </Text>

          <View style={{ height: 60 }} />
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0612',
  },
  safe: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(139, 92, 246, 0.15)',
  },
  backBtn: {
    padding: 4,
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: '#fff',
  },
  content: {
    padding: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 6,
  },
  updated: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.4)',
    marginBottom: 28,
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: '#8B5CF6',
    marginTop: 20,
    marginBottom: 8,
  },
  body: {
    fontSize: 15,
    color: 'rgba(255,255,255,0.7)',
    lineHeight: 24,
  },
});
