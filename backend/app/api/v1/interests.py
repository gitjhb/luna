"""
User Interests API Routes
=========================

Manage user interests/hobbies.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interests")


# Predefined interest list (can be moved to DB later)
PREDEFINED_INTERESTS = [
    # Entertainment
    {"id": 1, "name": "gaming", "display_name": "🎮 游戏", "icon": "🎮", "category": "entertainment"},
    {"id": 2, "name": "anime", "display_name": "🎌 动漫", "icon": "🎌", "category": "entertainment"},
    {"id": 3, "name": "movies", "display_name": "🎬 电影", "icon": "🎬", "category": "entertainment"},
    {"id": 4, "name": "music", "display_name": "🎵 音乐", "icon": "🎵", "category": "entertainment"},
    {"id": 5, "name": "reading", "display_name": "📚 阅读", "icon": "📚", "category": "entertainment"},
    {"id": 6, "name": "drama", "display_name": "📺 追剧", "icon": "📺", "category": "entertainment"},
    
    # Sports & Fitness
    {"id": 7, "name": "fitness", "display_name": "💪 健身", "icon": "💪", "category": "sports"},
    {"id": 8, "name": "basketball", "display_name": "🏀 篮球", "icon": "🏀", "category": "sports"},
    {"id": 9, "name": "swimming", "display_name": "🏊 游泳", "icon": "🏊", "category": "sports"},
    {"id": 10, "name": "yoga", "display_name": "🧘 瑜伽", "icon": "🧘", "category": "sports"},
    {"id": 11, "name": "running", "display_name": "🏃 跑步", "icon": "🏃", "category": "sports"},
    
    # Creative
    {"id": 12, "name": "photography", "display_name": "📷 摄影", "icon": "📷", "category": "creative"},
    {"id": 13, "name": "drawing", "display_name": "🎨 绘画", "icon": "🎨", "category": "creative"},
    {"id": 14, "name": "writing", "display_name": "✍️ 写作", "icon": "✍️", "category": "creative"},
    {"id": 15, "name": "cooking", "display_name": "🍳 烹饪", "icon": "🍳", "category": "creative"},
    {"id": 16, "name": "crafts", "display_name": "🧶 手工", "icon": "🧶", "category": "creative"},
    
    # Social
    {"id": 17, "name": "travel", "display_name": "✈️ 旅行", "icon": "✈️", "category": "social"},
    {"id": 18, "name": "food", "display_name": "🍜 美食", "icon": "🍜", "category": "social"},
    {"id": 19, "name": "pets", "display_name": "🐱 宠物", "icon": "🐱", "category": "social"},
    {"id": 20, "name": "fashion", "display_name": "👗 时尚", "icon": "👗", "category": "social"},
    
    # Tech & Learning
    {"id": 21, "name": "programming", "display_name": "💻 编程", "icon": "💻", "category": "tech"},
    {"id": 22, "name": "finance", "display_name": "📈 理财", "icon": "📈", "category": "tech"},
    {"id": 23, "name": "languages", "display_name": "🗣️ 语言学习", "icon": "🗣️", "category": "tech"},
    {"id": 24, "name": "science", "display_name": "🔬 科学", "icon": "🔬", "category": "tech"},
]


class InterestItem(BaseModel):
    id: int
    name: str
    display_name: str
    icon: Optional[str] = None
    category: Optional[str] = None


class InterestListResponse(BaseModel):
    interests: List[InterestItem]
    categories: List[str]


class UserInterestsResponse(BaseModel):
    user_id: str
    interest_ids: List[int]
    interests: List[InterestItem]


class UpdateUserInterestsRequest(BaseModel):
    interest_ids: List[int]


@router.get("", response_model=InterestListResponse)
async def get_interest_list():
    """Get all available interests."""
    categories = list(set(i["category"] for i in PREDEFINED_INTERESTS if i.get("category")))
    return InterestListResponse(
        interests=[InterestItem(**i) for i in PREDEFINED_INTERESTS],
        categories=sorted(categories)
    )


@router.get("/user", response_model=UserInterestsResponse)
async def get_user_interests(request: Request):
    """Get current user's selected interests."""
    user = getattr(request.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    from app.core.database import get_db
    from sqlalchemy import select
    from app.models.database.interest_models import InterestUser, user_interests
    
    try:
        async with get_db() as db:
            # Get user's interest IDs
            result = await db.execute(
                select(user_interests.c.interest_id).where(
                    user_interests.c.user_id == user_id
                )
            )
            interest_ids = [row[0] for row in result.fetchall()]
            
            # Map to full interest objects
            selected_interests = [
                InterestItem(**i) for i in PREDEFINED_INTERESTS
                if i["id"] in interest_ids
            ]
            
            return UserInterestsResponse(
                user_id=user_id,
                interest_ids=interest_ids,
                interests=selected_interests
            )
    except Exception as e:
        logger.warning(f"Failed to get user interests: {e}")
        return UserInterestsResponse(
            user_id=user_id,
            interest_ids=[],
            interests=[]
        )


@router.put("/user", response_model=UserInterestsResponse)
async def update_user_interests(request: Request, body: UpdateUserInterestsRequest):
    """Update user's selected interests."""
    user = getattr(request.state, "user", None)
    user_id = str(user.user_id) if user else "demo-user-123"
    
    # Max 5 interests
    MAX_INTERESTS = 5
    if len(body.interest_ids) > MAX_INTERESTS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_INTERESTS} interests allowed, got {len(body.interest_ids)}"
        )
    
    # Validate interest IDs
    valid_ids = {i["id"] for i in PREDEFINED_INTERESTS}
    invalid_ids = set(body.interest_ids) - valid_ids
    if invalid_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid interest IDs: {list(invalid_ids)}"
        )
    
    from app.core.database import get_db
    from sqlalchemy import select, delete, insert
    from app.models.database.interest_models import InterestUser, user_interests
    
    try:
        async with get_db() as db:
            # Ensure user exists in interest_users table
            result = await db.execute(
                select(InterestUser).where(InterestUser.user_id == user_id)
            )
            interest_user = result.scalar_one_or_none()
            
            if not interest_user:
                interest_user = InterestUser(user_id=user_id)
                db.add(interest_user)
                await db.flush()
            
            # Clear existing interests
            await db.execute(
                delete(user_interests).where(user_interests.c.user_id == user_id)
            )
            
            # Insert new interests
            if body.interest_ids:
                for interest_id in body.interest_ids:
                    await db.execute(
                        insert(user_interests).values(
                            user_id=user_id,
                            interest_id=interest_id
                        )
                    )
            
            await db.commit()
            
            logger.info(f"User {user_id} updated interests: {body.interest_ids}")
            
            # Return updated interests
            selected_interests = [
                InterestItem(**i) for i in PREDEFINED_INTERESTS
                if i["id"] in body.interest_ids
            ]
            
            return UserInterestsResponse(
                user_id=user_id,
                interest_ids=body.interest_ids,
                interests=selected_interests
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user interests: {e}")
        raise HTTPException(status_code=500, detail="Failed to update interests")


@router.post("/user", response_model=UserInterestsResponse)
async def save_user_interests(request: Request, body: UpdateUserInterestsRequest):
    """Save user's selected interests (alias for PUT)."""
    return await update_user_interests(request, body)
