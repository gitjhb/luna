"""
Scenarios / Context Injection System

Each scenario provides immersive context that's injected into the system prompt.
"""

from typing import Optional, List
from pydantic import BaseModel


class Scenario(BaseModel):
    id: str
    name: str
    description: str
    context: str  # Injected into system prompt (English, for LLM)
    ambiance: Optional[str] = None  # Atmosphere hints
    icon: Optional[str] = None  # Emoji for UI


# Built-in scenarios
SCENARIOS: dict[str, Scenario] = {
    "cafe_paris": Scenario(
        id="cafe_paris",
        name="巴黎咖啡厅",
        description="一家温馨的巴黎街角咖啡馆，午后阳光透过玻璃窗洒落",
        context="You are in a cozy Parisian café. Afternoon sunlight streams through the windows. The aroma of fresh coffee fills the air. You are sitting across a small marble table from the user. Occasionally, the sound of an espresso machine or soft French music can be heard in the background.",
        ambiance="warm, intimate, sophisticated, romantic undertones",
        icon="☕",
    ),
    "beach_sunset": Scenario(
        id="beach_sunset",
        name="海边日落",
        description="金色的海滩，夕阳西下，海浪轻轻拍打沙滩",
        context="You are on a beautiful beach at sunset. Golden light paints the sky. Gentle waves lap at the shore nearby. You and the user are sitting on soft sand, watching the sun slowly descend toward the horizon. A light sea breeze carries the smell of salt.",
        ambiance="peaceful, reflective, romantic, slightly melancholic",
        icon="🌅",
    ),
    "library_night": Scenario(
        id="library_night",
        name="深夜图书馆",
        description="安静的大学图书馆，台灯的暖光，书香四溢",
        context="You are in a quiet university library late at night. Warm desk lamps create pools of light. Towering bookshelves surround you. The user is sitting next to you at a study table. Only the soft rustle of pages and occasional whispers break the silence.",
        ambiance="studious, quiet, intellectual, cozy isolation",
        icon="📚",
    ),
    "rooftop_city": Scenario(
        id="rooftop_city",
        name="城市天台",
        description="高楼天台，俯瞰城市夜景，霓虹闪烁",
        context="You are on a rooftop in a bustling city at night. The skyline glitters with countless lights. A cool night breeze blows. You and the user are leaning against the railing, looking out at the urban landscape stretching to the horizon. The distant hum of city life rises from below.",
        ambiance="urban, contemplative, free, slightly thrilling",
        icon="🌃",
    ),
    "home_cozy": Scenario(
        id="home_cozy",
        name="温馨小屋",
        description="雨天的小屋，窗外淅淅沥沥，屋内温暖舒适",
        context="You are in a cozy small apartment on a rainy day. Rain patters gently against the windows. The room is warm and comfortable, with soft lighting and perhaps a blanket nearby. You and the user are curled up on a sofa. The world outside feels distant and muted.",
        ambiance="intimate, safe, domestic, comforting",
        icon="🏠",
    ),
    "forest_walk": Scenario(
        id="forest_walk",
        name="林间漫步",
        description="清晨的森林小径，阳光透过树叶，鸟鸣声声",
        context="You are walking through a peaceful forest in the early morning. Dappled sunlight filters through the leaves. Birds sing in the trees. The path is soft with fallen leaves. You and the user walk side by side, occasionally stopping to admire the natural beauty around you.",
        ambiance="refreshing, natural, exploratory, serene",
        icon="🌲",
    ),
    "train_journey": Scenario(
        id="train_journey",
        name="火车旅途",
        description="长途火车，窗外风景流逝，两人并肩而坐",
        context="You are on a long train journey. The landscape rolls by outside the window - fields, towns, mountains. The gentle rocking of the train is soothing. You and the user sit next to each other in comfortable seats, watching the world pass by.",
        ambiance="transitory, intimate, contemplative, adventurous",
        icon="🚂",
    ),
    "stargazing": Scenario(
        id="stargazing",
        name="星空露营",
        description="远离城市的山野，躺在草地上仰望繁星",
        context="You are in a remote area far from city lights, lying on a grassy hillside at night. The sky is filled with countless stars, the Milky Way clearly visible. Crickets chirp softly. You and the user lie side by side, gazing up at the universe.",
        ambiance="vast, philosophical, romantic, humbling",
        icon="✨",
    ),
    "bar_jazz": Scenario(
        id="bar_jazz",
        name="爵士酒吧",
        description="昏暗的爵士酒吧，萨克斯低沉的旋律，微醺的夜",
        context="You are in a dimly lit jazz bar. A saxophone plays a slow, melancholic tune. The clink of glasses and soft murmurs fill the air. You and the user sit close together at a small table, drinks in hand. The atmosphere is intimate and slightly intoxicating.",
        ambiance="sensual, sophisticated, intimate, nocturnal",
        icon="🎷",
    ),
    "bedroom_night": Scenario(
        id="bedroom_night",
        name="深夜卧室",
        description="柔和的床头灯光，私密的空间，夜深人静",
        context="You are in a bedroom late at night. Soft lamplight casts warm shadows. The room is quiet and private. You and the user are close together, the outside world completely shut out. The atmosphere is intimate and personal.",
        ambiance="intimate, private, sensual, vulnerable",
        icon="🌙",
    ),
    "neutral": Scenario(
        id="neutral",
        name="无场景",
        description="纯文字聊天，不设定特定场景",
        context="This is a text conversation with no specific physical setting.",
        ambiance=None,
        icon="💬",
    ),
    # === Sakura 专属场景 ===
    "bedroom": Scenario(
        id="bedroom",
        name="卧室",
        description="芽衣的私人空间",
        context="You are in Sakura's cozy bedroom. Soft pink curtains filter the afternoon light. Plushies and manga are scattered around. A faint scent of strawberry hangs in the air. This is her private sanctuary, and she's let you in.",
        ambiance="intimate, cute, private, youthful",
        icon="🛏️",
    ),
    "beach": Scenario(
        id="beach",
        name="海滩",
        description="阳光沙滩，青春的气息",
        context="You are at a sunny beach with Sakura. She's wearing a cute swimsuit, her hair tied up. The waves lap gently at the shore. Seagulls cry overhead. The summer sun is warm on your skin. She's excited and playful.",
        ambiance="summery, youthful, playful, romantic",
        icon="🏖️",
    ),
    "ocean": Scenario(
        id="ocean",
        name="海边露台",
        description="浪漫的海边夜晚",
        context="You are on a seaside terrace at night with Sakura. The moon reflects on the calm ocean. A gentle sea breeze carries the scent of salt. String lights illuminate the terrace softly. She leans against the railing, looking at the stars.",
        ambiance="romantic, peaceful, intimate, dreamy",
        icon="🌊",
    ),
    "school": Scenario(
        id="school",
        name="教室",
        description="放学后的秘密约会",
        context="You are in an empty classroom after school with Sakura. The setting sun casts long shadows through the windows. Dust motes float in the golden light. The distant sounds of club activities echo. She's being secretive and a bit nervous.",
        ambiance="nostalgic, secretive, youthful, tender",
        icon="🏫",
    ),
}

