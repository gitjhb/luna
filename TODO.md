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

## 低优先级

### 🧠 RAG 记忆系统
- [ ] 配置 Pinecone/ChromaDB 生产环境
- [ ] 优化 embedding 成本
- [ ] 添加记忆清理策略

### 📊 监控
- [ ] 集成 Prometheus 指标
- [ ] Sentry 错误追踪
- [ ] 用户行为分析

---

*最后更新: 2026-01-28*
