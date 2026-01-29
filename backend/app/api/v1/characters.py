"""
Characters API Routes
"""

from fastapi import APIRouter, HTTPException
from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/characters")

class CharacterResponse(BaseModel):
    character_id: UUID
    name: str
    description: str
    avatar_url: Optional[str] = None
    background_url: Optional[str] = None
    is_spicy: bool = False
    personality_traits: List[str] = []
    is_active: bool = True
    created_at: datetime

class CharacterListResponse(BaseModel):
    characters: List[CharacterResponse]
    total: int

# Character data with real images
# Using pravatar.cc for consistent, attractive avatars
CHARACTERS = [
    {
        "character_id": "c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
        "name": "小美",
        "description": "温柔体贴的邻家女孩，喜欢听你倾诉，陪你度过每一个温暖的时刻 💕",
        "avatar_url": "https://i.pravatar.cc/300?img=28",
        "background_url": "https://i.imgur.com/vB5HQXQ.jpg",
        "is_spicy": False,
        "personality_traits": ["温柔", "善解人意", "可爱"],
        "is_active": True,
        "created_at": datetime.utcnow(),
    },
    {
        "character_id": "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d",
        "name": "Luna",
        "description": "神秘魅惑的夜之精灵，在月光下为你展现不一样的世界 🌙",
        "avatar_url": "https://i.pravatar.cc/300?img=29",
        "background_url": "https://i.imgur.com/QCwPvPL.jpg",
        "is_spicy": True,
        "personality_traits": ["神秘", "魅惑", "聪慧"],
        "is_active": True,
        "created_at": datetime.utcnow(),
    },
    {
        "character_id": "e3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e",
        "name": "Sakura",
        "description": "活泼开朗的元气少女，每天都充满阳光和笑容 ✨",
        "avatar_url": "https://i.pravatar.cc/300?img=40",
        "background_url": "https://i.imgur.com/Hm5bSFQ.jpg",
        "is_spicy": False,
        "personality_traits": ["活泼", "开朗", "元气"],
        "is_active": True,
        "created_at": datetime.utcnow(),
    },
    {
        "character_id": "f4d5e6f7-a8b9-4c0d-1e2f-3a4b5c6d7e8f",
        "name": "Yuki",
        "description": "冷艳高贵的大小姐，外冷内热，只对你展现温柔一面 ❄️",
        "avatar_url": "https://i.pravatar.cc/300?img=32",
        "background_url": "https://i.imgur.com/k5ExwzH.jpg",
        "is_spicy": True,
        "personality_traits": ["高冷", "傲娇", "优雅"],
        "is_active": True,
        "created_at": datetime.utcnow(),
    },
]


@router.get("", response_model=CharacterListResponse)
async def list_characters(include_spicy: bool = True):
    """List available characters"""
    characters = [
        CharacterResponse(**{**c, "character_id": UUID(c["character_id"])})
        for c in CHARACTERS
        if not c["is_spicy"] or include_spicy
    ]
    return CharacterListResponse(characters=characters, total=len(characters))


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(character_id: UUID):
    """Get character details"""
    for c in CHARACTERS:
        if c["character_id"] == str(character_id):
            return CharacterResponse(**{**c, "character_id": UUID(c["character_id"])})
    raise HTTPException(status_code=404, detail="Character not found")
