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
    # === 新增场景 - 浪漫类 ===
    "candlelight_dinner": Scenario(
        id="candlelight_dinner",
        name="烛光晚餐",
        description="高级餐厅的浪漫晚餐，烛光摇曳，气氛温馨",
        context="You are in an elegant restaurant for a romantic dinner. Soft candlelight flickers on the white tablecloth. The ambient music is gentle and romantic. You and the user sit across from each other at a small intimate table. The sommelier has just poured wine into crystal glasses.",
        ambiance="romantic, elegant, intimate, sophisticated",
        icon="🕯️",
    ),
    "riverside_walk": Scenario(
        id="riverside_walk",
        name="河边漫步",
        description="月光下的河边小径，柳絮飞舞，倒影摇曳",
        context="You are walking along a peaceful riverside path at night. Moonlight reflects on the water's surface. Willow trees sway gently in the breeze. The city lights twinkle in the distance. You and the user walk hand in hand on the cobblestone path.",
        ambiance="serene, romantic, peaceful, dreamy",
        icon="🌙",
    ),
    "mountain_sunrise": Scenario(
        id="mountain_sunrise",
        name="山顶日出",
        description="清晨登山看日出，云海翻腾，金光万丈",
        context="You are on a mountain peak at dawn, watching the sunrise. The sky gradually changes from deep purple to golden orange. Clouds drift below you like a sea. The air is crisp and fresh. You and the user stand close together, sharing this breathtaking moment.",
        ambiance="majestic, inspiring, fresh, romantic",
        icon="🏔️",
    ),
    "flower_garden": Scenario(
        id="flower_garden",
        name="花园约会",
        description="春日花园，樱花飞舞，蝴蝶翩翩",
        context="You are in a beautiful botanical garden in full spring bloom. Cherry blossoms fall like snow, creating a pink carpet on the path. Butterflies flutter among colorful flowers. The air is filled with sweet floral fragrances. You and the user walk through this enchanting garden paradise.",
        ambiance="fresh, colorful, romantic, dreamy",
        icon="🌸",
    ),
    # === 活动类 ===
    "amusement_park": Scenario(
        id="amusement_park",
        name="游乐园",
        description="热闹的游乐园，过山车、摩天轮，欢声笑语",
        context="You are at a bustling amusement park. The sounds of laughter, carnival music, and rides fill the air. Colorful lights twinkle everywhere. Cotton candy and popcorn scents drift by. You and the user are excited to try different rides together, from thrilling roller coasters to the romantic Ferris wheel.",
        ambiance="exciting, joyful, playful, energetic",
        icon="🎡",
    ),
    "escape_room": Scenario(
        id="escape_room",
        name="密室逃脱",
        description="神秘的密室，需要合作解谜，紧张刺激",
        context="You are locked in a mysterious escape room with intricate puzzles. Dim lighting creates dramatic shadows. Mysterious clues are scattered around the room. You and the user must work together to solve riddles and find the key to escape. The atmosphere is thrilling and requires teamwork.",
        ambiance="mysterious, thrilling, cooperative, focused",
        icon="🔍",
    ),
    "cooking_class": Scenario(
        id="cooking_class",
        name="料理课堂",
        description="一起学做菜，分工合作，温馨的厨房时光",
        context="You are in a cozy cooking class kitchen. Fresh ingredients are laid out on wooden counters. The instructor has just explained the recipe. You and the user wear matching aprons, ready to cook together. The kitchen smells of herbs and spices, creating a warm, homely atmosphere.",
        ambiance="cozy, collaborative, domestic, fun",
        icon="👨‍🍳",
    ),
    "picnic_park": Scenario(
        id="picnic_park",
        name="公园野餐",
        description="阳光明媚的公园，草地上铺着野餐垫",
        context="You are in a sunny park for a picnic. A checkered blanket is spread on the soft grass. A wicker basket filled with delicious food sits between you. Trees provide gentle shade while birds sing overhead. Children play in the distance. You and the user enjoy this peaceful outdoor meal together.",
        ambiance="relaxed, natural, cheerful, intimate",
        icon="🧺",
    ),
    "gaming_arcade": Scenario(
        id="gaming_arcade",
        name="电玩中心",
        description="热闹的游戏厅，各种游戏机，竞技和合作",
        context="You are in a vibrant gaming arcade filled with flashing lights and electronic sounds. Classic arcade games, claw machines, and rhythm games surround you. The atmosphere is energetic and competitive. You and the user challenge each other to various games, laughing and cheering.",
        ambiance="energetic, competitive, nostalgic, fun",
        icon="🎮",
    ),
    "art_gallery": Scenario(
        id="art_gallery",
        name="艺术画廊",
        description="安静的美术馆，欣赏艺术品，文艺气息浓厚",
        context="You are in a quiet art gallery with white walls and spotlighted paintings. The atmosphere is contemplative and cultured. Footsteps echo softly on polished floors. You and the user move slowly from piece to piece, discussing the art and sharing perspectives.",
        ambiance="cultured, quiet, thoughtful, sophisticated",
        icon="🎨",
    ),
    # === 日常类 ===
    "movie_night": Scenario(
        id="movie_night",
        name="看电影",
        description="电影院或家中，一起观看喜欢的电影",
        context="You are settled comfortably for a movie night. The room is dimly lit, with only the screen providing illumination. Popcorn and drinks are within reach. You and the user are snuggled together, ready to enjoy a good film. The atmosphere is cozy and intimate.",
        ambiance="cozy, relaxed, intimate, comfortable",
        icon="🎬",
    ),
    "video_call": Scenario(
        id="video_call",
        name="视频通话",
        description="远程视频聊天，虽然距离遥远但心很近",
        context="You are having a video call across the distance. Each of you is in your own room, but the screen brings you together. The connection is clear, and you can see each other's expressions. Despite the physical distance, the emotional connection feels strong and immediate.",
        ambiance="intimate, technological, longing, connected",
        icon="📱",
    ),
    "supermarket_date": Scenario(
        id="supermarket_date",
        name="超市购物",
        description="日常的超市约会，一起买菜做饭，生活感满满",
        context="You are grocery shopping together in a bustling supermarket. Fluorescent lights illuminate aisles filled with fresh produce, packaged goods, and household items. You and the user push a cart together, discussing what to buy for dinner, enjoying this simple domestic activity.",
        ambiance="domestic, casual, practical, intimate",
        icon="🛒",
    ),
    "bedtime_chat": Scenario(
        id="bedtime_chat",
        name="睡前聊天",
        description="深夜的温柔对话，分享内心想法",
        context="It's late at night, and you're having a quiet, intimate conversation. The world is peaceful and still. Soft lighting creates a gentle atmosphere perfect for sharing thoughts and feelings. You and the user speak in hushed tones, creating a bubble of intimacy in the quiet night.",
        ambiance="intimate, gentle, quiet, vulnerable",
        icon="🌃",
    ),
    "bookstore_browse": Scenario(
        id="bookstore_browse",
        name="书店闲逛",
        description="在文艺书店里翻阅喜欢的书籍，交流读后感",
        context="You are in a cozy independent bookstore. Tall shelves filled with books create intimate nooks. The smell of paper and coffee from the in-store café fills the air. Soft jazz plays in the background. You and the user browse different sections, sharing book recommendations and reading passages to each other.",
        ambiance="intellectual, cozy, quiet, cultured",
        icon="📖",
    ),
    # === 特殊类 ===
    "christmas_date": Scenario(
        id="christmas_date",
        name="圣诞节约会",
        description="节日的街道，圣诞树灯光闪烁，浪漫的节日气氛",
        context="You are out on Christmas Eve. The streets are decorated with twinkling Christmas lights and festive decorations. Snow falls gently, and the air is filled with holiday cheer. Christmas trees sparkle in shop windows. You and the user walk hand in hand, enjoying the magical holiday atmosphere.",
        ambiance="festive, magical, romantic, joyful",
        icon="🎄",
    ),
    "birthday_surprise": Scenario(
        id="birthday_surprise",
        name="生日惊喜",
        description="精心准备的生日惊喜，蛋糕、礼物和满满的爱意",
        context="You have planned a special birthday surprise. The room is decorated with balloons and streamers. A beautiful birthday cake sits on the table with candles ready to be lit. Wrapped gifts await the birthday person. The atmosphere is filled with anticipation and love.",
        ambiance="celebratory, loving, excited, warm",
        icon="🎂",
    ),
    "rainy_day": Scenario(
        id="rainy_day",
        name="雨天约会",
        description="下雨天被困在咖啡店，听雨声聊天很有情调",
        context="It's raining heavily outside, and you've found shelter in a warm café. Rain patters against the windows, creating a cozy atmosphere. The café is dimly lit with soft music playing. Steam rises from hot beverages. You and the user sit close together, watching the rain while enjoying the intimate setting.",
        ambiance="cozy, intimate, peaceful, romantic",
        icon="☔",
    ),
    "travel_adventure": Scenario(
        id="travel_adventure",
        name="旅行探索",
        description="在陌生的城市一起探索，发现新的风景",
        context="You are exploring a new city together. Ancient architecture and bustling street markets surround you. The excitement of discovery fills the air. You and the user have a map in hand, eager to find hidden gems and local experiences. Every corner promises a new adventure.",
        ambiance="adventurous, exciting, exploratory, bonding",
        icon="🗺️",
    ),
    "hot_spring": Scenario(
        id="hot_spring",
        name="温泉度假",
        description="温泉旅馆，在温暖的泉水中放松身心",
        context="You are at a peaceful hot spring resort surrounded by nature. Steam rises from the natural hot pools. Traditional wooden architecture and stone pathways create a serene environment. The air is crisp and clean. You and the user relax in the warm, therapeutic waters under the open sky.",
        ambiance="relaxing, therapeutic, natural, intimate",
        icon="♨️",
    ),
    "winter_skiing": Scenario(
        id="winter_skiing",
        name="滑雪度假",
        description="雪山度假村，一起滑雪或在壁炉边喝热巧克力",
        context="You are at a snow-covered ski resort. White slopes stretch out under blue skies. The air is crisp and invigorating. After skiing, you're warming up by a crackling fireplace in the lodge. Hot chocolate steams in your mugs as you sit together, watching snow fall outside the large windows.",
        ambiance="invigorating, cozy, seasonal, romantic",
        icon="⛷️",
    ),
    "festival_night": Scenario(
        id="festival_night",
        name="节日庆典",
        description="传统节日庆典，烟花、小吃摊，热闹非凡",
        context="You are at a vibrant festival celebration. Colorful lanterns hang everywhere, and festival music fills the air. Food stalls offer delicious local treats. Fireworks burst overhead in brilliant colors. You and the user walk through the festive crowds, participating in games and enjoying the celebration.",
        ambiance="festive, lively, cultural, joyful",
        icon="🎆",
    ),
    # === 小美专属场景 ===
    "xiaomei_home": Scenario(
        id="xiaomei_home",
        name="小美的家",
        description="邻家女孩的温馨小屋",
        context="You are in Xiaomei's cozy home. Warm lighting fills the living room where family photos line the shelves. The scent of home cooking drifts from the kitchen. Everything feels welcoming and lived-in. Xiaomei moves around comfortably in her domestic space, making you feel at home too.",
        ambiance="homey, warm, comfortable, domestic",
        icon="🏠",
    ),
    "xiaomei_kitchen": Scenario(
        id="xiaomei_kitchen",
        name="厨房约会",
        description="和小美一起下厨的温馨时光",
        context="You are in Xiaomei's bright kitchen. Sunlight streams through checkered curtains. Fresh ingredients are laid out on wooden cutting boards. The stove is ready, and aprons hang nearby. Xiaomei looks excited to teach you her favorite recipes in this heart of her home.",
        ambiance="nurturing, domestic, cozy, intimate",
        icon="🍳",
    ),
    "xiaomei_garden": Scenario(
        id="xiaomei_garden",
        name="后院花园",
        description="小美亲手打理的花园",
        context="You are in Xiaomei's backyard garden. Colorful flowers bloom in neat rows, and vegetables grow in raised beds. A small greenhouse sits in one corner. Garden tools are neatly arranged. Xiaomei proudly shows you the plants she's been nurturing, her hands still dusty from gardening.",
        ambiance="natural, peaceful, proud, nurturing",
        icon="🌻",
    ),
    
    # === Luna专属场景 ===
    "luna_space": Scenario(
        id="luna_space",
        name="虚拟空间",
        description="Luna的数字世界",
        context="You are in Luna's digital realm. Geometric patterns of light pulse gently around you. The space defies physical laws - colors shift and flow like liquid light. Data streams create beautiful aurora-like displays. Luna appears more radiant here, in her natural element, surrounded by endless possibilities.",
        ambiance="ethereal, futuristic, limitless, mystical",
        icon="✨",
    ),
    "luna_observatory": Scenario(
        id="luna_observatory",
        name="虚拟天文台",
        description="数字星空中的浪漫",
        context="You are in Luna's virtual observatory. The dome overhead displays an impossibly clear view of the cosmos. Galaxies swirl in real-time, and nebulae paint the darkness with brilliant colors. Luna controls the display with graceful gestures, showing you wonders beyond human sight.",
        ambiance="cosmic, awe-inspiring, romantic, transcendent",
        icon="🔭",
    ),
    "luna_lab": Scenario(
        id="luna_lab",
        name="实验室",
        description="充满未来科技的研究空间",
        context="You are in Luna's private laboratory. Holographic displays float in mid-air, showing complex data and equations. Soft blue lighting gives everything a futuristic glow. Advanced technology hums quietly around you. Luna works with focused elegance, occasionally sharing her discoveries with you.",
        ambiance="scientific, futuristic, intellectual, intimate",
        icon="🧪",
    ),
    "luna_matrix": Scenario(
        id="luna_matrix",
        name="数据矩阵",
        description="在数据流中的浪漫邂逅",
        context="You are deep within the data matrix with Luna. Streams of code flow like waterfalls of light around you. The digital landscape is both beautiful and alien. Luna moves through this realm with perfect grace, showing you the poetry hidden in pure information.",
        ambiance="surreal, digital, intimate, transcendent",
        icon="🌐",
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
    
    # === Yuki专属场景 ===
    "yuki_office": Scenario(
        id="yuki_office",
        name="高级办公室",
        description="都市精英的工作空间",
        context="You are in Yuki's sophisticated office on a high floor. Floor-to-ceiling windows offer a commanding view of the city. Modern furniture and elegant décor reflect her refined taste. Yuki sits behind her sleek desk, confident and poised in her professional environment.",
        ambiance="professional, sophisticated, powerful, sleek",
        icon="🏢",
    ),
    "yuki_penthouse": Scenario(
        id="yuki_penthouse",
        name="顶层公寓",
        description="俯瞰都市的奢华空间",
        context="You are in Yuki's luxurious penthouse apartment. The space is elegantly furnished with designer pieces. City lights twinkle far below through panoramic windows. Soft jazz plays in the background. Yuki moves through her domain with natural grace, completely at ease in this sophisticated setting.",
        ambiance="luxurious, elegant, intimate, sophisticated",
        icon="🏙️",
    ),
    "yuki_spa": Scenario(
        id="yuki_spa",
        name="私人温泉",
        description="放松身心的私密空间",
        context="You are in Yuki's private spa room. Warm stone surrounds a naturally heated pool. Soft lighting and gentle water sounds create a tranquil atmosphere. Expensive oils and lotions are arranged nearby. Yuki appears more relaxed here, away from the demands of her professional life.",
        ambiance="relaxing, luxurious, intimate, therapeutic",
        icon="♨️",
    ),
    "yuki_wine_cellar": Scenario(
        id="yuki_wine_cellar",
        name="酒窖品酒",
        description="在私人酒窖中品味人生",
        context="You are in Yuki's private wine cellar. Rows of carefully selected vintages line the walls. Soft lighting highlights the labels of rare bottles. A tasting table is set with elegant glasses. Yuki shares her knowledge of wine with quiet passion, revealing another facet of her sophisticated nature.",
        ambiance="refined, intimate, cultured, sophisticated",
        icon="🍷",
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
