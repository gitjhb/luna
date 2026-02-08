/**
 * Terms of Service - Placeholder Page
 */

import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

export default function TermsScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safe}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
            <Ionicons name="chevron-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>服务条款</Text>
          <View style={{ width: 32 }} />
        </View>

        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <Text style={styles.title}>月光碎片 服务条款</Text>
          <Text style={styles.updated}>最后更新：2025 年 1 月</Text>

          <Text style={styles.sectionTitle}>1. 服务说明</Text>
          <Text style={styles.body}>
            月光碎片 是一款 AI 虚拟角色互动应用。所有角色均由人工智能生成，非真实人物。用户与角色的所有互动均为虚拟内容。
          </Text>

          <Text style={styles.sectionTitle}>2. 用户资格</Text>
          <Text style={styles.body}>
            本应用仅面向年满 18 周岁的用户。使用本应用即表明您确认已年满 18 岁。
          </Text>

          <Text style={styles.sectionTitle}>3. 用户行为</Text>
          <Text style={styles.body}>
            用户在使用本应用时应遵守相关法律法规，不得利用本应用从事违法活动。
          </Text>

          <Text style={styles.sectionTitle}>4. 虚拟货币</Text>
          <Text style={styles.body}>
            应用内虚拟货币（月石）仅供应用内消费，不可兑换为现金或转让给他人。
          </Text>

          <Text style={styles.sectionTitle}>5. 免责声明</Text>
          <Text style={styles.body}>
            AI 生成内容可能存在不准确或不当之处。我们不对 AI 生成内容的准确性或适当性承担责任。
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
