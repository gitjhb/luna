/**
 * Subscription Modal - RevenueCat Integration
 * 
 * Full-screen Luna background with glassmorphism style
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Modal,
  Alert,
  ActivityIndicator,
  Dimensions,
  ImageBackground,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { PurchasesPackage } from 'react-native-purchases';
import { useRevenueCat } from '../hooks/useRevenueCat';
import { revenueCatService, ENTITLEMENTS } from '../services/revenueCatService';
import { presentPaywall } from './RevenueCatPaywall';
import { presentCustomerCenter } from './CustomerCenter';
import { useUserStore } from '../store/userStore';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// ============================================================================
// Types
// ============================================================================

interface SubscriptionModalRCProps {
  visible: boolean;
  onClose: () => void;
  onSubscribeSuccess?: () => void;
  useRevenueCatPaywall?: boolean;
  highlightFeature?: string;
}

// ============================================================================
// Premium Features
// ============================================================================

const PREMIUM_FEATURES = [
  'Unlimited chats',
  'Tailored personality & memories',
  'Private voice & photo sharing',
  'Exclusive roleplay scenarios',
  'Experience New Features',
];

// ============================================================================
// Component
// ============================================================================

export const SubscriptionModalRC: React.FC<SubscriptionModalRCProps> = ({
  visible,
  onClose,
  onSubscribeSuccess,
  useRevenueCatPaywall = false,
}) => {
  const { setSubscription } = useUserStore();
  const {
    isLoading,
    packages,
    isPro,
    purchase,
    restore,
    refresh,
  } = useRevenueCat();

  const [selectedPackage, setSelectedPackage] = useState<PurchasesPackage | null>(null);
  const [purchasing, setPurchasing] = useState(false);
  const [restoring, setRestoring] = useState(false);

  useEffect(() => {
    if (visible) {
      refresh();
      setSelectedPackage(null);
      
      // If already Pro, show customer center instead
      if (isPro) {
        handleShowCustomerCenter();
      }
    }
  }, [visible, refresh, isPro]);

  const handleShowCustomerCenter = async () => {
    await presentCustomerCenter({
      onSubscriptionChanged: (customerInfo) => {
        // Update local state if subscription changed
        const hasLunaPro = !!customerInfo.entitlements.active[ENTITLEMENTS.LUNA_PRO];
        if (!hasLunaPro) {
          setSubscription('free', undefined);
        }
      },
    });
    onClose();
  };

  useEffect(() => {
    if (packages.length > 0 && !selectedPackage) {
      const yearly = packages.find(p => 
        p.identifier.toLowerCase().includes('yearly') ||
        p.identifier.toLowerCase().includes('annual')
      );
      setSelectedPackage(yearly || packages[0]);
    }
  }, [packages, selectedPackage]);

  useEffect(() => {
    if (visible && useRevenueCatPaywall) {
      handleShowRevenueCatPaywall();
    }
  }, [visible, useRevenueCatPaywall]);

  const handleShowRevenueCatPaywall = async () => {
    await presentPaywall({
      onPurchaseSuccess: (customerInfo) => {
        const hasLunaPro = !!customerInfo.entitlements.active[ENTITLEMENTS.LUNA_PRO];
        if (hasLunaPro) {
          const expDate = customerInfo.entitlements.active[ENTITLEMENTS.LUNA_PRO]?.expirationDate;
          setSubscription('premium', expDate ?? undefined);
          onSubscribeSuccess?.();
        }
      },
    });
    onClose();
  };

  const handlePurchase = async () => {
    if (!selectedPackage) return;

    setPurchasing(true);
    try {
      const result = await purchase(selectedPackage);

      if (result.success) {
        const hasLunaPro = !!result.customerInfo.entitlements.active[ENTITLEMENTS.LUNA_PRO];
        if (hasLunaPro) {
          const expDate = result.customerInfo.entitlements.active[ENTITLEMENTS.LUNA_PRO]?.expirationDate;
          setSubscription('premium', expDate ?? undefined);
        }

        Alert.alert(
          '🎉 Welcome to Luna Premium!',
          'Enjoy unlimited access to all features.',
          [{ text: 'Start', onPress: () => {
            onSubscribeSuccess?.();
            onClose();
          }}]
        );
      } else if (!result.userCancelled) {
        Alert.alert('Purchase Failed', revenueCatService.getErrorMessage(result.error));
      }
    } catch (error) {
      Alert.alert('Purchase Failed', 'Please try again later.');
    } finally {
      setPurchasing(false);
    }
  };

  const handleRestore = async () => {
    setRestoring(true);
    try {
      const restored = await restore();
      if (restored && isPro) {
        Alert.alert('Restored!', 'Your subscription has been restored.', [{ text: 'OK', onPress: onClose }]);
      } else {
        Alert.alert('Nothing to Restore', 'No previous subscription found.');
      }
    } finally {
      setRestoring(false);
    }
  };

  const isYearly = (pkg: PurchasesPackage) => {
    const id = pkg.identifier.toLowerCase();
    return id.includes('yearly') || id.includes('annual');
  };

  if (useRevenueCatPaywall) return null;

  const monthlyPkg = packages.find(p => !isYearly(p));
  const yearlyPkg = packages.find(p => isYearly(p));

  return (
    <Modal
      visible={visible}
      animationType="fade"
      presentationStyle="fullScreen"
      onRequestClose={onClose}
    >
      <ImageBackground
        source={require('../assets/images/luna-premium-bg.jpg')}
        style={styles.container}
        resizeMode="cover"
      >
        {/* Gradient overlay */}
        <LinearGradient
          colors={['rgba(0,0,0,0.1)', 'rgba(0,0,0,0.4)', 'rgba(0,0,0,0.85)']}
          locations={[0, 0.4, 0.7]}
          style={styles.gradient}
        />

        {/* Close Button */}
        <TouchableOpacity onPress={onClose} style={styles.closeButton}>
          <Ionicons name="close" size={28} color="#FFFFFF" />
        </TouchableOpacity>

        {/* Content */}
        <View style={styles.content}>
          {/* Title */}
          <Text style={styles.title}>Unlock Luna Premium</Text>

          {/* Features */}
          <View style={styles.features}>
            {PREMIUM_FEATURES.map((feature, index) => (
              <View key={index} style={styles.featureRow}>
                <Ionicons name="checkmark-circle" size={22} color="#10B981" />
                <Text style={styles.featureText}>{feature}</Text>
              </View>
            ))}
          </View>

          {/* Package Options */}
          {isLoading ? (
            <ActivityIndicator size="large" color="#FFFFFF" style={{ marginVertical: 20 }} />
          ) : (
            <View style={styles.packagesContainer}>
              {/* Yearly Option */}
              {yearlyPkg && (
                <TouchableOpacity
                  style={[styles.packageRow, selectedPackage?.identifier === yearlyPkg.identifier && styles.packageRowSelected]}
                  onPress={() => setSelectedPackage(yearlyPkg)}
                >
                  <View style={styles.packageLeft}>
                    <View style={[styles.radio, selectedPackage?.identifier === yearlyPkg.identifier && styles.radioSelected]}>
                      {selectedPackage?.identifier === yearlyPkg.identifier && <View style={styles.radioInner} />}
                    </View>
                    <View>
                      <Text style={styles.packageName}>Year</Text>
                      <Text style={styles.packageSub}>Only ${(yearlyPkg.product.price / 12).toFixed(2)}/mo</Text>
                    </View>
                  </View>
                  <View style={styles.packageRight}>
                    <View style={styles.discountBadge}>
                      <Text style={styles.discountText}>19% OFF</Text>
                    </View>
                    <Text style={styles.packagePrice}>{yearlyPkg.product.priceString}/yr</Text>
                  </View>
                </TouchableOpacity>
              )}

              {/* Monthly Option */}
              {monthlyPkg && (
                <TouchableOpacity
                  style={[styles.packageRow, selectedPackage?.identifier === monthlyPkg.identifier && styles.packageRowSelected]}
                  onPress={() => setSelectedPackage(monthlyPkg)}
                >
                  <View style={styles.packageLeft}>
                    <View style={[styles.radio, selectedPackage?.identifier === monthlyPkg.identifier && styles.radioSelected]}>
                      {selectedPackage?.identifier === monthlyPkg.identifier && <View style={styles.radioInner} />}
                    </View>
                    <Text style={styles.packageName}>Month</Text>
                  </View>
                  <Text style={styles.packagePrice}>{monthlyPkg.product.priceString}/mo</Text>
                </TouchableOpacity>
              )}
            </View>
          )}

          {/* CTA Button */}
          <TouchableOpacity
            style={[styles.ctaButton, purchasing && styles.ctaButtonDisabled]}
            onPress={handlePurchase}
            disabled={!selectedPackage || purchasing}
          >
            <LinearGradient
              colors={['#60A5FA', '#A78BFA']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.ctaGradient}
            >
              {purchasing ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <Text style={styles.ctaText}>Continue</Text>
              )}
            </LinearGradient>
          </TouchableOpacity>

          {/* Bottom Links */}
          <View style={styles.bottomLinks}>
            <TouchableOpacity onPress={handleRestore} disabled={restoring}>
              <Text style={styles.linkText}>{restoring ? 'Restoring...' : 'Restore Purchases'}</Text>
            </TouchableOpacity>
            <Text style={styles.linkDot}>·</Text>
            <TouchableOpacity><Text style={styles.linkText}>Terms</Text></TouchableOpacity>
            <Text style={styles.linkDot}>·</Text>
            <TouchableOpacity><Text style={styles.linkText}>Privacy</Text></TouchableOpacity>
          </View>
        </View>
      </ImageBackground>
    </Modal>
  );
};

