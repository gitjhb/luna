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
        from app.services.intimacy_service import intimacy_service
        from app.services.game_engine import GameEngine
        
        # 检查等级
        intimacy_data = await intimacy_service.get_or_create_intimacy(user_id, character_id)
        level = intimacy_data.get("current_level", 1)
        
        if level < DATE_UNLOCK_LEVEL:
            return False, f"需要达到 LV {DATE_UNLOCK_LEVEL} 才能解锁约会 (当前 LV {level})"
        
        # 检查是否已送过礼物
        game_engine = GameEngine()
        user_state = await game_engine._load_user_state(user_id, character_id)
        
        if "first_gift" not in user_state.events:
            return False, "需要先送过礼物才能邀请约会"
        
        # 检查是否已经约会过
        if "first_date" in user_state.events:
            return True, "已完成首次约会，可以再次约会"
        
        return True, "约会已解锁"
    
    async def start_date(
        self,
        user_id: str,
        character_id: str,
        scenario_id: Optional[str] = None,
    ) -> dict:
        """
        开始约会
        
        Args:
            user_id: 用户ID
            character_id: 角色ID
            scenario_id: 场景ID（可选，不传则随机）
            
        Returns:
            约会信息
        """
        from app.services.scenarios import get_scenario
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
        
        # 创建约会记录
        date_id = str(uuid4())
        date_key = f"{user_id}:{character_id}"
        
        date_info = {
            "date_id": date_id,
            "user_id": user_id,
            "character_id": character_id,
            "scenario_id": scenario_id,
            "scenario_name": scenario.name,
            "scenario_context": scenario.context,
            "scenario_icon": scenario.icon,
            "started_at": datetime.utcnow().isoformat(),
            "message_count": 0,
            "required_messages": DATE_COMPLETION_MESSAGES,
            "status": "in_progress",
        }
        
        _active_dates[date_key] = date_info
        
        logger.info(f"Date started: user={user_id}, character={character_id}, scenario={scenario_id}")
        
        return {
            "success": True,
            "date": date_info,
            "prompt_modifier": self._build_date_prompt(scenario),
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
            from app.core.database import get_session
            from app.models.database.event_memory_models import EventMemory, EventType as DBEventType
            from sqlalchemy import select
            
            async with get_session() as session:
                # 检查是否已存在
                stmt = select(EventMemory).where(
                    EventMemory.user_id == user_id,
                    EventMemory.character_id == character_id,
                    EventMemory.event_type == "first_date"
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    return False  # 已经有了
                
                # 创建事件记录
                event = EventMemory(
                    user_id=user_id,
                    character_id=character_id,
                    event_type="first_date",
                    event_summary="完成了第一次约会",
                    emotion_snapshot=50,
                    intimacy_snapshot=40,
                )
                session.add(event)
                await session.commit()
                
                return True
        except Exception as e:
            logger.error(f"Failed to trigger first_date event: {e}")
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


# 单例
date_service = DateService()
