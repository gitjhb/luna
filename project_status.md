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
| RevenueCat 连接 | LAUNCH_TODO | JHB | ⏳ 待配置 |

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

- (空)

---

## 📝 Recent Changes

### 2026-02-23
- ✅ Fix: `save_semantic_memory` 重复参数
- ✅ Fix: `INFO_PATTERNS` key 不匹配 (name → user_name)
- ✅ Feat: 添加 `/api/v1/chat/debug` endpoint (God Mode 支持)
- ✅ Fix: 正则优化，避免从问句提取名字
- ✅ Test: `tests/test_memory_system.py` (5 tests passing)
- ✅ Feat: 主动消息系统 (从 Mio 移植)
- ✅ Test: `tests/test_proactive_message.py` (12 tests passing)
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

*Last updated: 2026-02-23 00:35 PST*
