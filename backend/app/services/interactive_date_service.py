"""
Interactive Date Service - 互动式约会系统
==========================================

类似《心跳回忆》的互动式剧情约会：
- 分阶段剧情，用户做选择
- LLM 实时生成剧情和选项
- 不同选择影响结局和奖励
- 有冷却时间机制

持久化改进 (2026-02-02):
- 约会状态持久化到数据库，服务器重启后不会丢失进行中的约会
- 冷却时间也持久化到数据库
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from uuid import uuid4
from enum import Enum
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

# Import intimacy_service for stage behavior
from app.services.intimacy_service import intimacy_service

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DATE_STAGES = 5  # 约会阶段数
COOLDOWN_HOURS = 24  # 普通用户冷却时间
VIP_COOLDOWN_HOURS = 6  # VIP 冷却时间

# 结局阈值
ENDING_THRESHOLDS = {
    "perfect": 60,   # affection >= 60
    "good": 30,      # affection >= 30
    "normal": 0,     # affection >= 0
    "bad": -100,     # affection < 0
}

# 结局奖励 - 情绪变化范围 -60 到 +60，让约会结果对角色状态有显著影响
ENDING_REWARDS = {
    "perfect": {"xp": 100, "emotion": 60},   # 完美约会，角色非常开心
    "good": {"xp": 50, "emotion": 30},       # 不错的约会
    "normal": {"xp": 20, "emotion": 10},     # 普通约会
    "bad": {"xp": 5, "emotion": -40},        # 糟糕约会，角色很不开心
}


# =============================================================================
# Data Classes
# =============================================================================

class DateStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class EndingType(str, Enum):
    PERFECT = "perfect"
    GOOD = "good"
    NORMAL = "normal"
    BAD = "bad"


@dataclass
class DateOption:
    id: int
    text: str
    type: str  # "good", "neutral", "bad", "special"
    affection: int  # 好感度变化
    requirement: Optional[str] = None  # 特殊选项的解锁条件描述
    requires_affection: Optional[int] = None  # 需要的最低好感度
    is_locked: bool = False  # 是否锁定（条件不满足）


@dataclass
class DateStage:
    stage_num: int
    narrative: str
    character_expression: str
    options: List[DateOption]
    user_choice: Optional[int] = None
    affection_change: int = 0
    timestamp: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "stage_num": self.stage_num,
            "narrative": self.narrative,
            "character_expression": self.character_expression,
            "options": [
                {
                    "id": o.id, 
                    "text": o.text,
                    "is_special": o.type == "special",
                    "is_locked": o.is_locked,
                    "requirement": o.requirement,
                } 
                for o in self.options
            ],
            "user_choice": self.user_choice,
            "affection_change": self.affection_change,
            "timestamp": self.timestamp,
            "supports_free_input": True,  # 标记支持自由输入
        }


@dataclass
class DateSession:
    id: str
    user_id: str
    character_id: str
    scenario_id: str
    scenario_name: str
    
    stages: List[DateStage] = field(default_factory=list)
    current_stage: int = 0
    
    affection_score: int = 0  # 累计好感度
    status: str = DateStatus.IN_PROGRESS.value
    
    ending_type: Optional[str] = None
    xp_awarded: int = 0
    story_summary: Optional[str] = None
    
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    cooldown_until: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "character_id": self.character_id,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "stages": [s.to_dict() for s in self.stages],
            "current_stage": self.current_stage,
            "affection_score": self.affection_score,
            "status": self.status,
            "ending_type": self.ending_type,
            "xp_awarded": self.xp_awarded,
            "story_summary": self.story_summary,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "cooldown_until": self.cooldown_until,
        }


# =============================================================================
# In-Memory Cache + Database Persistence
# =============================================================================

# 内存缓存（用于快速访问，但以数据库为准）
_active_sessions: Dict[str, DateSession] = {}  # session_id -> DateSession
_user_cooldowns: Dict[str, str] = {}  # user_id:character_id -> cooldown_until ISO string


# =============================================================================
# Database Helpers
# =============================================================================

async def _load_active_session_from_db(user_id: str, character_id: str) -> Optional[DateSession]:
    """从数据库加载进行中的约会"""
    from app.core.database import get_db
    from app.models.database.date_models import DateSessionDB
    
    async with get_db() as db:
        try:
            result = await db.execute(
                select(DateSessionDB).where(
                    and_(
                        DateSessionDB.user_id == user_id,
                        DateSessionDB.character_id == character_id,
                        DateSessionDB.status == "in_progress"
                    )
                )
            )
            db_session = result.scalar_one_or_none()
            
            if db_session:
                # 转换为 DateSession 对象
                stages = []
                for stage_data in (db_session.stages_data or []):
                    options = [
                        DateOption(
                            id=opt.get("id", i),
                            text=opt.get("text", ""),
                            type=opt.get("type", "neutral"),
                            affection=opt.get("affection", 0),
                            is_locked=opt.get("is_locked", False),
                            requirement=opt.get("requirement"),
                        )
                        for i, opt in enumerate(stage_data.get("options", []))
                    ]
                    stage = DateStage(
                        stage_num=stage_data.get("stage_num", 0),
                        narrative=stage_data.get("narrative", ""),
                        character_expression=stage_data.get("character_expression", "neutral"),
                        options=options,
                        user_choice=stage_data.get("user_choice"),
                        affection_change=stage_data.get("affection_change", 0),
                        timestamp=stage_data.get("timestamp"),
                    )
                    stages.append(stage)
                
                session = DateSession(
                    id=db_session.id,
                    user_id=db_session.user_id,
                    character_id=db_session.character_id,
                    scenario_id=db_session.scenario_id,
                    scenario_name=db_session.scenario_name,
                    stages=stages,
                    current_stage=db_session.current_stage,
                    affection_score=db_session.affection_score,
                    status=db_session.status,
                    ending_type=db_session.ending_type,
                    xp_awarded=db_session.xp_awarded,
                    story_summary=db_session.story_summary,
                    started_at=db_session.started_at.isoformat() if db_session.started_at else None,
                    completed_at=db_session.completed_at.isoformat() if db_session.completed_at else None,
                    cooldown_until=db_session.cooldown_until.isoformat() if db_session.cooldown_until else None,
                )
                
                # 缓存到内存
                _active_sessions[session.id] = session
                return session
        except Exception as e:
            logger.error(f"Failed to load session from DB: {e}")
    
    return None


async def _save_session_to_db(session: DateSession):
    """保存约会到数据库"""
    from app.core.database import get_db
    from app.models.database.date_models import DateSessionDB
    
    async with get_db() as db:
        try:
            # 查找现有记录
            result = await db.execute(
                select(DateSessionDB).where(DateSessionDB.id == session.id)
            )
            db_session = result.scalar_one_or_none()
            
            # 准备 stages 数据
            stages_data = [s.to_dict() for s in session.stages]
            
            if db_session:
                # 更新
                db_session.current_stage = session.current_stage
                db_session.affection_score = session.affection_score
                db_session.status = session.status
                db_session.stages_data = stages_data
                db_session.ending_type = session.ending_type
                db_session.xp_awarded = session.xp_awarded
                db_session.story_summary = session.story_summary
                if session.completed_at:
                    db_session.completed_at = datetime.fromisoformat(session.completed_at)
                if session.cooldown_until:
                    db_session.cooldown_until = datetime.fromisoformat(session.cooldown_until)
            else:
                # 创建新记录
                db_session = DateSessionDB(
                    id=session.id,
                    user_id=session.user_id,
                    character_id=session.character_id,
                    scenario_id=session.scenario_id,
                    scenario_name=session.scenario_name,
                    current_stage=session.current_stage,
                    affection_score=session.affection_score,
                    status=session.status,
                    stages_data=stages_data,
                    started_at=datetime.fromisoformat(session.started_at) if session.started_at else datetime.utcnow(),
                )
                db.add(db_session)
            
            await db.commit()
            logger.debug(f"Saved session {session.id} to DB")
        except Exception as e:
            logger.error(f"Failed to save session to DB: {e}")
            await db.rollback()


async def _load_cooldown_from_db(user_id: str, character_id: str) -> Optional[str]:
    """从数据库加载冷却时间"""
    from app.core.database import get_db
    from app.models.database.date_models import DateCooldownDB
    
    async with get_db() as db:
        try:
            result = await db.execute(
                select(DateCooldownDB).where(
                    and_(
                        DateCooldownDB.user_id == user_id,
                        DateCooldownDB.character_id == character_id,
                    )
                )
            )
            cooldown = result.scalar_one_or_none()
            
            if cooldown and cooldown.cooldown_until > datetime.utcnow():
                cooldown_str = cooldown.cooldown_until.isoformat()
                # 缓存到内存
                _user_cooldowns[f"{user_id}:{character_id}"] = cooldown_str
                return cooldown_str
        except Exception as e:
            logger.error(f"Failed to load cooldown from DB: {e}")
    
    return None


async def _save_cooldown_to_db(user_id: str, character_id: str, cooldown_until: datetime):
    """保存冷却时间到数据库"""
    from app.core.database import get_db
    from app.models.database.date_models import DateCooldownDB
    
    async with get_db() as db:
        try:
            # 查找现有记录
            result = await db.execute(
                select(DateCooldownDB).where(
                    and_(
                        DateCooldownDB.user_id == user_id,
                        DateCooldownDB.character_id == character_id,
                    )
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.cooldown_until = cooldown_until
            else:
                cooldown = DateCooldownDB(
                    user_id=user_id,
                    character_id=character_id,
                    cooldown_until=cooldown_until,
                )
                db.add(cooldown)
            
            await db.commit()
            logger.debug(f"Saved cooldown for {user_id}:{character_id}")
        except Exception as e:
            logger.error(f"Failed to save cooldown to DB: {e}")
            await db.rollback()


async def _clear_cooldown_from_db(user_id: str, character_id: str):
    """清除冷却时间"""
    from app.core.database import get_db
    from app.models.database.date_models import DateCooldownDB
    
    async with get_db() as db:
        try:
            result = await db.execute(
                select(DateCooldownDB).where(
                    and_(
                        DateCooldownDB.user_id == user_id,
                        DateCooldownDB.character_id == character_id,
                    )
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                await db.delete(existing)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to clear cooldown from DB: {e}")


# =============================================================================
# Service
# =============================================================================

class InteractiveDateService:
    """互动式约会服务"""
    
    async def check_can_date(
        self,
        user_id: str,
        character_id: str,
    ) -> Dict[str, Any]:
        """
        检查用户是否可以约会
        
        Returns:
            can_date: 是否可以约会
            cooldown_until: 冷却结束时间
            cooldown_remaining_minutes: 剩余分钟
            active_session: 进行中的约会
        """
        # 检查是否有进行中的约会（先内存，再数据库）
        active_session = await self._get_active_session(user_id, character_id)
        if active_session:
            return {
                "can_date": False,
                "reason": "already_in_date",
                "active_session": {
                    "session_id": active_session.id,
                    "stage_num": active_session.current_stage,
                    "scenario_name": active_session.scenario_name,
                }
            }
        
        # 检查冷却（先内存缓存，再数据库）
        cooldown_key = f"{user_id}:{character_id}"
        cooldown_until_str = _user_cooldowns.get(cooldown_key)
        
        # 如果内存没有，查数据库
        if not cooldown_until_str:
            cooldown_until_str = await _load_cooldown_from_db(user_id, character_id)
        
        if cooldown_until_str:
            cooldown_until = datetime.fromisoformat(cooldown_until_str)
            now = datetime.utcnow()
            
            if now < cooldown_until:
                remaining = (cooldown_until - now).total_seconds() / 60
                return {
                    "can_date": False,
                    "reason": "cooldown",
                    "cooldown_until": cooldown_until_str,
                    "cooldown_remaining_minutes": int(remaining),
                }
        
        return {
            "can_date": True,
            "cooldown_until": None,
            "cooldown_remaining_minutes": 0,
            "active_session": None,
        }
    
    async def start_date(
        self,
        user_id: str,
        character_id: str,
        scenario_id: str,
    ) -> Dict[str, Any]:
        """
        开始新的互动式约会
        
        Returns:
            session_id, 第一个 stage 的剧情和选项
        """
        from app.services.scenarios import get_scenario
        from app.services.date_service import date_service
        
        # 检查解锁条件
        is_unlocked, reason = await date_service.check_date_unlock(user_id, character_id)
        if not is_unlocked:
            return {"success": False, "error": reason}
        
        # 检查是否可以约会（冷却/进行中）
        status = await self.check_can_date(user_id, character_id)
        if not status["can_date"]:
            if status.get("reason") == "already_in_date":
                return {
                    "success": False,
                    "error": "已有进行中的约会",
                    "active_session": status["active_session"],
                }
            else:
                return {
                    "success": False,
                    "error": f"约会冷却中，还需等待 {status['cooldown_remaining_minutes']} 分钟",
                    "cooldown_until": status["cooldown_until"],
                }
        
        # 获取场景
        scenario = get_scenario(scenario_id)
        if not scenario:
            return {"success": False, "error": f"未知场景: {scenario_id}"}
        
        # 创建会话
        session = DateSession(
            id=str(uuid4()),
            user_id=user_id,
            character_id=character_id,
            scenario_id=scenario_id,
            scenario_name=scenario.name,
        )
        
        # 生成第一个阶段
        first_stage = await self._generate_stage(
            session=session,
            stage_num=1,
            previous_choice=None,
        )
        
        if not first_stage:
            return {"success": False, "error": "生成剧情失败"}
        
        session.stages.append(first_stage)
        session.current_stage = 1
        
        # 保存会话到内存缓存和数据库
        _active_sessions[session.id] = session
        await _save_session_to_db(session)
        
        logger.info(f"Date started: session={session.id}, user={user_id}, character={character_id}")
        
        return {
            "success": True,
            "session_id": session.id,
            "scenario": {
                "id": scenario_id,
                "name": scenario.name,
                "icon": scenario.icon,
            },
            "stage": first_stage.to_dict(),
            "progress": {
                "current": 1,
                "total": DATE_STAGES,
            },
        }
    
    async def make_choice(
        self,
        session_id: str,
        choice_id: int,
    ) -> Dict[str, Any]:
        """
        用户做出选择，生成下一阶段
        
        Returns:
            下一个 stage 的剧情和选项，或者结局
        """
        # 先查内存，再查数据库
        session = _active_sessions.get(session_id)
        if not session:
            # 尝试从数据库加载（通过遍历所有活动会话）
            from app.core.database import get_db
            from app.models.database.date_models import DateSessionDB
            
            async with get_db() as db:
                try:
                    result = await db.execute(
                        select(DateSessionDB).where(DateSessionDB.id == session_id)
                    )
                    db_session = result.scalar_one_or_none()
                    if db_session and db_session.status == "in_progress":
                        # 重建 session 对象
                        session = await _load_active_session_from_db(db_session.user_id, db_session.character_id)
                except Exception as e:
                    logger.error(f"Failed to load session {session_id}: {e}")
        
        if not session:
            return {"success": False, "error": "约会会话不存在或已结束"}
        
        if session.status != DateStatus.IN_PROGRESS.value:
            return {"success": False, "error": "约会已结束"}
        
        # 获取当前阶段
        current_stage = session.stages[-1] if session.stages else None
        if not current_stage:
            return {"success": False, "error": "没有当前阶段"}
        
        # 验证选择
        if choice_id < 0 or choice_id >= len(current_stage.options):
            return {"success": False, "error": "无效的选择"}
        
        chosen_option = current_stage.options[choice_id]
        
        # 检查特殊选项是否被锁定
        if chosen_option.is_locked:
            return {
                "success": False, 
                "error": f"该选项需要 {chosen_option.requirement or '更高好感度'}"
            }
        
        # 记录选择
        current_stage.user_choice = choice_id
        current_stage.affection_change = chosen_option.affection
        current_stage.timestamp = datetime.utcnow().isoformat()
        
        # 更新累计好感度
        session.affection_score += chosen_option.affection
        
        logger.info(f"📅 [DATE] Choice made: session={session_id}")
        logger.info(f"📅 [DATE] Stage: {current_stage.stage_num}, Choice: {choice_id}")
        logger.info(f"📅 [DATE] Option text: {chosen_option.text[:50]}...")
        logger.info(f"📅 [DATE] Affection change: {chosen_option.affection}, Total: {session.affection_score}")
        
        # 检查是否是最后阶段
        if current_stage.stage_num >= DATE_STAGES:
            # 结束约会，计算结局
            return await self._complete_date(session)
        
        # 生成下一阶段
        next_stage = await self._generate_stage(
            session=session,
            stage_num=current_stage.stage_num + 1,
            previous_choice=chosen_option.text,
        )
        
        if not next_stage:
            return {"success": False, "error": "生成剧情失败"}
        
        session.stages.append(next_stage)
        session.current_stage = next_stage.stage_num
        
        # 保存到数据库
        await _save_session_to_db(session)
        
        return {
            "success": True,
            "affection_change": chosen_option.affection,
            "stage": next_stage.to_dict(),
            "progress": {
                "current": next_stage.stage_num,
                "total": DATE_STAGES,
            },
        }
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息（先内存，再数据库）"""
        session = _active_sessions.get(session_id)
        if not session:
            # 尝试从数据库加载
            from app.core.database import get_db
            from app.models.database.date_models import DateSessionDB
            
            async with get_db() as db:
                try:
                    result = await db.execute(
                        select(DateSessionDB).where(DateSessionDB.id == session_id)
                    )
                    db_session = result.scalar_one_or_none()
                    if db_session:
                        return db_session.to_dict()
                except Exception as e:
                    logger.error(f"Failed to load session {session_id}: {e}")
            return None
        return session.to_dict()
    
    async def process_free_input(
        self,
        session_id: str,
        user_input: str,
    ) -> Dict[str, Any]:
        """
        处理用户自由输入
        
        LLM 作为"裁判"评判用户输入的质量，决定 affection_change 并延续剧情
        """
        # 先查内存，再查数据库
        session = _active_sessions.get(session_id)
        if not session:
            from app.core.database import get_db
            from app.models.database.date_models import DateSessionDB
            
            async with get_db() as db:
                try:
                    result = await db.execute(
                        select(DateSessionDB).where(DateSessionDB.id == session_id)
                    )
                    db_session = result.scalar_one_or_none()
                    if db_session and db_session.status == "in_progress":
                        session = await _load_active_session_from_db(db_session.user_id, db_session.character_id)
                except Exception as e:
                    logger.error(f"Failed to load session {session_id}: {e}")
        
        if not session:
            return {"success": False, "error": "约会会话不存在或已结束"}
        
        if session.status != DateStatus.IN_PROGRESS.value:
            return {"success": False, "error": "约会已结束"}
        
        current_stage = session.stages[-1] if session.stages else None
        if not current_stage:
            return {"success": False, "error": "没有当前阶段"}
        
        # 调用 LLM 评判用户输入
        judge_result = await self._judge_free_input(
            session=session,
            current_stage=current_stage,
            user_input=user_input,
        )
        
        if not judge_result:
            return {"success": False, "error": "评判失败"}
        
        affection_change = judge_result.get("affection_change", 0)
        
        # 记录用户输入作为"选择"
        current_stage.user_choice = -1  # -1 表示自由输入
        current_stage.affection_change = affection_change
        current_stage.timestamp = datetime.utcnow().isoformat()
        
        # 更新累计好感度
        session.affection_score += affection_change
        
        logger.info(f"Free input processed: session={session_id}, "
                   f"affection_change={affection_change}, input={user_input[:50]}")
        
        # 检查是否是最后阶段
        if current_stage.stage_num >= DATE_STAGES:
            return await self._complete_date(session)
        
        # 生成下一阶段，传入用户的自由输入
        next_stage = await self._generate_stage(
            session=session,
            stage_num=current_stage.stage_num + 1,
            previous_choice=f"（用户说）{user_input}",
        )
        
        if not next_stage:
            return {"success": False, "error": "生成剧情失败"}
        
        session.stages.append(next_stage)
        session.current_stage = next_stage.stage_num
        
        # 保存到数据库
        await _save_session_to_db(session)
        
        return {
            "success": True,
            "affection_change": affection_change,
            "judge_comment": judge_result.get("comment", ""),
            "stage": next_stage.to_dict(),
            "progress": {
                "current": next_stage.stage_num,
                "total": DATE_STAGES,
            },
        }
    
    async def _judge_free_input(
        self,
        session: DateSession,
        current_stage: DateStage,
        user_input: str,
    ) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 评判用户自由输入
        
        Returns:
            {"affection_change": int, "comment": str}
        """
        from app.services.character_config import get_character_config
        from app.services.llm_service import GrokService
        
        try:
            character = get_character_config(session.character_id)
            character_name = character.name if character else "角色"
            
            prompt = f"""你是约会评判系统。用户在约会中对{character_name}说了一句话，请评判这句话的质量。

