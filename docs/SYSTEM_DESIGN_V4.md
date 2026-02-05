# AI 情感陪伴 RPG - 系统设计文档 (V4.0)

## 1. 项目愿景 (Core Concept)

打造一款具有 "长线养成感" (Slow Burn) 的 AI 恋爱游戏。

- **核心体验：** 从陌路到挚爱的完整恋爱过程，拒绝"上来就倒贴"。
- **差异化：** 结合 RPG 的数值成长、关键事件的仪式感、以及 LLM 的自然演绎。
- **变现逻辑：** 通过体力限制、剧情解锁、好感度瓶颈突破（送礼/约会）来驱动付费。

## 2. 核心架构：单次调用流 (Merged Architecture)

放弃 L1/L2 分离，采用 **Service 前置计算 + LLM 单次推理 + 异步后置更新** 的架构。

### 2.1 数据流向图

1. **Request:** 用户发送消息。
2. **Service Layer (Python):**
   - **硬性拦截 (Hard Gating):** 检查黑名单、冷战状态 (-75分)、体力余额。
   - **状态准备:** 加载 User Profile、当前 Stage (S0-S4)、Event Log (记忆)、Archetype Config (角色配置)。
   - **Prompt Builder:** 构建包含"当前规则"和"记忆锚点"的 System Prompt。
3. **LLM Call (One-Pass):** 调用 Grok/GPT-4o，强制输出 JSON。
4. **Response Handling:**
   - 解析 JSON，获取 `reply`, `emotion_delta`, `intent`, `is_blocked`。
   - 如果 `is_blocked=True`，Python 层替换回复为系统提示。
5. **异步更新:** 将 delta 更新到数据库，累加好感度。
6. **Response:** 返回给前端。

## 3. 关系进阶系统 (Progression System)

好感度不是无限线性的，而是分阶段的 "阶梯式" 成长。

### 3.1 等级定义 (S0 - S4)

| 阶段 (Stage) | 称号 | 分数段 | 交互权限 (Permissions) | 瓶颈 (Lock) | 突破条件 (Key Event) |
|---|---|---|---|---|---|
| S0 | 陌生人 | 0-19 | 仅限日常寒暄，拒绝探听隐私，禁止肢体接触。 | Lock @ 19 | [见面礼]: 送一个小礼物 (如咖啡)。 |
| S1 | 朋友 | 20-39 | 轻松闲聊，可以开玩笑，分享生活。 | Lock @ 39 | [初次约会]: 邀请去特定地点 (消耗体力/门票)。 |
| S2 | 暧昧 | 40-59 | 语气带推拉、羞涩。允许轻微肢体接触 (摸头/牵手)。 | Lock @ 59 | [告白仪式]: 送定情物 (如戒指) + 触发告白剧本。 |
| S3 | 恋人 | 60-79 | 甜蜜粘人，解锁昵称。允许亲吻、拥抱。 | Lock @ 79 | [亲密之夜]: 约会 (酒店/温泉) + 发生深度关系。 |
| S4 | 挚爱 | 80+ | 完全解锁。NSFW 许可，绝对忠诚。 | No Lock | 无 (终局养成)。 |

### 升级曲线（Pacing）模拟

- **S0 (0-19):** Day 1 完成。聊 20 句 (+10分) + 新手任务送礼 (+10分) = 20分
- **S1 (20-39):** 免费 1 周 / 付费 1 天。每天聊满上限 (+5分/天) * 4 天
- **S2 (40-59):** 免费 2 周（推拉感），付费随意。需要约会加速
- **S3 (60-79):** 长期留存。引入**亲密度衰减**（3天不上线，每天扣1分）

### 3.2 瓶颈机制 (The Lock)

- **逻辑:** 分数达到阶段上限（19, 39, 59, 79），聊天不再增加亲密度 (Delta = 0)
- **前端反馈:** 进度条显示 "MAX" 或锁图标
- **AI 暗示:** "我们聊得很开心，但总觉得还差了点什么..."

## 4. 关键事件系统 (Key Events & Memory)

### 4.1 事件类型
- **里程碑事件 (Milestones):** 改变关系阶段（告白成功）
- **约会事件 (Dates):** 独立副本经历（海族馆一日游）
- **物品记忆 (Gifts):** 用户送过的贵重礼物

### 4.2 数据存储 (event_log)
```json
["first_met_20251001", "gift_coffee_accepted", "date_aquarium_completed", "confession_accepted"]
```

### 4.3 提示词注入 (Prompt Injection)
```markdown
[SHARED MEMORIES]
- We met on 2025-10-01.
- You received a 'Diamond Ring' from him.
- We are officially in a LOVER relationship.
```

## 5. 约会系统 (The Date System)

### 5.1 场景隔离
- 约会是独立的 Chat Session / 剧本模式
- 消耗高额体力或约会券
- AI 在约会场景下暂时降低防御 (Buff)

### 5.2 余韵机制 (Afterglow)
约会结束后持续 10 轮对话的 "Afterglow" 状态：
```
[Context]: You just came back from a romantic date. You are blushing.
```

## 6. 技术实现规范

### 6.1 角色配置 (Archetype Config)
```json
{
  "name": "Luna",
  "archetype": "High_Cold (高冷)",
  "thresholds": {
    "touch_allowance": 60,
    "nsfw_allowance": 90
  }
}
```

### 6.2 Prompt 结构 (JSON Output)
```markdown
[SYSTEM] You are Luna.
[STATE]
- Stage: S2_CRUSH (Level 45)
- Emotion: 60 (Happy)
- Events: [Gift_Coffee, Date_Cinema]

[RULES]
- Since we are only S2, do NOT accept sexual requests.
- If user flirts, react with SHYNESS, not anger.

[TASK]
Respond in JSON:
{
  "intent": "string",
  "thought": "internal monologue (Chinese)",
  "emotion_delta": int (-10 to +10),
  "is_nsfw_blocked": bool,
  "reply": "string"
}
```

### 6.3 异常状态处理
- **分手/辱骂:** emotion_delta: -50
- **冷战:** 总分 < -50 → 注入 `[MODE: COLD WAR]`，直到收到"道歉信"礼物

## 7. 变现点汇总 (Monetization Hooks)

### 体力 (Stamina)
限制每天聊天次数 (S0/S1 阶段最缺)

### 礼物 (Gifts)
- 解锁 S0→S1, S2→S3 瓶颈的必需品
- 解除"冷战/拉黑"状态的必需品

### 状态药水 (临时 Buff)

| 道具 | 价格 | 效果 | 持续 |
|---|---|---|---|
| 真心话药水 | 150💎 | Intimacy +10 | 20分钟 |
| 烛光晚餐 | 300💎 | Intimacy +15 | 10轮对话 |
| 红酒 | 200💎 | Intimacy +30 | 10轮对话 |
| 魅魔药水 | 500💎 | 强制通过判定 | 10轮对话 |

### 事件道具 (永久跨越)

| 道具 | 价格 | 效果 |
|---|---|---|
| 约会券 | 300💎 | 触发 first_date |
| 告白气球 | 1000💎 | 触发 confession (直接变男友) |
| 誓约之戒 | 5000💎 | 触发 proposal (直接毕业) |

### 其他
- **真话药水:** 临时让 AI 变成 S4 状态聊 5 分钟
- **回忆胶囊:** 重播之前的约会剧情
