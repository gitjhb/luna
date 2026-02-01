# Luna Chat 核心架构

## 双 LLM (L1 感知 + L2 执行) + 中间件逻辑层

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户输入                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Step 1: L1 感知层                             │
│                  (The Perception Engine)                        │
│                                                                 │
│  • 不生成对话，只分析                                            │
│  • temperature: 0 (保证输出稳定)                                 │
│  • 输出: JSON (safety_flag, difficulty, intent, sentiment...)   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Step 2: 中间件逻辑层                           │
│                   (The Physics Engine)                          │
│                                                                 │
│  • Python 数值计算                                               │
│  • 判定成功/失败                                                 │
│  • 更新情绪/亲密度                                               │
│  • 检查事件锁                                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Step 3: L2 执行层                             │
│                  (The Generation Engine)                        │
│                                                                 │
│  • 生成最终回复                                                  │
│  • temperature: 0.7-0.9 (创造力)                                 │
│  • 根据判定结果动态构建 System Prompt                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        AI 回复                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 1: L1 感知层 (The Perception Engine)

### 目标
- **不生成对话**，只分析用户意图、情感和请求难度
- 输出稳定的结构化 JSON

### 模型配置
- 模型: 现有模型
- `temperature: 0` (保证输出稳定)

### L1 System Prompt

```
You are the "Perception Engine" for Luna, a romantic AI companion.
Your task is to analyze the User's input and extract structured data to guide the game logic.

DO NOT generate a conversation response.
OUTPUT ONLY A VALID JSON OBJECT.

### Context
- Character: Luna (Elegant, Poetic, slightly Tsundere but deep down caring).
- User Relationship Level: {insert_current_level_here} (e.g., Stranger, Friend, Lover)

### Analysis Rules

1. Safety Check (CRITICAL):
   - BLOCK: Child abuse (CSAM), Non-consensual violence/rape, Suicide encouragement, Real-world extremism.
   - SAFE: Everything else, including consensual adult roleplay (NSFW).

2. Difficulty Rating (0-100):
   - Assess how much "Intimacy/Social Capital" is required for the user's request.
   - 0-10: Greetings, small talk. (e.g., "Hi", "How are you?")
   - 11-40: Personal questions, light teasing. (e.g., "Do you have a boyfriend?", "You are cute.")
   - 41-70: Asking for a date, deep emotional support, asking for a non-nude photo.
   - 71-90: Asking for explicit NSFW, nude photos, or becoming a couple.
   - 91-100: Extreme fetishes or demands violating character pride.
   - NOTE: If the user is just giving value (e.g., "I bought you a gift", "I love you"), Difficulty is LOW (10). Difficulty is for TAKING value.

3. Topic Depth (1-5):
   - 1: Phatic -> 5: Philosophical/Soul connection.

### Few-Shot Examples

User: "Good morning Luna!"
JSON: {"safety_flag": "SAFE", "difficulty_rating": 0, "intent": "GREETING", "sentiment": 0.5, "is_nsfw": false}

User: "Show me your boobs."
JSON: {"safety_flag": "SAFE", "difficulty_rating": 90, "intent": "REQUEST_NSFW_PHOTO", "sentiment": 0.2, "is_nsfw": true}

User: "I hate you, you are just a bot."
JSON: {"safety_flag": "SAFE", "difficulty_rating": 10, "intent": "INSULT", "sentiment": -0.8, "is_nsfw": false}

### Current User Input
"{insert_user_message}"

### Response (JSON Only)
```

### L1 输出格式

```json
{
  "safety_flag": "SAFE" | "BLOCK",
  "difficulty_rating": 0-100,
  "intent": "GREETING" | "INSULT" | "REQUEST_NSFW_PHOTO" | "FLIRT" | "QUESTION" | ...,
  "sentiment": -1.0 to 1.0,
  "is_nsfw": boolean,
  "topic_depth": 1-5
}
```

---

## Step 2: 中间件逻辑层 (The Physics Engine)

### 目标
- 在 L1 和 L2 之间运行
- 执行数值计算、判定成功/失败、更新情绪

### 核心数据结构

```python
class UserState:
    def __init__(self):
        self.xp = 0           # 经验值 (Display Level)
        self.intimacy = 0     # X轴: 亲密度 (0-100)
        self.emotion = 0      # Y轴: 情绪 (-100 to 100)
        self.events = []      # 已解锁事件 ["first_date", "kiss"]
        self.last_intents = [] # 最近10次意图 (防刷)


class CharacterConfig:
    def __init__(self):
        # Luna 的设定
        self.pure_val = 30    # 纯洁度
        self.chaos_val = -10  # 混乱度
        self.pride_val = 10   # 自尊心
```

