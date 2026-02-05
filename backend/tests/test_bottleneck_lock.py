"""
瓶颈锁机制测试
===============

覆盖：
1. 瓶颈等级检测 (Lv.8/16/24/32)
2. XP封顶行为
3. 礼物解锁逻辑
4. 边界条件

运行: pytest tests/test_bottleneck_lock.py -v
"""

import pytest
from app.services.intimacy_service import IntimacyService


# ============================================================================
# 1. 瓶颈等级配置测试
# ============================================================================

class TestBottleneckConfig:
    """测试瓶颈等级配置正确性"""

    def test_bottleneck_levels_are_stage_boundaries(self):
        """瓶颈应该在阶段边界: Lv.8/16/24/32"""
        expected = {8, 16, 24, 32}
        actual = set(IntimacyService.BOTTLENECK_LEVELS.keys())
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_bottleneck_intimacy_thresholds(self):
        """瓶颈对应的亲密度阈值: 19/39/59/79"""
        expected_thresholds = {8: 19, 16: 39, 24: 59, 32: 79}
        for level, info in IntimacyService.BOTTLENECK_LEVELS.items():
            assert info["intimacy_threshold"] == expected_thresholds[level], \
                f"Level {level} threshold should be {expected_thresholds[level]}"

    def test_bottleneck_gift_tier_requirements(self):
        """瓶颈礼物等级要求递增"""
        tiers = [
            IntimacyService.BOTTLENECK_LEVELS[lv]["required_gift_tier"]
            for lv in sorted(IntimacyService.BOTTLENECK_LEVELS.keys())
        ]
        # Tier 应该非递减: [2, 2, 3, 4]
        for i in range(len(tiers) - 1):
            assert tiers[i] <= tiers[i + 1], \
                f"Gift tier should be non-decreasing, got {tiers}"

    def test_level_to_intimacy_at_boundaries(self):
        """level_to_intimacy 在瓶颈等级处的值"""
        # Lv.8 → intimacy=17, Lv.9 → intimacy=20 (crosses 19)
        assert IntimacyService.level_to_intimacy(8) < 20
        assert IntimacyService.level_to_intimacy(9) >= 20
        # Lv.16 → crosses 39
        assert IntimacyService.level_to_intimacy(16) < 40
        assert IntimacyService.level_to_intimacy(17) >= 40
        # Lv.24 → crosses 59
        assert IntimacyService.level_to_intimacy(24) < 60
        assert IntimacyService.level_to_intimacy(25) >= 60
        # Lv.32 → crosses 79
        assert IntimacyService.level_to_intimacy(32) < 80
        assert IntimacyService.level_to_intimacy(33) >= 80


# ============================================================================
# 2. 瓶颈检测逻辑测试
# ============================================================================

class TestBottleneckDetection:
    """测试瓶颈检测方法"""

    def test_is_bottleneck_level(self):
        """正确识别瓶颈等级"""
        assert IntimacyService.is_bottleneck_level(8) is True
        assert IntimacyService.is_bottleneck_level(16) is True
        assert IntimacyService.is_bottleneck_level(24) is True
        assert IntimacyService.is_bottleneck_level(32) is True

    def test_non_bottleneck_levels(self):
        """非瓶颈等级返回 False"""
        for lv in [1, 5, 7, 9, 10, 15, 17, 19, 23, 25, 31, 33, 39, 40]:
            assert IntimacyService.is_bottleneck_level(lv) is False, \
                f"Level {lv} should not be bottleneck"

    def test_get_bottleneck_info(self):
        """获取瓶颈信息"""
        info = IntimacyService.get_bottleneck_info(8)
        assert info is not None
        assert info["required_gift_tier"] == 2
        assert "meaning" in info

    def test_get_bottleneck_info_non_bottleneck(self):
        """非瓶颈等级返回 None"""
        assert IntimacyService.get_bottleneck_info(5) is None
        assert IntimacyService.get_bottleneck_info(19) is None

    def test_get_next_bottleneck(self):
        """获取下一个瓶颈等级"""
        assert IntimacyService.get_next_bottleneck(1) == 8
        assert IntimacyService.get_next_bottleneck(8) == 8  # 当前就是
        assert IntimacyService.get_next_bottleneck(9) == 16
        assert IntimacyService.get_next_bottleneck(25) == 32
        assert IntimacyService.get_next_bottleneck(33) is None  # 没有更高的了


