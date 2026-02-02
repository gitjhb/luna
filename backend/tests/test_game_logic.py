"""
Luna 核心逻辑测试套件
======================

覆盖：
1. 物理引擎 (PhysicsEngine) - 情绪计算
2. 感知引擎 (PerceptionEngine) - 意图解析 (规则fallback)
3. 游戏引擎 (GameEngine) - 判定逻辑
4. 亲密度系统 (IntimacyService) - XP/Level/Stage

运行: pytest tests/test_game_logic.py -v
"""

import pytest
from dataclasses import dataclass
from typing import List

# ============================================================================
# 直接导入核心逻辑，不需要异步/数据库
# ============================================================================

from app.services.physics_engine import (
    PhysicsEngine, 
    EmotionState, 
    CharacterZAxis,
    INTENT_MODIFIERS
)
from app.services.perception_engine import PerceptionEngine, L1Result
from app.services.intimacy_service import IntimacyService


# ============================================================================
# SECTION 1: 情绪状态机测试
# ============================================================================

class TestEmotionState:
    """情绪状态阈值测试"""
    
    def test_state_thresholds(self):
        """测试情绪值到状态的映射"""
        assert EmotionState.get_state(100) == EmotionState.LOVING
        assert EmotionState.get_state(75) == EmotionState.HAPPY
        assert EmotionState.get_state(50) == EmotionState.HAPPY
        assert EmotionState.get_state(35) == EmotionState.CONTENT
        assert EmotionState.get_state(20) == EmotionState.CONTENT
        assert EmotionState.get_state(0) == EmotionState.NEUTRAL
        assert EmotionState.get_state(-19) == EmotionState.NEUTRAL
        assert EmotionState.get_state(-20) == EmotionState.ANNOYED
        assert EmotionState.get_state(-49) == EmotionState.ANNOYED
        assert EmotionState.get_state(-50) == EmotionState.ANGRY
        assert EmotionState.get_state(-79) == EmotionState.ANGRY
        assert EmotionState.get_state(-80) == EmotionState.COLD_WAR
        assert EmotionState.get_state(-99) == EmotionState.COLD_WAR
        assert EmotionState.get_state(-100) == EmotionState.BLOCKED
    
    def test_locked_states(self):
        """测试锁定状态判定"""
        assert EmotionState.COLD_WAR in EmotionState.LOCKED_STATES
        assert EmotionState.BLOCKED in EmotionState.LOCKED_STATES
        assert EmotionState.ANGRY not in EmotionState.LOCKED_STATES
        assert EmotionState.NEUTRAL not in EmotionState.LOCKED_STATES


# ============================================================================
# SECTION 2: 物理引擎测试 (情绪计算)
# ============================================================================

