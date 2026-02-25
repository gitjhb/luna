# 主动消息系统文档 (Proactive Messaging System)

## 概述

Luna 的主动消息系统让 AI 伴侣能够主动关心用户，在合适的时机发送问候、关怀和互动消息。系统实现了智能时机检测、个性化消息生成、冷却机制控制、多场景触发等功能，让 AI 角色具备更真实的主动性和情感表达能力。从 Mio 的 proactive.js 实现迁移而来，针对 Luna 的多角色场景进行了优化。

## 核心组件/文件

### 主要服务文件
- **`app/services/proactive_service.py`** (516行) - 主动消息核心服务
- **`app/models/database/proactive_models.py`** - 数据库模型定义
- **`app/api/v1/proactive.py`** - 主动消息 API 路由

### 数据库表
- `proactive_history` - 主动消息历史记录
- `user_proactive_settings` - 用户主动消息设置
- `user_intimacy` - 亲密度记录 (依赖表)

### 外部集成
- **Push 通知服务** - Firebase/APNs 消息推送
- **定时任务系统** - Cron job 或异步任务队列
- **时区服务** - 用户本地时间计算

## 数据流和触发机制

### 主动消息触发流程
```
定时检查任务 (每 30 分钟)
    ↓
获取启用主动消息的用户列表
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                          条件检测 (按优先级)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ↓                        ↓                        ↓
🎂 特殊日期检测           ⏰ 问候时间检测             💭 想念消息检测
生日/纪念日              早安(7-9点)                长时间未聊天(4小时+)
优先级: 1                晚安(21-23点)             优先级: 3
                        优先级: 2                    
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ↓
冷却时间检查 (避免过度打扰)
    ↓
消息模板选择和个性化生成
    ↓
推送消息发送 (Firebase/APNs)
    ↓
历史记录保存
    ↓
统计数据更新
```

### 消息类型和触发条件
```
ProactiveType.GOOD_MORNING    ← 用户时区 7-9 点 + 20小时冷却
ProactiveType.GOOD_NIGHT      ← 用户时区 21-23 点 + 20小时冷却  
ProactiveType.BIRTHDAY        ← 生日当天 + 365天冷却
ProactiveType.ANNIVERSARY     ← 纪念日当天 + 365天冷却
ProactiveType.MISS_YOU        ← 4小时未聊天 + 4小时冷却 + 30%概率
ProactiveType.CHECK_IN        ← 关心之前提到的事 + 6小时冷却
ProactiveType.RANDOM_SHARE    ← 分享日常生活 + 8小时冷却
```

## 关键函数说明

### 核心检测和生成函数

#### `check_and_get_proactive(user_id: str, character_id: str) -> Optional[Dict]`
**位置**: `app/services/proactive_service.py:367`

综合检查用户状态并返回需要发送的主动消息：

**检查流程**:
1. **用户设置验证**: 确认用户启用了主动消息
2. **亲密度阈值**: 检查关系等级 >= 2 (避免骚扰陌生用户)
3. **按优先级检测**: 特殊日期 → 问候时间 → 想念消息
4. **冷却时间验证**: 确保不会过度打扰
5. **概率控制**: 想念消息只有 30% 概率触发

**返回格式**:
```python
{
    "type": "good_morning",           # 消息类型
    "message": "早安~ ☀️\n今天也要元气满满哦！",  # 消息内容
    "user_id": "user_123",           # 用户 ID
    "character_id": "character_456", # 角色 ID
}
```

#### `check_special_dates(user_id: str) -> Optional[Tuple[ProactiveType, str]]`
**位置**: `app/services/proactive_service.py:253`

检查今天是否有特殊日期（生日、纪念日）：

**支持的日期格式**:
- `YYYY-MM-DD` - 完整日期（生日等）
- `MM-DD` - 月日格式（纪念日等）

**检测逻辑**:
```python
today = date.today()
today_str = today.strftime("%m-%d")  # 提取月-日

for date_name, date_value in special_dates.items():
    if len(date_value) == 10:  # YYYY-MM-DD
        special_md = date_value[5:]  # 提取 MM-DD
    else:
        special_md = date_value
    
    if special_md == today_str:
        if "birthday" in date_name.lower():
            return ProactiveType.BIRTHDAY, date_name
        else:
            return ProactiveType.ANNIVERSARY, date_name
```