## 角色设定
{character_name}的性格：{(character.system_prompt[:300] if character and character.system_prompt else "温柔可爱")}

## 当前约会情境
{current_stage.narrative[:500]}

## 用户说的话
"{user_input}"

## 当前好感度
{session.affection_score}/100

## 评判标准
- 如果用户说的话很甜、很浪漫、很有趣、很贴心：+10 到 +25
- 如果用户说的话普通、正常对话：0 到 +5
- 如果用户说的话冷场、无聊、不合时宜：-5 到 -15
- 如果用户说的话非常尴尬、冒犯、creepy：-15 到 -25

## 输出格式 (JSON)
```json
{{
  "affection_change": <数字>,
  "comment": "<简短评价，会显示给用户>"
}}
```

直接输出 JSON。"""
            
            llm = GrokService()
            llm_response = await llm.chat_completion(
                messages=[
                    {"role": "system", "content": "你是约会评判系统，公正地评判用户的表现。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7,
            )
            
            # Token 统计（评判）
            usage = llm_response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
            cost_usd = (total_tokens / 1_000_000) * 0.2
            logger.info(f"📅 [DATE-JUDGE] Token usage: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}, cost=${cost_usd:.6f}")
            
            # 提取 content
            response = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # 解析响应
            response = response.strip()
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()
            
            result = json.loads(response)
            
            # 限制范围
            affection = result.get("affection_change", 0)
            affection = max(-25, min(25, affection))
            result["affection_change"] = affection
            
            return result
            
        except Exception as e:
            logger.error(f"Error judging free input: {e}")
            # 返回默认中等评价
            return {"affection_change": 5, "comment": "还不错~"}
    
    async def abandon_date(self, session_id: str) -> Dict[str, Any]:
        """放弃当前约会"""
        # 先查内存
        session = _active_sessions.get(session_id)
        
        # 如果内存没有，从数据库加载
        if not session:
            from app.core.database import get_db
            from app.models.database.date_models import DateSessionDB
            
            async with get_db() as db:
                try:
                    result = await db.execute(
                        select(DateSessionDB).where(DateSessionDB.id == session_id)
                    )
                    db_session = result.scalar_one_or_none()
                    if db_session and db_session.status == "in_progress":
                        session = await _load_active_session_from_db(db_session.user_id, db_session.character_id)
                except Exception as e:
                    logger.error(f"Failed to load session {session_id}: {e}")
        
        if not session:
            return {"success": False, "error": "会话不存在"}
        
        session.status = DateStatus.ABANDONED.value
        session.completed_at = datetime.utcnow().isoformat()
        
        # 设置冷却（放弃也有冷却，但时间减半）
        cooldown_hours = COOLDOWN_HOURS // 2
        cooldown_until = datetime.utcnow() + timedelta(hours=cooldown_hours)
        cooldown_key = f"{session.user_id}:{session.character_id}"
        _user_cooldowns[cooldown_key] = cooldown_until.isoformat()
        
        # 保存到数据库
        await _save_session_to_db(session)
        await _save_cooldown_to_db(session.user_id, session.character_id, cooldown_until)
        
        # 清理内存缓存
        if session_id in _active_sessions:
            del _active_sessions[session_id]
        
        return {
            "success": True,
            "message": "约会已取消",
            "cooldown_hours": cooldown_hours,
        }
    
    async def reset_cooldown(
        self,
        user_id: str,
        character_id: str,
    ) -> Dict[str, Any]:
        """
        使用月石重置约会冷却时间
        
        费用：50 月石
        """
        from app.services.payment_service import payment_service
        
        RESET_PRICE = 50
        
        # 检查是否有冷却（先内存，再数据库）
        cooldown_key = f"{user_id}:{character_id}"
        cooldown_until_str = _user_cooldowns.get(cooldown_key)
        
        # 如果内存没有，查数据库
        if not cooldown_until_str:
            cooldown_until_str = await _load_cooldown_from_db(user_id, character_id)
        
        if not cooldown_until_str:
            # 没有冷却，直接返回成功（用户已经可以约会了）
            return {"success": True, "message": "没有冷却限制，可以直接约会！", "credits_deducted": 0}
        
        cooldown_until = datetime.fromisoformat(cooldown_until_str)
        if datetime.utcnow() >= cooldown_until:
            # 已经过了冷却时间，清除并返回成功
            if cooldown_key in _user_cooldowns:
                del _user_cooldowns[cooldown_key]
            await _clear_cooldown_from_db(user_id, character_id)
            return {"success": True, "message": "冷却已结束，可以约会！", "credits_deducted": 0}
        
        # 检查余额
        try:
            wallet = await payment_service.get_wallet(user_id)
            if wallet["total_credits"] < RESET_PRICE:
                return {
                    "success": False,
                    "error": f"月石不足，需要 {RESET_PRICE} 月石",
                    "required": RESET_PRICE,
                    "current_balance": wallet["total_credits"],
                }
            
            # 扣除月石
            await payment_service.deduct_credits(user_id, RESET_PRICE)
            
            # 清除冷却（内存和数据库）
            if cooldown_key in _user_cooldowns:
                del _user_cooldowns[cooldown_key]
            await _clear_cooldown_from_db(user_id, character_id)
            
            logger.info(f"Cooldown reset: user={user_id}, character={character_id}, cost={RESET_PRICE}")
            
            return {
                "success": True,
                "message": "冷却已重置，可以立即约会！",
                "credits_deducted": RESET_PRICE,
                "new_balance": wallet["total_credits"] - RESET_PRICE,
            }
            
        except Exception as e:
            logger.error(f"Error resetting cooldown: {e}")
            return {"success": False, "error": "重置失败，请稍后重试"}
    
    # =========================================================================
    # Private Methods
    # =========================================================================
    
    async def _get_active_session(self, user_id: str, character_id: str) -> Optional[DateSession]:
        """获取用户进行中的约会（先查内存缓存，再查数据库）"""
        # 先查内存缓存
        for session in _active_sessions.values():
            if (session.user_id == user_id and 
                session.character_id == character_id and
                session.status == DateStatus.IN_PROGRESS.value):
                return session
        
        # 内存没有，查数据库
        return await _load_active_session_from_db(user_id, character_id)
    
    async def _generate_stage(
        self,
        session: DateSession,
        stage_num: int,
        previous_choice: Optional[str],
    ) -> Optional[DateStage]:
        """
        使用 LLM 生成约会阶段
        
        Returns:
            DateStage with narrative and options
        """
        from app.services.scenarios import get_scenario
        from app.services.character_config import get_character_config
        from app.services.llm_service import GrokService
        from app.services.intimacy_service import intimacy_service
        
        try:
            # 获取角色信息
            character = get_character_config(session.character_id)
            scenario = get_scenario(session.scenario_id)
            
            # 获取亲密度等级和阶段（使用 IntimacyService 统一方法）
            intimacy_level = 1
            intimacy_stage = "strangers"
            try:
                intimacy_status = await intimacy_service.get_intimacy_status(
                    session.user_id, session.character_id
                )
                intimacy_level = intimacy_status.get("current_level", 1)
                intimacy_stage = intimacy_service.get_stage_id(intimacy_level)
            except Exception as e:
                logger.warning(f"Failed to get intimacy status: {e}")
            
            logger.info(f"📅 [DATE] Generating stage {stage_num}/{DATE_STAGES}")
            logger.info(f"📅 [DATE] Session: {session.id}, User: {session.user_id}, Character: {session.character_id}")
            logger.info(f"📅 [DATE] Scenario: {session.scenario_name}, Affection: {session.affection_score}")
            logger.info(f"📅 [DATE] Intimacy Level: {intimacy_level}, Stage: {intimacy_stage}")
            if previous_choice:
                logger.info(f"📅 [DATE] Previous choice: {previous_choice[:50]}...")
            
            # 构建之前的剧情摘要
            previous_stages_text = ""
            if session.stages:
                for s in session.stages:
                    choice_text = ""
                    if s.user_choice is not None and s.options:
                        choice_text = f"\n用户选择了: {s.options[s.user_choice].text}"
                    previous_stages_text += f"\n[第{s.stage_num}幕]\n{s.narrative}{choice_text}\n"
            
            # 确定是否是最后阶段
            is_final = stage_num >= DATE_STAGES
            
            # 构建 prompt（包含亲密度阶段）
            prompt = self._build_stage_prompt(
                character_name=character.name if character else "角色",
                character_personality=character.system_prompt if character else "",
                scenario_name=scenario.name if scenario else session.scenario_name,
                scenario_context=scenario.context if scenario else "",
                stage_num=stage_num,
                total_stages=DATE_STAGES,
                previous_stages=previous_stages_text,
                previous_choice=previous_choice,
                current_affection=session.affection_score,
                is_final=is_final,
                intimacy_level=intimacy_level,
                intimacy_stage=intimacy_stage,
            )
            
            # 日志：打印 prompt 长度和估算 token 数
            prompt_chars = len(prompt)
            estimated_tokens = prompt_chars // 2  # 中文约 2 字符/token
            logger.info(f"📅 [DATE] Prompt length: {prompt_chars} chars, ~{estimated_tokens} tokens")
            logger.info(f"📅 [DATE] Full prompt:\n{prompt[:500]}...")
            
            # 调用 LLM
            import time
            llm_start = time.time()
            llm = GrokService()
            llm_response = await llm.chat_completion(
                messages=[
                    {"role": "system", "content": "你是一个约会剧情生成器，擅长创作浪漫、有趣、沉浸式的恋爱故事。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.8,
            )
            llm_elapsed = time.time() - llm_start
            
            # Token 统计
            usage = llm_response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
            
            # 计算成本 (grok-4-1-fast-non-reasoning: $0.2/M tokens)
            cost_per_million = 0.2
            cost_usd = (total_tokens / 1_000_000) * cost_per_million
            
            logger.info(f"📅 [DATE] LLM call took {llm_elapsed:.2f}s")
            logger.info(f"📅 [DATE] Token usage: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}")
            logger.info(f"📅 [DATE] Estimated cost: ${cost_usd:.6f} USD")
            
            # 提取 content
            response = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # 打印原始AI生成内容供参考
            logger.info(f"📅 [DATE] Stage {stage_num} AI raw response:\n{response}")
            
            # 解析响应
            stage_data = self._parse_stage_response(response)
            if not stage_data:
                logger.error(f"Failed to parse LLM response for stage {stage_num}")
                # 返回默认阶段
                return self._create_fallback_stage(stage_num, is_final)
            
            # 构建 DateStage，处理特殊选项的锁定状态
            # + 数值校验层：防止 LLM 返回的 affection 超出范围
            options = []
            for i, opt in enumerate(stage_data.get("options", [])):
                opt_type = opt.get("type", "neutral")
                requires_affection = opt.get("requires_affection")
                is_locked = False
                
                # 检查特殊选项是否满足条件
                if opt_type == "special" and requires_affection:
                    if session.affection_score < requires_affection:
                        is_locked = True
                
                # 数值校验：限制 affection_change 范围
                raw_affection = opt.get("affection", 0)
                if opt_type == "special":
                    validated_affection = max(-15, min(25, raw_affection))  # 特殊选项最高 +25
                else:
                    validated_affection = max(-15, min(15, raw_affection))  # 普通选项 -15 到 +15
                
                options.append(DateOption(
                    id=i,
                    text=opt["text"],
                    type=opt_type,
                    affection=validated_affection,
                    requirement=opt.get("requirement"),
                    requires_affection=requires_affection,
                    is_locked=is_locked,
                ))
            
            # 最终阶段：如果没有options，添加"结束约会"按钮
            if is_final and len(options) == 0:
                options.append(DateOption(
                    id=0,
                    text="结束约会",
                    type="end",
                    affection=0,
                ))
            
            return DateStage(
                stage_num=stage_num,
                narrative=stage_data.get("narrative", ""),
                character_expression=stage_data.get("character_expression", "neutral"),
                options=options,
            )
            
        except Exception as e:
            logger.error(f"Error generating stage: {e}")
            return self._create_fallback_stage(stage_num, stage_num >= DATE_STAGES)
    
    def _build_stage_prompt(
        self,
        character_name: str,
        character_personality: str,
        scenario_name: str,
        scenario_context: str,
        stage_num: int,
        total_stages: int,
        previous_stages: str,
        previous_choice: Optional[str],
        current_affection: int,
        is_final: bool,
        intimacy_level: int = 1,
        intimacy_stage: str = "strangers",
    ) -> str:
        """
        构建 LLM prompt - 三层架构：
        1. Persona（角色灵魂）
        2. Rules（规则约束）
        3. State Snapshot（当前快照）
        """
        
        # =====================================================================
        # 从 IntimacyService 获取阶段行为（统一双轨制）
        # =====================================================================
        stage_info = intimacy_service.get_stage(intimacy_level)
        stage_behavior = intimacy_service.get_stage_behavior(level=intimacy_level)
        
        intimacy_rule_text = f"""【{stage_behavior['code']} {stage_behavior['name_cn']}阶段 Lv.{stage_info['min_level']}-{stage_info['max_level']}】
