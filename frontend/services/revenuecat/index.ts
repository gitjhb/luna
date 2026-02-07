/**
 * RevenueCat Integration - Main Export
 * 
 * Centralized exports for all RevenueCat-related functionality.
 * 
 * @example
 * import { 
 *   revenueCatService, 
 *   useRevenueCat, 
 *   presentPaywall,
 *   ENTITLEMENTS 
 * } from '@/services/revenuecat';
 */

// Core Service
export { 
  default as revenueCatService,
  revenueCatService as rcService,
  ENTITLEMENTS,
  PRODUCT_IDS,
  type SubscriptionStatus,
  type SubscriptionProduct,
  type PurchaseResult,
} from '../revenueCatService';

// React Hook
export { 
  default as useRevenueCat,
  useRevenueCat as useSubscription,
  useIsPro,
  useRequirePro,
  type UseRevenueCatReturn,
} from '../../hooks/useRevenueCat';

// Paywall Components
export {
  default as RevenueCatPaywall,
  presentPaywall,
  presentPaywallIfNeeded,
  InlinePaywall,
  PaywallFooter,
  type PaywallResult,
  type RevenueCatPaywallProps,
} from '../../components/RevenueCatPaywall';

// Customer Center
export {
  default as CustomerCenter,
  presentCustomerCenter,
  openSystemSubscriptionManagement,
  CustomerCenterButton,
  SubscriptionInfoCard,
  type CustomerCenterResult,
  type CustomerCenterProps,
} from '../../components/CustomerCenter';

// Subscription Modal
export { 
  default as SubscriptionModalRC,
  SubscriptionModalRC as SubscriptionModal,
} from '../../components/SubscriptionModalRC';

// Re-export useful RevenueCat types
export type { 
  CustomerInfo,
  PurchasesPackage,
  PurchasesOffering,
  PurchasesError,
} from 'react-native-purchases';
