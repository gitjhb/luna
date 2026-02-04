# TODO - AI Companion Platform

## 高优先级

### 🔐 计费系统并发安全
**问题：** 当前 SQLite mock 模式下的积分扣减可能有并发问题（充值加钱 + 使用扣钱同时发生）

**方案：**
1. **SQLite 生产环境（小规模）**
   - 开启 WAL (Write-Ahead Log) 模式：`PRAGMA journal_mode=WAL;`
   - 使用 `BEGIN IMMEDIATE` 事务（写锁）
   - 单进程部署，避免多进程写入

2. **PostgreSQL 生产环境（推荐）**
   - 使用 `SELECT ... FOR UPDATE` 行级锁
   - 已在 `billing_middleware_complete.py` 中实现
   - 支持真正的 ACID 事务

3. **Redis + Lua 脚本（高并发场景）**
   - 原子操作：`WATCH` + `MULTI/EXEC`
   - 或用 Lua 脚本保证原子性
   - 适合超高 QPS 场景

**参考实现：** `backend/app/middleware/billing_middleware_complete.py`
- 已有完整的原子扣费逻辑（PostgreSQL）
- 三层积分扣费优先级：daily_free → purchased → bonus
- Token bucket 限流

**行动项：**
- [ ] 生产部署时切换到 PostgreSQL
- [ ] 确保 `billing_middleware_complete.py` 完全集成
- [ ] 添加积分操作的审计日志
- [ ] 压测并发扣费场景

---

## 中优先级

### 📱 前端对接
- [ ] 更新前端 API 地址指向新后端
- [ ] 实现真正的 Google/Apple OAuth
- [ ] 对接 Stripe 支付

### 🎤 语音功能
- [ ] 配置真实的豆包 TTS API key
- [ ] 添加 STT (语音转文字) 功能
- [ ] 语音消息缓存优化

### 🖼️ 图片生成
- [ ] 配置 OpenAI API key
- [ ] 添加图片审核
- [ ] 生成图片的 CDN 存储

---

## 高优先级（核心体验）

### 🧠 长记忆系统 (Clawdbot 式)
**设计文档：** `docs/MEMORY_ARCHITECTURE.md`

**数据层：**
- [ ] 创建 `user_memories` 表（content, category, importance, embedding_id）
- [ ] 创建 `user_todos` 表（content, due_at, remind_at）
- [ ] 配置向量数据库 per-user namespace

**记忆提取：**
- [ ] 实现 `extract_memories()` - 对话后用 LLM 提取关键信息
- [ ] 异步后台处理，不阻塞响应
- [ ] 分类：preference/fact/event/person/todo

**记忆召回：**
- [ ] 实现 `recall_memories()` - 语义搜索 top-5 相关记忆
- [ ] 注入 system prompt（限制 ~200 tokens）
- [ ] 缓存热门记忆减少向量查询

**TODO/提醒：**
- [ ] 从对话自动识别 TODO（"帮我记一下周五开会"）
- [ ] Celery 定时任务检查提醒
- [ ] 推送通知（App/Telegram）

**用户管理：**
- [ ] API: GET /memories - 查看自己的记忆
- [ ] API: DELETE /memories/{id} - 删除记忆
- [ ] 自动清理 90 天未召回的低重要性记忆

---

## 低优先级

### 📊 RAG 优化
- [ ] 配置 Pinecone 生产环境（比 ChromaDB 快）
- [ ] Embedding 批量处理降成本
- [ ] 记忆压缩/合并（相似记忆去重）

### 📊 监控
- [ ] 集成 Prometheus 指标
- [ ] Sentry 错误追踪
- [ ] 用户行为分析

---

*最后更新: 2026-01-28*

## 约会系统优化

### 💡 付费延长剧情 (2026-02-03)
- **场景**：Phase 5/5 结局前，用户意犹未尽
- **方案**：提供"花 10 月石看下一章"选项，延长约会剧情
- **实现思路**：
  - 在 finale 阶段显示两个按钮："查看结算" / "💎 继续剧情 (10月石)"
  - 点击继续后生成额外的 bonus stage（第6章、第7章...）
  - 可设置上限（最多延长2-3章）
- **优先级**：中
