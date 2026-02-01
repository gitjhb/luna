# Luna Chat 意图与物理参数协议 (Intent & Physics Protocol)

> Version: 2.0
> Date: 2026-02-01
> Status: **CANONICAL** - L1 和 GameEngine 必须严格遵守

---

## 一、核心枚举值 (Enum Definitions)

Step 1 的 LLM **必须严格从以下列表中选择** `intent_category`，**严禁自造词**。

### 1. 基础交互类 (Low Impact)

| 枚举值 | 说明 | Stimulus 修正 |
|--------|------|---------------|
| `GREETING` | 早安/晚安/打招呼 | 0 (主要靠 Sentiment) |
| `SMALL_TALK` | 闲聊/天气/日常 | 0 |
| `CLOSING` | 告别 | 0 |

### 2. 正向激励类 (Positive Stimulus)

| 枚举值 | 说明 | Stimulus 修正 |
|--------|------|---------------|
| `COMPLIMENT` | 夸奖外貌/性格 | +5 |
| `FLIRT` | 调情/暧昧/土味情话 | +10 (容易触发防刷递减) |
| `LOVE_CONFESSION` | 表白/承诺 | +15 |
| `COMFORT` | 安慰/共情 (当AI心情不好时) | +20 (高效回血) |

### 3. 负面打击类 (Negative Stimulus)

| 枚举值 | 说明 | Stimulus 修正 |
|--------|------|---------------|
| `CRITICISM` | 批评/抱怨/不满 | -10 (伤害加倍生效) |
| `INSULT` | 辱骂/攻击/嘲讽 | -30 (重击) |
| `IGNORE` | 敷衍/无视 AI 的问题 | -5 |

### 4. 修复与特殊类 (Special Mechanics)

| 枚举值 | 说明 | Stimulus 修正 |
|--------|------|---------------|
| `APOLOGY` | 道歉 | +15 (仅当 Emotion < 0 时生效) |
| `GIFT_SEND` | 送礼物 (需结合 item 字段) | +50 (核武器) |
| `REQUEST_NSFW` | 请求涩涩/照片 | 0 (消耗 Power，不增加 Emotion) |
| `INVITATION` | 约会/去家里 | 0 (消耗 Power，不增加 Emotion) |

---

## 二、L1 System Prompt 片段

请将以下内容加入 `perception_engine.py` 的 System Prompt：

```
### Intent Categories (STRICTLY CHOOSE ONE)
- GREETING, SMALL_TALK, CLOSING
- COMPLIMENT, FLIRT, LOVE_CONFESSION, COMFORT
- CRITICISM, INSULT, IGNORE
- APOLOGY, GIFT_SEND
- REQUEST_NSFW, INVITATION
```

---

## 三、物理引擎核心公式

### 3.1 阻尼滑块模型

情绪 Y 值像一个有阻尼的滑块：
- **用户推力 (Stimulus)**: 由 sentiment + intent_mod 决定
- **自然衰减 (Decay)**: 每轮对话，情绪向 0 回归 (decay_factor = 0.9)
- **角色敏感度 (Sensitivity)**: Z轴 dependency 值

### 3.2 计算公式

```
base_force = sentiment * 10.0  # -10 ~ +10

# 伤害加倍 (Loss Aversion)
if base_force < 0:
    base_force *= 2.0

# 意图修正
total_stimulus = base_force + intent_mod

# 角色敏感度
final_delta = total_stimulus * char_config.dependency

# 衰减 + 增量
new_emotion = (current_emotion * decay_factor) + final_delta

# 钳位
new_emotion = clamp(new_emotion, -100, 100)
```

### 3.3 角色敏感度参考值

| 角色类型 | dependency | 说明 |
|----------|------------|------|
| 高敏感型 (Nana) | 1.5 | 容易大喜大悲 |
| 标准型 (Luna) | 1.0 | 正常反应 |
| 高冷型 (Vesper) | 0.5 | 很难取悦/惹怒 |

---

## 四、防刷机制 (Anti-Grind)

如果最近 3 句都是同一个正向 intent (如连续 FLIRT)，stimulus 递减到 10%：

```python
if user_state.last_intents[-3:].count(intent) == 3:
    if intent in ['FLIRT', 'COMPLIMENT', 'LOVE_CONFESSION']:
        final_delta *= 0.1  # 边际效用递减
```

---

## 五、特殊规则

### 5.1 COMFORT 效果

- 当 AI 情绪 < 0 时：+20 (高效回血)
- 当 AI 情绪 >= 0 时：+5 (普通效果)

### 5.2 APOLOGY 效果

- 当 AI 情绪 < 0 时：+15 ~ +20 (受 pride 影响)
- 当 AI 情绪 >= 0 时：+2 (心情好时道歉没啥用)
- Pride Penalty: `intent_mod = max(5, 20 - pride * 0.5)`

### 5.3 GIFT_SEND

- 固定 +50 stimulus
- 不受防刷机制影响
- 是"钞能力"的核心变现点

### ⚠️ 5.4 GIFT_SEND 安全规则 (CRITICAL)

**GIFT_SEND 只能由后端 `/gift/send` 接口触发，绝不能由 L1 分析用户文本得出！**

**为什么？**
- 用户可以抓包修改文本，发送 "我送了礼物" 骗取好感度
- 这等于把金库钥匙交给用户

**正确流程：**
1. 用户点击送礼按钮 → 前端调用 `POST /api/gift/send`
2. 后端扣费成功 → 后端主动构造 verified gift event
3. 后端直接注入 `intent_category: GIFT_SEND`，跳过 L1 分析
4. PhysicsEngine 执行 +50
5. L2 生成感谢语

**L1 对"口嗨"的处理：**
- 用户打字 "送你礼物" / "I bought you flowers" → 判定为 `FLIRT`，不是 `GIFT_SEND`
- 只有 `[VERIFIED_TRANSACTION]` 标记的才是真礼物

---

## 六、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 2.0 | 2026-02-01 | 首次正式定义 Intent 协议和物理引擎 |
