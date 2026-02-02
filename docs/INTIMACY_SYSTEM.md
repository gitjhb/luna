# Luna 亲密度系统盘点

## 当前存在的变量

| 变量 | 类型 | 范围 | 用途 |
|------|------|------|------|
| `xp` | int | 0-∞ | 累计经验值 |
| `intimacy_level` | int | 1-50+ | **展示用**等级（UI 显示） |
| `intimacy_x` | float | 0-100 | **内部用**亲密度系数（Power 计算） |

### intimacy_x 计算公式
```python
intimacy_x = min(100, math.log10(xp + 1) * 30)
```

| XP | intimacy_x | 大约需要 |
|----|------------|----------|
| 0 | 0 | - |
| 10 | 30 | 几句话 |
| 100 | 60 | 几天聊天 |
| 1000 | 90 | 几周 |
| 10000 | 100 | 长期 |

---

## 当前混乱的阶段定义

### 1. prompt_builder._get_relationship_stage (用 intimacy_x 0-100)
```python
< 10: "Strangers"
10-24: "Acquaintances"
25-44: "Friends"
45-64: "Close Friends"
65-84: "Romantic Interest"
85+: "Lovers"
```

### 2. perception_engine._get_relationship_level (用 intimacy_level 1-50)
```python
≤ 3: "Stranger"
4-10: "Acquaintance"
11-25: "Friend"
26-40: "Close Friend"
41+: "Intimate"
```

### 3. prompt_builder.get_intimacy_guidance (用 intimacy 0-100)
```python
< 20: "barely know"
20-39: "getting to know"
40-59: "comfortable"
60-79: "deep bond"
80+: "soul-deep"
```

### 4. 友情墙判断 (用 intimacy_x 0-100)
```python
< 40: FRIENDZONE_STRANGER
≥ 40: FRIENDZONE_FLIRTY
```

### 5. 事件解锁 (用 intimacy_x 0-100)
```python
first_date: intimacy_x >= 40
first_confession: intimacy_x >= 60
first_kiss: intimacy_x >= 70
```

---

## 问题

1. **两套"等级"概念**
   - `intimacy_level` (1-50) 给用户看
   - `intimacy_x` (0-100) 内部计算
   - 两者没有直接对应关系！

2. **阈值不统一**
   - 不同功能用不同的阈值
   - 40 在一个地方是"暧昧"，在另一个地方是"普通朋友"

3. **阶段名称不一致**
   - Stranger / Strangers
   - Friend / Friends
   - Close Friend / Close Friends / Intimate

---

## 建议：统一标准

### 方案 A：以 intimacy_x (0-100) 为准

| intimacy_x | 阶段 | 中文 | 可解锁 |
|------------|------|------|--------|
| 0-19 | Stranger | 陌生人 | first_chat |
| 20-39 | Acquaintance | 熟人 | - |
| 40-59 | Friend | 朋友 | first_date |
| 60-79 | Close Friend | 好友/暧昧 | first_confession |
| 80-89 | Romantic | 恋人 | first_kiss |
| 90+ | Lover | 深爱 | first_nsfw |

### 方案 B：以 intimacy_level (1-50) 为准

| Level | 阶段 | intimacy_x 约等于 |
|-------|------|-------------------|
| 1-5 | 陌生人 | 0-30 |
| 6-15 | 熟人 | 30-50 |
| 16-25 | 朋友 | 50-65 |
| 26-35 | 暧昧 | 65-80 |
| 36-45 | 恋人 | 80-95 |
| 46+ | 深爱 | 95+ |

---

## 待决策

1. 以哪个为主？`intimacy_x` 还是 `intimacy_level`？
2. 阶段划分具体阈值？
3. 友情墙在哪个阶段可以突破？
4. 各阶段的拒绝风格？