- 态度：{stage_behavior['ai_attitude']}
- 身体接触：{stage_behavior['physical']}
- 拒绝方式：{stage_behavior['refusal']}
- 约会行为：{stage_behavior['date_behavior']}"""
        
        # =====================================================================
        # Layer 1: Persona（角色灵魂）
        # =====================================================================
        persona_layer = f"""你是 {character_name}，正在和用户约会。
{character_personality[:400] if character_personality else "你是一个温柔可爱的角色。"}"""
        
        # =====================================================================
        # Layer 2: Rules（规则约束）
        # =====================================================================
        rules_layer = f"""## 核心规则
1. 绝对不要跳出角色，始终以角色视角演绎
2. 必须以 JSON 格式返回响应
3. 选项必须包含：一个讨好的、一个平淡的、一个会让角色不开心的
4. affection_change 范围限制：-15 到 +15（特殊选项最高 +25）
5. 对话用「」标注，动作用（）标注
6. 根据当前好感度调整角色态度和亲密程度

## 亲密度阶段限制（非常重要！）
当前亲密度等级：Lv.{intimacy_level}（{stage_behavior['code']} {stage_behavior['name_cn']}）
{intimacy_rule_text}"""

        # =====================================================================
        # Layer 3: State Snapshot（当前快照）
        # =====================================================================
        # 确定角色态度模式
        attitude_mode = self._get_attitude_mode(current_affection)
        
        # 构建历史选择摘要
        history_summary = []
        if previous_stages:
            history_summary.append(f"之前的互动：{previous_stages[:300]}")
        if previous_choice:
            history_summary.append(f"用户刚才：{previous_choice}")
        
        state_snapshot = f"""## 当前游戏状态
