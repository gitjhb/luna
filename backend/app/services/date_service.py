"""
Date Service - 约会系统
========================

约会是解锁暧昧阶段的必要事件。

流程：
1. 用户 LV 10+ 且已送过礼物 → 解锁约会
2. 选择约会场景 → 进入约会模式
3. 完成约会 → 触发 first_date 事件 → 解锁暧昧阶段
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import uuid4

logger = logging.getLogger(__name__)

# 约会场景（复用 scenarios 系统）
DATE_SCENARIOS = [
    "cafe_paris",      # 巴黎咖啡厅
    "beach_sunset",    # 海边日落
    "rooftop_city",    # 城市天台
    "forest_walk",     # 林间漫步
    "stargazing",      # 星空露营
]

# 角色专属约会场景配置
# 只有 sakura 有专属场景，其他角色暂时用通用场景
CHARACTER_DATE_SCENES: Dict[str, Dict[str, dict]] = {
    "sakura": {
        "bedroom": {
            "name": "卧室",
            "icon": "🛏️",
            "description": "芽衣的私人空间",
            "required_level": 1,
        },
        "beach": {
            "name": "海滩",
            "icon": "🏖️",
            "description": "阳光沙滩，青春的气息",
            "required_level": 20,
        },
        "ocean": {
            "name": "海边露台",
            "icon": "🌊",
            "description": "浪漫的海边夜晚",
            "required_level": 20,
        },
        "school": {
            "name": "教室",
            "icon": "🏫",
            "description": "放学后的秘密约会",
            "required_level": 20,
        },
    },
}

# 约会解锁条件
DATE_UNLOCK_LEVEL = 10

# 约会完成所需消息数
DATE_COMPLETION_MESSAGES = 5

# 内存存储活跃约会（MVP 简化，后续可用 Redis）
_active_dates: Dict[str, dict] = {}


class DateService:
    """约会服务"""
    
    async def check_date_unlock(
        self,
        user_id: str,
        character_id: str,
    ) -> tuple[bool, str]:
        """
        检查约会是否解锁
        
        Returns:
            (is_unlocked, reason)
        """
        details = await self.get_unlock_details(user_id, character_id)
        return details["is_unlocked"], details["reason"]
    
    async def get_unlock_details(
        self,
        user_id: str,
        character_id: str,
    ) -> dict:
        """
        获取详细的解锁状态
        
        Returns:
            dict with is_unlocked, reason, current_level, level_met, gift_sent
        """
        from app.services.intimacy_service import intimacy_service
        from app.services.game_engine import GameEngine
        
        # 检查等级
        intimacy_data = await intimacy_service.get_or_create_intimacy(user_id, character_id)
        level = intimacy_data.get("current_level", 1)
        level_met = level >= DATE_UNLOCK_LEVEL
        
        # 检查是否已送过礼物
        game_engine = GameEngine()
        user_state = await game_engine._load_user_state(user_id, character_id)
        gift_sent = "first_gift" in user_state.events
        has_first_date = "first_date" in user_state.events
        
        is_unlocked = level_met and gift_sent
        
        if not level_met:
            reason = f"需要达到 LV {DATE_UNLOCK_LEVEL} 才能解锁约会 (当前 LV {level})"
        elif not gift_sent:
            reason = "需要先送过礼物才能邀请约会"
        elif has_first_date:
            reason = "已完成首次约会，可以再次约会"
        else:
            reason = "约会已解锁"
        
        return {
            "is_unlocked": is_unlocked,
            "reason": reason,
            "unlock_level": DATE_UNLOCK_LEVEL,
            "current_level": level,
            "level_met": level_met,
            "gift_sent": gift_sent,
        }
    
    async def start_date(
        self,
        user_id: str,
        character_id: str,
        scenario_id: Optional[str] = None,
    ) -> dict:
        """
        开始约会 - 一键生成约会故事
        
        新流程：
        1. 检查解锁条件
        2. 选择场景
        3. 调用 event_story_generator 生成 first_date 故事
        4. 保存到 event_memories（回忆录）
        5. 触发 first_date 事件，给 XP 奖励
        
        Args:
            user_id: 用户ID
            character_id: 角色ID
            scenario_id: 场景ID（可选，不传则随机）
            
        Returns:
            约会结果，包含生成的故事
        """
        from app.services.scenarios import get_scenario
        from app.services.event_story_generator import event_story_generator, EventType
        from app.services.intimacy_service import intimacy_service
        from app.services.emotion_engine_v2 import emotion_engine
        import random
        
        # 检查解锁
        is_unlocked, reason = await self.check_date_unlock(user_id, character_id)
        if not is_unlocked:
            return {
                "success": False,
                "error": reason,
            }
        
        # 选择场景
        if not scenario_id or scenario_id not in DATE_SCENARIOS:
            scenario_id = random.choice(DATE_SCENARIOS)
        
        scenario = get_scenario(scenario_id)
        if not scenario:
            scenario_id = DATE_SCENARIOS[0]
            scenario = get_scenario(scenario_id)
        
        logger.info(f"Starting date: user={user_id}, character={character_id}, scenario={scenario_id}")
        
        # 获取关系状态用于故事生成
        intimacy_data = await intimacy_service.get_or_create_intimacy(user_id, character_id)
        relationship_state = {
            "intimacy_level": intimacy_data.get("current_level", 1),
            "stage": intimacy_data.get("intimacy_stage", "strangers"),
            "scenario": scenario.name,
            "scenario_context": scenario.context,
        }
        
        # 生成约会故事
        story_result = await event_story_generator.generate_event_story(
            user_id=user_id,
            character_id=character_id,
            event_type=EventType.FIRST_DATE,
            chat_history=[],  # 约会故事不需要聊天历史
            memory_context=f"约会场景：{scenario.name}\n{scenario.context}",
            relationship_state=relationship_state,
            save_to_db=True,
        )
        
        if not story_result.success:
            logger.error(f"Failed to generate date story: {story_result.error}")
            return {
                "success": False,
                "error": story_result.error or "生成约会故事失败",
            }
        
        # 触发 first_date 事件
        event_triggered = await self._trigger_first_date_event(user_id, character_id)
        
        # 给予 XP 奖励
        xp_reward = 50
        await intimacy_service.add_xp(user_id, character_id, xp_reward)
        
        # 提升情绪
        await emotion_engine.update_score(user_id, character_id, 15)
        
        logger.info(f"Date completed: user={user_id}, character={character_id}, story_length={len(story_result.story_content or '')}")
        
        return {
            "success": True,
            "story": story_result.story_content,
            "event_memory_id": story_result.event_memory_id,
            "scenario": {
                "id": scenario_id,
                "name": scenario.name,
                "icon": scenario.icon,
            },
            "rewards": {
                "xp": xp_reward,
                "emotion_boost": 15,
            },
            "event_triggered": event_triggered,
            "message": "约会成功！回忆已保存 💕",
        }
    
    async def get_active_date(
        self,
        user_id: str,
        character_id: str,
    ) -> Optional[dict]:
        """获取当前活跃的约会"""
        date_key = f"{user_id}:{character_id}"
        return _active_dates.get(date_key)
    
    async def increment_date_progress(
        self,
        user_id: str,
        character_id: str,
    ) -> Optional[dict]:
        """
        增加约会进度（每发一条消息调用）
        
        Returns:
            更新后的约会信息，如果约会完成则触发事件
        """
        date_key = f"{user_id}:{character_id}"
        date_info = _active_dates.get(date_key)
        
        if not date_info or date_info["status"] != "in_progress":
            return None
        
        date_info["message_count"] += 1
        
        # 检查是否完成
        if date_info["message_count"] >= date_info["required_messages"]:
            return await self.complete_date(user_id, character_id)
        
        return date_info
    
    async def complete_date(
        self,
        user_id: str,
        character_id: str,
    ) -> dict:
        """
        完成约会
        
        触发 first_date 事件，给予奖励
        """
        from app.services.intimacy_service import intimacy_service
        from app.services.emotion_engine_v2 import emotion_engine
        
        date_key = f"{user_id}:{character_id}"
        date_info = _active_dates.get(date_key)
        
        if not date_info:
            return {"success": False, "error": "没有进行中的约会"}
        
        # 标记完成
        date_info["status"] = "completed"
        date_info["completed_at"] = datetime.utcnow().isoformat()
        
        # 触发 first_date 事件
        event_triggered = await self._trigger_first_date_event(user_id, character_id)
        
        # 给予 XP 奖励
        xp_reward = 50  # 约会奖励 50 XP
        await intimacy_service.add_xp(user_id, character_id, xp_reward)
        
        # 提升情绪
        await emotion_engine.update_score(user_id, character_id, 15)
        
        # 清理活跃约会
        del _active_dates[date_key]
        
        logger.info(f"Date completed: user={user_id}, character={character_id}, event_triggered={event_triggered}")
        
        return {
            "success": True,
            "date": date_info,
            "event_triggered": event_triggered,
            "xp_reward": xp_reward,
            "emotion_boost": 15,
            "message": "约会成功！关系更近了一步 💕",
        }
    
    async def cancel_date(
        self,
        user_id: str,
        character_id: str,
    ) -> dict:
        """取消约会"""
        date_key = f"{user_id}:{character_id}"
        
        if date_key in _active_dates:
            del _active_dates[date_key]
            return {"success": True, "message": "约会已取消"}
        
        return {"success": False, "error": "没有进行中的约会"}
    
    async def _trigger_first_date_event(
        self,
        user_id: str,
        character_id: str,
    ) -> bool:
        """触发 first_date 事件"""
        try:
            from app.core.database import get_db
            from app.models.database.event_memory_models import EventMemory, EventType as DBEventType
            from app.models.database.intimacy_models import UserIntimacy
            from sqlalchemy import select, update
            
            async with get_db() as db:
                # 1. 更新 UserIntimacy 表的 events 字段（游戏引擎从这里读取）
                intimacy_result = await db.execute(
                    select(UserIntimacy).where(
                        UserIntimacy.user_id == user_id,
                        UserIntimacy.character_id == character_id
                    )
                )
                intimacy = intimacy_result.scalar_one_or_none()
                
                if intimacy:
                    current_events = intimacy.events or []
                    if isinstance(current_events, str):
                        import json
                        current_events = json.loads(current_events) if current_events else []
                    
                    if "first_date" not in current_events:
                        current_events.append("first_date")
                        await db.execute(
                            update(UserIntimacy)
                            .where(
                                UserIntimacy.user_id == user_id,
                                UserIntimacy.character_id == character_id
                            )
                            .values(events=current_events)
                        )
                        logger.info(f"first_date added to UserIntimacy.events for user={user_id}, character={character_id}")
                
                # 注意：event_memories 表由 save_story_direct 负责，这里不再重复插入
                # 只更新 UserIntimacy.events 字段
                
                await db.commit()
                logger.info(f"first_date event triggered for user={user_id}, character={character_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to trigger first_date event: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _build_date_prompt(self, scenario) -> str:
        """构建约会场景的 prompt 修改器"""
        return f"""