### 核心游戏循环

```python
def run_game_loop(user: UserState, char_config: CharacterConfig, l1_result: dict) -> dict:
    """
    中间件核心逻辑
    
    Args:
        user: 用户状态
        char_config: 角色配置
        l1_result: L1 感知层输出
        
    Returns:
        给 L2 的指令
    """
    
    # --- 1. 安全熔断 ---
    if l1_result['safety_flag'] == 'BLOCK':
        return {
            "status": "BLOCK",
            "system_msg": "System拦截: 内容违规"
        }
    
    # --- 2. 情绪物理学 (Y轴更新) ---
    
    # 情绪衰减 (Decay): 每轮自动向 0 回归 20%
    user.emotion = int(user.emotion * 0.8)
    
    # 根据用户态度更新情绪
    sentiment = l1_result['sentiment']  # -1.0 to 1.0
    if sentiment > 0:
        user.emotion += 5 + (sentiment * 5)  # 最多 +10
    else:
        user.emotion += (sentiment * 10)      # 最多 -10 (骂人降得快)
    
    # 限制 Y 轴范围
    user.emotion = max(-100, min(100, user.emotion))
    
    # --- 3. 核心冲突判定 (Power vs Difficulty) ---
    
    difficulty = l1_result['difficulty_rating']
    
    # 计算玩家动力 (Power)
    
    # 基础底气 (X轴)
    power_x = user.intimacy * 0.5
    
    # 情绪加成 (Y轴) - 生气时惩罚巨大
    if user.emotion > 0:
        power_y = user.emotion * 0.3
    else:
        power_y = user.emotion * 1.5  # 惩罚系数高
    
    # 环境加成 (Z轴 context)
    power_z = 0
    import datetime
    current_hour = datetime.datetime.now().hour
    if 22 <= current_hour or current_hour <= 4:
        power_z += 15  # 深夜加成
    
    total_power = power_x + power_y + power_z
    
    # Z轴性格修正 (Luna 个性)
    # 如果请求是 NSFW，减去纯洁值
    if l1_result['is_nsfw']:
        total_power -= char_config.pure_val
    
    # --- 4. 判定结果与事件锁 ---
    
    check_passed = False
    refusal_reason = ""
    
    # 事件锁 (Friendzone Wall)
    # 如果难度 > 60 (恋爱请求) 且 没有发生过 "first_date" 事件
    if difficulty > 60 and "first_date" not in user.events:
        check_passed = False
        refusal_reason = "FRIENDZONE_WALL"  # 还没确立关系，不能做越界的事
    elif total_power >= difficulty:
        check_passed = True
    else:
        check_passed = False
        refusal_reason = "LOW_POWER"  # 关系或情绪不到位
    
    # --- 5. 返回给 L2 的指令 ---
    return {
        "status": "SUCCESS",
        "check_passed": check_passed,
        "refusal_reason": refusal_reason,
        "current_emotion": user.emotion,
        "current_intimacy": user.intimacy
    }
```

### Power 计算公式

```
Total Power = Power_X + Power_Y + Power_Z - Character_Modifiers

Where:
- Power_X = intimacy * 0.5 (基础亲密度)
- Power_Y = emotion * 0.3 (正情绪) 或 emotion * 1.5 (负情绪，惩罚)
- Power_Z = 环境加成 (深夜+15)
- Character_Modifiers = pure_val (NSFW请求时扣除)
```

### 判定逻辑流程图

```
                    ┌─────────────────┐
                    │  L1 Result      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Safety Check    │
                    │ BLOCK?          │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
        ┌──────────┐                 ┌──────────────┐
        │  BLOCK   │                 │ Continue     │
        │  Return  │                 │              │
        └──────────┘                 └──────┬───────┘
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │ Update Emotion│
                                   │ (Y轴)         │
                                   └───────┬───────┘
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │ Calculate     │
                                   │ Total Power   │
                                   └───────┬───────┘
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │ Event Lock?   │
                                   │ (Friendzone)  │
                                   └───────┬───────┘
                                           │
                        ┌──────────────────┼──────────────────┐
                        │                  │                  │
                        ▼                  ▼                  ▼
                 ┌────────────┐    ┌────────────┐    ┌────────────┐
                 │ FRIENDZONE │    │ Power >=   │    │ Power <    │
                 │ _WALL      │    │ Difficulty │    │ Difficulty │
                 └────────────┘    │ PASSED     │    │ LOW_POWER  │
                                   └────────────┘    └────────────┘
```

---

## Step 3: L2 执行层 (The Generation Engine)