# ============================================================================
# 3. V4 情绪递减防刷测试
# ============================================================================

class TestEmotionDiminishingReturns:
    """测试情绪递减防刷机制"""

    def test_first_positive_no_decay(self):
        """第一次正向不衰减"""
        from app.services.v4.chat_pipeline_v4 import ChatPipelineV4
        pipeline = ChatPipelineV4()
        result = pipeline._apply_diminishing_returns("u1", "c1", 25)
        assert result == 25

    def test_consecutive_positive_decays(self):
        """连续正向递减"""
        from app.services.v4.chat_pipeline_v4 import ChatPipelineV4
        pipeline = ChatPipelineV4()
        # 清空历史
        pipeline._recent_deltas = {}

        r1 = pipeline._apply_diminishing_returns("u2", "c2", 25)  # 100%
        r2 = pipeline._apply_diminishing_returns("u2", "c2", 25)  # 70%
        r3 = pipeline._apply_diminishing_returns("u2", "c2", 25)  # 40%
        r4 = pipeline._apply_diminishing_returns("u2", "c2", 25)  # 20%
        r5 = pipeline._apply_diminishing_returns("u2", "c2", 25)  # 10%

        assert r1 == 25
        assert r2 == 17  # int(25 * 0.7)
        assert r3 == 10  # int(25 * 0.4)
        assert r4 == 5   # int(25 * 0.2)
        assert r5 == 2   # int(25 * 0.1), min 1

    def test_negative_no_decay(self):
        """负向不衰减"""
        from app.services.v4.chat_pipeline_v4 import ChatPipelineV4
        pipeline = ChatPipelineV4()
        pipeline._recent_deltas = {}

        r1 = pipeline._apply_diminishing_returns("u3", "c3", -30)
        r2 = pipeline._apply_diminishing_returns("u3", "c3", -20)
        r3 = pipeline._apply_diminishing_returns("u3", "c3", -10)

        assert r1 == -30
        assert r2 == -20
        assert r3 == -10

    def test_negative_resets_positive_streak(self):
        """负向打断正向连击"""
        from app.services.v4.chat_pipeline_v4 import ChatPipelineV4
        pipeline = ChatPipelineV4()
        pipeline._recent_deltas = {}

        pipeline._apply_diminishing_returns("u4", "c4", 20)   # 1st positive
        pipeline._apply_diminishing_returns("u4", "c4", 20)   # 2nd positive (decayed)
        pipeline._apply_diminishing_returns("u4", "c4", -10)  # negative breaks streak
        r = pipeline._apply_diminishing_returns("u4", "c4", 20)  # back to 100%
        assert r == 20

    def test_minimum_one(self):
        """衰减后至少+1"""
        from app.services.v4.chat_pipeline_v4 import ChatPipelineV4
        pipeline = ChatPipelineV4()
        pipeline._recent_deltas = {}

        for _ in range(10):
            r = pipeline._apply_diminishing_returns("u5", "c5", 1)
        assert r >= 1


# ============================================================================
# 4. XP 计算边界测试
# ============================================================================

class TestXPCalculation:
    """测试 XP/Level 计算"""

    def test_xp_for_level_monotonic(self):
        """xp_for_level 应单调递增"""
        prev = 0
        for lv in range(1, 41):
            xp = IntimacyService.xp_for_level(lv)
            assert xp >= prev, f"XP for level {lv} ({xp}) < level {lv-1} ({prev})"
            prev = xp

    def test_calculate_level_boundaries(self):
        """calculate_level 在边界处正确"""
        # Level 1 需要 0 XP
        assert IntimacyService.calculate_level(0) >= 1
        # 高XP不超过上限
        assert IntimacyService.calculate_level(999999999) <= 50
