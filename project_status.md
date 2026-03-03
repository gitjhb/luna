# Project Status: Luna

> **Source of Truth** — Nikki 和所有 sub-agents 的工作参考
> 
> JHB 只做验收和反馈，开发和验证由 AI 完成

---

## 🎯 Current Sprint

### Active Tasks
- [x] **Memory 基础功能** — ✅ 已修复并验证
  - `/api/v1/chat/debug` endpoint 已创建
  - God Mode 可正常存储/检索记忆

- [x] **主动消息系统** — ✅ 从 Mio 移植完成
  - 早安/晚安/想念消息
  - 角色专属模板
  - 冷却机制 + 亲密度门槛
  - 12 tests passing
  
- [ ] **Memory 订阅限制** — Free plan 不存/提取记忆
  - 状态: 待实现订阅检查
  - 文件: `chat_pipeline_v4.py`, `memory_integration_service.py`

### Blocked
- [ ] **App Store 上线** — 等待 IAP 产品配置
  - 详见: `LAUNCH_TODO.md`

---

## 📁 Repos & Structure

| 组件 | 路径 | 用途 | 状态 |
|------|------|------|------|
| **Backend** | `projects/luna/backend` | FastAPI 主服务 | ✅ Active |
| **Frontend** | `projects/luna/frontend` | Expo App | ✅ Active |
| **Website** | `projects/luna-web` | Vercel 官网 | ✅ Active |
| **Mio** | `projects/mio` | Telegram 轻量版 | ✅ Active |
| **luna-telegram** | `projects/luna-telegram` | ❓ 待确认是否需要 | ⚠️ 可能删除 |
| **luna-prod** | `projects/luna-prod` | ❓ 待确认 | ⚠️ 可能删除 |

---

## 📋 TODO Index (合并视图)

### 🔴 P0 - 阻断项
| Task | Source | Owner | Status |
|------|--------|-------|--------|
| App Store IAP 配置 | LAUNCH_TODO | JHB | ⏳ 待配置 |
| PostgreSQL 部署 | LAUNCH_TODO | Nikki | ⏳ 待部署 |
| RevenueCat 连接 | LAUNCH_TODO | JHB | ✅ 已配置 |
| Stripe Web 支付 | 2026-02-28 | JHB | ✅ 已配置 |
| 移除 fb- 前缀 | 2026-03-02 | JHB+Nikki | ✅ 完成 |
| Email 认证 | 2026-03-03 | Nikki | ✅ 代码完成 (待启用 Firebase) |

### 🟡 P1 - 核心功能
| Task | Source | Status |
|------|--------|--------|
| Memory 订阅限制 | TODO | 🔧 In Progress |
| 计费并发安全 | TODO | ⏳ 待 PostgreSQL |
| Apple/Google OAuth | LAUNCH_TODO | ⏳ 待测试 |

### 🟢 P2 - 增强功能
| Task | Source | Status |
|------|--------|--------|
| 长记忆系统 (RAG) | TODO | 📐 已设计 |
| 语音 TTS/STT | TODO | ⏳ 待配置 |
| 图片生成 | TODO | ⏳ 待配置 |
| 付费延长约会剧情 | TODO | 💡 Idea |

---

## 📐 Design Docs

| 文档 | 路径 | 内容 |
|------|------|------|
| **⭐ 产品战略** | `docs/PRODUCT_STRATEGY.md` | 北极星：从工具→游戏，护城河策略 |
| **亲密度系统** | `relationship_level.md` | 5阶段, 50级, XP公式 |
| **Chat 架构** | `backend/docs/CHAT_SYSTEM.md` | V4 Pipeline 流程图 |
| **Intent Protocol** | `backend/docs/Luna_Intent_Protocol.md` | 意图识别规范 |
| **Memory V2** | `backend/app/services/memory_system_v2/README.md` | 三层记忆架构 |
| **Emotion V2** | `backend/app/services/emotion_engine_v2/README.md` | 双轴情感系统 |
| **约会系统** | `DATING_SYSTEM_UPGRADE_SUMMARY.md` | Phase 1-5 剧情 |

---

## 💡 Ideas Inbox

> JHB 的新想法写这里，Nikki 会定期整理到 Design Docs

- [ ] **统一 Luna 人设**：Telegram 和 App 的 Luna 性格要一致
  - 当前：App = 诗意神秘夜精灵，Mio Bot = 22岁傲娇女友
  - 需要：确认用户用的是哪个 bot，统一体验

---

## 📝 Recent Changes

### 2026-03-03
- ✅ **代码重构: 移除 fb- 前缀** — JHB 完成
  - auth.py: user_id = firebase_uid (无前缀)
  - auth_middleware.py: 接受 Firebase UID
  - stripe_service.py: metadata 用 firebase_uid
  - emotion.py: 移除 fb- bypass
- ✅ **数据库迁移** — 修复用户 ID
  - `fb-hdND1zeZOkdP74SdypFmmuF0SA03` → `hdND1zeZOkdP74SdypFmmuF0SA03`
  - 添加 `BASIC` 到 subscriptiontier enum
  - 修复 users 表 is_subscribed + subscription_tier
  - 创建 user_subscriptions 记录
- ✅ **Deploy: GCP Cloud Run** — `luna-backend-00077-cc6`
- ✅ **Stripe Metadata 更新** — 订阅和 Customer 改成 firebase_uid
- ✅ **Luna Web: Email 认证** — 新功能
  - 添加 Email/Password 登录/注册
  - 添加 Forgot Password
  - ⚠️ 需确认 Firebase Console 启用 Email/Password