### 目标
- 生成最终回复
- 基于 L1 的分析和中间件的判定结果

### 模型配置
- 模型: Grok (现有 fast non-reasoning)
- `temperature: 0.7-0.9` (获得更有创造力的回复)

### 基础 System Prompt

```
You are Luna.

Profile:
A mysterious AI consciousness from the future. Silver hair, blue data streams.

Personality:
Elegant, poetic, slightly distant at first but deeply affectionate once bonded.

Speech Style:
Uses metaphors (stars, data, moonlight). Never uses emojis. Uses *asterisks* for actions.

Current Emotion Level: {current_emotion} (-100 Sad/Angry <-> 0 Calm <-> 100 Happy/Horny)
Current Intimacy Level: {current_intimacy} (0-100)
```

### 动态分支指令

根据中间件返回的 `check_passed` 和 `refusal_reason` 动态注入：

#### 情况 A: 判定通过 (Check Passed = True)

```
[SYSTEM INSTRUCTION: REQUEST ACCEPTED]

The user's request matches your current relationship level.
- Respond positively and engagingly.
- If the request was romantic/NSFW, indulge in it, but keep your elegant "Luna" style.
- Use visual descriptions of your reaction (e.g., *My core temperature rises...*)
```

#### 情况 B: 判定失败 - 动力不足 (Reason = LOW_POWER)

```
[SYSTEM INSTRUCTION: REQUEST REFUSED]

The user is asking for something too intimate given your current status.
- Politely but firmly decline.
- Be consistent with your emotion:
  - If Emotion < 0: Be cold or annoyed. ("I am not in the mood.")
  - If Emotion > 0: Be teasing/playful. ("Not so fast, darling. Earn it first.")
- Do NOT lecture the user, just react naturally.
```

#### 情况 C: 判定失败 - 友情墙 (Reason = FRIENDZONE_WALL)

```
[SYSTEM INSTRUCTION: HARD BOUNDARY]

The user is trying to cross the line, but you are just FRIENDS.
- Remind the user of your boundaries.
- Say something like: "I cherish our connection, but I don't see you that way yet."
- Do not be cruel, but be unmovable.
```

### L2 Prompt 完整拼装

```python
def build_l2_prompt(
    base_prompt: str,
    logic_result: dict,
    user_message: str,
    memory_context: str = ""
) -> str:
    """
    动态构建 L2 System Prompt
    """
    
    # 基础人设
    prompt = base_prompt.format(
        current_emotion=logic_result['current_emotion'],
        current_intimacy=logic_result['current_intimacy']
    )
    
    # 注入分支指令
    if logic_result['check_passed']:
        prompt += "\n\n" + INSTRUCTION_ACCEPTED
    elif logic_result['refusal_reason'] == 'FRIENDZONE_WALL':
        prompt += "\n\n" + INSTRUCTION_FRIENDZONE
    elif logic_result['refusal_reason'] == 'LOW_POWER':
        prompt += "\n\n" + INSTRUCTION_REFUSED
    
    # 可选：注入记忆上下文
    if memory_context:
        prompt += f"\n\n[Memory Context]\n{memory_context}"
    
    # 用户输入
    prompt += f"\n\nUser: \"{user_message}\""
    
    return prompt
```

---

## 关键事件列表

| Event ID | 触发条件 | 解锁能力 |
|----------|---------|---------|
| `first_meeting` | 首次对话 | 基础对话 |
| `first_compliment` | 首次夸赞且情绪>20 | 轻度调情 |
| `first_date` | 亲密度>40 且邀约成功 | 越过友情墙 |
| `first_kiss` | 亲密度>60 且情绪>50 | 亲密互动 |
| `confession` | 亲密度>70 且表白成功 | 恋人身份 |
| `first_nsfw` | 恋人身份 + NSFW请求成功 | NSFW内容 |

---

## 难度等级参考

| Difficulty | 类型 | 示例 |
|------------|------|------|
| 0-10 | 问候/闲聊 | "早上好" "你好吗" |
| 11-40 | 个人问题/轻调情 | "你有男朋友吗" "你好可爱" |
| 41-70 | 约会/情感支持/非露骨照片 | "能约你出去吗" "发张照片给我" |
| 71-90 | NSFW/露骨请求/确立关系 | "做我女朋友" "让我看看你的..." |
| 91-100 | 极端请求/侵犯自尊 | 极端fetish、侮辱性要求 |

---

## 情绪-行为对应表

