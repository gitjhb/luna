# Luna 支付系统设计文档

> **状态**: 正式设计 | **最后更新**: 2026-03-02  
> **适用范围**: luna-backend, luna-frontend, luna-web, telegram bot

---

## 一、核心设计决策

### 1. User ID 格式

```
✅ 正确: Firebase UID 作为唯一主键
   例: hdND1zeZOkdP74SdypFmmuF0SA03

❌ 错误: 加任何前缀 (fb-, user-, etc.)
```

**原则**: 前端传什么，后端存什么，不做任何转换。
- 数据库主键: `user_id = firebase_uid`
- Stripe metadata: `firebase_uid = firebase_uid`
- RevenueCat app_user_id: `firebase_uid`

---

### 2. 订阅等级

| Tier | 名称 | 说明 |
|------|------|------|
| `free` | 免费版 | 基础体验，有限额度 |
| `basic` | 基础版 | 解锁付费功能 |
| `premium` | 高级版 | 全部功能 + 更多额度 |

**注意**: 月卡/季卡/年卡是**价格维度**，不是等级维度，不要混淆。

```
# 正确理解
basic_monthly, basic_yearly     → 都是 basic tier
premium_monthly, premium_yearly → 都是 premium tier
```

---

### 3. 支付入口

| 平台 | 支付方式 | 原因 |
|------|----------|------|
| iOS App | Apple IAP (RevenueCat) | Apple 强制要求 |
| Android App | Google Play IAP (RevenueCat) | Google 强制要求 |
| Web | Stripe Checkout | 费率低 (~2.9%) |
| Telegram | Stripe Checkout | 费率低 (~2.9%) |

**RevenueCat 角色**: IAP 的管理层，统一 Apple/Google 回调，同步订阅状态。

---

## 二、关键实现要点

### ⭐ 最重要的一条

> **Stripe Checkout 创建时必须写 `firebase_uid` 到 metadata**  
> 没有这个，webhook 收到事件就不知道是哪个用户。

```python
# ✅ 正确
stripe.checkout.Session.create(
    ...
    metadata={
        "firebase_uid": user_id,  # 必须！
        "tier": "basic",
    },
    subscription_data={
        "metadata": {
            "firebase_uid": user_id,  # subscription 也要！
            "tier": "basic",
        }
    },
    client_reference_id=user_id,  # 备用
)

# ❌ 错误: metadata 为空
stripe.checkout.Session.create(
    ...
    metadata={},  # webhook 找不到用户！
)
```

---

### Email 处理

**原则**: 登录时存好，不要用时再查。

```python
# 登录 API
async def firebase_login(request):
    firebase_uid = verify_token(request.id_token)
    email = decoded_token.get("email")  # 从 Firebase token 拿
    
    # 存到数据库
    user = await get_or_create_user(
        user_id=firebase_uid,
        email=email,  # 必须存！
    )
    
    # 创建 Stripe Customer 时也存
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=email,
            metadata={"firebase_uid": firebase_uid}
        )
        user.stripe_customer_id = customer.id
```

---

### Stripe Webhook 处理

```python
async def handle_checkout_completed(session):
    # 1. 从 metadata 拿 user_id
    firebase_uid = session["metadata"].get("firebase_uid")
    
    # 2. 如果 metadata 没有，fallback 到 client_reference_id
    if not firebase_uid:
        firebase_uid = session.get("client_reference_id")
    
    # 3. 还是没有？记录错误，不能处理
    if not firebase_uid:
        logger.error("No firebase_uid in checkout session!")
        return {"error": "Missing firebase_uid"}
    
    # 4. 拿到 user_id 后正常处理
    tier = session["metadata"].get("tier", "basic")
    await activate_subscription(firebase_uid, tier)
```

---

## 三、Stripe 配置

### Products (Test Mode)

| 产品 | Product ID | 用途 |
|------|------------|------|
| Basic Plan | `prod_TyaqYmJJSZjbV9` | basic tier 订阅 |
| Premium | `prod_TyaZ8zAFF70OqP` | premium tier 订阅 |
| Moonshard | `prod_U2Kb5naLvLxRzb` | 虚拟货币 (后期) |

### Prices

| Plan | Price ID | 价格 | Tier |
|------|----------|------|------|
| Basic Monthly | `price_1T3Zy1BGtpEcBypWJlKScOSD` | $X.XX | basic |
| Premium Monthly | `price_1T3ZzKBGtpEcBypWCQBVv5Ek` | $XX.XX | premium |

### Webhook Events

必须启用:
- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`

---

## 四、RevenueCat 配置

### App User ID

```
app_user_id = firebase_uid  # 不加前缀！
```

### Entitlements

| Entitlement | 对应 Tier |
|-------------|-----------|
| `basic` | basic |
| `premium` | premium |

### Webhook

RevenueCat → Luna Backend `/api/v1/payment/revenuecat/webhook`

---

## 五、数据库 Schema

### users 表

```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,  -- Firebase UID, 无前缀
    email TEXT NOT NULL,
    stripe_customer_id TEXT,   -- Stripe Customer ID
    ...
);
```

### user_subscriptions 表

```sql
CREATE TABLE user_subscriptions (
    user_id TEXT PRIMARY KEY REFERENCES users(user_id),
    tier TEXT NOT NULL DEFAULT 'free',  -- free/basic/premium
    expires_at TIMESTAMP,
    auto_renew BOOLEAN DEFAULT true,
    payment_provider TEXT,  -- 'stripe' / 'apple' / 'google'
    provider_subscription_id TEXT,
    ...
);
```

---

## 六、Tier 权益配置

```python
TIER_BENEFITS = {
    "free": {
        "daily_credits": 10,
        "nsfw_enabled": False,
        "premium_characters": False,
        "extended_memory": False,
    },
    "basic": {
        "daily_credits": 50,
        "nsfw_enabled": True,
        "premium_characters": False,
        "extended_memory": True,
    },
    "premium": {
        "daily_credits": 200,
        "nsfw_enabled": True,
        "premium_characters": True,
        "extended_memory": True,
        "priority_response": True,
    },
}
```

---

## 七、代码清理 Checklist

### 需要删除/修改

- [ ] 删除所有 `fb-` 前缀逻辑
- [ ] 删除 `vip` tier 相关代码
- [ ] 确保 Stripe checkout 必须有 `firebase_uid` metadata
- [ ] 登录时存储 email 和创建 Stripe Customer
- [ ] Webhook 优先从 metadata 读 `firebase_uid`

### 相关文件

- `backend/app/services/stripe_service.py`
- `backend/app/services/subscription_service.py`
- `backend/app/middleware/auth_middleware.py`
- `backend/app/api/v1/auth.py`
- `backend/app/api/v1/payment.py`

---

## 八、测试验证

### 必须通过的测试

1. **新用户订阅流程**
   - 登录 → 存储 email → Stripe Checkout → Webhook → 订阅激活
   - 验证: user_id 一致，email 正确，tier 正确

2. **Portal 访问**
   - 登录 → 点击 Manage Subscription → 打开 Stripe Portal
   - 验证: 显示正确的订阅信息和账单历史

3. **RevenueCat 同步**
   - App 内购买 → RevenueCat Webhook → 订阅激活
   - 验证: tier 同步到 Luna 后端

---

*文档结束*
