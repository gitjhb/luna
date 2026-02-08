/**
 * Privacy Policy - App Store Compliant
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
          <Text style={styles.title}>月光碎片 隐私政策</Text>
          <Text style={styles.updated}>最后更新：2026 年 2 月 5 日</Text>

          <Text style={styles.sectionTitle}>1. 概述</Text>
          <Text style={styles.body}>
            月光碎片（"本应用"）是一款 AI 虚拟角色互动应用。本隐私政策说明我们如何收集、使用和保护您的个人信息。使用本应用即表示您同意本政策。
          </Text>

          <Text style={styles.sectionTitle}>2. AI 生成内容声明</Text>
          <Text style={styles.body}>
            本应用中所有角色对话内容均由人工智能（AI）技术生成，不代表真实人物的观点或行为。AI 生成的内容可能不完全准确，请勿将其作为专业建议（包括但不限于医疗、法律、财务建议）。
          </Text>

          <Text style={styles.sectionTitle}>3. 信息收集</Text>
          <Text style={styles.body}>
            我们收集以下信息：{'\n'}
            • 账户信息：登录方式（Apple ID / Google / 访客）{'\n'}
            • 使用数据：对话内容、兴趣偏好、应用使用习惯{'\n'}
            • 设备信息：设备型号、操作系统版本、唯一设备标识符{'\n\n'}
            我们不会收集您的真实姓名、电话号码、精确位置或通讯录。
          </Text>

          <Text style={styles.sectionTitle}>4. 信息使用</Text>
          <Text style={styles.body}>
            收集的信息用于：{'\n'}
            • 提供和改善 AI 对话体验{'\n'}
            • 个性化角色互动和内容推荐{'\n'}
            • 维护应用安全和防止滥用{'\n'}
            • 分析使用趋势以改进服务
          </Text>

          <Text style={styles.sectionTitle}>5. 数据存储与安全</Text>
          <Text style={styles.body}>
            您的数据经过加密传输（TLS）和加密存储。对话内容存储在安全的服务器上，仅授权人员可以访问。我们采用行业标准的安全措施保护您的数据。
          </Text>

          <Text style={styles.sectionTitle}>6. 数据共享</Text>
          <Text style={styles.body}>
            我们不会出售您的个人数据。我们可能在以下情况下共享数据：{'\n'}
            • 经您明确同意{'\n'}
            • 法律要求或法律程序{'\n'}
            • 与为我们提供服务的第三方（如 AI 模型提供商、云存储），这些第三方受严格的数据保护协议约束
          </Text>

          <Text style={styles.sectionTitle}>7. 未成年人保护</Text>
          <Text style={styles.body}>
            本应用仅面向 18 岁及以上用户。我们不会故意收集未成年人的个人信息。如发现未成年人使用本应用，我们将删除相关数据。
          </Text>

          <Text style={styles.sectionTitle}>8. 您的权利</Text>
          <Text style={styles.body}>
            您有权：{'\n'}
            • 访问和导出您的个人数据{'\n'}
            • 请求更正不准确的数据{'\n'}
            • 请求删除您的账户和所有数据{'\n'}
            • 撤回对数据处理的同意{'\n\n'}
            删除请求可通过应用内"角色资料 → 删除数据"或联系我们处理，将在 30 天内完成。
          </Text>

          <Text style={styles.sectionTitle}>9. Cookie 与追踪</Text>
          <Text style={styles.body}>
            本应用不使用 Cookie。我们可能使用匿名分析工具来了解应用使用情况。
          </Text>

          <Text style={styles.sectionTitle}>10. 政策更新</Text>
          <Text style={styles.body}>
            我们可能不时更新本隐私政策。重大变更将通过应用内通知告知您。继续使用本应用即表示接受更新后的政策。
          </Text>

          <Text style={styles.sectionTitle}>11. 联系我们</Text>
          <Text style={styles.body}>
            如有隐私相关问题，请联系：{'\n'}
            📧 support@luna-app.com
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
