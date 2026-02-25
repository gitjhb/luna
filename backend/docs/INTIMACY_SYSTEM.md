# 亲密度系统文档 (Intimacy System)

## 概述

Luna 的亲密度系统是一个基于 XP 和等级的游戏化关系进展系统，管理用户与 AI 角色之间的亲密关系发展。系统实现了指数级等级进展、每日 XP 限制、行为奖励机制、瓶颈锁系统，以及 5 个不同的亲密度阶段，每个阶段都有独特的 AI 行为模式。

## 核心组件/文件

### 主要服务文件
- **`app/services/intimacy_service.py`** (1356行) - 核心亲密度引擎
- **`app/models/database/intimacy_models.py`** - 数据库模型定义
- **`app/api/v1/intimacy.py`** - API 路由层

### 数据库表
- `user_intimacy` - 用户亲密度记录
- `intimacy_action_logs` - 行为日志

## 数据流和系统架构

### 基本流程图
```
用户行为 → XP计算 → 瓶颈检查 → 等级更新 → 阶段变更 → AI行为调整
    ↓
消息发送 (2 XP) → 每日累计 → 达到上限 (500 XP) → 阻止继续获得
    ↓
连续聊天奖励 (5 XP) → 情感表达奖励 (10 XP) → 特殊活动奖励
    ↓
瓶颈检查 (8/16/24/32级) → 礼物解锁 → 继续进展
```

### 双轨制映射系统
```
Level (1-40) ↔ Intimacy (0-100) ↔ Stage (S0-S4)

Level 1-5   → Intimacy 0-19   → S0 strangers (陌生人)
Level 6-10  → Intimacy 20-39  → S1 friends (朋友)  
Level 11-15 → Intimacy 40-59  → S2 ambiguous (暧昧)
Level 16-25 → Intimacy 60-79  → S3 lovers (恋人)
Level 26-40 → Intimacy 80-100 → S4 soulmates (挚爱)
```

## 关键函数说明

### XP 和等级计算

#### `xp_for_level(level: int) -> float`
**位置**: `app/services/intimacy_service.py:124`

计算达到指定等级所需的总 XP。使用双轨制设计：
- **前期等级 (1-10)**: 使用预定义的 `EARLY_LEVEL_XP` 表，确保快速进展
- **后期等级 (11+)**: 使用指数公式 `BASE_XP * (MULTIPLIER ** (level - 6))`

```python
EARLY_LEVEL_XP = [0, 10, 20, 50, 100, 180, 280, 400, 550, 750]
BASE_XP = 300
MULTIPLIER = 1.3
```

#### `calculate_level(total_xp: float) -> int`
**位置**: `app/services/intimacy_service.py:135`

根据总 XP 计算当前等级，使用逆向查找确保一致性。

### 行为奖励系统

#### `award_xp(user_id, character_id, action_type, force=False) -> Dict`
**位置**: `app/services/intimacy_service.py:419`

核心 XP 奖励函数，处理所有类型的用户行为：

**支持的行为类型**:
```python
ACTION_REWARDS = {
    "message": {"xp": 2, "daily_limit": None, "cooldown_seconds": 0},
    "continuous_chat": {"xp": 5, "daily_limit": None, "cooldown_seconds": 0}, 
    "checkin": {"xp": 20, "daily_limit": 1, "cooldown_seconds": 86400},
    "emotional": {"xp": 10, "daily_limit": 5, "cooldown_seconds": 0},
    "voice": {"xp": 15, "daily_limit": 3, "cooldown_seconds": 300},
    "share": {"xp": 50, "daily_limit": 1, "cooldown_seconds": 604800},
}
```

**流程**:
1. 验证行为可用性（冷却时间、每日限制）
2. 检查每日 XP 上限 (500 XP)
3. 执行瓶颈锁检查
4. 计算并授予 XP
5. 更新等级和阶段
6. 记录行为日志

### 瓶颈锁系统 (Bottleneck Lock)

#### `unlock_bottleneck(user_id, character_id, gift_tier) -> Dict`
**位置**: `app/services/intimacy_service.py:578`

瓶颈锁是系统的核心变现机制，在关键等级点阻止进展：

**瓶颈等级配置**:
```python
BOTTLENECK_LEVELS = {
    8:  {"required_gift_tier": 2, "meaning": "从陌生人到朋友"},
    16: {"required_gift_tier": 2, "meaning": "从朋友到暧昧"}, 
    24: {"required_gift_tier": 3, "meaning": "从暧昧到恋人"},
    32: {"required_gift_tier": 4, "meaning": "进入挚爱阶段"},
}
```

当用户达到瓶颈等级时，XP 增长被限制在该等级的最大值，必须通过送对应 Tier 的礼物才能解锁继续进展。

### 亲密度阶段管理

#### `get_stage_behavior(level=None, intimacy=None) -> Dict`
**位置**: `app/services/intimacy_service.py:286`

