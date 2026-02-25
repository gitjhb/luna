# 记忆系统文档 (Memory System)

## 概述

Luna 的记忆系统是一个三层架构的先进记忆管理系统，模拟人类的记忆模式，包括语义记忆 (用户特征)、情节记忆 (重要事件) 和工作记忆 (短期上下文)。系统实现了智能记忆提取、存储、衰减和检索机制，让 AI 角色能够记住用户的个人信息、重要对话和情感历程，提供更加个性化和连贯的对话体验。

## 核心组件/文件

### 主要服务文件
- **`app/services/memory_system_v2/`** - V2 记忆系统目录
- **`app/services/memory_system_v2/memory_models.py`** (278行) - 数据库模型定义
- **`app/services/memory_system_v2/memory_manager.py`** - 记忆管理核心逻辑
- **`app/services/memory_system_v2/memory_prompts.py`** - 记忆提示词模板
- **`app/services/memory_integration_service.py`** - 记忆集成服务

### 向量存储组件
- **`app/services/vector_service.py`** - 向量数据库服务 (Pinecone)
- **`app/services/embedding_service.py`** - 文本嵌入服务

### 数据库表
- `semantic_memories` - 语义记忆 (用户特征)
- `episodic_memories` - 情节记忆 (重要事件)
- `memory_extraction_logs` - 记忆提取日志
- `embedding_vectors` - 向量存储索引

## 数据流和记忆架构

### 三层记忆模型
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 工作记忆 (Working Memory)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ↑ 当前对话上下文 (最近 5-10 条消息)
   ↑ 临时状态信息
   ↑ 即时反应和响应
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  
🧠 语义记忆 (Semantic Memory)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ↑ 用户个人信息 (姓名、生日、职业)
   ↑ 偏好和兴趣 (喜欢、不喜欢、爱好)  
   ↑ 性格特征和沟通风格
   ↑ 关系信息 (昵称、重要日期)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💭 情节记忆 (Episodic Memory)  
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ↑ 重要事件 (表白、争吵、里程碑)
   ↑ 情感历程和关键对话
   ↑ 特殊时刻和纪念日
   ↑ 礼物历史和感谢回忆
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 记忆处理流程
```
用户消息输入
    ↓
记忆提取阶段 (get_memory_context_for_chat)
    ↓
┌─语义记忆检索────┬─情节记忆搜索────┬─工作记忆整理─┐
│  用户偏好信息    │  相关事件检索    │  近期对话    │
│  个人特征       │  情感状态历史    │  上下文整理   │
│  关系状态       │  重要时刻       │  即时状态    │
└────────────────┴────────────────┴─────────────┘
    ↓
记忆提示词生成 (generate_memory_prompt)
    ↓
注入 LLM 系统提示词
    ↓
AI 响应生成
    ↓
记忆存储阶段 (process_conversation_for_memory)
    ↓
┌─新信息提取──┬─事件检测──┬─记忆更新──┬─衰减处理─┐
│ 个人信息更新 │ 重要事件   │ 强化相关   │ 弱化无关  │
│ 偏好学习    │ 情感变化   │ 记忆关联   │ 清理冗余  │
│ 特征识别    │ 里程碑     │ 权重调整   │ 存储优化  │
└───────────┴─────────┴─────────┴─────────┘
```

## 关键函数说明

### 记忆上下文检索

#### `get_memory_context_for_chat(user_id, character_id, current_message, working_memory)`
**位置**: `app/services/memory_integration_service.py`

为当前对话检索相关的记忆上下文：

**检索策略**:
1. **语义记忆加载**: 获取用户的基本信息和偏好
2. **情节记忆搜索**: 基于当前消息的向量相似度搜索
3. **时间权重**: 结合记忆重要性和时间衰减
4. **工作记忆整合**: 合并短期对话上下文

**返回结构**:
```python
@dataclass
class MemoryContext:
    user_profile: Optional[UserProfile]          # 用户画像
    relevant_episodes: List[EpisodicMemory]      # 相关事件记忆
    recent_episodes: List[EpisodicMemory]        # 最近事件记忆  
    working_memory: List[Dict]                   # 工作记忆
    total_memories: int                          # 记忆总数
```

### 记忆提示词生成

#### `generate_memory_prompt(memory_context, intimacy_level, current_query)`
**位置**: `app/services/memory_integration_service.py`

将记忆上下文转换为 LLM 可理解的提示词：

**生成策略**:
```python
def generate_memory_prompt(memory_context, intimacy_level, current_query):
    sections = []
    
    # 用户画像部分
    if memory_context.user_profile:
        profile_prompt = f"""
=== 🧑‍💼 用户信息 ===
• 姓名: {user_profile.user_name or '未知'}
• 生日: {user_profile.birthday or '未知'}
• 职业: {user_profile.occupation or '未知'}
• 喜好: {', '.join(user_profile.likes or [])}
• 性格: {', '.join(user_profile.personality_traits or [])}
"""
        sections.append(profile_prompt)
    
    # 重要事件记忆
    if memory_context.relevant_episodes:
        events_prompt = "=== 💭 相关回忆 ===\n"
        for episode in memory_context.relevant_episodes:
            events_prompt += f"• {episode.summary} (重要性: {episode.importance}/4)\n"
        sections.append(events_prompt)
    
    return "\n".join(sections)
```

