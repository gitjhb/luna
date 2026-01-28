# 记忆系统架构设计

## 核心理念

像 Clawdbot 一样：**不是记住所有对话，而是记住重要的事**。

用户说"我喜欢猫"→ 存入记忆
下次提到宠物 → 召回"用户喜欢猫" → 自然地融入回复

---

## 1. 数据结构

### 用户记忆表 (user_memories)
```sql
CREATE TABLE user_memories (
    memory_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    
    -- 记忆内容
    content TEXT NOT NULL,           -- "用户喜欢猫，养了一只叫小白的猫"
    category VARCHAR(50),            -- preference/fact/event/person/todo
    importance INT DEFAULT 5,        -- 1-10, 用于排序和清理
    
    -- 向量检索
    embedding_id VARCHAR(100),       -- Pinecone/ChromaDB 中的 ID
    
    -- 来源追踪
    source_session_id UUID,          -- 从哪个对话提取的
    source_message_id UUID,          -- 从哪条消息提取的
    
    -- 时间
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed_at TIMESTAMP,      -- 上次被召回的时间
    expires_at TIMESTAMP,            -- 可选：自动过期（用于临时提醒）
    
    INDEX idx_user_memories_user (user_id),
    INDEX idx_user_memories_category (user_id, category)
);
```

### 用户 TODO 表 (user_todos)
```sql
CREATE TABLE user_todos (
    todo_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    
    content TEXT NOT NULL,           -- "周五前完成报告"
    due_at TIMESTAMP,                -- 截止时间
    remind_at TIMESTAMP,             -- 提醒时间
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    
    -- 来源
    source_session_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_user_todos_user (user_id),
    INDEX idx_user_todos_due (user_id, due_at)
);
```

---

## 2. 记忆提取 (Memory Extraction)

每次对话后，后台异步提取值得记住的信息：

```python
async def extract_memories(messages: list[dict]) -> list[dict]:
    """用 LLM 从对话中提取记忆"""
    
    prompt = """从以下对话中提取值得长期记住的信息。

规则：
- 只提取有长期价值的：偏好、事实、重要事件、人物关系、待办事项
- 忽略闲聊、问候、临时性内容
- 每条记忆一句话概括
- 分类：preference(偏好)/fact(事实)/event(事件)/person(人物)/todo(待办)

对话：
{conversation}

返回 JSON 数组：[{"content": "...", "category": "...", "importance": 1-10}]
如果没有值得记住的，返回空数组 []"""
    
    # 用便宜的模型（gpt-4o-mini）
    response = await llm.chat(prompt)
    return json.loads(response)
```

**示例：**
```
用户: 我下周要去东京出差
助手: 好的，东京这个季节很舒服...

提取结果:
[{"content": "用户下周要去东京出差", "category": "event", "importance": 7}]
```

---

## 3. 记忆召回 (Memory Recall)

每次对话前，搜索相关记忆注入 context：

```python
async def recall_memories(user_id: str, current_message: str, top_k: int = 5) -> list[dict]:
    """语义搜索用户相关记忆"""
    
    # 1. Embed 当前消息
    query_embedding = await embed(current_message)
    
    # 2. 在用户的 namespace 中搜索
    results = await vector_db.search(
        namespace=f"user_{user_id}",
        embedding=query_embedding,
        top_k=top_k,
        filter={"user_id": user_id}
    )
    
    # 3. 格式化为 context
    return [
        {"content": r.content, "category": r.category, "relevance": r.score}
        for r in results
    ]

def build_memory_context(memories: list[dict]) -> str:
    """构建注入 prompt 的记忆上下文"""
    if not memories:
        return ""
    
    lines = ["[关于用户的相关记忆]"]
    for m in memories:
        lines.append(f"- {m['content']}")
    return "\n".join(lines)
```

---

## 4. System Prompt 模板

```python
SYSTEM_PROMPT = """你是 {character_name}，用户的专属 AI 伙伴。

{character_personality}

{memory_context}

重要指引：
- 如果记忆中有相关信息，自然地融入回复，但不要说"我记得你说过..."
- 保持人设一致
- 对用户的事情表现出真诚的关心
"""
```