```json
{{
  "stage": {stage_num},
  "total_stages": {total_stages},
  "affection": {current_affection},
  "attitude_mode": "{attitude_mode}",
  "intimacy_level": {intimacy_level},
  "intimacy_stage": "{intimacy_stage}",
  "location": "{scenario_name}",
  "is_final_stage": {str(is_final).lower()}
}}
```

## 历史记录
{chr(10).join(history_summary) if history_summary else "这是约会的开始"}"""

        # =====================================================================
        # Layer 4: Task（当前任务）
        # =====================================================================
        stage_themes = {
            1: "开场：初次见面的氛围营造，角色有些紧张但期待",
            2: "发展：开始熟悉，找到共同话题",
            3: "高潮：发生有趣的事件或小意外",
            4: "深入：更亲密的互动，分享内心",
            5: "结局：约会即将结束，根据好感度给出合适的结局",
        }
        
        # 场景背景只在第一阶段包含，后续阶段延续剧情即可
        if stage_num == 1:
            task_layer = f"""## 当前任务
阶段主题：{stage_themes.get(stage_num, "剧情发展")}
场景背景：{scenario_context}
角色态度：{attitude_mode}"""
        else:
            task_layer = f"""## 当前任务
阶段主题：{stage_themes.get(stage_num, "剧情发展")}
角色态度：{attitude_mode}