// ============================================================================
// Styles
// ============================================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  gradient: {
    ...StyleSheet.absoluteFillObject,
  },
  closeButton: {
    position: 'absolute',
    top: 50,
    right: 20,
    padding: 8,
    zIndex: 10,
  },
  content: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    paddingHorizontal: 24,
    paddingBottom: 40,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#FFFFFF',
    textAlign: 'center',
    marginBottom: 24,
  },
  features: {
    marginBottom: 24,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 14,
  },
  featureText: {
    fontSize: 16,
    color: '#E5E7EB',
    marginLeft: 12,
  },
  packagesContainer: {
    marginBottom: 20,
  },
  packageRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(31, 41, 55, 0.8)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  packageRowSelected: {
    borderColor: '#8B5CF6',
    backgroundColor: 'rgba(139, 92, 246, 0.15)',
  },
  packageLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  packageRight: {
    alignItems: 'flex-end',
  },
  radio: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: '#6B7280',
    marginRight: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioSelected: {
    borderColor: '#8B5CF6',
  },
  radioInner: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#8B5CF6',
  },
  packageName: {
    fontSize: 17,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  packageSub: {
    fontSize: 13,
    color: '#9CA3AF',
    marginTop: 2,
  },
  packagePrice: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  discountBadge: {
    backgroundColor: '#EC4899',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    marginBottom: 4,
  },
  discountText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  ctaButton: {
    borderRadius: 14,
    overflow: 'hidden',
    marginBottom: 16,
  },
  ctaButtonDisabled: {
    opacity: 0.6,
  },
  ctaGradient: {
    paddingVertical: 16,
    alignItems: 'center',
  },
  ctaText: {
    fontSize: 18,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  bottomLinks: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  linkText: {
    fontSize: 13,
    color: 'rgba(255, 255, 255, 0.5)',
  },
  linkDot: {
    color: 'rgba(255, 255, 255, 0.3)',
    marginHorizontal: 10,
  },
});

export default SubscriptionModalRC;
