# RevenueCat Integration Guide

## Overview

Luna uses RevenueCat for subscription management. This replaces the previous `react-native-iap` implementation with a more robust, cross-platform solution.

## Configuration

- **API Key**: `test_FBObZPlGuTyizNXjsTFNnnHSqNc`
- **Entitlement**: `Luna Pro`
- **Products**: `monthly`, `yearly`, `lifetime`

## Installation

Already installed via:
```bash
npx expo install react-native-purchases react-native-purchases-ui
```

## File Structure

```
frontend/
├── services/
│   ├── revenueCatService.ts      # Core service (init, purchase, restore)
│   └── revenuecat/
│       └── index.ts              # Centralized exports
├── components/
│   ├── RevenueCatPaywall.tsx     # Paywall presentation
│   ├── CustomerCenter.tsx        # Subscription management UI
│   └── SubscriptionModalRC.tsx   # Custom subscription modal
├── hooks/
│   └── useRevenueCat.ts          # React hook for subscription state
└── providers/
    └── RevenueCatProvider.tsx    # Context provider (optional)
```

## Quick Start

### 1. Initialize (already done in `_layout.tsx`)

```tsx
import { revenueCatService } from '../services/revenueCatService';

useEffect(() => {
  revenueCatService.init(userId);
}, [userId]);
```

### 2. Check Pro Access

```tsx
import { useRevenueCat, useIsPro } from '../hooks/useRevenueCat';

// Full hook with all features
const { isPro, showPaywall, products } = useRevenueCat();

// Simple hook for quick checks
const isPro = useIsPro();
```

### 3. Show Paywall

```tsx
// Option A: RevenueCat's pre-built paywall (recommended)
import { presentPaywall } from '../components/RevenueCatPaywall';

const handleUpgrade = async () => {
  const result = await presentPaywall();
  if (result.purchased) {
    // User subscribed!
  }
};

// Option B: Custom modal
import { SubscriptionModalRC } from '../components/SubscriptionModalRC';

<SubscriptionModalRC 
  visible={showModal}
  onClose={() => setShowModal(false)}
  onSubscribeSuccess={() => console.log('Subscribed!')}
/>
```

### 4. Gate Features

```tsx
import { presentPaywallIfNeeded } from '../components/RevenueCatPaywall';
import { ENTITLEMENTS } from '../services/revenueCatService';

const handleProFeature = async () => {
  const result = await presentPaywallIfNeeded(ENTITLEMENTS.LUNA_PRO);
  
  if (result.purchased || result.restored) {
    // User has access, proceed with feature
    doProFeature();
  }
};
```

### 5. Customer Center (Manage Subscriptions)

```tsx
import { presentCustomerCenter, CustomerCenterButton } from '../components/CustomerCenter';

// Programmatic
await presentCustomerCenter();

// Or use the button component
<CustomerCenterButton onSubscriptionChanged={(info) => {
  console.log('Subscription changed:', info);
}} />
```

## API Reference

### revenueCatService

| Method | Description |
|--------|-------------|
| `init(userId?)` | Initialize SDK |
| `login(userId)` | Associate purchases with user |
| `logout()` | Reset to anonymous |
| `getCustomerInfo()` | Get current subscription status |
| `getOfferings()` | Get available products |
| `purchasePackage(pkg)` | Purchase a subscription |
| `restorePurchases()` | Restore previous purchases |
| `hasLunaPro()` | Check if user has Luna Pro |
| `getErrorMessage(error)` | Get user-friendly error message |

### useRevenueCat Hook

```tsx
const {
  // State
  isLoading,
  customerInfo,
  
  // Subscription status
  isPro,
  isSubscribed,
  expirationDate,
  willRenew,
  
  // Products
  products,
  packages,
  
  // Actions
  purchase,
  restore,
  refresh,
  
  // UI Helpers
  showPaywall,
  showPaywallIfNeeded,
  showCustomerCenter,
} = useRevenueCat();
```

## Entitlements

| ID | Description |
|----|-------------|
| `Luna Pro` | Main subscription entitlement |

## Products

| ID | Type | Description |
|----|------|-------------|
| `monthly` | Subscription | Monthly subscription |
| `yearly` | Subscription | Yearly subscription (40% off) |
| `lifetime` | Non-renewing | One-time lifetime purchase |

## Testing

### Sandbox Testing

1. Use TestFlight (iOS) or Internal Testing (Android)
2. RevenueCat automatically uses sandbox for debug builds
3. Test purchases don't charge real money

### Test Scenarios

- [ ] New subscription purchase
- [ ] Subscription renewal
- [ ] Subscription cancellation
- [ ] Restore purchases
- [ ] Upgrade/downgrade
- [ ] Lifetime purchase

## Dashboard Configuration

Configure products and offerings in the [RevenueCat Dashboard](https://app.revenuecat.com):

1. **Products**: Create products matching App Store Connect / Play Console
2. **Entitlements**: Create "Luna Pro" entitlement
3. **Offerings**: Create default offering with all packages
4. **Paywalls**: Design paywall in dashboard (optional)

## Webhooks (Backend)

RevenueCat sends webhooks for subscription events. Configure in backend:

```python
@router.post("/webhooks/revenuecat")
async def revenuecat_webhook(request: Request):
    payload = await request.json()
    event_type = payload["event"]["type"]
    app_user_id = payload["event"]["app_user_id"]
    
    if event_type == "INITIAL_PURCHASE":
        await activate_subscription(app_user_id)
    elif event_type == "RENEWAL":
        await extend_subscription(app_user_id)
    elif event_type in ["CANCELLATION", "EXPIRATION"]:
        await expire_subscription(app_user_id)
```

## Troubleshooting

### Products not loading

1. Check API key is correct
2. Verify products are configured in RevenueCat dashboard
3. Ensure offerings are set up correctly

### Purchases failing

1. Check sandbox account setup
2. Verify bundle ID matches App Store Connect
3. Check RevenueCat logs for errors

### Restore not working

1. Ensure same Apple/Google account
2. Check subscription is still active
3. Verify app user ID mapping

## Migration from react-native-iap

The old `iapService.ts` can be removed. Key changes:

| Old (react-native-iap) | New (RevenueCat) |
|------------------------|------------------|
| `iapService.init()` | `revenueCatService.init()` |
| `iapService.getProducts()` | `revenueCatService.getOfferings()` |
| `iapService.purchaseSubscription(sku)` | `revenueCatService.purchasePackage(pkg)` |
| `iapService.restorePurchases()` | `revenueCatService.restorePurchases()` |
| Manual receipt verification | Automatic via RevenueCat |