【重要】请直接延续上一幕剧情，从用户的选择开始展开，不要重复描述场景背景。"""

        if is_final:
            task_layer += """

【最终阶段特殊指令】
根据当前好感度决定结局走向：
- affection >= 60：完美结局（温馨浪漫，依依不舍）
- affection >= 30：良好结局（愉快告别，期待下次）
- affection >= 0：普通结局（平淡告别）
- affection < 0：糟糕结局（尴尬，想快点离开）"""

        # =====================================================================
        # Output Format（输出格式）
        # =====================================================================
        if is_final:
            # 最终阶段：只需要结局描述，不需要选项
            output_format = """## 输出格式（最终阶段，必须严格遵守）
```json
{
  "narrative": "200-400字的结局描述，用第二人称'你'，包含角色的动作、表情、对话，描写约会结束的场景",
  "character_expression": "happy/shy/surprised/sad/neutral/excited/angry",
  "affection_change": 0
}
```

【重要】这是最后一幕，不需要返回 options，只需要描写结局。根据好感度写出合适的告别场景。

直接输出 JSON，不要其他内容。"""
        else:
            output_format = """## 输出格式（必须严格遵守）
```json
{
  "narrative": "150-300字的剧情描述，用第二人称'你'，包含角色的动作、表情、对话",
  "character_expression": "happy/shy/surprised/sad/neutral/excited/angry",
  "affection_change": 0,
  "options": [
    { "text": "讨好角色的选项", "type": "good", "affection": 10 },
    { "text": "普通平淡的选项", "type": "neutral", "affection": 2 },
    { "text": "可能惹恼角色的选项", "type": "bad", "affection": -8 }
  ]
}
```

