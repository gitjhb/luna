# Luna 情绪系统文档

## 概述

Luna 有一套完整的情绪系统，让 AI 角色能根据用户的行为产生情绪反应。

## 核心组件

### 1. EmotionScoreService (`emotion_score_service.py`)
- **分数范围**: -100 到 +100
- **存储**: 内存 (`_EMOTION_SCORES` 字典) + 数据库同步
- **核心功能**:
  - `get_score()` - 获取当前情绪分数
  - `update_score()` - 更新分数 (带亲密度加成)
  - `apply_message_impact()` - 应用消息影响
  - `apply_gift_effect()` - 应用礼物效果

### 2. EmotionLLMService (`emotion_llm_service.py`)
- **功能**: 使用 LLM 分析用户消息的情绪影响
- **输出**: delta (分数变化), trigger_type, should_reject, suggested_mood
- **调用位置**: `chat_service.py` 的聊天流程中

### 3. 数据库存储 (`user_character_emotions` 表)
- `emotional_state`: 情绪状态名称
- `emotion_intensity`: 情绪强度 (⚠️ 存的是 abs(score)!)
- `emotion_reason`: 原因
- `times_angered`, `times_hurt`: 统计

## 情绪状态对照表

| 分数范围 | 状态 | 中文 |
|---------|------|------|
| +75 ~ +100 | loving | 甜蜜/热恋 |
| +50 ~ +74 | happy | 开心 |
| +20 ~ +49 | content | 满足 |
| -19 ~ +19 | neutral | 平静 |
| -34 ~ -20 | annoyed | 不满 |
| -49 ~ -35 | angry | 生气 |
| -74 ~ -50 | furious | 暴怒 |
| -100 ~ -75 | cold_war | 冷战 ❄️ |

## 冷战机制

当分数降到 -75 以下时进入"冷战"状态：
- 角色只接受真诚道歉/忏悔礼物
- 普通消息效果为 0 或负数
- 需要特殊礼物 (`apology_letter`, `sincere_apology_box` 等) 解锁

## 聊天流程中的情绪处理

```
用户发消息
    ↓
chat_service.send_message()
    ↓
1. emotion_score_service.get_score() - 获取当前情绪
    ↓
2. emotion_llm_service.analyze_message() - LLM分析消息影响
    ↓
3. emotion_score_service.apply_message_impact() - 更新分数
    ↓
4. 情绪上下文注入到 system_prompt
    ↓
5. LLM 生成带情绪的回复
```

## 礼物对情绪的影响

| 礼物类型 | 正常时效果 | 生气时效果 | 冷战时效果 |
|---------|-----------|-----------|-----------|
| 普通礼物 | +10~25 | 效果减半 | 几乎无效 |
| 浪漫礼物 | +15~30 | 效果减半 | 几乎无效 |
| 道歉礼物 | +10~30 | 额外 +30~60 | **可解除冷战** |
| 奢华礼物 | +40~50 | 效果减半 | 部分有效 |

## Admin Panel 显示问题

### 问题
Admin Panel 显示 "0/100" 或低数值，原因是：

1. **数据库存储用 `abs(score)`**:
   ```python
   db_emotion.emotion_intensity = abs(score)
   ```
   所以 -50 变成 50，负数信息丢失

2. **初始分数是 30** (content 状态)，不是 0

3. **如果没有聊天，分数不会变化**

### 修复建议
在 `_sync_to_database()` 中改为直接存储原始 score:
```python
db_emotion.emotion_intensity = score  # 不要 abs()
```

或者新增字段:
```python
db_emotion.emotion_score = score  # 原始分数 -100 ~ +100
db_emotion.emotion_intensity = abs(score)  # 强度 0 ~ 100
```

## 测试情绪系统

### 1. 查看当前情绪
```bash
curl http://localhost:8001/api/v1/admin/emotions
```

### 2. 手动修改情绪
```bash
curl -X PUT "http://localhost:8001/api/v1/admin/emotions/USER_ID/CHAR_ID?score=-50&state=angry"
```

### 3. 触发冷战测试
连续发送侮辱性消息，观察分数下降到 -75 以下

### 4. 解除冷战测试
发送道歉礼物，观察分数恢复

## 相关文件

- `app/services/emotion_score_service.py` - 分数管理
- `app/services/emotion_llm_service.py` - LLM 分析
- `app/services/chat_service.py` - 聊天集成 (line 213-255)
- `app/api/v1/emotion.py` - 情绪 API
- `app/api/v1/admin.py` - Admin API (emotions endpoint)
- `app/models/database/emotion_models.py` - 数据库模型
- `app/models/database/gift_models.py` - 礼物定义 (含道歉礼物)

## TODO

- [ ] 修复 Admin Panel 显示问题 (abs 导致负数丢失)
- [ ] 添加情绪历史记录功能
- [ ] 添加情绪变化通知 (push notification)
- [ ] 前端情绪可视化改进
