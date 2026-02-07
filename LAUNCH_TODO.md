# 🚀 Luna App Store 上线 TODO

> 最后更新: 2026-02-07

## 📊 当前状态概览

| 模块 | 状态 | 备注 |
|------|------|------|
| 前端 UI | ✅ 95% | 基本完成，细节打磨 |
| 后端 API | ✅ 90% | 核心功能完成 |
| 登录认证 | ⚠️ 70% | Apple/Google 待测试 |
| 支付系统 | ⚠️ 60% | RevenueCat 已集成，待配置 |
| App Store | ⏳ 30% | 需要配置产品和审核材料 |
| 服务器部署 | ⏳ 20% | 本地开发中，生产环境待部署 |

---

## 🔴 P0 - 上线阻断项 (必须完成)

### 1. App Store Connect 配置
- [ ] **创建 IAP 产品**
  - [ ] `monthly` - 月度订阅 (¥18/月)
  - [ ] `yearly` - 年度订阅 (¥128/年)
  - [ ] `lifetime` - 终身会员 (¥298)
- [ ] **配置订阅组** - Luna Pro
- [ ] **填写 App Store 元数据**
  - [ ] App 名称、副标题、关键词
  - [ ] 完整描述 (中/英)
  - [ ] 截图 (6.7", 6.5", 5.5")
  - [ ] App 预览视频 (可选)
- [ ] **年龄分级** - 17+ (成人内容)
- [ ] **隐私政策 URL** - 需要公网可访问

### 2. RevenueCat Dashboard 配置
- [ ] **连接 App Store Connect**
  - [ ] 上传 App Store Connect API Key
  - [ ] 配置 Shared Secret
- [ ] **创建 Products** (对应 IAP)
- [ ] **创建 Entitlement**: `Luna Pro`
- [ ] **创建 Offering**: default
- [ ] **配置 Webhook** → 后端接收
- [ ] **设计 Paywall** (可选，用 Dashboard)

### 3. 后端生产部署
- [ ] **服务器选择** (推荐 AWS/GCP/阿里云)
- [ ] **PostgreSQL** 替代 SQLite
- [ ] **Redis** 缓存/限流
- [ ] **域名 + HTTPS**
- [ ] **API 地址更新** → 前端 `EXPO_PUBLIC_API_URL`
- [ ] **RevenueCat Webhook 端点**
  ```
  POST /api/v1/webhooks/revenuecat
  ```

### 4. 认证系统
- [ ] **Apple Sign In** 
  - [ ] App Store Connect 启用
  - [ ] 后端验证 identityToken
- [ ] **Google Sign In** (可选，iOS 可先不做)
- [ ] **Firebase Auth** 集成确认

### 5. 法律合规
- [ ] **隐私政策页面** - 公网 URL
- [ ] **服务条款页面** - 公网 URL
- [ ] **年龄验证** (已有，确认流程)
- [ ] **AI 生成内容声明** (已有)

---

## 🟡 P1 - 上线前建议完成

### 6. 支付流程测试
- [ ] TestFlight Sandbox 测试
  - [ ] 新订阅购买
  - [ ] 订阅续费
  - [ ] 订阅取消
  - [ ] 恢复购买
  - [ ] 终身会员购买
- [ ] RevenueCat Dashboard 确认事件同步

### 7. 推送通知
- [ ] **APNs 证书** 上传 Expo
- [ ] **Firebase Cloud Messaging** 配置
- [ ] 后端推送逻辑测试

### 8. 内容审核
- [ ] 确认成人内容仅限 VIP
- [ ] 测试年龄验证流程
- [ ] 添加内容举报功能 (Apple 要求)

### 9. 错误监控
- [ ] Sentry 集成 (前端 + 后端)
- [ ] Crash 报告收集

### 10. App 图标和启动图
- [ ] 确认 1024x1024 图标 ✅ (已生成)
- [ ] 启动屏幕适配各设备

---

## 🟢 P2 - 可延后/优化项

### 11. 性能优化
- [ ] 图片 CDN
- [ ] API 响应缓存
- [ ] 消息列表虚拟化

### 12. 用户体验
- [ ] 新手引导流程
- [ ] 角色开场白动画
- [ ] 打字机效果优化

### 13. 功能完善
- [ ] 长记忆系统
- [ ] 语音消息
- [ ] 图片生成

### 14. 运营功能
- [ ] 邀请码系统
- [ ] 关注社交媒体领金币
- [ ] 每日签到奖励

---

## 📋 上线 Checklist

### 提交前 24 小时
- [ ] TestFlight 最终测试
- [ ] 截图/描述最终确认
- [ ] 后端服务稳定运行
- [ ] RevenueCat 产品同步正常
- [ ] 隐私政策/服务条款可访问

### 提交审核
- [ ] `eas build --platform ios --profile production`
- [ ] `eas submit --platform ios`
- [ ] 准备审核备注 (解释 AI 功能/成人内容)
- [ ] 准备演示账号 (如需)

### 审核通过后
- [ ] 确认上架时间
- [ ] 监控 Crash 报告
- [ ] 准备应急回滚方案

---

## ⏱️ 时间估算

| 阶段 | 预估时间 |
|------|----------|
| P0 阻断项 | 3-5 天 |
| P1 建议项 | 2-3 天 |
| 审核等待 | 1-7 天 |
| **总计** | **1-2 周** |

---

## 🔗 相关资源

- [App Store Connect](https://appstoreconnect.apple.com)
- [RevenueCat Dashboard](https://app.revenuecat.com)
- [Expo EAS Build](https://expo.dev)
- [Apple App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)

---

## 📝 Notes

### 关于成人内容审核
Apple 对成人内容有严格限制：
1. 必须标记 17+ 年龄分级
2. 必须有年龄验证机制
3. 不能在 App Store 截图中展示
4. 建议在审核备注中说明

### RevenueCat vs 自建验证
已切换到 RevenueCat，优势：
- 自动处理收据验证
- 跨平台统一
- Dashboard 分析
- 减少后端复杂度

### 后端部署建议
最简方案：
1. Railway / Render (一键部署)
2. 或 DigitalOcean App Platform
3. PostgreSQL + Redis 托管服务
