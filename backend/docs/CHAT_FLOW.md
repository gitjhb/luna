# 聊天流程系统文档 (Chat Flow System)

## 概述

Luna 的聊天流程系统是一个复杂的多层架构，支持 RAG 记忆检索、情绪分析、内容审核、流式响应等功能。系统采用三层架构设计：L1 感知层 (Perception) → 中间件逻辑层 (Game Engine) → L2 执行层 (Generation)，同时提供 V4.0 单次调用优化管道作为高性能替代方案。

## 核心组件/文件

### 主要 API 文件
- **`app/api/v1/chat.py`** (1356行) - 主要聊天 API 路由
- **`app/services/chat_service.py`** (1294行) - 聊天服务核心逻辑
- **`app/services/chat_repository.py`** - 消息存储和检索

### 关键服务组件
- **`app/services/llm_service.py`** - LLM 调用服务 (Grok API)
- **`app/services/perception_engine.py`** - L1 感知分析引擎
- **`app/services/game_engine.py`** - 中间件游戏逻辑引擎
- **`app/services/prompt_builder.py`** - 动态提示词构建
- **`app/services/v4/chat_pipeline_v4.py`** - V4.0 优化管道

### 数据库表
- `chat_sessions` - 聊天会话
- `chat_messages` - 消息记录
- `embedding_vectors` - 向量存储 (RAG)

## 数据流和完整聊天流程

### 标准三层架构流程 (Legacy Mode)
```
用户消息输入
    ↓
API 接收和验证 (chat.py:455)
    ↓
获取会话信息和角色配置
    ↓
体力系统检查 (非阻塞)
    ↓
重复消息检测
    ↓
========== L1 感知层 ==========
当前情绪状态加载 → 消息意图分析 → 安全检查 → 难度评级
    ↓
========== 中间件逻辑层 ==========
情绪引擎更新 → 亲密度检查 → 游戏规则验证 → 状态效果处理
    ↓
========== L2 执行层 ==========
记忆上下文检索 → 系统提示词构建 → LLM 调用 → 响应生成
    ↓
消息存储 → 亲密度 XP 奖励 → 统计记录 → 返回响应
```

### V4.0 单次调用管道流程
```
用户消息输入
    ↓
前置计算 (记忆、情绪、亲密度状态)
    ↓
单次 LLM 调用 (所有上下文注入)
    ↓
后置更新 (状态、XP、记忆存储)
    ↓
返回响应
```

## 关键函数说明

### 主聊天完成接口

#### `chat_completion(request: ChatCompletionRequest, req: Request)`
**位置**: `app/api/v1/chat.py:455`

主要的聊天完成端点，处理所有聊天请求：

**输入验证**:
- 会话存在性检查
- 角色配置验证
- 用户权限验证

**流程控制**:
```python
USE_V4_PIPELINE = os.getenv("USE_V4_PIPELINE", "true").lower() == "true"
if USE_V4_PIPELINE:
    # V4.0 单次调用优化
    v4_response = await chat_pipeline_v4.process_message(v4_request)
else:
    # 传统三层架构
    l1_result = await perception_engine.analyze(...)
    game_result = await game_engine.process(...)
    # LLM 调用
```

### L1 感知层处理

#### 意图识别和情绪分析
**位置**: `app/services/perception_engine.py`

L1 层负责理解用户输入的语义和情感：

**功能**:
- 消息安全检查
- 意图分类 (问候、请求、情感表达等)
- 情感倾向分析 (-1.0 到 1.0)
- NSFW 内容检测
- 难度评级 (1-100)

**输出结构**:
```python
class L1Result:
    safety_flag: str
    intent: str  
    difficulty_rating: int
    sentiment: float
    is_nsfw: bool
    confidence: float
```

### 中间件逻辑层处理

#### `game_engine.process(user_id, character_id, l1_result, user_message)`
**位置**: `app/services/game_engine.py`

中间件层处理游戏逻辑、状态更新和内容过滤：

**核心功能**:
1. **情绪引擎更新**: 根据 L1 分析结果更新角色情绪状态
2. **亲密度检查**: 验证用户与角色的关系等级
3. **内容过滤**: NSFW 内容检查和分级
4. **状态效果**: 处理 Tier 2 礼物的临时效果
5. **事件触发**: 检测里程碑事件 (first_kiss, confession 等)

