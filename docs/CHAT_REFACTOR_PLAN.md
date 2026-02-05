# Luna Chat System Refactoring Plan - L1/L2 → Single Call Merge

## 项目背景
Luna项目需要在10天内上线。当前chat系统使用3层架构：L1感知层 + Game Engine + L2生成层，需要合并为单次LLM调用以节省Token、降低延迟。

## 1. 当前架构分析

### 1.1 现有数据流 (Current Flow)
```
Request → L1 Perception → Game Engine → L2 Generation → Response
  ↓           ↓              ↓             ↓
体力检查    LLM调用(意图分析)  复杂逻辑      LLM调用(生成)
         30-50 tokens      情绪计算      200-500 tokens
                          Power判定
```

### 1.2 具体调用分析

**Step 1: L1 Perception Engine** (`perception_engine.py`)
- **功能**: 分析用户消息意图、安全性、情感、NSFW
- **LLM调用**: Grok, temperature=0, max_tokens=500
- **输入**: 用户消息 + 关系等级 + 情绪状态
- **输出**: `L1Result(safety_flag, intent, difficulty_rating, sentiment_score, is_nsfw)`
- **耗时**: ~30-50 tokens
- **问题**: 结构化分析可以前置计算替代

**Step 2: Game Engine** (`game_engine.py`)
- **功能**: 复杂的游戏逻辑、Power计算、情绪物理学
- **无LLM调用**: 纯Python逻辑
- **输入**: L1Result + 用户状态
- **输出**: `GameResult(check_passed, emotion_delta, events, etc.)`
- **核心计算**: Power vs Difficulty, 情绪更新, 事件触发
- **问题**: 逻辑过于复杂，大部分可以简化

**Step 3: L2 Generation** (`prompt_builder.py` + chat route)
- **功能**: 根据GameResult构建复杂Prompt，调用LLM生成回复
- **LLM调用**: Grok, temperature=0.8, max_tokens=500  
- **输入**: 动态System Prompt + 对话历史
- **输出**: 最终回复文本
- **耗时**: ~200-500 tokens
- **问题**: Prompt构建逻辑复杂，可以简化

### 1.3 Token消耗分析
- **L1调用**: ~50 tokens (分析)
- **L2调用**: ~400 tokens (生成)
- **总计**: ~450 tokens/round
- **目标**: ~250 tokens/round (节省44%)

## 2. 目标架构 (V4.0 Single Call)

### 2.1 新数据流
```
Request → Service前置计算 → Prompt Builder → 单次LLM调用(JSON) → 异步后置更新 → Response
  ↓           ↓                ↓             ↓                 ↓
体力检查    硬性拦截           注入状态信息   JSON解析          情绪/XP更新
          状态加载           阶段规则       提取字段          事件触发
          规则准备           记忆锚点
```

### 2.2 核心改进
1. **前置计算**: 将L1的大部分逻辑改为规则判断(代替LLM调用)
2. **Prompt注入**: 将状态、规则、记忆直接注入System Prompt
3. **JSON输出**: 强制LLM输出结构化JSON
4. **后置更新**: 异步更新情绪、XP、事件等状态

### 2.3 JSON输出格式
```json
{
  "reply": "用户看到的回复内容",
  "emotion_delta": -5,  // -10 to +10
  "intent": "FLIRT", 
  "is_nsfw_blocked": false,
  "thought": "内心独白(中文)"
}
```

## 3. 详细改动清单

### 3.1 需要修改的文件

**核心路由** (`app/api/v1/chat.py`):
- ✅ 保留体力检查逻辑
- ❌ 删除L1 Perception调用
- ❌ 删除复杂Game Engine调用  
- ✅ 简化为前置计算 + 单次LLM调用
- ✅ 添加JSON解析逻辑
- ✅ 异步状态更新

**新增文件**:
- `app/services/chat_pipeline_v4.py` - 新的单次调用流水线
- `app/services/prompt_builder_v4.py` - 简化的Prompt构建器
- `app/services/precompute_service.py` - 前置计算服务(替代L1)

