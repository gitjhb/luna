"""
Characters API Routes
"""

from fastapi import APIRouter, HTTPException
from uuid import UUID, uuid4
from datetime import datetime

from app.models.schemas import CharacterResponse, CharacterListResponse

router = APIRouter(prefix="/characters")

# Mock character data
MOCK_CHARACTERS = [
    {
        "character_id": uuid4(),
        "name": "小美",
        "description": "温柔体贴的邻家女孩，喜欢听你倾诉",
        "avatar_url": None,
        "is_spicy": False,
        "personality_traits": ["温柔", "善解人意", "可爱"],
        "is_active": True,
        "created_at": datetime.utcnow(),
    },
    {
        "character_id": uuid4(),
        "name": "Alex",
        "description": "幽默风趣的朋友，总能让你开心",
        "avatar_url": None,
        "is_spicy": False,
        "personality_traits": ["幽默", "阳光", "乐观"],
        "is_active": True,
        "created_at": datetime.utcnow(),
    },
    {
        "character_id": uuid4(),
        "name": "Luna",
        "description": "神秘魅惑的夜之精灵 (Premium)",
        "avatar_url": None,
        "is_spicy": True,
        "personality_traits": ["神秘", "魅惑", "聪慧"],
        "is_active": True,
        "created_at": datetime.utcnow(),
    },
]


@router.get("", response_model=CharacterListResponse)
async def list_characters(include_spicy: bool = False):
    """List available characters"""
    characters = [
        CharacterResponse(**c)
        for c in MOCK_CHARACTERS
        if not c["is_spicy"] or include_spicy
    ]
    return CharacterListResponse(characters=characters, total=len(characters))


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(character_id: UUID):
    """Get character details"""
    for c in MOCK_CHARACTERS:
        if str(c["character_id"]) == str(character_id):
            return CharacterResponse(**c)
    raise HTTPException(status_code=404, detail="Character not found")
