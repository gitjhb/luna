# Luna 记忆系统 v2 修复总结

## 问题诊断

记忆系统"没通"的原因：
1. **数据库表未创建** - `semantic_memories`, `episodic_memories` 表不存在
2. **未集成到聊天服务** - `chat_service.py` 完全没有导入或使用记忆系统
3. **memory_manager 未初始化** - 单例没有传入 db_service 和 llm_service

## 修复内容

### 1. 创建数据库模型 (`app/models/database/memory_v2_models.py`)
- 使用现有的 `ChatBase` 而非独立的 Base
- 定义 `SemanticMemory`, `EpisodicMemory`, `MemoryExtractionLog` 表
- 表会在服务启动时自动创建

### 2. 更新数据库初始化 (`app/core/database.py`)
- 导入 `memory_v2_models` 确保表被创建

### 3. 创建记忆数据库服务 (`app/services/memory_db_service.py`)
- 实现 MemoryManager 需要的 `db_service` 接口
- 使用 SQLAlchemy async session 进行 CRUD 操作

### 4. 创建记忆集成服务 (`app/services/memory_integration_service.py`)
- 提供简洁的 API 给 chat_service 使用
- `get_memory_context_for_chat()` - 获取记忆上下文
- `process_conversation_for_memory()` - 处理对话提取记忆
- `generate_memory_prompt()` - 生成记忆 prompt

### 5. 集成到聊天服务 (`app/services/chat_service.py`)
- Step 3.6: 在 LLM 调用前获取记忆上下文并加入 system prompt
- Step 8.5: 在回复后处理对话提取新记忆

## 数据库表

```sql
-- 语义记忆（用户档案）
CREATE TABLE semantic_memories (
    id INTEGER PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    character_id VARCHAR(64) NOT NULL,
    user_name VARCHAR(64),
    user_nickname VARCHAR(64),
    birthday VARCHAR(32),
    occupation VARCHAR(128),
    location VARCHAR(128),
    likes JSON DEFAULT '[]',
    dislikes JSON DEFAULT '[]',
    interests JSON DEFAULT '[]',
    personality_traits JSON DEFAULT '[]',
    communication_style VARCHAR(64),
    relationship_status VARCHAR(32),
    pet_names JSON DEFAULT '[]',
    important_dates JSON DEFAULT '{}',
    shared_jokes JSON DEFAULT '[]',
    sensitive_topics JSON DEFAULT '[]',
    created_at DATETIME,
    updated_at DATETIME,
    UNIQUE (user_id, character_id)
);

-- 情节记忆（重要事件）
CREATE TABLE episodic_memories (
    id INTEGER PRIMARY KEY,
    memory_id VARCHAR(32) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    character_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    summary TEXT NOT NULL,
    key_dialogue JSON DEFAULT '[]',
    emotion_state VARCHAR(32),
    importance INTEGER DEFAULT 2,
    strength FLOAT DEFAULT 1.0,
    recall_count INTEGER DEFAULT 0,
    last_recalled DATETIME,
    created_at DATETIME
);
```

## 测试方法

### 1. 验证表已创建
```bash
cd backend
sqlite3 data/app.db ".tables" | grep -E "semantic|episodic"
# 应该看到: episodic_memories  semantic_memories
```

### 2. Python 测试
```python
import asyncio
from app.core.database import init_db
from app.services.memory_db_service import memory_db_service

async def test():
    await init_db()
    
    # 保存语义记忆
    await memory_db_service.save_semantic_memory(
        user_id="test-user",
        character_id="test-char",
        data={"user_name": "小明", "likes": ["猫", "动漫"]}
    )
    
    # 读取
    result = await memory_db_service.get_semantic_memory("test-user", "test-char")
    print(result)  # {'user_name': '小明', 'likes': ['猫', '动漫'], ...}

asyncio.run(test())
```

### 3. 通过 API 测试
发送聊天消息，查看日志中是否有 memory 相关输出：
```bash
tail -f server.log | grep -i memory
```

当用户说 "我叫小明，喜欢猫" 时，系统应该：
1. 提取语义记忆: `user_name=小明`, `likes=[猫]`
2. 下次对话时，AI 会知道用户叫小明、喜欢猫

## 工作流程

```
用户消息 ──► chat_completion()
               │
               ▼
        获取工作记忆（最近对话）
               │
               ▼
        获取记忆上下文 ◄── memory_integration_service
               │
               ▼
        生成记忆 prompt
               │
               ▼
        构建 system prompt
        (角色设定 + 情绪 + 记忆)
               │
               ▼
        调用 LLM
               │
               ▼
        存储消息
               │
               ▼
        处理对话提取记忆 ──► 更新 semantic_memories
               │              或创建 episodic_memories
               ▼
        返回响应
```

## 注意事项

1. **记忆提取是规则 + LLM 混合的**
   - 简单信息（名字、生日）用正则提取
   - 复杂事件（表白、吵架）可选择性使用 LLM 分析

2. **记忆衰减**
   - 需要设置定时任务调用 `apply_daily_decay()`
   - 重要记忆衰减慢，普通记忆衰减快
   - 被回忆时会强化记忆

3. **性能考虑**
   - 记忆操作是异步的，不会阻塞响应
   - 失败不会导致聊天失败（graceful degradation）