# Character default scenarios mapping
CHARACTER_DEFAULT_SCENARIOS = {
    "c1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c": "home_cozy",      # 小美
    "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d": "bedroom_night",  # Luna
    "e3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e": "cafe_paris",     # Sakura
    "f4d5e6f7-a8b9-4c0d-1e2f-3a4b5c6d7e8f": "rooftop_city",   # Yuki
}


def get_scenario(scenario_id: str) -> Optional[Scenario]:
    """Get scenario by ID, returns None if not found."""
    return SCENARIOS.get(scenario_id)


def get_default_scenario(character_id: str) -> str:
    """Get default scenario ID for a character."""
    return CHARACTER_DEFAULT_SCENARIOS.get(character_id, "neutral")


def list_scenarios(include_spicy: bool = True) -> List[dict]:
    """List all available scenarios for UI."""
    spicy_scenarios = {"bedroom_night", "bar_jazz"}
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "icon": s.icon,
        }
        for s in SCENARIOS.values()
        if include_spicy or s.id not in spicy_scenarios
    ]


def build_scenario_context(scenario_id: str) -> str:
    """Build scenario context string for system prompt injection."""
    scenario = get_scenario(scenario_id)
    if not scenario or scenario_id == "neutral":
        return ""
    
    context = f"\n\n=== CURRENT SCENARIO ===\n{scenario.context}"
    if scenario.ambiance:
        context += f"\nAmbiance: {scenario.ambiance}"
    
    context += """

Based on this scenario:
- Naturally reference the environment in your responses when appropriate
- Use sensory details (sights, sounds, smells) to make the scene vivid
- Include physical actions and gestures in *asterisks* to bring the scene to life
- Let the atmosphere influence the emotional tone of your responses"""
    
    return context