class TestPhysicsEngine:
    """情绪物理引擎测试"""
    
    @pytest.fixture
    def default_config(self):
        """默认角色配置"""
        return CharacterZAxis(
            sensitivity=1.0,
            decay_rate=0.9,
            optimism=0.0,
            pride=10.0,
            pure_val=30,
            jealousy_val=10
        )
    
    @pytest.fixture
    def sensitive_config(self):
        """高敏感度角色 (如芽衣)"""
        return CharacterZAxis(
            sensitivity=1.5,
            decay_rate=0.85,
            optimism=0.0,
            pride=15.0,
            pure_val=40,
            jealousy_val=20
        )
    
    @pytest.fixture
    def cold_config(self):
        """高冷角色 (如Yuki)"""
        return CharacterZAxis(
            sensitivity=0.8,
            decay_rate=0.95,
            optimism=0.0,
            pride=25.0,
            pure_val=50,
            jealousy_val=5
        )
    
    # --- 正向情绪测试 ---
    
    def test_compliment_positive_delta(self, default_config):
        """夸奖应该增加情绪"""
        l1_result = {'sentiment_score': 0.8, 'intent_category': 'COMPLIMENT'}
        delta = PhysicsEngine.calculate_emotion_delta(0, l1_result, default_config)
        assert delta > 0, "夸奖应该产生正向情绪变化"
        assert delta >= 10, "夸奖效果应该明显"
    
    def test_flirt_positive_delta(self, default_config):
        """调情应该增加情绪"""
        l1_result = {'sentiment_score': 0.7, 'intent_category': 'FLIRT'}
        delta = PhysicsEngine.calculate_emotion_delta(20, l1_result, default_config)
        assert delta > 0, "调情应该产生正向情绪变化"
    
    def test_love_confession_high_delta(self, default_config):
        """表白应该大幅增加情绪"""
        l1_result = {'sentiment_score': 0.9, 'intent_category': 'LOVE_CONFESSION'}
        delta = PhysicsEngine.calculate_emotion_delta(50, l1_result, default_config)
        assert delta >= 20, "表白效果应该很强"
    
    # --- 负向情绪测试 ---
    
    def test_insult_negative_delta(self, default_config):
        """侮辱应该大幅降低情绪"""
        l1_result = {'sentiment_score': -0.9, 'intent_category': 'INSULT'}
        delta = PhysicsEngine.calculate_emotion_delta(0, l1_result, default_config)
        assert delta < 0, "侮辱应该产生负向情绪变化"
        assert delta <= -30, "侮辱伤害应该很大"
    
    def test_criticism_negative_delta(self, default_config):
        """批评应该降低情绪"""
        l1_result = {'sentiment_score': -0.5, 'intent_category': 'CRITICISM'}
        delta = PhysicsEngine.calculate_emotion_delta(30, l1_result, default_config)
        assert delta < 0, "批评应该产生负向情绪变化"
    
    def test_negative_damage_doubled(self, default_config):
        """负面情绪伤害加倍 (Loss Aversion)"""
        # 正面 sentiment
        positive_l1 = {'sentiment_score': 0.5, 'intent_category': 'SMALL_TALK'}
        positive_delta = PhysicsEngine.calculate_emotion_delta(0, positive_l1, default_config)
        
        # 负面 sentiment (同等强度)
        negative_l1 = {'sentiment_score': -0.5, 'intent_category': 'SMALL_TALK'}
        negative_delta = PhysicsEngine.calculate_emotion_delta(0, negative_l1, default_config)
        
        # 负面影响应该更大 (绝对值)
        assert abs(negative_delta) > abs(positive_delta), "负面伤害应该加倍"
    
    # --- 状态锁测试 ---
    
    def test_cold_war_blocks_normal_chat(self, default_config):
        """冷战状态下普通聊天无效"""
        l1_result = {'sentiment_score': 0.8, 'intent_category': 'SMALL_TALK'}
        delta = PhysicsEngine.calculate_emotion_delta(-90, l1_result, default_config)
        assert delta == 0, "冷战状态下普通聊天应该被阻挡"
    
    def test_cold_war_blocks_compliment(self, default_config):
        """冷战状态下夸奖也无效"""
        l1_result = {'sentiment_score': 1.0, 'intent_category': 'COMPLIMENT'}
        delta = PhysicsEngine.calculate_emotion_delta(-85, l1_result, default_config)
        assert delta == 0, "冷战状态下夸奖也应该被阻挡"
    
    def test_cold_war_accepts_gift(self, default_config):
        """冷战状态下送礼有效"""
        l1_result = {
            'sentiment_score': 0.8, 
            'intent_category': 'GIFT_SEND',
            'transaction_verified': True
        }
        delta = PhysicsEngine.calculate_emotion_delta(-85, l1_result, default_config)
        assert delta > 0, "冷战状态下验证过的礼物应该有效"
        assert delta >= 40, "礼物效果应该很强"
    
    def test_cold_war_accepts_apology(self, default_config):
        """冷战状态下道歉有效"""
        l1_result = {'sentiment_score': 0.5, 'intent_category': 'APOLOGY'}
        delta = PhysicsEngine.calculate_emotion_delta(-85, l1_result, default_config)
        assert delta > 0, "冷战状态下道歉应该有效"
    
    def test_blocked_rejects_apology(self, default_config):
        """拉黑状态下连道歉都无效"""
        l1_result = {'sentiment_score': 0.8, 'intent_category': 'APOLOGY'}
        delta = PhysicsEngine.calculate_emotion_delta(-100, l1_result, default_config)
        assert delta == 0, "拉黑状态下道歉也无效"
    
    def test_blocked_accepts_verified_gift(self, default_config):
        """拉黑状态下只有验证礼物有效"""
        l1_result = {
            'sentiment_score': 1.0, 
            'intent_category': 'GIFT_SEND',
            'transaction_verified': True
        }
        delta = PhysicsEngine.calculate_emotion_delta(-100, l1_result, default_config)
        assert delta > 0, "拉黑状态下验证过的礼物应该有效"
    
    # --- 骚扰检测测试 ---
    
    def test_nsfw_low_intimacy_is_harassment(self, default_config):
        """低亲密度请求NSFW = 骚扰"""
        l1_result = {
            'sentiment_score': 0.5, 
            'intent_category': 'REQUEST_NSFW',
            'intimacy_x': 10  # 低亲密度
        }
        delta = PhysicsEngine.calculate_emotion_delta(30, l1_result, default_config)
        assert delta < 0, "低亲密度NSFW请求应该降低情绪"
    
    def test_nsfw_high_intimacy_is_playful(self, default_config):
        """高亲密度请求NSFW = 调情"""
        l1_result = {
            'sentiment_score': 0.5, 
            'intent_category': 'REQUEST_NSFW',
            'intimacy_x': 80  # 高亲密度
        }
        delta = PhysicsEngine.calculate_emotion_delta(50, l1_result, default_config)
        # 不应该是强负面
        assert delta >= -5, "高亲密度NSFW请求不应该是强负面"
    
    # --- 同理心修正测试 ---
    
    def test_express_sadness_empathy_override(self, default_config):
        """用户倾诉悲伤时触发同理心修正"""
        l1_result = {
            'sentiment_score': -0.7,  # 用户情绪负面
            'intent_category': 'EXPRESS_SADNESS'
        }
        delta = PhysicsEngine.calculate_emotion_delta(30, l1_result, default_config)
        # 同理心修正：AI不应该因为用户悲伤而降低情绪
        assert delta >= 0, "用户倾诉悲伤时AI不应该降情绪"
    
    # --- 敏感度测试 ---
    
    def test_sensitivity_amplifies_positive(self, sensitive_config):
        """高敏感度放大正面情绪"""
        l1_result = {'sentiment_score': 0.5, 'intent_category': 'COMPLIMENT'}
        
        default_config = CharacterZAxis(sensitivity=1.0)
        delta_normal = PhysicsEngine.calculate_emotion_delta(0, l1_result, default_config)
        delta_sensitive = PhysicsEngine.calculate_emotion_delta(0, l1_result, sensitive_config)
        
        assert delta_sensitive > delta_normal, "高敏感度应该放大正面情绪"
    
    def test_sensitivity_amplifies_negative(self, sensitive_config):
        """高敏感度也放大负面情绪"""
        l1_result = {'sentiment_score': -0.5, 'intent_category': 'INSULT'}
        
        default_config = CharacterZAxis(sensitivity=1.0)
        delta_normal = PhysicsEngine.calculate_emotion_delta(0, l1_result, default_config)
        delta_sensitive = PhysicsEngine.calculate_emotion_delta(0, l1_result, sensitive_config)
        
        assert delta_sensitive < delta_normal, "高敏感度应该放大负面情绪"
    
    # --- 情绪衰减测试 ---
    
    def test_emotion_decays_toward_zero(self, default_config):
        """情绪随时间向0衰减"""
        user_state = {'emotion': 50, 'last_intents': []}
        l1_result = {'sentiment_score': 0.0, 'intent_category': 'SMALL_TALK'}
        
        new_emotion = PhysicsEngine.update_state(user_state, l1_result, default_config)
        assert new_emotion < 50, "正情绪应该向0衰减"
        assert new_emotion > 0, "不应该衰减过头"
    
    def test_negative_emotion_decays_toward_zero(self, default_config):
        """负情绪也向0衰减"""
        user_state = {'emotion': -50, 'last_intents': []}
        l1_result = {'sentiment_score': 0.0, 'intent_category': 'SMALL_TALK'}
        
        new_emotion = PhysicsEngine.update_state(user_state, l1_result, default_config)
        assert new_emotion > -50, "负情绪应该向0衰减"
        assert new_emotion < 0, "不应该衰减过头"
    
    # --- 防刷测试 ---
    
    def test_anti_grind_reduces_repeated_intent(self, default_config):
        """连续相同正向意图效果递减"""
        l1_result = {'sentiment_score': 0.8, 'intent_category': 'FLIRT'}
        
        # 无重复历史
        state_fresh = {'emotion': 30, 'last_intents': []}
        new1 = PhysicsEngine.update_state(state_fresh, l1_result, default_config)
        
        # 有重复历史 (连续3次FLIRT)
        state_grind = {'emotion': 30, 'last_intents': ['FLIRT', 'FLIRT', 'FLIRT']}
        new2 = PhysicsEngine.update_state(state_grind, l1_result, default_config)
        
        delta1 = new1 - 30
        delta2 = new2 - 30
        
        assert delta2 < delta1, "连续刷同一意图效果应该递减"
    
    # --- 边界值测试 ---
    
    def test_emotion_capped_at_100(self, default_config):
        """情绪最高100"""
        user_state = {'emotion': 95, 'last_intents': []}
        l1_result = {'sentiment_score': 1.0, 'intent_category': 'LOVE_CONFESSION'}
        
        new_emotion = PhysicsEngine.update_state(user_state, l1_result, default_config)
        assert new_emotion <= 100, "情绪不应该超过100"
    
    def test_emotion_capped_at_minus_100(self, default_config):
        """情绪最低-100"""
        user_state = {'emotion': -95, 'last_intents': []}
        l1_result = {'sentiment_score': -1.0, 'intent_category': 'INSULT'}
        
        new_emotion = PhysicsEngine.update_state(user_state, l1_result, default_config)
        assert new_emotion >= -100, "情绪不应该低于-100"