**输出结构**:
```python
class GameResult:
    check_passed: bool
    current_emotion: int
    current_intimacy: int  
    emotion_state: str
    emotion_locked: bool
    new_event: str
    events: List[str]
    power: float  # v3.0 综合权力值
    stage: str
```

### 记忆系统集成

#### RAG 记忆检索
**位置**: `app/services/chat_service.py:288`

为高级用户提供记忆增强的对话体验：

**免费用户**: 滑动窗口上下文 (最近 10 条消息)
```python
async def _build_sliding_window_context(session_id: UUID) -> List[Dict]:
    messages = await chat_repo.get_recent_messages(str(session_id), count=10)
    # 系统消息优先，事件消息转换为摘要
    return system_messages + conversation_messages
```

**付费用户**: RAG 向量搜索
```python
async def _build_rag_context(user_id: UUID, current_message: str) -> List[Dict]:
    # 向量搜索相关记忆
    relevant_memories = await vector_service.search_memories(
        user_id=user_id, query_text=current_message, top_k=5
    )
    return memory_context + recent_context
```

### 提示词构建

#### `prompt_builder.build(game_result, character_id, user_message, ...)`
**位置**: `app/services/prompt_builder.py`

动态构建上下文相关的系统提示词：

**输入组件**:
- 游戏引擎结果 (情绪、亲密度状态)
- 角色配置 (人设、性格特征)
- 用户消息上下文
- 记忆上下文 (礼物历史、重要事件)
- 时区信息

**亲密度规则注入**:
```python
intimacy_rules = self._get_intimacy_rules(intimacy_level)
base_prompt += f"\n\n=== 当前亲密度等级: {intimacy_level} ===\n{intimacy_rules}"
```

**状态效果注入**:
```python
if effect_modifier:
    system_prompt = f"{system_prompt}\n\n{effect_modifier}"
```

### 流式响应处理

#### `stream_chat_completion(request: StreamChatRequest)`
**位置**: `app/api/v1/chat.py:1241`

实现 Server-Sent Events (SSE) 流式聊天：

**流式事件类型**:
- `event: chunk` - 部分文本内容
- `event: done` - 完成信息 (message_id, tokens, 情绪状态)
- `event: error` - 错误信息

**生成器实现**:
```python
async def generate_stream() -> AsyncGenerator[str, None]:
    async for chunk_data in grok.stream_completion(messages):
        if content:
            yield f"event: chunk\ndata: {json.dumps({'content': content})}\n\n"
    yield f"event: done\ndata: {json.dumps(done_data)}\n\n"
```

## RAG 记忆集成详解

### 记忆系统 V2 集成
**位置**: `app/services/chat_service.py:167`

```python
if memory_system_available:
    memory_context = await get_memory_context_for_chat(
        user_id=str(user_context.user_id),
        character_id=str(session["character_id"]),
        current_message=request.message,
        working_memory=context_messages,
    )
    if memory_context:
        memory_prompt = generate_memory_prompt(memory_context, intimacy_level)
        system_prompt += f"\n\n{memory_prompt}"
```

### 向量检索流程
1. **消息嵌入**: 当前用户消息转换为向量
2. **相似性搜索**: 在用户历史中检索相关对话
3. **上下文排序**: 按相关性和时间权重排序
4. **记忆注入**: 将检索结果注入系统提示词

## 情绪分析集成

### LLM 情绪分析服务
**位置**: `app/services/emotion_llm_service.py`

```python
emotion_analysis = await emotion_llm_service.analyze_message(
    message=request.message,
    intimacy_level=intimacy_level,
    current_mood=current_mood,
    current_state=current_state,
    is_spicy=is_spicy,
    boundaries=boundaries,
)
```

### 持久化情绪分数
**位置**: `app/services/emotion_score_service.py`

情绪分数影响 AI 响应风格：
- **Happy** (>0): 更积极、友好的回应
- **Neutral** (-20到0): 正常响应模式  
- **Angry** (<-20): 冷淡或拒绝性回应
- **Locked** (<-75): 进入冷战模式，需要道歉礼物

