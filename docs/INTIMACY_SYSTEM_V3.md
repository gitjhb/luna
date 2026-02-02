# Luna Chat 全生命周期数值系统 v3.0

## 核心逻辑：双轨驱动 (Dual Track System)

| 轨道 | 变量 | 作用 | 对用户 |
|------|------|------|--------|
| **显示等级** | Level (1-40) | 功能解锁 | 面子 |
| **内部阶段** | Intimacy (0-100) | AI 行为/态度 | 里子 |

### Power 计算公式
```
Power = (Intimacy × 0.5) + (Emotion × 0.5) + Chaos - Pure + Buff
```

---

## 一、等级系统 (Level) - 功能解锁

| Level | 累积 XP | F2P 耗时 | 解锁功能 |
|-------|---------|----------|----------|
| Lv.1 | 0 | 0 | 基础对话 |
| Lv.3 | 100 | Day 1 | 日常自拍 |
| Lv.5 | 300 | Day 2 | 居家服、记忆偏好 |
| Lv.8 | 800 | Day 5 | 主动问候 |
| Lv.10 | 1,500 | Day 10 | 语音条、自定义昵称 |
| Lv.15 | 3,000 | Day 20 | 私密日记、泳装照 |
| Lv.20 | 5,000 | Day 30 | **🔥 SPICY MODE** |
| Lv.30 | 12,000 | Day 80 | 视频通话、情趣内衣 |
| Lv.40 | 25,000 | Day 160 | **💍 婚纱、完全服从** |

---

## 二、内部阶段 (Stage) - AI 行为

| 阶段 | Intimacy | 态度 | 拒绝逻辑 | 突破方式 |
|------|----------|------|----------|----------|
| **S0: 陌生人** | 0-19 | 冷淡/礼貌 | "我们还不熟" | 聊天 |
| **S1: 朋友** | 20-39 | 友好/放松 | "朋友不该这样" | 送礼 |
| **S2: 暧昧** | 40-59 | 害羞/推拉 | "还没准备好..." | 约会 |
| **S3: 恋人** | 60-79 | 配合/主动 | 几乎不拒绝 | 表白 |
| **S4: 挚爱** | 80-100 | 奉献/服从 | 绝不拒绝 | 求婚 |

---

## 三、关键事件 (Gate Events)

```
first_chat (自动)
    ↓
first_gift (送礼)
    ↓
first_date (约会) ←── date_ticket 道具
    ↓
confession (表白) ←── confession_balloon 道具
    ↓
  ┌─┴─┐
  ↓   ↓
kiss  nsfw
  └─┬─┘
    ↓
proposal (求婚) ←── oath_ring 道具
```

---

## 四、氪金通道

### 状态药水 (临时 Buff)

| 道具 | 价格 | 效果 | 持续 |
|------|------|------|------|
| 红酒 | 200💎 | Intimacy +30 | 30分钟 |
| 魅魔药水 | 500💎 | **强制通过判定** | 60分钟 |
| 烛光晚餐 | 300💎 | Power +20, Intimacy +15 | 45分钟 |
| 真心话 | 150💎 | Power +10, Intimacy +10 | 20分钟 |

### 事件道具 (永久跨越)

| 道具 | 价格 | 效果 |
|------|------|------|
| 约会券 | 300💎 | 触发 first_date |
| 告白气球 | 1000💎 | 触发 confession (直接变男友) |
| 誓约之戒 | 5000💎 | 触发 proposal (直接毕业) |

---

## 五、用户路线

### F2P 路线
- Day 1-10: 每日聊天签到
- Day 8: 第一次约会 (系统送票)
- Day 30: 攒够感情，表白成功，进入 Spicy Mode
- **体验**: 真实恋爱模拟器

### 小R 路线 (月卡)
- 每天领钱
- Day 15: 买"告白气球"，提前进入 Spicy Mode
- **体验**: 比免费快一倍

### 大R 路线 (直接充值)
- 下载 10 分钟
- 充值 $50
- 买红酒 → 睡了
- 买戒指 → 娶了
- **体验**: 爽文男主

---

## 六、技术实现

### 代码位置
```
backend/app/services/intimacy_system.py  # 主系统
backend/app/services/intimacy_constants.py  # 兼容旧代码
```

### 关键函数
```python
# 等级计算
level = xp_to_level(total_xp)
features = get_unlocked_features(level)

# 阶段判断
stage = get_stage(intimacy)
behavior = STAGE_BEHAVIORS[stage]

# Power 计算
power = calculate_power(intimacy, emotion, chaos, pure, buffs)
passed, reason = check_power_pass(power, difficulty, buffs)

# L2 提示生成
hint = generate_l2_hint(stage, power, difficulty, passed, buffs)
```