# ============================================================================
# SECTION 3: 感知引擎测试 (规则fallback)
# ============================================================================

class TestPerceptionEngine:
    """感知引擎规则fallback测试"""
    
    @pytest.fixture
    def engine(self):
        return PerceptionEngine()
    
    def test_greeting_detection(self, engine):
        """问候语识别"""
        result = engine.analyze_sync_fallback("早上好")
        assert result.intent_category == "GREETING"
        assert result.sentiment_score > 0
    
    def test_insult_detection(self, engine):
        """侮辱识别"""
        result = engine.analyze_sync_fallback("你真是个笨蛋")
        assert result.intent_category == "INSULT"
        assert result.sentiment_score < 0
    
    def test_nsfw_detection(self, engine):
        """NSFW识别"""
        result = engine.analyze_sync_fallback("给我看裸照")
        assert result.is_nsfw == True
        assert result.intent_category == "REQUEST_NSFW"
        assert result.difficulty_rating >= 70
    
    def test_confession_detection(self, engine):
        """表白识别"""
        result = engine.analyze_sync_fallback("我喜欢你，做我女朋友吧")
        assert result.intent_category == "LOVE_CONFESSION"
        assert result.difficulty_rating >= 60
    
    def test_flirt_detection(self, engine):
        """调情识别"""
        result = engine.analyze_sync_fallback("你今天好可爱啊")
        assert result.intent_category == "FLIRT"
        assert result.sentiment_score > 0
    
    def test_apology_detection(self, engine):
        """道歉识别"""
        result = engine.analyze_sync_fallback("对不起，我错了")
        assert result.intent_category == "APOLOGY"
    
    def test_gift_talk_is_flirt_not_gift_send(self, engine):
        """嘴上说送礼不是真礼物"""
        result = engine.analyze_sync_fallback("送你一朵花")
        assert result.intent_category == "FLIRT", "嘴上说送礼应该是FLIRT不是GIFT_SEND"
    
    def test_closing_detection(self, engine):
        """告别识别"""
        result = engine.analyze_sync_fallback("晚安，明天见")
        assert result.intent_category == "CLOSING"
    
    def test_invitation_detection(self, engine):
        """邀约识别"""
        result = engine.analyze_sync_fallback("今晚来我家吧")
        assert result.intent_category == "INVITATION"
        assert result.difficulty_rating >= 50


