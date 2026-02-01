/**
 * Chat Screen Styles
 * 
 * 统一的聊天页面样式，基于 Luna Design System
 * 设计风格：赛博朋克 × 亲密感
 */

import { StyleSheet, Platform, Dimensions } from 'react-native';
import { colors, spacing, radius, typography, shadows, gradients } from '../../theme/designSystem';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

export const chatStyles = StyleSheet.create({
  // ============================================================================
  // 容器
  // ============================================================================
  container: {
    flex: 1,
    backgroundColor: colors.background.base,
  },
  backgroundImage: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    height: SCREEN_HEIGHT,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
  },
  safeArea: {
    flex: 1,
  },

  // ============================================================================
  // 头部
  // ============================================================================
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  backButton: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: radius.md,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
  },
  headerCenter: {
    flex: 1,
    alignItems: 'center',
  },
  characterName: {
    fontSize: typography.size.lg,
    fontWeight: typography.weight.semibold,
    color: colors.text.primary,
    textShadowColor: colors.primary.glow,
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 8,
  },
  menuButton: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: radius.md,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
  },

  // ============================================================================
  // 状态栏
  // ============================================================================
  statusBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    backgroundColor: 'rgba(13, 17, 23, 0.8)',
    borderRadius: radius.lg,
    marginHorizontal: spacing.lg,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border.default,
  },
  levelContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  levelRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  levelText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.bold,
    color: colors.secondary.light,
  },
  xpBarContainer: {
    width: 52,
    height: 6,
    backgroundColor: 'rgba(139, 92, 246, 0.2)',
    borderRadius: radius.full,
    overflow: 'hidden',
  },
  xpBar: {
    height: '100%',
    backgroundColor: colors.secondary.main,
    borderRadius: radius.full,
  },
  creditsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(252, 238, 10, 0.12)',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs + 2,
    borderRadius: radius.full,
    borderWidth: 1,
    borderColor: 'rgba(252, 238, 10, 0.2)',
    gap: spacing.xs,
  },
  coinEmoji: {
    fontSize: 14,
  },
  creditsText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.bold,
    color: colors.warning.main,
  },
  addCreditsButton: {
    marginLeft: 2,
  },
  upgradeButton: {
    borderRadius: radius.lg,
    overflow: 'hidden',
  },
  upgradeGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    gap: spacing.xs,
  },
  upgradeIcon: {
    fontSize: 12,
  },
  upgradeText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.bold,
    color: colors.text.primary,
    letterSpacing: 0.5,
  },

  // ============================================================================
  // 消息列表
  // ============================================================================
  messagesList: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
    paddingBottom: spacing.sm,
  },
  messageRow: {
    flexDirection: 'row',
    marginBottom: spacing.md,
    alignItems: 'flex-end',
  },
  messageRowUser: {
    justifyContent: 'flex-end',
  },
  messageRowAI: {
    justifyContent: 'flex-start',
  },
  avatar: {
    width: 34,
    height: 34,
    borderRadius: radius.lg,
    marginRight: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border.accent,
  },
  bubble: {
    maxWidth: SCREEN_WIDTH * 0.72,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radius.xl,
  },
  bubbleUser: {
    backgroundColor: 'rgba(0, 240, 255, 0.12)',
    borderBottomRightRadius: radius.sm,
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.2)',
  },
  bubbleAI: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderBottomLeftRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border.default,
  },
  // 锁定消息样式
  lockedBubble: {
    position: 'relative',
    overflow: 'hidden',
  },
  blurredContent: {
    opacity: 0.3,
  },
  blurredText: {},
  unlockOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: radius.xl,
  },
  unlockBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(139, 92, 246, 0.3)',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.full,
    borderWidth: 1,
    borderColor: colors.secondary.glow,
    gap: spacing.sm,
  },
  unlockText: {
    color: colors.text.primary,
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
  messageText: {
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.relaxed,
  },
  messageTextUser: {
    color: colors.text.primary,
  },
  messageTextAI: {
    color: 'rgba(255, 255, 255, 0.92)',
  },
  typingBubble: {
    paddingVertical: spacing.sm,
  },
  typingText: {
    color: colors.primary.main,
    fontSize: typography.size.sm,
    fontStyle: 'italic',
  },

  // ============================================================================
  // 操作按钮
  // ============================================================================
  actionButtonsRow: {
    flexDirection: 'row',
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.sm,
    gap: spacing.md,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 240, 255, 0.08)',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.2)',
    gap: spacing.sm,
  },
  actionButtonEmoji: {
    fontSize: 16,
  },
  actionButtonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
    color: colors.primary.main,
  },

  // ============================================================================
  // 输入区域
  // ============================================================================
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.lg,
    gap: spacing.md,
  },
  inputWrapper: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: radius['2xl'],
    borderWidth: 1,
    borderColor: colors.border.default,
    paddingHorizontal: spacing.xl,
    paddingVertical: Platform.OS === 'ios' ? spacing.md : spacing.sm,
    minHeight: 48,
    justifyContent: 'center',
  },
  inputWrapperFocused: {
    borderColor: colors.primary.main,
    backgroundColor: 'rgba(0, 240, 255, 0.04)',
  },
  input: {
    fontSize: typography.size.md,
    color: colors.text.primary,
    maxHeight: 100,
  },
  sendButton: {
    borderRadius: radius['2xl'],
    overflow: 'hidden',
  },
  sendButtonDisabled: {
    opacity: 0.4,
  },
  sendButtonGradient: {
    width: 48,
    height: 48,
    justifyContent: 'center',
    alignItems: 'center',
  },

  // ============================================================================
  // Modal 通用样式
  // ============================================================================
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: colors.background.elevated,
    borderTopLeftRadius: radius['2xl'],
    borderTopRightRadius: radius['2xl'],
    maxHeight: SCREEN_HEIGHT * 0.85,
    paddingBottom: 34,
    borderWidth: 1,
    borderBottomWidth: 0,
    borderColor: colors.border.default,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xl,
    paddingBottom: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.default,
  },
  modalTitle: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
    color: colors.text.primary,
  },
  modalCloseButton: {
    width: 36,
    height: 36,
    borderRadius: radius.md,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalScroll: {
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.lg,
  },

  // ============================================================================
  // 升级弹窗
  // ============================================================================
  levelUpOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing['2xl'],
  },
  levelUpContent: {
    backgroundColor: colors.background.elevated,
    borderRadius: radius['2xl'],
    padding: spacing['2xl'],
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.secondary.glow,
    ...shadows.glow(colors.secondary.main, 0.3),
    width: '100%',
    maxWidth: 320,
  },
  levelUpEmoji: {
    fontSize: 64,
    marginBottom: spacing.lg,
  },
  levelUpTitle: {
    fontSize: typography.size['2xl'],
    fontWeight: typography.weight.bold,
    color: colors.text.primary,
    marginBottom: spacing.sm,
  },
  levelUpLevel: {
    fontSize: typography.size['3xl'],
    fontWeight: typography.weight.extrabold,
    color: colors.secondary.light,
    marginBottom: spacing.lg,
  },
  levelUpDesc: {
    fontSize: typography.size.base,
    color: colors.text.secondary,
    textAlign: 'center',
    marginBottom: spacing.xl,
  },
  levelUpButton: {
    borderRadius: radius.lg,
    overflow: 'hidden',
    width: '100%',
  },
  levelUpButtonGradient: {
    paddingVertical: spacing.lg,
    alignItems: 'center',
  },
  levelUpButtonText: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.bold,
    color: colors.text.primary,
  },

  // ============================================================================
  // 等级信息弹窗
  // ============================================================================
  levelInfoOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    justifyContent: 'flex-end',
  },
  levelInfoContent: {
    backgroundColor: colors.background.elevated,
    borderTopLeftRadius: radius['2xl'],
    borderTopRightRadius: radius['2xl'],
    maxHeight: SCREEN_HEIGHT * 0.85,
    borderWidth: 1,
    borderBottomWidth: 0,
    borderColor: colors.border.default,
  },
  levelInfoHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xl,
    paddingBottom: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border.default,
  },
  levelInfoTitle: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
    color: colors.text.primary,
  },
  levelInfoScroll: {
    paddingHorizontal: spacing.xl,
    paddingBottom: 34,
  },
  levelInfoSection: {
    marginTop: spacing.xl,
  },
  levelInfoSectionTitle: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.bold,
    color: colors.primary.main,
    marginBottom: spacing.md,
  },
  currentStatusCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'rgba(139, 92, 246, 0.1)',
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.secondary.glow,
  },
  currentStatusLevel: {
    fontSize: typography.size['2xl'],
    fontWeight: typography.weight.extrabold,
    color: colors.secondary.light,
  },
  currentStatusStage: {
    fontSize: typography.size.sm,
    color: colors.text.secondary,
    marginTop: spacing.xs,
  },
  xpStatusBox: {
    alignItems: 'flex-end',
  },
  xpStatusText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
    color: colors.text.secondary,
  },
  xpStatusBar: {
    width: 100,
    height: 6,
    backgroundColor: 'rgba(139, 92, 246, 0.2)',
    borderRadius: radius.full,
    marginTop: spacing.xs,
    overflow: 'hidden',
  },
  xpStatusBarFill: {
    height: '100%',
    backgroundColor: colors.secondary.main,
    borderRadius: radius.full,
  },
  xpStatusHint: {
    fontSize: typography.size.xs,
    color: colors.text.tertiary,
    marginTop: spacing.xs,
  },

  // 阶段卡片
  stageCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.border.default,
  },
  stageCardActive: {
    backgroundColor: 'rgba(0, 240, 255, 0.08)',
    borderColor: colors.border.accent,
  },
  stageHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  stageEmoji: {
    fontSize: 28,
    marginRight: spacing.md,
  },
  stageInfo: {
    flex: 1,
  },
  stageName: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.bold,
    color: colors.text.primary,
  },
  stageLevel: {
    fontSize: typography.size.xs,
    color: colors.text.tertiary,
  },
  stageDesc: {
    fontSize: typography.size.sm,
    color: colors.text.secondary,
    marginBottom: spacing.sm,
  },
  stageFeatures: {
    gap: spacing.xs,
  },
  featureItem: {
    fontSize: typography.size.sm,
    color: colors.success.main,
  },
  featureLocked: {
    color: colors.text.tertiary,
  },

  // XP获取方式
  xpWayCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderRadius: radius.lg,
    padding: spacing.lg,
    gap: spacing.sm,
  },
  xpWayItem: {
    fontSize: typography.size.sm,
    color: colors.text.secondary,
  },
  xpAmount: {
    color: colors.secondary.light,
    fontWeight: typography.weight.semibold,
  },

  // 礼物商城预览
  giftDesc: {
    fontSize: typography.size.sm,
    color: colors.text.secondary,
    marginBottom: spacing.md,
  },
  giftGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
  },
  giftItem: {
    width: (SCREEN_WIDTH - spacing.xl * 2 - spacing.md * 3) / 4,
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: radius.lg,
    padding: spacing.md,
    alignItems: 'center',
  },
  giftEmoji: {
    fontSize: 28,
    marginBottom: spacing.xs,
  },
  giftName: {
    fontSize: typography.size.xs,
    color: colors.text.secondary,
  },
  giftPrice: {
    fontSize: typography.size.xs,
    color: colors.warning.main,
    fontWeight: typography.weight.semibold,
  },
  giftXp: {
    fontSize: 10,
    color: colors.secondary.light,
  },
  giftShopButton: {
    backgroundColor: 'rgba(139, 92, 246, 0.2)',
    borderRadius: radius.lg,
    paddingVertical: spacing.md,
    alignItems: 'center',
    marginTop: spacing.lg,
    marginBottom: spacing['2xl'],
  },
  giftShopButtonText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
    color: colors.secondary.light,
  },

  // ============================================================================
  // Toast
  // ============================================================================
  toastContainer: {
    position: 'absolute',
    top: 120,
    left: 0,
    right: 0,
    alignItems: 'center',
    zIndex: 1000,
  },
  toast: {
    backgroundColor: 'rgba(13, 17, 23, 0.95)',
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    borderRadius: radius.full,
    borderWidth: 1,
    borderColor: colors.border.accent,
  },
  toastText: {
    color: colors.primary.main,
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
  },
});