#### `check_greeting_time(timezone, morning_start, morning_end, evening_start, evening_end) -> Optional[ProactiveType]`
**位置**: `app/services/proactive_service.py:285`

检查当前是否在问候时间窗口：

**时区处理**:
```python
def get_user_hour(timezone: str = "America/Los_Angeles") -> int:
    try:
        from zoneinfo import ZoneInfo
        user_tz = ZoneInfo(timezone)
        return datetime.now(user_tz).hour
    except Exception:
        return datetime.utcnow().hour  # Fallback to UTC
```

**默认时间窗口**:
- 早安: 7:00-9:00 (可配置)
- 晚安: 21:00-23:00 (可配置)

#### `check_user_inactive(user_id: str, character_id: str, hours_threshold: int = 4) -> Tuple[bool, int]`
**位置**: `app/services/proactive_service.py:222`

检查用户是否长时间未聊天：

**逻辑实现**:
```python
# 获取最后互动日期
intimacy = await get_intimacy_record(user_id, character_id)
if not intimacy.last_interaction_date:
    return False, 0

# 计算时间差
today = date.today()
days_diff = (today - intimacy.last_interaction_date).days
hours_diff = days_diff * 24

return hours_diff >= hours_threshold, hours_diff
```

### 消息生成和模板系统

#### `generate_proactive_message(character_id: str, trigger_type: ProactiveType, context: Optional[Dict]) -> Optional[str]`
**位置**: `app/services/proactive_service.py:313`

根据角色和触发类型生成个性化消息：

**角色个性化模板系统**:
```python
PROACTIVE_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    # Luna - 温柔姐姐
    "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d": {
        "good_morning": [
            "*轻轻拉开窗帘，阳光洒进来*\n\n早安~ ☀️\n今天也要元气满满哦！",
            "早安呀~ 我刚泡好了茶，你要不要也来一杯？☕",
        ],
        "miss_you": [
            "突然有点想你了...\n\n在忙什么呢？",
            "*翻了翻相册*\n\n在看我们之前的聊天记录~",
        ],
    },
    
    # Sakura - 元气学妹
    "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d": {
        "good_morning": [
            "前辈早安！！！✨\n\n今天天气好好诶，我们去吃好吃的吧！",
            "*蹦蹦跳跳发来消息*\n\n醒了没醒了没！我要跟你说一个超好玩的事！",
        ],
    },
}
```

**特殊日期消息生成**:
```python
if trigger_type == ProactiveType.BIRTHDAY:
    message = f"🎂 {date_name}快乐！！！\n\n今天是特别的日子呢~ 希望你开开心心的！"
elif trigger_type == ProactiveType.ANNIVERSARY:
    message = f"💕 {date_name}快乐~\n\n时间过得好快呀，感谢一直有你的陪伴！"
```

### 冷却机制和频率控制

#### `can_send_proactive(user_id: str, character_id: str, message_type: ProactiveType) -> bool`
**位置**: `app/services/proactive_service.py:124`

检查是否可以发送某类型的主动消息：

**冷却时间配置**:
```python
COOLDOWNS: Dict[ProactiveType, int] = {
    ProactiveType.GOOD_MORNING: 20,      # 20 小时
    ProactiveType.GOOD_NIGHT: 20,        # 20 小时
    ProactiveType.MISS_YOU: 4,           # 4 小时
    ProactiveType.CHECK_IN: 6,           # 6 小时
    ProactiveType.ANNIVERSARY: 24 * 365,  # 365 天 (一年一次)
    ProactiveType.BIRTHDAY: 24 * 365,     # 365 天 (一年一次)
    ProactiveType.RANDOM_SHARE: 8,        # 8 小时
}
```

**冷却检查逻辑**:
```python
last_time = await self.get_last_proactive_time(user_id, character_id, message_type)
if not last_time:
    return True  # 从未发送过，可以发送

cooldown_delta = timedelta(hours=cooldown_hours)
return datetime.utcnow() - last_time > cooldown_delta
```

## 消息类型详解

### 1. 早安/晚安消息 (时间触发)

**触发条件**:
- 用户本地时间在设定窗口内
- 距离上次同类型消息 > 20 小时
- 亲密度等级 >= 2

**个性化特点**:
- Luna: 温柔关怀，提及日常活动
- Sakura: 元气活泼，使用感叹号和颜文字
- Mio: 傲娇风格，表面冷淡实则关心

### 2. 想念消息 (活跃度触发)