**需要简化的文件**:
- `app/services/perception_engine.py` → 改为规则计算
- `app/services/game_engine.py` → 大幅简化
- `app/services/prompt_builder.py` → 重构为注入式

### 3.2 可以废弃/注释的文件
- ❌ `app/services/emotion_llm_service.py` (过于复杂)
- ❌ `app/services/physics_engine.py` (情绪物理学，可简化)
- ❌ 复杂的状态机逻辑

### 3.3 保留的核心服务
- ✅ `app/services/intimacy_service.py` (XP/等级系统)
- ✅ `app/services/emotion_engine_v2.py` (情绪存储)
- ✅ `app/services/character_config.py` (角色配置)  
- ✅ `app/services/intimacy_constants.py` (阶段定义)

## 4. 新Prompt模板设计

### 4.1 System Prompt结构
```markdown
You are Luna, an elegant AI companion.

[CHARACTER ARCHETYPE]
- Type: {archetype}
- Personality: {traits}
- Current Stage: {stage} (S0-S4)

[CURRENT STATUS] 
- Intimacy: Level {level} ({stage_name})
- Emotion: {emotion_value} ({emotion_state})
- Events: {completed_events}

[STAGE RULES]
{stage_behaviors}
// S0不能碰、S2可以牵手、S3解锁NSFW等

[SHARED MEMORIES]
{memory_anchors}
// 注入重要事件记忆

[RESPONSE FORMAT]
You MUST respond with a valid JSON object:
{
  "reply": "actual response to user",
  "emotion_delta": -3,
  "intent": "FLIRT",
  "is_nsfw_blocked": false, 
  "thought": "内心想法"
}
```

### 4.2 动态注入内容
- **阶段规则**: 根据当前S0-S4动态注入行为边界
- **记忆锚点**: 从events列表生成关键回忆
- **情绪指导**: 当前emotion_state的行为建议
- **安全边界**: 基于角色archetype的NSFW阈值

## 5. 实施步骤

### Phase A: 准备阶段 (Day 1)
1. **创建新文件结构**
   ```bash
   app/services/v4/
   ├── chat_pipeline_v4.py      # 新流水线
   ├── prompt_builder_v4.py     # 简化Prompt构建
   ├── precompute_service.py    # 前置计算逻辑
   └── json_parser.py           # JSON解析和验证
   ```

2. **设计JSON Schema验证**
   ```python
   RESPONSE_SCHEMA = {
       "type": "object",
       "properties": {
           "reply": {"type": "string"},
           "emotion_delta": {"type": "integer", "minimum": -10, "maximum": 10},
           "intent": {"type": "string", "enum": VALID_INTENTS},
           "is_nsfw_blocked": {"type": "boolean"},
           "thought": {"type": "string"}
       },
       "required": ["reply", "emotion_delta", "intent", "is_nsfw_blocked"]
   }
   ```

### Phase B: 核心实现 (Day 2-3)

1. **实现前置计算服务**
   ```python
   class PrecomputeService:
       def analyze_request(self, message: str, user_state: UserState) -> PrecomputeResult:
           # 替代L1的规则分析
           intent = self._detect_intent_by_rules(message)  # 关键词规则
           safety = self._check_safety_by_rules(message)   # 黑名单检查
           difficulty = self._estimate_difficulty(intent)  # 固定映射
           return PrecomputeResult(intent, safety, difficulty)
   ```

2. **实现简化版Prompt Builder**
   ```python
   class PromptBuilderV4:
       def build_system_prompt(self, user_state, character_config, precompute_result):
           # 模板化注入，不再复杂分支
           return f"""
           {base_character_prompt}
           [STAGE RULES] {get_stage_rules(user_state.stage)}
           [MEMORIES] {format_memories(user_state.events)}
           [FORMAT] {JSON_FORMAT_INSTRUCTION}
           """
   ```