### 对话记忆处理

#### `process_conversation_for_memory(user_id, character_id, user_message, assistant_response, context)`
**位置**: `app/services/memory_integration_service.py`

从对话中提取和存储新记忆：

**处理流程**:
1. **信息提取**: 使用 LLM 分析对话中的新信息
2. **事件检测**: 识别重要事件和情感变化
3. **记忆分类**: 区分语义信息和情节记忆
4. **重要性评估**: 评估记忆的保存价值 (1-4级)
5. **存储更新**: 更新或创建新的记忆记录

**提取提示词模板**:
```python
EXTRACTION_PROMPT = """
分析以下对话，提取用户的新信息：

对话:
用户: {user_message}
AI: {assistant_response}

请提取:
1. 个人信息 (姓名、年龄、职业、生日等)
2. 偏好信息 (喜欢、不喜欢、兴趣爱好)
3. 重要事件 (表白、争吵、纪念日等)
4. 情感变化 (心情、关系状态)

输出JSON格式...
"""
```

## 记忆类型详解

### 1. 语义记忆 (Semantic Memory)

**数据模型**: `app/services/memory_system_v2/memory_models.py:15`

```python
class SemanticMemoryModel(Base):
    user_name = Column(String(64))               # 用户姓名
    birthday = Column(String(32))                # 生日
    occupation = Column(String(128))             # 职业
    likes = Column(JSON, default=[])             # 喜好列表
    dislikes = Column(JSON, default=[])          # 不喜欢的
    personality_traits = Column(JSON, default=[]) # 性格特征
    pet_names = Column(JSON, default=[])         # 昵称列表
    important_dates = Column(JSON, default={})   # 重要日期
    sensitive_topics = Column(JSON, default=[])  # 敏感话题
```

**存储策略**:
- 每个用户-角色对维护一条记录
- 增量更新，不覆盖已有信息
- 支持数组类型的累积 (喜好、特征等)
- 实时更新和查询

### 2. 情节记忆 (Episodic Memory)

**数据模型**: `app/services/memory_system_v2/memory_models.py:55`

```python
class EpisodicMemoryModel(Base):
    event_type = Column(String(32))              # 事件类型
    summary = Column(Text)                       # 事件摘要 
    key_dialogue = Column(JSON, default=[])      # 关键对话
    emotion_state = Column(String(32))           # 当时情绪
    importance = Column(Integer, default=2)      # 重要性 1-4
    strength = Column(Float, default=1.0)        # 记忆强度
    recall_count = Column(Integer, default=0)    # 回忆次数
```

**事件类型分类**:
```python
EVENT_TYPES = {
    "confession": "表白",
    "first_kiss": "初吻", 
    "fight": "争吵",
    "makeup": "和好",
    "gift": "送礼",
    "milestone": "里程碑",
    "date": "约会",
    "anniversary": "纪念日",
    "personal_share": "个人分享",
}
```

### 3. 工作记忆 (Working Memory)

**实现方式**: 动态组装，不持久化存储

**组成部分**:
- 当前对话上下文 (最近 5-10 条消息)
- 会话级临时状态 (情绪、场景)
- 即时反应信息 (礼物、事件触发)

## 记忆提取和存储

### LLM 辅助提取

使用专门的记忆提取提示词模板：

```python
MEMORY_EXTRACTION_TEMPLATES = {
    "personal_info": """
从对话中提取用户的个人信息：
- 基本信息：姓名、年龄、生日、职业、居住地
- 关系信息：称呼偏好、重要人物、家庭状况
- 联系方式：社交账号、特殊节日
输出格式：JSON
""",
    
    "preferences": """
识别用户的偏好信息：
- 喜好：食物、音乐、电影、活动、颜色等
- 厌恶：不喜欢的事物、过敏、禁忌
- 兴趣：爱好、特长、关注领域
输出格式：JSON数组
""",
    
    "events": """
检测重要事件：
- 情感事件：表白、分手、和好、争吵
- 里程碑：第一次、纪念日、成就
- 特殊时刻：生日、节日、重要决定
评估重要性：1(一般) 到 4(极重要)
"""
}
```

### 智能存储策略

**去重机制**:
- 语义相似度检查，避免重复存储
- 关键词重叠检测
- 时间窗口内的事件合并

**重要性评估**:
```python
def calculate_importance(event_type, emotion_intensity, intimacy_level):
    base_importance = {
        "confession": 4,
        "fight": 3, 
        "gift": 2,
        "casual": 1
    }.get(event_type, 2)
    
    # 情感强度调整
    emotion_modifier = emotion_intensity * 0.5
    
    # 亲密度调整
    intimacy_modifier = min(intimacy_level / 50, 1.0)
    
    return min(4, base_importance + emotion_modifier + intimacy_modifier)
```