---

## 5. TODO / 提醒系统

### 创建 TODO
```python
async def create_todo(user_id: str, content: str, due_at: datetime = None):
    """从对话中识别并创建 TODO"""
    
    todo_id = uuid4()
    await db.execute("""
        INSERT INTO user_todos (todo_id, user_id, content, due_at, remind_at)
        VALUES (?, ?, ?, ?, ?)
    """, todo_id, user_id, content, due_at, due_at - timedelta(hours=1))
    
    # 同时存入记忆，方便召回
    await add_memory(user_id, f"用户有待办事项：{content}", category="todo")
```

### 定时检查提醒 (Celery/Cron)
```python
@celery.task
async def check_reminders():
    """每分钟检查需要提醒的 TODO"""
    
    todos = await db.fetch("""
        SELECT * FROM user_todos 
        WHERE remind_at <= NOW() 
        AND is_completed = FALSE
        AND reminded = FALSE
    """)
    
    for todo in todos:
        await send_notification(
            user_id=todo.user_id,
            message=f"提醒：{todo.content}"
        )
        await db.execute("UPDATE user_todos SET reminded = TRUE WHERE todo_id = ?", todo.todo_id)
```

---

## 6. 存储架构

### 开发环境
```
SQLite + ChromaDB (本地)
- user_memories 表
- user_todos 表
- ChromaDB collection per user
```

### 生产环境
```
PostgreSQL + Pinecone (云端)
- user_memories 表（带 pgvector 可选）
- user_todos 表
- Pinecone namespace per user
```

### 向量存储策略
```python
# 每用户一个 namespace，隔离性好
namespace = f"user_{user_id}"

# 或者统一 namespace + metadata filter (更省成本)
filter = {"user_id": user_id}
```

---

## 7. 记忆管理

### 自动清理旧记忆
```python
@celery.task
async def cleanup_old_memories():
    """每天清理低重要性的旧记忆"""
    
    # 删除 90 天未被召回且重要性 < 5 的记忆
    await db.execute("""
        DELETE FROM user_memories 
        WHERE last_accessed_at < NOW() - INTERVAL '90 days'
        AND importance < 5
    """)
```

### 用户手动管理
```python
# API: GET /api/v1/memories
# 用户可以查看/编辑/删除自己的记忆

@router.get("/memories")
async def list_memories(user_id: str, category: str = None):
    return await db.fetch(
        "SELECT * FROM user_memories WHERE user_id = ? ORDER BY created_at DESC",
        user_id
    )

@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str, user_id: str):
    # 同时删除向量库中的记录
    await vector_db.delete(namespace=f"user_{user_id}", id=memory_id)
    await db.execute("DELETE FROM user_memories WHERE memory_id = ?", memory_id)
```

---

## 8. Token 成本控制

| 操作 | 成本 | 优化策略 |
|------|------|----------|
| 记忆提取 | ~100 tokens/次 | 用 gpt-4o-mini，批量处理 |
| Embedding | ~20 tokens/条 | text-embedding-3-small ($0.02/1M) |
| 记忆注入 | ~100-200 tokens | 限制 top-5，总字数 < 500 |
| 召回搜索 | 免费 | 向量检索本身不消耗 LLM tokens |

**关键：召回 5 条记忆 vs 塞 100 条历史 = 省 10x tokens**

---

## 9. 完整对话流程

```
1. 用户发消息 "周五去东京有什么推荐？"
2. 召回记忆 → 找到 "用户下周要去东京出差"
3. 构建 prompt:
   - System: 角色人设 + [记忆：用户下周要去东京出差]
   - History: 最近 5 条消息
   - User: 周五去东京有什么推荐？
4. LLM 生成回复 → "出差之余也想逛逛对吧？东京这几个地方..."
5. 后台提取 → 无新记忆
6. 扣减积分
```

---

*这就是 Clawdbot 式的记忆体验：像老朋友一样记得你说过的事。*
