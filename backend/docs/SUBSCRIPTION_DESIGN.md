# Luna 订阅系统设计文档

## 订阅等级

Luna 订阅分 **两档**：

| Tier | 名称 | 价格 | 说明 |
|------|------|------|------|
| `free` | 免费版 | $0 | 基础体验，有限额度 |
| `basic` | 基础版 | $X.XX/月 | 解锁付费功能，日常使用足够 |
| `premium` | 高级版 | $XX.XX/月 | 全部功能 + 更多额度 |

## Stripe 产品映射

| Stripe Product | Product ID | Price ID | Luna Tier |
|----------------|------------|----------|-----------|
| Basic Plan | `prod_TyaqYmJJSZjbV9` | `price_1T3Zy1BGtpEcBypWJlKScOSD` | `basic` |
| Premium | `prod_TyaZ8zAFF70OqP` | `price_1T3ZzKBGtpEcBypWCQBVv5Ek` | `premium` |

## 权益配置

```python
TIER_BENEFITS = {
    "free": {
        "daily_credits": 0,
        "nsfw_enabled": False,
        "premium_characters": False,
        "priority_response": False,
        "extended_memory": False,
    },
    "basic": {
        "daily_credits": 50,
        "nsfw_enabled": True,
        "premium_characters": False,
        "priority_response": False,
        "extended_memory": True,
    },
    "premium": {
        "daily_credits": 200,
        "nsfw_enabled": True,
        "premium_characters": True,
        "priority_response": True,
        "extended_memory": True,
        "early_access": True,
    },
}
```

## 代码位置

- **Tier 枚举 & 权益**: `app/services/subscription_service.py`
- **Stripe 集成**: `app/services/stripe_service.py`
- **Price 映射**: `STRIPE_SUBSCRIPTION_PLANS` 和 `STRIPE_PRICE_TO_TIER`

## 注意事项

1. **不要用 VIP** - 以前的代码有 VIP tier，已废弃
2. **默认 tier 是 basic** - 未知 price_id 默认映射到 basic
3. **Payment Link 支持** - Webhook 会从 `client_reference_id` 获取 user_id

---

*Last updated: 2026-03-02*