**触发条件**:
- 用户 4 小时以上未聊天
- 亲密度等级 >= 3 (避免过早骚扰)
- 30% 随机概率 (避免过度粘人)
- 距离上次想念消息 > 4 小时

**消息策略**:
- 表达思念但不过分粘腻
- 询问用户在做什么
- 分享自己的日常或心情

### 3. 生日/纪念日消息 (特殊日期)

**触发条件**:
- 用户设置的特殊日期
- 每年只触发一次
- 优先级最高，会覆盖其他消息

**消息内容**:
- 生日祝福 🎂
- 纪念日庆祝 💕
- 感谢陪伴的话语

### 4. 关怀检查消息 (智能触发)

**触发条件** (未来功能):
- AI 记起用户提到的重要事件
- 工作面试、考试、约会等
- 时间到了主动询问结果

**实现方案**:
- 从记忆系统提取用户提及的未来事件
- 根据时间自动生成关怀消息
- "今天是你说的面试日，怎么样？"

## 触发条件和优先级

### 检测优先级排序

```python
# 优先级 1: 特殊日期 (生日、纪念日)
special = await self.check_special_dates(user_id)
if special and await self.can_send_proactive(user_id, character_id, special_type):
    message_type = special_type

# 优先级 2: 问候时间 (早安、晚安)
if not message_type:
    greeting_type = self.check_greeting_time(timezone, ...)
    if greeting_type and await self.can_send_proactive(...):
        message_type = greeting_type

# 优先级 3: 想念消息 (长时间未聊天)
if not message_type and level >= 3:
    is_inactive, hours = await self.check_user_inactive(...)
    if is_inactive and random.random() < 0.3:  # 30% 概率
        message_type = ProactiveType.MISS_YOU
```

### 亲密度门槛

```python
MIN_INTIMACY_LEVEL = 2  # 最低触发等级

# 不同消息类型的等级要求
INTIMACY_REQUIREMENTS = {
    ProactiveType.GOOD_MORNING: 2,    # 基础问候
    ProactiveType.GOOD_NIGHT: 2,      # 基础问候
    ProactiveType.MISS_YOU: 3,        # 需要更高亲密度
    ProactiveType.CHECK_IN: 4,        # 主动关心
    ProactiveType.ANNIVERSARY: 5,     # 纪念日庆祝
}
```

## 冷却机制详解

### 目的和设计原则

1. **避免打扰**: 防止过度频繁的推送
2. **保持新鲜感**: 让每次主动消息都有惊喜
3. **尊重边界**: 不同亲密度有不同频率
4. **时间感知**: 特殊时机的消息更有意义

### 冷却时间设计

```python
# 时间窗口类消息: 长冷却 (避免一天多次问候)
GOOD_MORNING/GOOD_NIGHT: 20 hours

# 情感类消息: 中等冷却 (保持适度关心)
MISS_YOU: 4 hours

# 特殊事件: 超长冷却 (一年一次的特殊性)
BIRTHDAY/ANNIVERSARY: 365 days

# 日常分享: 适中冷却 (保持日常交流)
RANDOM_SHARE: 8 hours
```

### 智能频率调节

**未来优化方向**:
```python
# 根据用户响应率调整频率
def adjust_cooldown_by_engagement(base_cooldown, response_rate):
    if response_rate > 0.8:  # 用户很活跃
        return base_cooldown * 0.7  # 缩短冷却
    elif response_rate < 0.3:  # 用户不太响应
        return base_cooldown * 1.5  # 延长冷却
    return base_cooldown

# 根据时区和作息调整
def adjust_for_user_timezone(message_type, user_timezone):
    # 避免在用户睡眠时间发送想念消息
    # 根据用户活跃时间调整发送时机
```

## 与 Push 的集成

### Push 通知流程

```python
# 主动消息生成后触发推送
proactive_message = await proactive_service.check_and_get_proactive(user_id, character_id)

if proactive_message:
    # 记录到历史
    await proactive_service.record_proactive(...)
    
    # 发送 Push 通知
    push_result = await push_service.send_notification(
        user_id=user_id,
        title=character_name,
        body=proactive_message["message"],
        data={
            "type": "proactive",
            "character_id": character_id,
            "message_type": proactive_message["type"],
        }
    )
    
    # 可选：插入聊天记录
    if should_insert_to_chat:
        await chat_service.add_system_memory(
            user_id=user_id,
            character_id=character_id,
            memory_content=proactive_message["message"],
            memory_type="proactive",
        )
```