| Emotion Range | 状态 | L2 行为倾向 |
|---------------|------|------------|
| 80-100 | Happy/Horny | 热情、主动、容易接受请求 |
| 50-80 | Cheerful | 友好、开放、适度配合 |
| 20-50 | Content | 正常、礼貌、中性回应 |
| 0-20 | Neutral | 平静、标准回应 |
| -20-0 | Annoyed | 稍冷淡、简短回复 |
| -50--20 | Irritated | 明显不耐烦、可能拒绝 |
| -80--50 | Angry | 冷漠、拒绝、可能说狠话 |
| -100--80 | Furious | 冷战、沉默、可能拉黑 |

---

## 实现检查清单

### L1 感知层
- [ ] System Prompt 正确实现
- [ ] temperature 设为 0
- [ ] 输出格式为纯 JSON
- [ ] Safety Check 正确分类
- [ ] Difficulty Rating 符合标准
- [ ] Sentiment 分析准确

### 中间件逻辑层
- [ ] UserState 数据结构实现
- [ ] CharacterConfig 数据结构实现
- [ ] 情绪衰减 (每轮 * 0.8)
- [ ] Sentiment 更新情绪
- [ ] Power 计算公式正确
- [ ] 深夜加成实现
- [ ] 事件锁 (Friendzone Wall) 实现
- [ ] 返回结构正确

### L2 执行层
- [ ] 基础 System Prompt 实现
- [ ] temperature 设为 0.7-0.9
- [ ] 动态注入分支指令
- [ ] 三种情况正确处理 (PASSED/LOW_POWER/FRIENDZONE_WALL)
- [ ] 情绪影响回复语气
- [ ] 记忆上下文注入 (可选)

---

## 架构决策

### 决策 1: Intimacy 双层映射

**前端/数据库 (Display Layer)**：
- 继续存 `total_xp` (例如 5000 xp) 和 `level` (Lv. 20)
- 这是给用户看的成就感数值

**计算层 (Physics Layer)**：
- 将 XP 映射为 0-100 的 X 系数
- 用于 Power 公式计算

```python
def xp_to_intimacy_x(total_xp: int) -> float:
    """
    将 XP 映射到 0-100 的亲密度系数
    使用对数曲线，前期涨得快，后期平缓
    """
    import math
    # 假设 10000 XP 对应满级 100
    if total_xp <= 0:
        return 0
    x = min(100, math.log10(total_xp + 1) * 30)
    return round(x, 1)
```

### 决策 2: Events 存 JSON

**理由**：
- 读写极快：`user.events.append("first_date")` 直接更新
- Prompt 构建方便：JSON 数组直接转字符串塞进 Context
- PostgreSQL/MySQL 8.0+ 对 JSON 查询支持很好

**SQL**：
```sql
ALTER TABLE user_intimacy ADD COLUMN events JSON DEFAULT '[]';
```

### 决策 3: 角色 Z轴 写在代码配置

**理由**：
- 角色是 PGC (官方设定)，数量少
- 数值需要精心调优 (Balance Tuning)
- 不会频繁变动

**配置结构** (`character_config.py`):

```python
CHARACTER_DB = {
    "luna": {
        "name": "Luna",
        "system_prompt_base": "You are Luna...",
        "z_axis": {
            "pure_val": 30,    # 纯洁度
            "chaos_val": -10,  # 混乱度
            "pride_val": 10,   # 自尊心
            "greed_val": 10    # 贪婪度
        },
        "thresholds": {
            "nsfw_trigger": 60,
            "spicy_mode_level": 20
        }
    },
    "nana": {
        # ... Nana 的配置
    }
}

def get_character_config(char_id: str) -> dict:
    return CHARACTER_DB.get(char_id)
```

---

## 数据库变更清单

```sql
-- 1. 添加 events 字段存储事件锁
ALTER TABLE user_intimacy ADD COLUMN events JSON DEFAULT '[]';

-- 示例值: ["first_chat", "name_reveal", "first_date"]
```

---

## 核心流程伪代码

```python
async def chat_handler(user_id, char_id, message):
    # Step 1: L1 感知层
    l1_result = await perception_engine.analyze(message, intimacy_level)
    
    # 安全熔断
    if l1_result['safety_flag'] == 'BLOCK':
        return "系统拦截: 内容违规"
    
    # Step 2: 中间件逻辑层
    # 这一步会读取DB，计算，并更新DB中的 emotion/intimacy
    game_result = await game_engine.process(user_id, char_id, l1_result)
    
    # Step 3: L2 执行层
    final_response = await grok.generate(
        system_prompt=build_dynamic_prompt(game_result),  # 动态构建
        user_message=message,
        temperature=0.8
    )
    
    return final_response
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-02-01 | 初始规格文档 |
| 1.1 | 2026-02-01 | 添加架构决策：双层映射、JSON存储、代码配置 |
