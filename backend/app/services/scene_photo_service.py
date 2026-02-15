"""
Scene Photo Service - 场景识别照片生成
======================================

功能：
- 根据对话实时识别场景 (work/gym/intimate)
- 统一成本 10 credits
- 日上限控制 (free: 3, premium: 10, vip: 20)
- 禁止工作场景出现卧室照片

Author: Luna AI
Date: February 2026
"""

import logging
import httpx
from datetime import datetime, date
from typing import Optional, Dict, Any, Literal, List
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

class PhotoScene(str, Enum):
    """照片场景"""
    WORK = "work"           # 工作/职业
    GYM = "gym"             # 健身房
    INTIMATE = "intimate"   # 私密/居家


# 统一成本
PHOTO_COST = 10  # credits

# 日上限配置
DAILY_LIMITS = {
    "free": 3,
    "premium": 10,
    "vip": 20,
}


# 场景prompt模板
SCENE_PROMPT_TEMPLATES = {
    PhotoScene.WORK: {
        "base": "{character_desc}, professional business look",
        "modifiers": [
            "office setting or modern workspace",
            "professional attire",
            "confident expression",
            "clean background",
            "corporate environment",
        ],
        "forbidden": ["bedroom", "bed", "bathroom", "lingerie", "pajamas"],
    },
    PhotoScene.GYM: {
        "base": "{character_desc}, at the gym or fitness center",
        "modifiers": [
            "athletic wear",
            "workout clothes",
            "gym equipment visible",
            "fitness mirror selfie",
            "energetic and healthy look",
        ],
        "forbidden": [],
    },
    PhotoScene.INTIMATE: {
        "base": "{character_desc}, relaxed intimate setting",
        "modifiers": [
            "cozy home environment",
            "comfortable casual wear",
            "warm soft lighting",
            "bedroom or living room",
            "personal and intimate mood",
        ],
        "forbidden": [],
    },
}


# 场景识别system prompt
SCENE_DETECTION_PROMPT = """分析以下对话，判断用户当前想要的照片场景。

场景选项：
- work: 讨论工作、职业、求职、商务相关话题
- gym: 讨论健身、运动、锻炼、身材相关话题  
- intimate: 私密聊天、暧昧、想念、日常闲聊、撒娇

只返回一个词: work, gym, 或 intimate
不要返回其他任何内容。

对话内容:
{conversation}

场景:"""


@dataclass
class PhotoGenerationResult:
    """照片生成结果"""
    success: bool
    image_id: str = ""
    image_url: str = ""
    scene: str = ""
    cost_credits: int = 0
    remaining_daily: int = 0
    error: Optional[str] = None
    error_code: Optional[str] = None  # insufficient_credits, daily_limit_reached


# ============================================================================
# Scene Photo Service
# ============================================================================