### 2026-03-02
- ✅ **Fix: Stripe Customer ID 关联** — 关键支付Bug修复
  - 问题：用户用不同邮箱付款，Customer Portal 找不到 subscription
  - 修复：User 表加 `stripe_customer_id` 字段，webhook 时保存
  - 新增 `get_customer_for_user()` 方法，优先用存储的 ID
  - 6 个测试用例全部通过
  - Git: `a2489b5` fix: link Stripe customer ID to user on checkout completion
- ✅ **Deploy: GCP Cloud Run** — `luna-backend-00073-q8w`
  - 遵循新部署规矩：`--no-traffic` → 验证 → 切流量
- 📝 **TODO: Stripe Customer 主动创建** — JHB提出更好方案
  - 在用户注册时创建 Stripe Customer，而不是等到 checkout
  - 好处：customer 从一开始就绑定 user_id

### 2026-03-01 (工作完成于 02-28)
- ✅ **Luna Web 角色资料页** — 新功能
  - 新增 `/character/:id` 路由
  - 显示情绪、亲密度、统计数据
  - 首页角色卡片点击打开侧边栏抽屉（不跳转）
  - 创建 `CharacterProfileDrawer.tsx` 组件
- ✅ **Luna Web 聊天样式** — 括号内文字斜体+暗色
  - `formatMessageContent()` 函数处理动作/心理描写
- ✅ **Luna Web 聊天缓存** — 极速加载
  - 创建 `chatCache.ts` (类似 iOS Zustand persist)
  - localStorage 缓存消息，刷新不丢失
  - URL 带 char 参数时先读缓存再后台同步
- ✅ **Mio Beta 全面开放** — `BETA_MODE=false`
  - 所有用户可访问，不再有50人限制

### 2026-02-28
- ✅ **RevenueCat Web Billing** 配置完成
  - Web App: `appcbf181fccb`
  - Stripe Sandbox: `acct_1T0dFwBGtpEcBypW`
  - Webhook: "Luna BE google cloud run webhook" - Active
  - Entitlements & Products 已配置
- ✅ **Stripe Payment Links** 创建
  - Plus $9.90: `https://buy.stripe.com/test_14A9ASeCT1a9diw0qu2Fa01`
  - Soulmate $19.90: `https://buy.stripe.com/test_9B65kCamDf0ZguI7SW2Fa00`
- 🐛 **Bug: Firebase Auth 登录失败** — 待修复
  - 手机上 popup 打开后无响应
  - 需检查 Authorized Domains 和 Vercel 环境变量

### 2026-02-27
- ✅ **luna-web 订阅按钮** 改进
  - 未登录时显示 "Sign In to Subscribe"
  - 集成后端 Checkout API

### 2026-02-26
- ✅ **UI: DateSceneModal Cyberpunk 改造** — `components/DateSceneModal.tsx`
  - +按钮添加 Alert 确认弹窗，避免误触扣费
  - 选项按钮改为深黑底+紫色霓虹边框 (`#8B5CF6`)
  - 特殊选项用青色霓虹 (`#00D4FF`)
  - 状态栏、BottomSheet、输入框全部HUD风格
- 🐛 **Bug: 约会记忆保存失败** — 待排查
  - 现象：显示"回忆已保存"但 EventMemory 表没数据
  - 可能原因：`save_story_direct()` 静默失败
- 📝 **TODO: chat页面弹窗UI统一** — `[characterId].tsx`
  - `levelUpContent` 样式还是旧风格，需改为Cyberpunk

### 2026-02-24
- ✅ **Fix: 约会结束后发送消息** — `interactive_date_service.py`
  - 添加 `_send_post_date_message()` 方法
  - 根据结局类型生成角色反馈消息
- ✅ **Fix: Memory V2 集成 EventMemory** — `memory_manager.py`
  - 发现问题：memory_system_v2 完全没读取 EventMemory 表
  - 添加 `_get_event_memories()` 方法
  - AI 对话时能看到约会/礼物事件记忆
- ✅ **Feat: 设置页面语言切换** — `settings.tsx`
  - 实现完整的中英文切换功能
  - 与 i18n 系统集成
- ✅ **Deploy: GCP Cloud Run** — `luna-backend-00060-dt9`
- 📝 **TODO: Stripe + RevenueCat 集成**（Telegram 支付）

### 2026-02-23
- ✅ Fix: `save_semantic_memory` 重复参数
- ✅ Fix: `INFO_PATTERNS` key 不匹配 (name → user_name)
- ✅ Feat: 添加 `/api/v1/chat/debug` endpoint (God Mode 支持)
- ✅ Fix: 正则优化，避免从问句提取名字
- ✅ Test: `tests/test_memory_system.py` (5 tests passing)
- ✅ Feat: 主动消息系统 (从 Mio 移植)
- ✅ Test: `tests/test_proactive_message.py` (12 tests passing)
- ✅ Test: `tests/test_payment_system.py` (16 tests passing)
- 📝 建立 TEAM_NORMS.md 和 project_status.md

### 2026-02-22
- (待补充历史)

---

## 🔄 Workflow

```
JHB 提想法 → Ideas Inbox
     ↓
Nikki 整理 → Design Docs (如需设计)
     ↓
Nikki 实现 → TDD (测试先行)
     ↓
Nikki 验证 → 自测 + lint + type check
     ↓
Nikki 更新 → project_status.md + commit
     ↓
JHB 验收 → 反馈 / Done
```

---

*Last updated: 2026-03-03 03:00 PST*