## 记忆衰减机制

### 时间衰减算法

**Ebbinghaus 遗忘曲线**: 基于心理学的记忆衰减模型

```python
def calculate_memory_strength(initial_strength, days_ago, importance, recall_count):
    # 基础衰减 (指数衰减)
    time_decay = math.exp(-days_ago / (importance * 30))  # 重要记忆衰减更慢
    
    # 回忆强化
    recall_bonus = 1 + (recall_count * 0.1)
    
    # 重要性保护
    importance_protection = 0.2 + (importance / 4) * 0.8
    
    final_strength = initial_strength * time_decay * recall_bonus * importance_protection
    
    return max(0.1, min(1.0, final_strength))  # 限制在 [0.1, 1.0] 范围
```

### 自动清理机制

**位置**: `app/services/memory_system_v2/memory_models.py:265`

```python
async def delete_weak_memories(
    user_id: str,
    character_id: str, 
    min_strength: float = 0.3,
    keep_important: bool = True,
):
    # 删除强度低于阈值的记忆
    # 保护重要性 >= 3 的记忆不被删除
    # 定期执行以维护存储效率
```

## 与聊天的集成

### 聊天流程集成

**记忆检索阶段** (聊天开始):
1. 加载用户语义记忆 
2. 向量搜索相关情节记忆
3. 构建记忆提示词
4. 注入 LLM 系统提示

**记忆存储阶段** (聊天结束):
1. 分析对话内容
2. 提取新信息和事件
3. 更新语义记忆
4. 创建情节记忆
5. 调整记忆强度

### 上下文增强

**免费用户**: 基础记忆支持
- 基本的语义记忆 (姓名、生日)
- 最近 3 个重要事件
- 简化的记忆提示

**付费用户**: 完整记忆体验
- 完整语义记忆档案
- 向量搜索历史事件
- 详细记忆上下文
- 个性化记忆分析

## 配置项

### 记忆存储配置
```python
MAX_EPISODIC_MEMORIES = 1000        # 每用户最大情节记忆数
MIN_IMPORTANCE_THRESHOLD = 2        # 最小重要性阈值
MEMORY_DECAY_INTERVAL = 7          # 记忆衰减检查间隔 (天)
VECTOR_SEARCH_LIMIT = 5            # 向量搜索结果数量
```

### 向量数据库配置
```python
PINECONE_INDEX_NAME = "luna-memories"
EMBEDDING_DIMENSION = 1536          # OpenAI embedding 维度
SIMILARITY_THRESHOLD = 0.7          # 相似度阈值
```

### 记忆提取配置
```python
EXTRACTION_MODEL = "grok-beta"      # 记忆提取使用的模型
EXTRACTION_TEMPERATURE = 0.3       # 低温度确保准确性
BATCH_EXTRACTION_SIZE = 10          # 批量提取对话数量
```

## 与其他系统的关系

### 1. 亲密度系统
- **记忆深度**: 亲密度越高，记忆越详细
- **隐私界限**: 低亲密度时避免过度个人化
- **解锁机制**: 特定等级解锁深度记忆功能

### 2. 情绪系统
- **情感记忆**: 记录重要的情绪变化
- **情绪上下文**: 回忆时考虑当时的情绪状态
- **触发机制**: 特定记忆可能触发情绪反应

### 3. 礼物系统
- **礼物记忆**: 记录送礼历史和感谢
- **偏好学习**: 从礼物反应中学习用户偏好
- **纪念价值**: 特殊礼物成为重要记忆

### 4. 约会系统
- **约会记录**: 每次约会都创建情节记忆
- **地点偏好**: 学习用户喜欢的约会场所
- **里程碑**: 首次约会等重要时刻标记

## TODO/改进建议

### 短期优化
1. **记忆可视化**: 为用户提供记忆管理界面
2. **手动编辑**: 允许用户修正记忆信息
3. **记忆导出**: 支持记忆数据的导入/导出

### 中期扩展
1. **多模态记忆**: 支持图片、语音记忆
2. **记忆分享**: 用户间的记忆交换功能
3. **记忆分析**: 提供用户关系发展报告

### 长期愿景
1. **预测记忆**: 基于历史预测重要事件
2. **情感地图**: 可视化情感发展历程
3. **记忆传承**: 跨角色的记忆继承机制
4. **集体记忆**: 社区共享的记忆体验

### 技术优化
1. **向量优化**: 更高效的向量搜索算法
2. **缓存策略**: 热点记忆的智能缓存
3. **并行处理**: 记忆提取的异步处理
4. **压缩算法**: 记忆数据的智能压缩

通过持续的记忆系统优化，Luna 将能够提供越来越智能和个性化的 AI 伴侣体验，让用户感受到真实的关系成长和情感连接。