class ScenePhotoService:
    """
    场景照片生成服务
    
    功能：
    - 场景识别：根据对话判断 work/gym/intimate
    - 额度检查：检查用户credits是否足够
    - 日上限：追踪每日生成次数
    - 照片生成：调用image service生成对应场景照片
    """
    
    def __init__(self):
        self.cost = PHOTO_COST
        self.daily_limits = DAILY_LIMITS
        logger.info("ScenePhotoService initialized")
    
    async def detect_scene(
        self,
        messages: List[Dict[str, str]],
        db: Optional[AsyncSession] = None,
    ) -> PhotoScene:
        """
        根据对话内容识别场景
        
        Args:
            messages: 最近的对话消息 [{"role": "user/assistant", "content": "..."}]
            db: 数据库session（暂不使用）
        
        Returns:
            PhotoScene枚举值
        """
        # 构建对话文本
        conversation = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in messages[-10:]  # 最近10条
        ])
        
        prompt = SCENE_DETECTION_PROMPT.format(conversation=conversation)
        
        # 调用LLM识别场景
        if settings.MOCK_LLM:
            # Mock模式，简单关键词匹配
            text = conversation.lower()
            if any(kw in text for kw in ["工作", "面试", "老板", "公司", "work", "job", "office"]):
                return PhotoScene.WORK
            elif any(kw in text for kw in ["健身", "运动", "锻炼", "gym", "workout", "exercise"]):
                return PhotoScene.GYM
            else:
                return PhotoScene.INTIMATE
        
        try:
            # 使用配置的LLM
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{settings.OPENAI_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.OPENAI_MODEL,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 10,
                        "temperature": 0,
                    },
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    result = data["choices"][0]["message"]["content"].strip().lower()
                    
                    if result == "work":
                        return PhotoScene.WORK
                    elif result == "gym":
                        return PhotoScene.GYM
                    else:
                        return PhotoScene.INTIMATE
                        
        except Exception as e:
            logger.error(f"Scene detection failed: {e}")
        
        # 默认返回intimate
        return PhotoScene.INTIMATE
    
    async def check_daily_limit(
        self,
        user_id: str,
        tier: str,
        db: AsyncSession,
    ) -> tuple[bool, int]:
        """
        检查用户今日是否还有额度
        
        Args:
            user_id: 用户ID
            tier: 用户等级 (free/premium/vip)
            db: 数据库session
        
        Returns:
            (是否可以生成, 今日剩余次数)
        """
        from app.models.database.image_models import GeneratedImage
        
        # 获取今日已生成数量
        today = date.today()
        start_of_day = datetime.combine(today, datetime.min.time())
        
        query = select(func.count()).select_from(GeneratedImage).where(
            and_(
                GeneratedImage.user_id == user_id,
                GeneratedImage.created_at >= start_of_day,
                GeneratedImage.is_deleted == False,
            )
        )
        
        result = await db.execute(query)
        today_count = result.scalar() or 0
        
        # 获取用户日限额
        limit = self.daily_limits.get(tier, self.daily_limits["free"])
        remaining = max(0, limit - today_count)
        
        return remaining > 0, remaining
    
    async def check_credits(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> tuple[bool, float]:
        """
        检查用户credits是否足够
        
        Args:
            user_id: 用户ID
            db: 数据库session
        
        Returns:
            (是否足够, 当前余额)
        """
        from app.models.database.billing_models import UserWallet
        
        query = select(UserWallet).where(UserWallet.user_id == user_id)
        result = await db.execute(query)
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            return False, 0.0
        
        return wallet.total_credits >= self.cost, wallet.total_credits
    
    async def deduct_credits(
        self,
        user_id: str,
        amount: float,
        description: str,
        db: AsyncSession,
    ) -> bool:
        """
        扣除用户credits
        
        Args:
            user_id: 用户ID
            amount: 扣除金额
            description: 交易描述
            db: 数据库session
        
        Returns:
            是否成功
        """
        from app.models.database.billing_models import UserWallet, TransactionHistory, TransactionType
        
        try:
            query = select(UserWallet).where(UserWallet.user_id == user_id)
            result = await db.execute(query)
            wallet = result.scalar_one_or_none()
            
            if not wallet or wallet.total_credits < amount:
                return False
            
            # 优先扣free credits
            if wallet.free_credits >= amount:
                wallet.free_credits -= amount
            else:
                # 先扣完free，再扣purchased
                remaining = amount - wallet.free_credits
                wallet.free_credits = 0
                wallet.purchased_credits -= remaining
            
            wallet.total_credits = wallet.free_credits + wallet.purchased_credits
            wallet.updated_at = datetime.utcnow()
            
            # 记录交易
            transaction = TransactionHistory(
                user_id=user_id,
                transaction_type=TransactionType.DEDUCTION,
                amount=-amount,
                balance_after=wallet.total_credits,
                description=description,
            )
            db.add(transaction)
            
            await db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to deduct credits: {e}")
            await db.rollback()
            return False
    
    async def generate_scene_photo(
        self,
        user_id: str,
        character_id: str,
        messages: List[Dict[str, str]],
        tier: str,
        db: AsyncSession,
        scene_override: Optional[PhotoScene] = None,
    ) -> PhotoGenerationResult:
        """
        生成场景照片（完整流程）
        
        流程：
        1. 检查日上限
        2. 检查credits
        3. 识别场景（或使用指定场景）
        4. 生成照片
        5. 扣费
        
        Args:
            user_id: 用户ID
            character_id: 角色ID
            messages: 最近对话
            tier: 用户等级
            db: 数据库session
            scene_override: 强制指定场景（可选）
        
        Returns:
            PhotoGenerationResult
        """
        # 1. 检查日上限
        can_generate, remaining = await self.check_daily_limit(user_id, tier, db)
        if not can_generate:
            return PhotoGenerationResult(
                success=False,
                error="今日照片额度已用完，明天再来吧~",
                error_code="daily_limit_reached",
                remaining_daily=0,
            )
        
        # 2. 检查credits
        has_credits, balance = await self.check_credits(user_id, db)
        if not has_credits:
            return PhotoGenerationResult(
                success=False,
                error=f"额度不足哦，还需要{self.cost}积分才能解锁照片~",
                error_code="insufficient_credits",
                remaining_daily=remaining,
            )
        
        # 3. 识别场景
        scene = scene_override or await self.detect_scene(messages, db)
        
        # 4. 生成照片
        from app.services.image_service import get_image_service, ImageStyle, GenerationType
        
        image_service = get_image_service()
        
        # 根据场景选择对应的style
        style_map = {
            PhotoScene.WORK: ImageStyle.PORTRAIT,
            PhotoScene.GYM: ImageStyle.CASUAL,
            PhotoScene.INTIMATE: ImageStyle.ROMANTIC,
        }
        style = style_map.get(scene, ImageStyle.CASUAL)
        
        # 构建场景特定的prompt
        scene_template = SCENE_PROMPT_TEMPLATES[scene]
        scene_prompt = ", ".join(scene_template["modifiers"])
        
        # 添加forbidden检查（工作场景禁止卧室）
        if scene == PhotoScene.WORK:
            scene_prompt += ", NOT in bedroom, NOT in bed, professional environment only"
        
        result = await image_service.generate_image(
            prompt=scene_prompt,
            style=style,
            character_id=character_id,
            user_id=user_id,
            generation_type=GenerationType.USER_REQUEST,
            db=db,
            context={"scene": scene.value},
        )
        
        if not result.success:
            return PhotoGenerationResult(
                success=False,
                error=result.error or "照片生成失败，请稍后重试",
                remaining_daily=remaining,
            )
        
        # 5. 扣费
        deducted = await self.deduct_credits(
            user_id=user_id,
            amount=self.cost,
            description=f"场景照片生成 ({scene.value})",
            db=db,
        )
        
        if not deducted:
            # 扣费失败，但图片已生成...记录日志
            logger.error(f"Failed to deduct credits for user {user_id}, but image was generated")
        
        return PhotoGenerationResult(
            success=True,
            image_id=result.image_id,
            image_url=result.image_url,
            scene=scene.value,
            cost_credits=self.cost,
            remaining_daily=remaining - 1,
        )


# Singleton
_scene_photo_service: Optional[ScenePhotoService] = None


def get_scene_photo_service() -> ScenePhotoService:
    """获取或创建service单例"""
    global _scene_photo_service
    if _scene_photo_service is None:
        _scene_photo_service = ScenePhotoService()
    return _scene_photo_service
