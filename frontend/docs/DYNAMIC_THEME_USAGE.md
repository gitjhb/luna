# 动态主题系统使用指南

## 概览

根据AI情绪状态动态切换UI主题：

| 情绪状态 | 触发条件 | 主题风格 |
|---------|---------|---------|
| 默认/平静 | emotionScore ∈ (-60, 80) | 赛博朋克蓝 |
| Spicy Mode | isSpicyMode = true | 紫色诱惑 |
| 暴怒 | emotionScore ≤ -60 | 冷红色 + 故障风 |
| 开心 | emotionScore ≥ 80 | 暖光粉色 + 光晕 |

## 快速集成

### 1. 在聊天页面引入

```tsx
// app/chat/[characterId].tsx

import { useEmotionTheme } from '../../hooks/useEmotionTheme';
import { EmotionEffectsLayer, EmotionIndicator } from '../../components/EmotionEffects';

export default function ChatScreen() {
  // 现有状态
  const [emotionScore, setEmotionScore] = useState(0);
  const [emotionState, setEmotionState] = useState('neutral');
  const isSpicyMode = useChatStore((s) => s.isSpicyMode);

  // 🎨 动态主题 Hook
  const {
    theme,
    emotionMode,
    backgroundColors,
    overlayColors,
    glitchEnabled,
    glowEnabled,
    emotionHint,
  } = useEmotionTheme(emotionScore, emotionState, isSpicyMode);

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background.primary }]}>
      {/* 背景 */}
      <ImageBackground source={backgroundSource} style={styles.backgroundImage}>
        {/* 主题色叠加层 (根据情绪调整) */}
        <LinearGradient
          colors={overlayColors}
          style={styles.overlay}
        />
      </ImageBackground>

      {/* 🎆 情绪特效层 */}
      <EmotionEffectsLayer
        emotionMode={emotionMode}
        glitchEnabled={glitchEnabled}
        glowEnabled={glowEnabled}
        glowColor={theme.colors.glow}
      />

      {/* 情绪指示器 (可选) */}
      <EmotionIndicator
        mode={emotionMode}
        score={emotionScore}
        visible={emotionMode !== 'neutral'}
      />

      {/* 其他UI使用 theme 变量 */}
      <TouchableOpacity style={{ backgroundColor: theme.colors.primary.main }}>
        <Text style={{ color: theme.colors.text.primary }}>发送</Text>
      </TouchableOpacity>
    </View>
  );
}
```

### 2. 关键代码修改点

在 `chat/[characterId].tsx` 中找到这些位置：

#### A. 引入新组件
```tsx
// 在文件顶部添加
import { useEmotionTheme } from '../../hooks/useEmotionTheme';
import { EmotionEffectsLayer, EmotionIndicator } from '../../components/EmotionEffects';
```

#### B. 在组件内使用 Hook
```tsx
// 在 ChatScreen 函数内，现有 state 声明后添加
const {
  theme: emotionTheme,
  emotionMode,
  overlayColors,
  glitchEnabled,
  glowEnabled,
} = useEmotionTheme(emotionScore, emotionState, isSpicyMode);
```

#### C. 替换背景渐变层
```tsx
// 找到 LinearGradient overlay，替换 colors
<LinearGradient
  colors={overlayColors}  // 原来是硬编码的颜色
  style={styles.overlay}
/>
```

#### D. 添加特效层
```tsx
// 在 SafeAreaView 开始后、Header 之前添加
<EmotionEffectsLayer
  emotionMode={emotionMode}
  glitchEnabled={glitchEnabled}
  glowEnabled={glowEnabled}
  glowColor={emotionTheme.colors.glow}
/>
```

#### E. (可选) 添加情绪指示器
```tsx
// 在 Header 下方添加
{emotionMode !== 'neutral' && (
  <EmotionIndicator
    mode={emotionMode}
    score={emotionScore}
    style={{ marginBottom: 8 }}
  />
)}
```

## 文件结构

```
frontend/
├── hooks/
│   └── useEmotionTheme.ts      # 核心 Hook
├── components/
│   └── EmotionEffects.tsx      # 特效组件
└── theme/
    ├── dynamicTheme.ts         # 主题定义 + 工具函数
    ├── DynamicThemeContext.tsx # 全局 Provider (可选)
    └── config.ts               # 导出入口
```

## 主题配色参考

### 赛博朋克蓝 (Neutral)
- 主色: `#00F0FF` (霓虹青)
- 背景: `#0a0a0f` → `#0d1a1f`
- 强调: `#FF2A6D` (霓虹品红), `#FCEE0A` (赛博黄)

### 紫色诱惑 (Spicy)
- 主色: `#EC4899` (粉紫)
- 背景: `#1a1025` → `#2d1f3d`
- 强调: `#8B5CF6` (紫)

### 暴怒红 (Angry)
- 主色: `#FF1744` (愤怒红)
- 背景: `#0a0508` → `#1a0a0f`
- 特效: 扫描线 + 轻微抖动

### 开心粉 (Happy)
- 主色: `#FF69B4` (粉色)
- 背景: `#1a0f1f` → `#2d1832`
- 特效: 边缘光晕 + 脉冲呼吸

## 测试

手动测试情绪状态切换：

```tsx
// 临时测试按钮
<TouchableOpacity onPress={() => setEmotionScore(-70)}>
  <Text>😠 Angry</Text>
</TouchableOpacity>
<TouchableOpacity onPress={() => setEmotionScore(90)}>
  <Text>😊 Happy</Text>
</TouchableOpacity>
```