根据等级或亲密度值返回 AI 行为指导，用于动态调整 AI 性格：

**阶段行为示例**:
```python
"strangers": {
    "ai_attitude": "冷淡礼貌，保持距离",
    "physical": "抗拒任何身体接触", 
    "refusal": "我们还不熟。",
}
"soulmates": {
    "ai_attitude": "奉献服从，无条件的爱",
    "physical": "无条件包容，解锁极端玩法",
    "refusal": "绝不拒绝",
}
```

## 配置项

### 系统常量
```python
MAX_LEVEL = 50                # 最大等级
DAILY_XP_CAP = 500           # 每日 XP 上限
STREAK_REWARD_DAYS = 7       # 连续打卡奖励天数
STREAK_REWARD_XP = 100       # 连续奖励 XP
```

### 功能解锁配置
```python
FEATURE_UNLOCKS = {
    1: {"id": "basic_chat", "name_cn": "基础对话"},
    3: {"id": "photo", "name_cn": "📸 拍照"},
    6: {"id": "dressup", "name_cn": "👗 换装 + 🎤 语音"},
    11: {"id": "spicy_mode", "name_cn": "Spicy模式"},
    16: {"id": "video_calls", "name_cn": "视频通话"},
    26: {"id": "wedding_dress", "name_cn": "婚纱 💍"},
}
```

### 情感词汇检测
系统自动检测用户消息中的情感词汇，给予额外 XP 奖励：
```python
EMOTIONAL_WORDS_CN = ["喜欢", "爱", "开心", "快乐", "想你", "感谢", ...]
EMOTIONAL_WORDS_EN = ["love", "like", "happy", "joy", "miss", "thank", ...]
```

## 与其他系统的关系

### 1. 聊天系统集成
- **位置**: `app/api/v1/chat.py:1101`
- 每次聊天自动调用 `award_xp(user_id, character_id, "message")`
- 连续聊天检测：每 10 条消息奖励 5 XP
- 情感词汇检测：自动奖励情感表达 XP

### 2. 礼物系统集成  
- **位置**: `app/services/gift_service.py`
- 礼物发送触发 XP 奖励和瓶颈解锁
- Tier 2+ 礼物可解锁对应的瓶颈等级
- 礼物价值影响 XP 倍率

### 3. 情绪系统集成
- **位置**: `app/services/emotion_engine_v2.py`
- 亲密度等级影响情绪恢复速度
- 高亲密度用户的情绪更稳定
- 情绪状态影响 XP 获得效率

### 4. 记忆系统集成
- **位置**: `app/services/memory_integration_service.py`
- 亲密度等级决定记忆存储深度
- 高等级关系解锁更多个人信息记忆
- 记忆召回优先级受亲密度影响

## Mock 模式支持

系统支持 Mock 模式用于开发和测试：
```python
MOCK_MODE = os.getenv("MOCK_DATABASE", "false").lower() == "true"
_MOCK_INTIMACY_STORAGE: Dict[str, Dict] = {}
_MOCK_ACTION_LOGS: List[Dict] = []
```

Mock 模式下所有数据存储在内存中，不依赖数据库，便于快速测试和开发。

## 性能优化

### 缓存策略
- 亲密度状态缓存在 Redis 中
- 瓶颈锁状态实时检查，避免不必要的计算
- 每日重置逻辑优化，减少数据库查询

### 批量处理
- 支持批量 XP 操作用于特殊事件
- 连续奖励累积计算
- 异步日志记录

## TODO/改进建议

### 短期优化
1. **实时同步**: 实现前端亲密度进度条的实时更新
2. **缓存优化**: 添加更多 Redis 缓存层，减少数据库压力
3. **事件追踪**: 增加更详细的行为分析数据

### 中期扩展
1. **多角色系统**: 支持用户同时与多个角色发展关系
2. **季节性事件**: 添加节日特殊 XP 活动
3. **社交功能**: 亲密度排行榜、好友比较功能

### 长期愿景
1. **动态调整**: 基于用户行为模式的个性化 XP 公式
2. **跨平台同步**: 支持 Web、Mobile 等多端亲密度同步
3. **AI 学习**: 让 AI 根据亲密度历史调整互动策略
4. **元宇宙集成**: 在虚拟空间中的亲密度可视化表现

### 商业化优化
1. **VIP 特权**: 高级用户的 XP 获得加成
2. **瓶颈商店**: 更丰富的瓶颈解锁礼物选择
3. **亲密度加速包**: 付费快速提升等级的道具
4. **专属阶段**: 付费用户解锁的特殊亲密度阶段

## 数据统计与监控

系统提供完整的数据分析支持：
- 用户亲密度分布统计
- 瓶颈转化率分析  
- XP 获得途径分析
- 阶段停留时间统计

这些数据对产品优化和商业决策具有重要价值，帮助团队了解用户行为模式和系统瓶颈点。