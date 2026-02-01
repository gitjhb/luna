# Luna Design System

## 设计理念

**赛博朋克 × 亲密感**
- 深色背景 + 霓虹高光
- 硬朗边角 + 柔和发光
- 科技感 + 温暖交互

---

## 颜色系统

### 主色调 - 霓虹青
```
main:  #00F0FF  ← 主按钮、高亮边框、重要文字
light: #5CFFFF
dark:  #00B8C4
glow:  rgba(0, 240, 255, 0.4)
```

### 强调色 - 霓虹品红
```
main:  #FF2A6D  ← 警告、通知徽章
light: #FF5A8A
dark:  #D4205A
```

### 次要色 - 霓虹紫
```
main:  #8B5CF6  ← 等级、亲密度、Spicy Mode
light: #A78BFA
dark:  #7C3AED
```

### 警示色 - 赛博黄
```
main:  #FCEE0A  ← 金币、重要提示
```

### 背景层级
```
base:     #0a0a0f  ← 最深层
elevated: #0d1117  ← 卡片、浮层
surface:  #161b22  ← 表面元素
```

---

## 间距系统

```
xs:   4px
sm:   8px
md:   12px
lg:   16px
xl:   20px
2xl:  24px
3xl:  32px
4xl:  48px
```

---

## 圆角系统 (赛博朋克风格 - 硬朗)

```
none: 0
sm:   4px   ← 小元素
md:   8px   ← 按钮、输入框
lg:   12px  ← 卡片
xl:   16px  ← 大卡片、弹窗
2xl:  20px  ← 底部面板
full: 9999  ← 徽章、圆形按钮
```

---

## 字体系统

### 尺寸
```
xs:   11px  ← 徽章、小标签
sm:   13px  ← 次要文字
base: 15px  ← 正文
md:   16px  ← 输入框
lg:   18px  ← 标题
xl:   20px  ← 大标题
2xl:  24px  ← 特大标题
3xl:  30px  ← 数字展示
```

### 字重
```
normal:    400
medium:    500
semibold:  600  ← 按钮、强调
bold:      700  ← 标题
extrabold: 800  ← 数字
```

---

## 组件规范

### 按钮

**Primary (主按钮)**
- 背景: #00F0FF
- 文字: #0a0a0f
- 圆角: 8px

**Secondary (描边按钮)**
- 背景: transparent
- 边框: #00F0FF
- 文字: #00F0FF

**Ghost (透明按钮)**
- 背景: rgba(0, 240, 255, 0.1)
- 文字: #00F0FF

**Gradient (渐变按钮)**
- 渐变: #00F0FF → #FF2A6D
- 文字: #fff

---

### 消息气泡

**用户消息**
```
背景: rgba(0, 240, 255, 0.12)
边框: rgba(0, 240, 255, 0.2)
圆角: 16px (右下 4px)
```

**AI消息**
```
背景: rgba(255, 255, 255, 0.08)
边框: rgba(255, 255, 255, 0.1)
圆角: 16px (左下 4px)
```

---

### 卡片

**Base**
```
背景: #0d1117
边框: rgba(255, 255, 255, 0.1)
圆角: 12px
```

**Highlighted**
```
背景: #0d1117
边框: rgba(0, 240, 255, 0.3)
发光: #00F0FF
```

**Glass**
```
背景: rgba(255, 255, 255, 0.08)
边框: rgba(255, 255, 255, 0.12)
```

---

### 徽章

**Primary** - 青色背景
**Secondary** - 紫色透明背景
**Warning** - 黄色透明背景 (金币)
**Error** - 红色透明背景

---

## 渐变预设

```typescript
// 主渐变 (按钮、CTA)
primary: ['#00F0FF', '#FF2A6D']

// 强调渐变
accent: ['#FF2A6D', '#8B5CF6']

// 紫色渐变 (Spicy Mode)
purple: ['#8B5CF6', '#EC4899']

// 金色渐变 (金币、VIP)
gold: ['#FFD700', '#FFA500']

// 背景渐变
background: ['#0a0a0f', '#0d1a1f', '#0a0a0f']
```

---

## 动态主题

根据AI情绪状态自动切换：

| 情绪 | 触发条件 | 主题色 |
|-----|---------|-------|
| 默认 | emotionScore ∈ (-60, 80) | 赛博朋克蓝 |
| Spicy | isSpicyMode = true | 紫色诱惑 |
| 暴怒 | emotionScore ≤ -60 | 冷红 + Glitch |
| 开心 | emotionScore ≥ 80 | 暖光粉 + Glow |

---

## 使用方法

```typescript
// 导入设计系统
import { colors, spacing, radius, typography, shadows, gradients } from '../theme/designSystem';

// 在样式中使用
const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.background.base,
    padding: spacing.lg,
    borderRadius: radius.lg,
  },
  title: {
    fontSize: typography.size.lg,
    fontWeight: typography.weight.bold,
    color: colors.text.primary,
  },
});
```

```typescript
// 使用 UI 组件
import { Button, Card, Badge, IconButton } from '../components/ui';

<Button 
  title="发送" 
  variant="gradient" 
  onPress={handleSend}
  icon="send"
/>

<Card variant="highlighted">
  <Text>高亮卡片</Text>
</Card>

<Badge text="LV 5" variant="secondary" />
```

---

## 文件结构

```
theme/
├── designSystem.ts      # 设计系统常量
├── themes.ts            # 主题配置
├── dynamicTheme.ts      # 动态主题逻辑
├── DynamicThemeContext.tsx
└── config.ts            # 导出入口

components/
├── ui/
│   └── index.tsx        # 通用 UI 组件
├── EmotionEffects.tsx   # 情绪特效
├── MessageBubble.tsx
└── ...

hooks/
└── useEmotionTheme.ts   # 情绪主题 Hook

app/chat/
└── chatStyles.ts        # 聊天页面统一样式
```
