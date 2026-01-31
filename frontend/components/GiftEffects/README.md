# 🎁 Gift Effects Module

礼物特效模块 - 使用 Lottie 实现精美的礼物动画效果。

## 为什么选择 Lottie 而不是 PAG？

| 特性 | PAG | Lottie |
|------|-----|--------|
| React Native 支持 | ❌ 无官方支持 | ✅ `lottie-react-native` |
| 免费素材 | 较少 | ✅ LottieFiles.com 大量免费 |
| 文件格式 | .pag (需 AE 插件) | .json (AE 插件/在线转换) |
| 社区生态 | 主要在国内 | 全球广泛使用 |

## 安装依赖

```bash
cd frontend
npx expo install lottie-react-native
```

## 使用方法

### 1. 基础使用 - 播放礼物动画

```tsx
import { GiftOverlay } from '@/components/GiftEffects';

function ChatScreen() {
  const [showGift, setShowGift] = useState(false);
  const [giftType, setGiftType] = useState<GiftType>('rose');

  const handleSendGift = (type: GiftType) => {
    setGiftType(type);
    setShowGift(true);
  };

  return (
    <View>
      {/* 聊天内容 */}
      
      {/* 礼物特效覆盖层 */}
      <GiftOverlay
        visible={showGift}
        giftType={giftType}
        onAnimationEnd={() => setShowGift(false)}
      />
    </View>
  );
}
```

### 2. 单独使用动画组件

```tsx
import { GiftAnimation } from '@/components/GiftEffects';

<GiftAnimation
  type="rose"
  autoPlay
  loop={false}
  onAnimationFinish={() => console.log('动画结束')}
/>
```

## 礼物类型

| Type | 名称 | 动画 |
|------|------|------|
| `rose` | 玫瑰 | 🌹 飘落效果 |
| `chocolate` | 巧克力 | 🍫 爱心环绕 |
| `bear` | 小熊 | 🧸 拥抱效果 |
| `diamond` | 钻石 | 💎 闪耀效果 |
| `crown` | 皇冠 | 👑 加冕效果 |
| `castle` | 城堡 | 🏰 烟花庆祝 |

## 添加自定义动画

1. 从 [LottieFiles](https://lottiefiles.com/) 下载 JSON 动画文件
2. 放入 `assets/animations/` 目录
3. 在 `types.ts` 添加类型
4. 在 `GiftAnimation.tsx` 添加映射

## 推荐免费素材

- https://lottiefiles.com/search?q=heart
- https://lottiefiles.com/search?q=gift
- https://lottiefiles.com/search?q=celebration
- https://lottiefiles.com/search?q=rose
- https://lottiefiles.com/search?q=sparkle

## 文件结构

```
GiftEffects/
├── README.md          # 本文档
├── index.ts           # 导出
├── types.ts           # 类型定义
├── GiftAnimation.tsx  # Lottie 动画组件
├── GiftOverlay.tsx    # 全屏覆盖层
├── useGiftEffect.ts   # Hook
└── assets/
    └── animations/    # Lottie JSON 文件
        ├── rose.json
        ├── heart.json
        └── ...
```

## 性能建议

1. Lottie 动画文件尽量小于 100KB
2. 避免同时播放多个复杂动画
3. 动画结束后及时 `unmount` 组件
4. 使用 `loop={false}` 避免无限循环