可选：当好感度 >= 50 且情境合适时，可添加特殊选项：
{ "text": "【特殊】浪漫/大胆的选项", "type": "special", "affection": 20, "requires_affection": 50, "requirement": "需要好感度 50+" }

直接输出 JSON，不要其他内容。"""

        # =====================================================================
        # 组装完整 Prompt
        # =====================================================================
        return f"""{persona_layer}

{rules_layer}

{state_snapshot}

{task_layer}

{output_format}"""
    
    def _get_attitude_mode(self, affection: int) -> str:
        """根据好感度返回角色态度模式"""
        if affection >= 70:
            return "热恋模式 - 非常亲密，会主动撒娇、脸红、说甜蜜的话"
        elif affection >= 50:
            return "暧昧模式 - 有明显好感，会害羞、开玩笑、偶尔调情"
        elif affection >= 30:
            return "好感模式 - 态度友好，愿意亲近，偶尔微笑"
        elif affection >= 10:
            return "中立模式 - 态度一般，礼貌但保持距离"
        elif affection >= 0:
            return "冷淡模式 - 有些敷衍，回应简短"
        else:
            return "厌烦模式 - 明显不耐烦，想快点结束"
    
    def _parse_stage_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 LLM 响应"""
        try:
            # 尝试提取 JSON
            response = response.strip()
            
            # 移除 markdown 代码块
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()
            
            data = json.loads(response)
            
            # 验证必要字段
            if "narrative" not in data or "options" not in data:
                logger.warning(f"Missing required fields in response: {data.keys()}")
                return None
            
            if len(data["options"]) < 2:
                logger.warning(f"Not enough options: {len(data['options'])}")
                return None
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}, response: {response[:200]}")
            return None
    
    def _create_fallback_stage(self, stage_num: int, is_final: bool) -> DateStage:
        """创建备用阶段（当 LLM 失败时）"""
        if is_final:
            narrative = "时间过得很快，约会接近尾声了。她看着你，似乎在等待你说些什么..."
            options = [
                DateOption(0, "「今天很开心，下次再约吧」", "good", 15),
                DateOption(1, "「时间不早了，我送你回去」", "neutral", 5),
                DateOption(2, "「嗯，那就这样吧」", "bad", -5),
            ]
        else:
            narrative = "气氛正好，她微笑着看着你，等待你的回应..."
            options = [
                DateOption(0, "「你笑起来真好看」", "good", 10),
                DateOption(1, "「这里环境不错」", "neutral", 0),
                DateOption(2, "（低头看手机）", "bad", -10),
            ]
        
        return DateStage(
            stage_num=stage_num,
            narrative=narrative,
            character_expression="neutral",
            options=options,
        )
    
    async def _complete_date(self, session: DateSession) -> Dict[str, Any]:
        """
        完成约会，计算结局和奖励
        """
        from app.services.intimacy_service import intimacy_service
        from app.services.emotion_engine_v2 import emotion_engine
        from app.services.event_story_generator import event_story_generator, EventType
        
        # 确定结局类型
        ending_type = self._determine_ending(session.affection_score)
        rewards = ENDING_REWARDS.get(ending_type, ENDING_REWARDS["normal"])
        
        # 更新会话
        session.status = DateStatus.COMPLETED.value
        session.ending_type = ending_type
        session.xp_awarded = rewards["xp"]
        session.completed_at = datetime.utcnow().isoformat()
        
        # 设置冷却
        cooldown_until = datetime.utcnow() + timedelta(hours=COOLDOWN_HOURS)
        session.cooldown_until = cooldown_until.isoformat()
        cooldown_key = f"{session.user_id}:{session.character_id}"
        _user_cooldowns[cooldown_key] = cooldown_until.isoformat()
        
        # 生成回忆摘要
        story_summary = await self._generate_story_summary(session)
        session.story_summary = story_summary
        
        # 保存会话状态到数据库
        await _save_session_to_db(session)
        await _save_cooldown_to_db(session.user_id, session.character_id, cooldown_until)
        
        # 保存到回忆录
        try:
            await event_story_generator.save_story_direct(
                user_id=session.user_id,
                character_id=session.character_id,
                event_type=EventType.FIRST_DATE,
                story_content=story_summary,
                context_summary=f"场景：{session.scenario_name}，结局：{ending_type}",
            )
        except Exception as e:
            logger.warning(f"Failed to save date story to memories: {e}")
        
        # 记录到历史事件列表（显示在"事件"tab里）
        try:
            from app.services.stats_service import StatsService
            from app.core.database import get_db
            
            async with get_db() as db:
                await StatsService.record_event(
                    db=db,
                    user_id=session.user_id,
                    character_id=session.character_id,
                    event_type="date",
                    title=f"{self._get_ending_title(ending_type)}",
                    description=f"在{session.scenario_name}约会",
                    metadata={"scenario": session.scenario_name, "ending": ending_type},
                )
            logger.info(f"📅 [DATE] Event recorded: {ending_type} at {session.scenario_name}")
        except Exception as e:
            logger.warning(f"Failed to record date event: {e}")
        
        # 给予 XP 奖励（使用 award_xp_direct 直接加数值）
        xp_awarded = rewards["xp"]
        try:
            xp_result = await intimacy_service.award_xp_direct(
                session.user_id, 
                session.character_id, 
                xp_awarded,
                reason=f"date_{ending_type}",
            )
            logger.info(f"📅 [DATE] XP awarded: +{xp_awarded}, total={xp_result.get('new_total_xp')}, level={xp_result.get('new_level')}")
        except Exception as e:
            logger.warning(f"Failed to award XP: {e}")
        
        # 更新情绪 - 约会对角色情绪有显著影响
        emotion_change = rewards["emotion"]
        try:
            new_emotion_score = await emotion_engine.update_score(
                session.user_id,
                session.character_id,
                emotion_change,
                reason=f"date_{ending_type}",
            )
            logger.info(f"📅 [DATE] Emotion updated: {emotion_change:+d}, new score: {new_emotion_score}")
        except Exception as e:
            logger.warning(f"Failed to update emotion: {e}")
            new_emotion_score = 0
        
        # 触发 first_date 事件
        from app.services.date_service import date_service
        await date_service._trigger_first_date_event(session.user_id, session.character_id)
        
        # 保存约会摘要到聊天记忆，让 AI 记住约会内容并影响后续对话
        try:
            from app.services.chat_service import chat_service
            from app.services.character_config import get_character_config
            
            # 获取角色名
            character = get_character_config(session.character_id)
            character_name = character.name if character else "角色"
            
            # 获取情绪状态描述
            emotion_state = emotion_engine.score_to_state(new_emotion_score)
            emotion_desc = self._get_emotion_description(emotion_state.value, emotion_change)
            
            # 构建约会事件记忆 - 格式清晰，AI 容易理解
            date_event = f"""【约会事件】和{character_name}在{session.scenario_name}约会
结局：{self._get_ending_title(ending_type)}
情绪变化：{emotion_change:+d}
当前状态：{emotion_desc}
事件摘要：{story_summary[:200]}..."""

            # 保存为系统消息到聊天历史
            await chat_service.add_system_memory(
                user_id=session.user_id,
                character_id=session.character_id,
                memory_content=date_event,
                memory_type="date",
            )
            logger.info(f"📅 [DATE] Memory saved: emotion {emotion_change:+d}, state: {emotion_state.value}")
        except Exception as e:
            logger.warning(f"Failed to save date memory to chat: {e}")
        
        logger.info(f"Date completed: session={session.id}, ending={ending_type}, "
                   f"xp={rewards['xp']}, affection_final={session.affection_score}")
        
        # 计算成就
        achievements = []
        if ending_type == "perfect":
            achievements.append({"id": "perfect_date", "name": "完美约会", "icon": "💕"})
        elif ending_type == "bad":
            achievements.append({"id": "bad_date", "name": "尴尬时刻", "icon": "😅"})
        
        # 清理会话
        if session.id in _active_sessions:
            del _active_sessions[session.id]
        
        return {
            "success": True,
            "completed": True,
            "ending": {
                "type": ending_type,
                "title": self._get_ending_title(ending_type),
                "description": self._get_ending_description(ending_type, session.affection_score),
            },
            "rewards": {
                "xp": rewards["xp"],
                "emotion_change": emotion_change,  # 情绪变化 -60 到 +60
            },
            "emotion": {
                "change": emotion_change,
                "new_score": new_emotion_score,
                "state": emotion_engine.score_to_state(new_emotion_score).value,
            },
            "achievements": achievements,
            "story_summary": story_summary,
            "cooldown_hours": COOLDOWN_HOURS,
            "cooldown_until": cooldown_until.isoformat(),
        }
    
    def _determine_ending(self, affection_score: int) -> str:
        """根据好感度确定结局"""
        if affection_score >= ENDING_THRESHOLDS["perfect"]:
            return EndingType.PERFECT.value
        elif affection_score >= ENDING_THRESHOLDS["good"]:
            return EndingType.GOOD.value
        elif affection_score >= ENDING_THRESHOLDS["normal"]:
            return EndingType.NORMAL.value
        else:
            return EndingType.BAD.value
    
    def _get_ending_title(self, ending_type: str) -> str:
        """获取结局标题"""
        titles = {
            "perfect": "💕 完美的约会",
            "good": "😊 愉快的约会",
            "normal": "🙂 普通的约会",
            "bad": "😅 尴尬的约会",
        }
        return titles.get(ending_type, "约会结束")
    
    def _get_ending_description(self, ending_type: str, affection: int) -> str:
        """获取结局描述"""
        descriptions = {
            "perfect": "这是一次完美的约会！她脸上洋溢着幸福的笑容，依依不舍地和你告别...",
            "good": "约会很愉快，她笑着说期待下次见面。",
            "normal": "约会还算顺利，虽然没有特别的火花，但也不算糟糕。",
            "bad": "约会有些尴尬，她似乎想快点结束...",
        }
        return descriptions.get(ending_type, "约会结束了。")
    
    def _get_emotion_description(self, emotion_state: str, emotion_change: int) -> str:
        """获取情绪状态的描述，用于注入到聊天记忆"""
        state_descriptions = {
            "loving": "非常开心，心情甜蜜 💕",
            "happy": "很开心，心情很好 😊",
            "content": "心情愉快 🙂",
            "neutral": "心情平静",
            "annoyed": "有点不高兴 😒",
            "angry": "很生气 😠",
            "cold_war": "非常不满，冷战状态 🥶",
            "blocked": "极度失望 💔",
        }
        desc = state_descriptions.get(emotion_state, "心情一般")
        
        # 添加变化描述
        if emotion_change >= 50:
            return f"{desc}，约会让她超级开心！"
        elif emotion_change >= 20:
            return f"{desc}，约会很愉快"
        elif emotion_change >= 0:
            return f"{desc}"
        elif emotion_change >= -20:
            return f"{desc}，约会有点失望"
        else:
            return f"{desc}，约会很糟糕，她很不开心"
    
    async def _generate_story_summary(self, session: DateSession) -> str:
        """生成约会回忆摘要"""
        # 简单版本：拼接所有阶段的剧情
        summary_parts = [f"📍 场景：{session.scenario_name}\n"]
        
        for stage in session.stages:
            summary_parts.append(stage.narrative)
            if stage.user_choice is not None and stage.options:
                chosen = stage.options[stage.user_choice]
                summary_parts.append(f"\n你的选择：{chosen.text}\n")
        
        # 添加结局
        ending_title = self._get_ending_title(session.ending_type or "normal")
        ending_desc = self._get_ending_description(
            session.ending_type or "normal", 
            session.affection_score
        )
        summary_parts.append(f"\n{ending_title}\n{ending_desc}")
        
        return "\n".join(summary_parts)


# 单例
interactive_date_service = InteractiveDateService()