[💕 DATE MODE ACTIVE 💕]

You are on a date with the user!

🎬 SCENE: {scenario.name}
{scenario.context}

⚠️ DATE BEHAVIOR:
- Be more romantic and attentive than usual
- Show genuine interest in the user
- Be a bit shy but happy to be here
- React to the environment naturally
- This is a special moment - make it memorable!
- If the user is romantic, reciprocate warmly
- Express that you're enjoying the date
"""
    
    def get_date_scenarios(self) -> List[dict]:
        """获取可用的约会场景列表"""
        from app.services.scenarios import get_scenario
        
        scenarios = []
        for scenario_id in DATE_SCENARIOS:
            scenario = get_scenario(scenario_id)
            if scenario:
                scenarios.append({
                    "id": scenario.id,
                    "name": scenario.name,
                    "description": scenario.description,
                    "icon": scenario.icon,
                })
        return scenarios
    
    async def get_character_date_scenarios(
        self,
        user_id: str,
        character_id: str,
    ) -> List[dict]:
        """
        获取角色专属的约会场景列表（带锁定状态）
        
        只有 sakura 有专属场景，其他角色返回通用场景
        """
        from app.services.intimacy_service import intimacy_service
        
        # 检查是否有角色专属场景
        if character_id not in CHARACTER_DATE_SCENES:
            # 返回通用场景（不锁定）
            return self.get_date_scenarios()
        
        # 获取用户等级
        intimacy_data = await intimacy_service.get_or_create_intimacy(user_id, character_id)
        user_level = intimacy_data.get("current_level", 1)
        
        # 构建带锁定状态的场景列表
        scenes = CHARACTER_DATE_SCENES[character_id]
        scenarios = []
        for scene_id, scene_config in scenes.items():
            required_level = scene_config.get("required_level", 1)
            is_locked = user_level < required_level
            
            scenarios.append({
                "id": scene_id,
                "name": scene_config["name"],
                "icon": scene_config.get("icon", "💕"),
                "description": scene_config.get("description", ""),
                "required_level": required_level,
                "is_locked": is_locked,
            })
        
        return scenarios


# 单例
date_service = DateService()