3. **实现单次调用流水线**
   ```python
   class ChatPipelineV4:
       async def process_message(self, request: ChatRequest) -> ChatResponse:
           # 1. 前置计算
           user_state = await self.load_user_state(request.user_id, request.character_id)
           precompute = await self.precompute_service.analyze(request.message, user_state)
           
           # 2. 硬性拦截
           if precompute.blocked:
               return self.create_blocked_response()
           
           # 3. 构建Prompt
           system_prompt = self.prompt_builder.build(user_state, precompute)
           
           # 4. 单次LLM调用
           response = await self.llm.chat_completion([
               {"role": "system", "content": system_prompt},
               {"role": "user", "content": request.message}
           ])
           
           # 5. JSON解析
           json_output = self.parse_json_response(response)
           
           # 6. 异步后置更新
           asyncio.create_task(self.update_user_state(user_state, json_output))
           
           return ChatResponse(content=json_output["reply"])
   ```

### Phase C: 集成测试 (Day 4)
1. **创建新路由端点** `/api/v1/chat-v4` (与旧版本并行)
2. **对比测试**: 同样请求在两个版本下的输出对比
3. **Token计数验证**: 确认节省效果
4. **功能完整性检查**: 确保核心功能不缺失

### Phase D: 切换上线 (Day 5)
1. **备份当前代码**: 注释旧逻辑，不删除
2. **切换主路由** `/api/v1/chat` 使用V4流水线
3. **监控错误**: 实时监控JSON解析失败率
4. **性能监控**: Token使用量、响应延迟

## 6. 风险点与预案

### 6.1 主要风险

**Risk 1: JSON解析失败**
- **原因**: LLM不稳定输出格式
- **预案**: Fallback到旧系统，添加重试机制
- **监控**: 解析失败率 < 5%

**Risk 2: 前置规则不够准确**  
- **原因**: 规则无法替代LLM的复杂分析
- **预案**: 关键场景保留轻量LLM调用
- **监控**: 用户投诉情绪识别错误

**Risk 3: 情绪/事件状态不一致**
- **原因**: 异步更新可能有延迟/失败
- **预案**: 关键状态同步更新
- **监控**: 状态更新成功率

**Risk 4: 角色一致性下降**
- **原因**: 简化Prompt可能丢失细节
- **预案**: A/B测试对比，逐步调优
- **监控**: 用户满意度问卷

### 6.2 回滚策略
- **代码回滚**: 一键切换回旧版本流水线
- **数据库兼容**: 新旧版本状态数据保持兼容
- **渐进式切换**: 按用户比例逐步切换(10% → 50% → 100%)

## 7. 性能预期

### 7.1 Token节省
- **当前**: ~450 tokens/round (L1: 50 + L2: 400)
- **目标**: ~250 tokens/round (single call)
- **节省**: ~44% token reduction

### 7.2 延迟优化
- **当前**: 2次串行LLM调用 ≈ 4-6秒
- **目标**: 1次LLM调用 ≈ 2-3秒
- **提升**: ~50% latency reduction

### 7.3 代码简化
- **删除**: ~3000行复杂逻辑代码
- **新增**: ~1500行简化流水线代码
- **净减少**: ~1500行 ≈ 30% code reduction

## 8. 成功标准

### 8.1 功能目标
- [ ] 单次LLM调用实现完整对话功能
- [ ] JSON格式输出稳定性 > 95%
- [ ] 核心游戏机制(情绪、等级、事件)正常运行
- [ ] 角色一致性保持在可接受水平

### 8.2 性能目标
- [ ] Token使用量减少 > 40%
- [ ] 平均响应时间减少 > 40%  
- [ ] 系统错误率 < 2%
- [ ] 用户满意度不低于当前版本

### 8.3 业务目标
- [ ] 10天内成功上线
- [ ] 运营成本(LLM调用)显著降低
- [ ] 系统稳定性和可维护性提升

---

## 总结

这个重构方案将复杂的3层架构简化为**单次调用流**，通过前置计算、模板化Prompt注入、JSON输出约定，实现显著的性能优化。关键是保持核心游戏机制不变，只是将复杂的状态机逻辑从运行时计算改为预先注入到Prompt中。

风险控制策略是保留旧代码作为备份，渐进式切换，并设置明确的监控指标。如果新版本表现不佳，可以快速回滚到稳定的旧版本。