// ============================================================================
// 计划卡片样式 (用于充值/订阅弹窗)
// ============================================================================
export const planStyles = StyleSheet.create({
  planCard: {
    marginBottom: spacing.lg,
    borderRadius: radius.lg,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.border.default,
  },
  planGradient: {
    padding: spacing.xl,
  },
  planHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginBottom: spacing.sm,
  },
  planName: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
    color: colors.text.primary,
  },
  planBadge: {
    backgroundColor: 'rgba(0, 240, 255, 0.2)',
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
    borderRadius: radius.sm,
  },
  planBadgeText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.bold,
    color: colors.primary.main,
  },
  planPrice: {
    fontSize: typography.size['3xl'],
    fontWeight: typography.weight.extrabold,
    color: colors.text.primary,
    marginBottom: spacing.md,
  },
  planPeriod: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.normal,
    color: colors.text.secondary,
  },
  planFeatures: {
    gap: spacing.sm,
  },
  planFeature: {
    fontSize: typography.size.sm,
    color: colors.text.secondary,
  },
  planDailyCredits: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
    color: colors.warning.main,
    marginBottom: spacing.md,
  },
});

// ============================================================================
// 金币包样式
// ============================================================================
export const coinPackStyles = StyleSheet.create({
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginBottom: spacing.xl,
  },
  card: {
    width: (SCREEN_WIDTH - spacing.xl * 2 - spacing.md) / 2,
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: radius.lg,
    padding: spacing.lg,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border.default,
    position: 'relative',
  },
  cardSelected: {
    borderColor: colors.primary.main,
    backgroundColor: 'rgba(0, 240, 255, 0.08)',
  },
  popularBadge: {
    position: 'absolute',
    top: -8,
    right: -8,
    backgroundColor: colors.accent.main,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radius.sm,
  },
  popularText: {
    fontSize: 10,
    fontWeight: typography.weight.bold,
    color: colors.text.primary,
  },
  discountBadge: {
    position: 'absolute',
    top: -8,
    left: -8,
    backgroundColor: colors.success.main,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radius.sm,
  },
  discountText: {
    fontSize: 10,
    fontWeight: typography.weight.bold,
    color: colors.background.base,
  },
  coinAmount: {
    fontSize: typography.size['2xl'],
    fontWeight: typography.weight.extrabold,
    color: colors.warning.main,
  },
  price: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.semibold,
    color: colors.text.primary,
    marginTop: spacing.xs,
  },
});