## 内容审核流程

### 多层内容安全
1. **L1 感知层检查**: 基础安全标记
2. **游戏引擎过滤**: 基于亲密度和订阅状态的分级过滤
3. **输出审核**: 助手回应的基础检查

### NSFW 分级处理
```python
should_lock_response = (
    emotion_analysis 
    and emotion_analysis.get("requires_subscription", False)
    and not user_context.is_subscribed
)
```

免费用户的成人内容会被锁定，显示预览 + 订阅提示。

## 流式响应 vs 非流式

### 非流式模式 (标准)
- **用途**: 标准聊天、复杂逻辑处理
- **特点**: 完整的三层架构处理
- **响应**: 一次性返回完整消息
- **延迟**: 2-5 秒

### 流式模式 (实时)
- **用途**: 实时对话体验
- **特点**: 简化的处理管道
- **响应**: 逐步流式输出
- **延迟**: <1 秒首字

**流式模式优化**:
- 跳过部分游戏逻辑计算
- 使用缓存的上下文
- 并行处理 XP 奖励

## 配置项

### 环境变量
```python
MOCK_LLM = settings.MOCK_LLM                    # Mock 模式
USE_V4_PIPELINE = "true"                        # V4.0 管道
```

### 上下文限制
```python
context_limit = 20 if is_premium else 10       # 付费用户更多上下文
max_rag_memories = 5                           # 最大记忆检索数量  
max_context_messages = 10                      # 免费用户上下文限制
```

### LLM 参数
```python
temperature = 0.8                              # 创意温度
max_tokens = 500                               # 最大生成长度
```

## 与其他系统的关系

### 1. 亲密度系统
- **XP 奖励**: 每条消息 +2 XP
- **连续奖励**: 每 10 条消息额外 +5 XP  
- **情感奖励**: 检测情感词汇 +10 XP
- **等级影响**: 高等级用户获得更多上下文和功能

### 2. 礼物系统  
- **状态效果**: Tier 2 礼物的临时 AI 行为调整
- **记忆注入**: 礼物历史作为对话上下文
- **瓶颈解锁**: 特定礼物解锁聊天功能

### 3. 约会系统
- **场景注入**: 约会状态下的特殊提示词
- **进度更新**: 聊天推进约会完成度
- **奖励机制**: 约会完成触发特殊事件

### 4. 主动消息系统
- **消息插入**: 主动消息以 system 角色插入聊天历史
- **触发条件**: 基于聊天频率的主动触达逻辑

## V4.0 管道优化

### 单次调用优势
1. **性能提升**: 减少 LLM 调用次数
2. **一致性**: 避免多次调用的状态不一致
3. **成本优化**: 降低 API 调用成本
4. **延迟降低**: 简化的处理流程

### 实现特点
```python
v4_request = ChatRequestV4(
    user_id=user_id,
    character_id=character_id, 
    session_id=session_id,
    message=request.message,
    intimacy_level=intimacy_level,
)
v4_response = await chat_pipeline_v4.process_message(v4_request)
```

## TODO/改进建议

### 短期优化
1. **缓存增强**: 增加更多 Redis 缓存层
2. **错误恢复**: 改善 LLM 调用失败的容错机制
3. **性能监控**: 添加详细的性能指标跟踪

### 中期扩展  
1. **多模态支持**: 图片、语音消息处理
2. **实时协作**: 多用户群聊功能
3. **智能推荐**: 基于历史的话题推荐

### 长期愿景
1. **自适应 AI**: 根据用户喜好自动调整 AI 性格
2. **跨会话记忆**: 跨角色的长期记忆系统
3. **AI 学习**: 从用户反馈中持续学习和优化

### 架构重构
1. **微服务化**: 将各层拆分为独立微服务
2. **事件驱动**: 采用事件驱动架构提升解耦
3. **GraphQL**: 提供更灵活的 API 查询接口
4. **容器化**: 全面容器化部署支持

通过不断的系统优化和功能扩展，Luna 的聊天流程系统将为用户提供更加智能、个性化的 AI 伴侣体验。