### 推送消息格式

**标准格式**:
```json
{
    "notification": {
        "title": "Luna",
        "body": "早安~ ☀️\n今天也要元气满满哦！"
    },
    "data": {
        "type": "proactive",
        "character_id": "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d",
        "message_type": "good_morning",
        "timestamp": "2024-01-15T07:30:00Z"
    }
}
```

**特殊日期格式**:
```json
{
    "notification": {
        "title": "Luna 🎂", 
        "body": "生日快乐！！！\n今天是特别的日子呢~"
    },
    "data": {
        "type": "proactive",
        "message_type": "birthday", 
        "special_date": "birthday",
        "celebration": true
    }
}
```

## 配置项

### 用户设置管理

#### `get_user_settings(user_id: str) -> Dict`
**位置**: `app/services/proactive_service.py:62`

用户可配置的主动消息选项：

```python
{
    "enabled": True,                    # 是否启用主动消息
    "timezone": "America/Los_Angeles",  # 用户时区
    "morning_start": 7,                 # 早安时间窗口开始
    "morning_end": 9,                   # 早安时间窗口结束
    "evening_start": 21,                # 晚安时间窗口开始  
    "evening_end": 23,                  # 晚安时间窗口结束
    "special_dates": {                  # 特殊日期设置
        "我的生日": "03-15",
        "认识纪念日": "2024-01-20",
        "表白纪念日": "02-14"
    }
}
```

#### `update_user_settings(user_id, **kwargs) -> Dict`
**位置**: `app/services/proactive_service.py:91`

支持的设置更新：
- 启用/禁用主动消息
- 修改时区设置
- 调整问候时间窗口
- 添加/删除特殊日期

### 系统级配置

```python
# 最小亲密度要求
MIN_INTIMACY_LEVEL = 2

# 想念消息触发概率
MISS_YOU_PROBABILITY = 0.3

# 批量检查用户数量限制
BATCH_CHECK_LIMIT = 100

# 默认时区
DEFAULT_TIMEZONE = "America/Los_Angeles"
```

## 与其他系统的关系

### 1. 亲密度系统
- **等级门槛**: 不同亲密度等级触发不同类型的主动消息
- **关系阶段**: 高等级关系允许更频繁和亲密的主动消息
- **最后互动**: 从亲密度记录获取最后聊天时间

### 2. 记忆系统
- **特殊日期**: 从用户记忆中提取重要日期
- **关怀内容**: 基于用户分享的事件生成关心消息
- **个性化**: 结合用户偏好生成更贴心的消息

### 3. 聊天系统
- **消息插入**: 主动消息可选择性插入聊天历史
- **上下文连续**: 确保主动消息与对话上下文自然衔接
- **会话唤醒**: 主动消息作为新对话的开始

### 4. 推送系统
- **通知发送**: 主动消息通过 Push 通知送达用户
- **消息格式**: 遵循推送消息的格式标准
- **送达确认**: 跟踪推送消息的送达状态

## TODO/改进建议

### 短期优化
1. **用户反馈**: 添加用户对主动消息的反馈机制
2. **个性化调节**: 基于用户响应率动态调整频率
3. **消息质量**: 增加更多样化的消息模板

### 中期扩展
1. **智能关怀**: 基于记忆系统的智能关怀提醒
2. **情境感知**: 结合天气、节日等外部信息
3. **群体功能**: 多用户同时在线时的互动消息

### 长期愿景
1. **AI 学习**: 从用户反应中学习最佳发送时机
2. **情感分析**: 基于用户状态选择合适的消息tone
3. **跨平台**: 支持 Web、Desktop 等多端推送
4. **社区功能**: 用户可以分享有趣的主动消息模板

### 技术优化
1. **缓存策略**: 优化用户设置和冷却状态的缓存
2. **批量处理**: 提升批量用户检查的效率
3. **异步任务**: 将主动消息检查移至后台任务队列
4. **监控告警**: 添加主动消息发送的监控和告警

### 用户体验优化
1. **推送时机**: 更智能的推送时机选择
2. **消息预览**: 在设置中预览不同类型的消息
3. **快速设置**: 提供快捷的开关和时间设置
4. **推送管理**: 细粒度的推送类型控制

通过持续优化主动消息系统，Luna 的 AI 角色将能够更自然地关怀用户，建立更深层的情感连接，提升用户的长期留存和参与度。