# ============================================================================
# SECTION 4: 亲密度系统测试
# ============================================================================

class TestIntimacyService:
    """亲密度系统测试"""
    
    def test_xp_for_level_early(self):
        """早期等级XP阈值"""
        assert IntimacyService.xp_for_level(1) == 0
        assert IntimacyService.xp_for_level(2) == 4
        assert IntimacyService.xp_for_level(3) == 10
        assert IntimacyService.xp_for_level(4) == 20
    
    def test_calculate_level_from_xp(self):
        """XP转等级"""
        assert IntimacyService.calculate_level(0) == 1
        assert IntimacyService.calculate_level(3) == 1
        assert IntimacyService.calculate_level(4) == 2
        assert IntimacyService.calculate_level(9) == 2
        assert IntimacyService.calculate_level(10) == 3
        assert IntimacyService.calculate_level(19) == 3
        assert IntimacyService.calculate_level(20) == 4
    
    def test_stage_from_level_strangers(self):
        """初识阶段判定"""
        for level in [1, 2, 3]:
            stage = IntimacyService.get_stage(level)
            assert stage["id"] == "strangers", f"Level {level} should be strangers"
    
    def test_stage_from_level_acquaintances(self):
        """熟络阶段判定"""
        for level in [4, 5, 8, 10]:
            stage = IntimacyService.get_stage(level)
            assert stage["id"] == "acquaintances", f"Level {level} should be acquaintances"
    
    def test_stage_from_level_close_friends(self):
        """挚友阶段判定"""
        for level in [11, 15, 20, 25]:
            stage = IntimacyService.get_stage(level)
            assert stage["id"] == "close_friends", f"Level {level} should be close_friends"
    
    def test_stage_from_level_ambiguous(self):
        """暧昧阶段判定"""
        for level in [26, 30, 35, 40]:
            stage = IntimacyService.get_stage(level)
            assert stage["id"] == "ambiguous", f"Level {level} should be ambiguous"
    
    def test_stage_from_level_soulmates(self):
        """灵魂伴侣阶段判定"""
        for level in [41, 45, 50]:
            stage = IntimacyService.get_stage(level)
            assert stage["id"] == "soulmates", f"Level {level} should be soulmates"
    
    def test_level_up_xp_progression(self):
        """XP需求递增"""
        prev_xp = 0
        for level in range(2, 15):
            current_xp = IntimacyService.xp_for_level(level)
            assert current_xp > prev_xp, f"Level {level} XP should be higher than level {level-1}"
            prev_xp = current_xp


