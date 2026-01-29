# Luna Frontend TODO

## ✅ Completed
- [x] Expo SDK 54 升级
- [x] 修复依赖版本冲突
- [x] 登录页面（mock 模式）
- [x] 角色列表页面
- [x] 聊天页面
- [x] 聊天历史页面
- [x] 个人中心页面
- [x] 底部 Tab 导航
- [x] 连接真实后端 API
- [x] 主题美化（深色 luxury 风格）

## 🔧 In Progress
- [ ] TypeScript 严格模式类型修复（LinearGradient）
- [ ] 角色头像（目前用占位图）

## 📋 TODO
### 高优先级
- [ ] Firebase 认证集成
- [ ] Apple Sign-In 实现
- [ ] Google Sign-In 实现
- [ ] Expo Push Notifications

### 中优先级
- [ ] 积分充值（RevenueCat/Stripe）
- [ ] 订阅功能
- [ ] 语音消息
- [ ] 图片生成展示

### 低优先级
- [ ] 离线缓存
- [ ] 消息搜索
- [ ] 角色收藏
- [ ] 分享功能

## 🐛 Known Issues
- TypeScript 严格模式下 LinearGradient colors 需要 tuple 类型（不影响运行）
- xcrun simctl 警告（无 iOS 模拟器环境）

## 📝 Notes
- Mock 模式：登录用 mock，其他 API 调用真实后端
- 后端地址：http://192.168.1.125:8000/api/v1
- Expo 端口：8081