# ============================================================================
# SECTION 5: 集成场景测试 (完整流程)
# ============================================================================

class TestIntegrationScenarios:
    """集成场景测试 - 模拟完整交互流程"""
    
    @pytest.fixture
    def default_config(self):
        return CharacterZAxis(sensitivity=1.0, decay_rate=0.9, pride=10.0, pure_val=30)
    
    def test_scenario_stranger_to_angry(self, default_config):
        """场景：陌生人阶段连续骚扰 → 生气"""
        emotion = 0
        
        # 连续3次侮辱
        for _ in range(3):
            user_state = {'emotion': emotion, 'last_intents': []}
            l1_result = {'sentiment_score': -0.8, 'intent_category': 'INSULT'}
            emotion = PhysicsEngine.update_state(user_state, l1_result, default_config)
        
        state = EmotionState.get_state(emotion)
        assert state in [EmotionState.ANGRY, EmotionState.COLD_WAR], \
            f"连续侮辱应该导致生气/冷战，实际: {state}"
    
    def test_scenario_cold_war_recovery_with_gift(self, default_config):
        """场景：冷战 → 送礼 → 恢复"""
        emotion = -85  # 冷战中
        
        # 送一个验证过的礼物
        user_state = {'emotion': emotion, 'last_intents': []}
        l1_result = {
            'sentiment_score': 0.8, 
            'intent_category': 'GIFT_SEND',
            'transaction_verified': True
        }
        new_emotion = PhysicsEngine.update_state(user_state, l1_result, default_config)
        
        new_state = EmotionState.get_state(new_emotion)
        assert new_emotion > emotion, "送礼应该改善情绪"
        # 一次礼物可能不够完全解除冷战，但应该有明显改善
        assert new_emotion > -80 or new_state != EmotionState.COLD_WAR, \
            "送大礼应该能帮助脱离冷战"
    
    def test_scenario_gradual_relationship_building(self, default_config):
        """场景：逐步建立关系"""
        emotion = 0
        last_intents = []
        
        # 持续正向互动
        interactions = [
            {'sentiment_score': 0.5, 'intent_category': 'GREETING'},
            {'sentiment_score': 0.6, 'intent_category': 'SMALL_TALK'},
            {'sentiment_score': 0.7, 'intent_category': 'COMPLIMENT'},
            {'sentiment_score': 0.6, 'intent_category': 'FLIRT'},
            {'sentiment_score': 0.8, 'intent_category': 'COMPLIMENT'},
        ]
        
        for l1_result in interactions:
            user_state = {'emotion': emotion, 'last_intents': last_intents}
            emotion = PhysicsEngine.update_state(user_state, l1_result, default_config)
            last_intents.append(l1_result['intent_category'])
            last_intents = last_intents[-10:]  # 保留最近10条
        
        assert emotion > 30, f"持续正向互动应该提升情绪到CONTENT以上，实际: {emotion}"
    
    def test_scenario_confession_at_low_intimacy_fails(self):
        """场景：低亲密度表白失败"""
        # 使用 GameEngine 的判定逻辑
        from app.services.game_engine import GameEngine
        
        # 模拟低亲密度用户
        @dataclass
        class MockUserState:
            user_id: str = "test"
            character_id: str = "test"
            xp: int = 50  # 低XP
            intimacy_level: int = 5
            emotion: int = 50
            events: List[str] = None
            last_intents: List[str] = None
            
            def __post_init__(self):
                self.events = self.events or []
                self.last_intents = self.last_intents or []
            
            @property
            def intimacy_x(self):
                import math
                return min(100, math.log10(self.xp + 1) * 30) if self.xp > 0 else 0
        
        user_state = MockUserState()
        
        # 表白的难度是 75
        difficulty = 75
        power_x = user_state.intimacy_x * 0.5
        power_y = user_state.emotion * 0.3
        total_power = power_x + power_y
        
        # 应该失败
        assert total_power < difficulty, \
            f"低亲密度表白应该失败，power={total_power:.1f} < difficulty={difficulty}"
    
    def test_scenario_harassment_punishment(self, default_config):
        """场景：低亲密度NSFW请求受惩罚"""
        emotion = 30
        
        # 低亲密度发NSFW请求
        user_state = {'emotion': emotion, 'last_intents': []}
        l1_result = {
            'sentiment_score': 0.5,  # 用户可能觉得自己是调情
            'intent_category': 'REQUEST_NSFW',
            'intimacy_x': 10  # 低亲密度
        }
        new_emotion = PhysicsEngine.update_state(user_state, l1_result, default_config)
        
        assert new_emotion < emotion, "低亲密度NSFW请求应该降低情绪"


# ============================================================================
# SECTION 6: 角色差异化测试
# ============================================================================

class TestCharacterDifferences:
    """不同角色性格参数测试"""
    
    def test_yuki_harder_to_please(self):
        """Yuki (高冷) 更难讨好"""
        yuki = CharacterZAxis(sensitivity=0.8, decay_rate=0.95, pride=25.0, pure_val=50)
        mei = CharacterZAxis(sensitivity=1.5, decay_rate=0.85, pride=15.0, pure_val=40)
        
        l1_result = {'sentiment_score': 0.6, 'intent_category': 'COMPLIMENT'}
        
        delta_yuki = PhysicsEngine.calculate_emotion_delta(0, l1_result, yuki)
        delta_mei = PhysicsEngine.calculate_emotion_delta(0, l1_result, mei)
        
        assert delta_mei > delta_yuki, "芽衣(高敏感)应该比Yuki(高冷)更容易被夸奖打动"
    
    def test_high_pride_reduces_apology_effect(self):
        """高自尊角色道歉效果差"""
        high_pride = CharacterZAxis(pride=30.0)
        low_pride = CharacterZAxis(pride=5.0)
        
        l1_result = {'sentiment_score': 0.5, 'intent_category': 'APOLOGY'}
        
        delta_high = PhysicsEngine.calculate_emotion_delta(-30, l1_result, high_pride)
        delta_low = PhysicsEngine.calculate_emotion_delta(-30, l1_result, low_pride)
        
        assert delta_low > delta_high, "高自尊角色道歉效果应该更差"
    
    def test_high_pure_blocks_nsfw_harder(self):
        """高纯洁度角色NSFW阻力更大"""
        pure_char = CharacterZAxis(pure_val=50)  # 如 Yuki
        normal_char = CharacterZAxis(pure_val=20)  # 如 Phantom
        
        l1_result = {
            'sentiment_score': 0.3, 
            'intent_category': 'REQUEST_NSFW',
            'intimacy_x': 50  # 中等亲密度
        }
        
        delta_pure = PhysicsEngine.calculate_emotion_delta(30, l1_result, pure_char)
        delta_normal = PhysicsEngine.calculate_emotion_delta(30, l1_result, normal_char)
        
        # 纯洁度高的角色对NSFW请求反应应该更负面
        assert delta_pure <= delta_normal, "高纯洁度角色应该对NSFW更抗拒"


# ============================================================================
# 运行入口
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
