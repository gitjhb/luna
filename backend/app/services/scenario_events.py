"""
场景事件系统 - Scenario Event System
====================================

为每个约会场景定义独特事件，让不同场景有完全不同的体验。

事件类型：
1. 固定事件（Fixed Events）- 特定阶段必定触发
2. 随机事件（Random Events）- 有概率触发，增加变化
3. 特殊事件（Special Events）- 需要满足条件才能触发
"""

import random
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class EventType(str, Enum):
    FIXED = "fixed"       # 固定事件，特定阶段触发
    RANDOM = "random"     # 随机事件，有概率触发
    SPECIAL = "special"   # 特殊事件，需要满足条件


@dataclass
class ScenarioEvent:
    """场景事件定义"""
    id: str
    name: str
    description: str  # 给 LLM 的事件描述
    event_type: EventType
    trigger_stage: int  # 触发阶段 (1-5)，0表示任意阶段
    probability: float = 1.0  # 触发概率 (0-1)
    min_affection: int = -100  # 最低好感度要求
    options_hint: List[str] = None  # 建议的选项方向
    
    def __post_init__(self):
        if self.options_hint is None:
            self.options_hint = []


# =============================================================================
# 全局随机事件（任何场景都可能发生）
# =============================================================================

GLOBAL_RANDOM_EVENTS: List[ScenarioEvent] = [
    ScenarioEvent(
        id="sudden_rain",
        name="突然下雨",
        description="天空突然下起雨来，你们需要找地方躲雨。这是一个增进亲密度的好机会。",
        event_type=EventType.RANDOM,
        trigger_stage=0,  # 任意阶段
        probability=0.08,
        options_hint=["把外套给她", "一起跑向最近的屋檐", "继续淋雨，享受这个浪漫时刻"],
    ),
    ScenarioEvent(
        id="meet_her_friend",
        name="偶遇她的朋友",
        description="你们偶遇了她的一个朋友，对方好奇地打量你们。这是一个社交考验。",
        event_type=EventType.RANDOM,
        trigger_stage=0,
        probability=0.05,
        options_hint=["大方地自我介绍", "让她来处理", "表现得很亲密"],
    ),
    ScenarioEvent(
        id="phone_dies",
        name="手机没电了",
        description="她的手机突然没电了，这意味着接下来只能专心约会了。",
        event_type=EventType.RANDOM,
        trigger_stage=0,
        probability=0.06,
        options_hint=["借她充电宝", "说这样更好，可以专心约会", "帮她找附近的充电点"],
    ),
    ScenarioEvent(
        id="she_trips",
        name="她差点摔倒",
        description="她不小心被什么东西绊了一下，差点摔倒。",
        event_type=EventType.RANDOM,
        trigger_stage=0,
        probability=0.07,
        min_affection=10,
        options_hint=["眼疾手快扶住她", "关心地问她有没有受伤", "开玩笑缓解尴尬"],
    ),
    ScenarioEvent(
        id="beautiful_moment",
        name="美丽的瞬间",
        description="阳光/月光恰好照在她脸上，她看起来特别美。你愣住了。",
        event_type=EventType.RANDOM,
        trigger_stage=0,
        probability=0.10,
        min_affection=20,
        options_hint=["忍不住夸她好看", "偷偷拍下这一刻", "假装没注意到"],
    ),
    ScenarioEvent(
        id="she_initiates",
        name="她主动靠近",
        description="她主动挽住你的手臂/靠近你。这是一个亲密升级的信号。",
        event_type=EventType.SPECIAL,
        trigger_stage=0,
        probability=0.15,
        min_affection=50,  # 需要高好感度
        options_hint=["自然地接受", "害羞但开心", "握住她的手"],
    ),
]


# =============================================================================
# 场景专属事件
# =============================================================================

SCENARIO_EVENTS: Dict[str, List[ScenarioEvent]] = {
    # ========== 游乐园 ==========
    "amusement_park": [
        ScenarioEvent(
            id="roller_coaster",
            name="过山车挑战",
            description="你们来到过山车前，她看起来既期待又有点害怕。",
            event_type=EventType.FIXED,
            trigger_stage=2,
            options_hint=["牵着她的手一起上", "说不敢就不坐了", "假装自己也害怕让她安心"],
        ),
        ScenarioEvent(
            id="claw_machine",
            name="抓娃娃机",
            description="她在抓娃娃机前停下，眼睛盯着里面一个可爱的玩偶。",
            event_type=EventType.FIXED,
            trigger_stage=3,
            options_hint=["挑战帮她抓到", "一起尝试，享受过程", "直接去买一个送她"],
        ),
        ScenarioEvent(
            id="ferris_wheel",
            name="摩天轮时刻",
            description="夜幕降临，摩天轮的灯光亮起。这是约会的经典浪漫场景。",
            event_type=EventType.FIXED,
            trigger_stage=5,
            options_hint=["在最高点表白", "安静欣赏夜景", "拍一张合照"],
        ),
        ScenarioEvent(
            id="haunted_house",
            name="鬼屋惊魂",
            description="你们路过鬼屋，她犹豫要不要进去。",
            event_type=EventType.RANDOM,
            trigger_stage=0,
            probability=0.5,
            options_hint=["拉着她进去保护她", "说不想进去", "让她决定"],
        ),
    ],
    
    # ========== 海边日落 ==========
    "beach_sunset": [
        ScenarioEvent(
            id="waves_splash",
            name="浪花溅湿",
            description="一个大浪突然涌来，打湿了她的裙摆和你的裤脚。",
            event_type=EventType.FIXED,
            trigger_stage=2,
            options_hint=["大笑着继续玩水", "脱下外套给她披上", "带她去更安全的地方"],
        ),
        ScenarioEvent(
            id="collect_shells",
            name="捡贝壳",
            description="她发现了一些漂亮的贝壳，兴奋地蹲下去捡。",
            event_type=EventType.FIXED,
            trigger_stage=3,
            options_hint=["一起捡，比赛谁找到更漂亮的", "把找到的贝壳送给她", "帮她找特别的贝壳"],
        ),
        ScenarioEvent(
            id="sunset_confession",
            name="夕阳告白",
            description="太阳即将落入海平面，金色的光芒洒在她身上。这是告白的完美时刻。",
            event_type=EventType.FIXED,
            trigger_stage=5,
            min_affection=40,
            options_hint=["趁着美景表白", "牵起她的手", "只是静静看着她"],
        ),
        ScenarioEvent(
            id="crab_encounter",
            name="螃蟹出没",
            description="一只小螃蟹突然从沙子里钻出来，朝你们横行。",
            event_type=EventType.RANDOM,
            trigger_stage=0,
            probability=0.3,
            options_hint=["保护她", "一起观察小螃蟹", "假装被吓到逗她"],
        ),
    ],
    
    # ========== 咖啡厅 ==========
    "cafe_paris": [
        ScenarioEvent(
            id="order_together",
            name="点单时刻",
            description="服务员来了，你们需要点单。这是了解她口味的好机会。",
            event_type=EventType.FIXED,
            trigger_stage=1,
            options_hint=["让她先点", "推荐店里的招牌", "点一样的表示默契"],
        ),
        ScenarioEvent(
            id="share_dessert",
            name="分享甜点",
            description="她点的甜点看起来很好吃，她注意到你在看。",
            event_type=EventType.FIXED,
            trigger_stage=3,
            options_hint=["说想尝一口", "等她主动分享", "点一份一样的"],
        ),
        ScenarioEvent(
            id="cafe_closing",
            name="咖啡厅要打烊了",
            description="服务员提醒你们快打烊了。约会要结束了吗？",
            event_type=EventType.FIXED,
            trigger_stage=5,
            options_hint=["提议换个地方继续", "送她回家", "在门口多聊一会"],
        ),
        ScenarioEvent(
            id="coffee_art",
            name="咖啡拉花",
            description="咖啡上的拉花是一颗爱心，她看到后有点害羞。",
            event_type=EventType.RANDOM,
            trigger_stage=0,
            probability=0.4,
            options_hint=["开玩笑说是特意点的", "假装没注意到", "说这是好兆头"],
        ),
    ],
    
    # ========== 城市天台 ==========
    "rooftop_city": [
        ScenarioEvent(
            id="city_lights",
            name="城市灯火",
            description="城市的灯光次第亮起，霓虹闪烁。她靠在栏杆上，望着远方。",
            event_type=EventType.FIXED,
            trigger_stage=2,
            options_hint=["站在她身边", "从背后轻轻环住她", "和她分享这座城市的故事"],
        ),
        ScenarioEvent(
            id="cold_wind",
            name="夜风微凉",
            description="一阵冷风吹过，她微微打了个寒颤。",
            event_type=EventType.FIXED,
            trigger_stage=3,
            options_hint=["把外套披给她", "建议去室内暖和一下", "站近一点帮她挡风"],
        ),
        ScenarioEvent(
            id="make_a_wish",
            name="许个愿望",
            description="她指着远处的一颗星星，说想许个愿。",
            event_type=EventType.FIXED,
            trigger_stage=5,
            options_hint=["问她许了什么愿", "说自己的愿望已经实现了", "一起许愿"],
        ),
        ScenarioEvent(
            id="shooting_star",
            name="流星划过",
            description="一颗流星突然划过夜空！",
            event_type=EventType.RANDOM,
            trigger_stage=0,
            probability=0.15,
            options_hint=["快许愿！", "拉着她一起看", "说这是为你们出现的"],
        ),
    ],
    
    # ========== 星空露营 ==========
    "stargazing": [
        ScenarioEvent(
            id="find_constellation",
            name="找星座",
            description="你们躺在草地上，试着找出各种星座。",
            event_type=EventType.FIXED,
            trigger_stage=2,
            options_hint=["教她认星座", "让她指给你看", "编一个属于你们的星座"],
        ),
        ScenarioEvent(
            id="campfire_talk",
            name="篝火夜话",
            description="篝火噼啪作响，火光映照着她的脸。适合聊些心里话。",
            event_type=EventType.FIXED,
            trigger_stage=3,
            options_hint=["分享一个秘密", "问她的梦想", "只是安静地陪伴"],
        ),
        ScenarioEvent(
            id="meteor_shower",
            name="流星雨",
            description="天空开始出现一颗又一颗的流星，是小型流星雨！",
            event_type=EventType.FIXED,
            trigger_stage=5,
            options_hint=["把每颗流星的愿望都给她", "默默许愿", "趁她看流星时偷看她"],
        ),
        ScenarioEvent(
            id="cold_night",
            name="夜晚变冷",
            description="深夜的温度下降了，她往你这边挪了挪。",
            event_type=EventType.RANDOM,
            trigger_stage=0,
            probability=0.4,
            min_affection=30,
            options_hint=["把毯子分她一半", "建议去帐篷里", "自然地靠近取暖"],
        ),
    ],
    
    # ========== 密室逃脱 ==========
    "escape_room": [
        ScenarioEvent(
            id="first_puzzle",
            name="第一个谜题",
            description="你们面对第一个谜题，需要合作解开。",
            event_type=EventType.FIXED,
            trigger_stage=2,
            options_hint=["主导解谜", "让她来主导", "一起讨论思路"],
        ),
        ScenarioEvent(
            id="stuck_moment",
            name="卡关了",
            description="你们被一个难题困住了，时间在流逝。",
            event_type=EventType.FIXED,
            trigger_stage=3,
            options_hint=["冷静分析", "请求提示", "安慰她不要着急"],
        ),
        ScenarioEvent(
            id="escape_success",
            name="成功逃脱",
            description="最后一刻，你们成功了！她激动地跳了起来。",
            event_type=EventType.FIXED,
            trigger_stage=5,
            options_hint=["拥抱庆祝", "击掌", "说都是她的功劳"],
        ),
        ScenarioEvent(
            id="scary_moment",
            name="吓人环节",
            description="突然，房间里出现了恐怖的声效和灯光，她吓了一跳。",
            event_type=EventType.RANDOM,
            trigger_stage=0,
            probability=0.35,
            options_hint=["拉住她的手", "装作害怕让她保护你", "冷静地安慰她"],
        ),
    ],
    
    # ========== 电影院 ==========
    "movie_night": [
        ScenarioEvent(
            id="choose_movie",
            name="选电影",
            description="你们站在电影海报前，要选一部电影看。",
            event_type=EventType.FIXED,
            trigger_stage=1,
            options_hint=["让她选", "推荐你喜欢的", "选浪漫片"],
        ),
        ScenarioEvent(
            id="scary_scene",
            name="恐怖镜头",
            description="电影里突然出现了恐怖/惊悚的画面，她下意识抓住了你。",
            event_type=EventType.FIXED,
            trigger_stage=3,
            min_affection=20,
            options_hint=["轻轻握住她的手", "小声安慰她", "假装你也害怕"],
        ),
        ScenarioEvent(
            id="movie_ends",
            name="电影结束",
            description="灯光亮起，电影结束了。你们还不想分开。",
            event_type=EventType.FIXED,
            trigger_stage=5,
            options_hint=["提议去吃夜宵", "问她想不想再逛逛", "送她回家"],
        ),
        ScenarioEvent(
            id="hand_touch",
            name="手碰到了",
            description="拿爆米花时，你们的手不小心碰到了一起。",
            event_type=EventType.RANDOM,
            trigger_stage=0,
            probability=0.5,
            options_hint=["假装没发生", "对视一笑", "顺势牵住"],
        ),
    ],
    
    # ========== 料理课堂 ==========
    "cooking_class": [
        ScenarioEvent(
            id="assign_tasks",
            name="分工合作",
            description="你们需要分工，一个切菜一个炒菜。",
            event_type=EventType.FIXED,
            trigger_stage=2,
            options_hint=["主动承担难的部分", "让她选想做什么", "说一起做所有步骤"],
        ),
        ScenarioEvent(
            id="cooking_mistake",
            name="翻车了",
            description="菜好像做失败了，有点焦/咸/糊了...",
            event_type=EventType.FIXED,
            trigger_stage=3,
            probability=0.7,
            options_hint=["大笑着说这是我们的特色", "主动尝一口说还行", "重新做一份"],
        ),
        ScenarioEvent(
            id="taste_together",
            name="一起品尝",
            description="终于做好了！你们准备品尝自己的成果。",
            event_type=EventType.FIXED,
            trigger_stage=5,
            options_hint=["喂她吃第一口", "夸她做得好吃", "说下次再一起做"],
        ),
        ScenarioEvent(
            id="flour_accident",
            name="面粉飞了",
            description="面粉不小心撒了，弄了她一脸。",
            event_type=EventType.RANDOM,
            trigger_stage=0,
            probability=0.25,
            options_hint=["帮她擦掉", "也往自己脸上抹一点", "拍下来当纪念"],
        ),
    ],
    
    # ========== 书店 ==========
    "bookstore_browse": [
        ScenarioEvent(
            id="browse_together",
            name="一起逛书架",
            description="你们在书架间穿行，偶尔分享看到的有趣书籍。",
            event_type=EventType.FIXED,
            trigger_stage=2,
            options_hint=["给她推荐你喜欢的书", "问她喜欢什么类型", "默契地各自探索"],
        ),
        ScenarioEvent(
            id="same_book",
            name="同时看上同一本书",
            description="你们的手同时伸向了同一本书。",
            event_type=EventType.FIXED,
            trigger_stage=3,
            options_hint=["让给她", "说真巧，我也喜欢这本", "提议一起看"],
        ),
        ScenarioEvent(
            id="reading_corner",
            name="阅读角落",
            description="你们找到一个安静的角落，并肩坐下看书。",
            event_type=EventType.FIXED,
            trigger_stage=5,
            options_hint=["靠近她一点", "分享正在看的内容", "安静地享受这个时刻"],
        ),
    ],
    
    # ========== 烛光晚餐 ==========
    "candlelight_dinner": [
        ScenarioEvent(
            id="wine_toast",
            name="举杯",
            description="红酒倒好了，该说点什么敬酒词。",
            event_type=EventType.FIXED,
            trigger_stage=2,
            options_hint=["说一句浪漫的祝酒词", "简单地说「为我们」", "让她先说"],
        ),
        ScenarioEvent(
            id="share_food",
            name="喂她吃",
            description="你夹起一块牛排，犹豫要不要喂她。",
            event_type=EventType.FIXED,
            trigger_stage=3,
            min_affection=30,
            options_hint=["大方地喂她", "放到她盘子里", "作罢，继续吃自己的"],
        ),
        ScenarioEvent(
            id="romantic_music",
            name="浪漫音乐",
            description="餐厅放起了一首浪漫的老歌，气氛变得更温馨了。",
            event_type=EventType.FIXED,
            trigger_stage=5,
            options_hint=["邀请她跳舞", "说这首歌让你想起她", "静静地听完这首歌"],
        ),
        ScenarioEvent(
            id="candle_flicker",
            name="烛光摇曳",
            description="一阵微风让烛光摇曳，她的影子在墙上轻轻晃动。",
            event_type=EventType.RANDOM,
            trigger_stage=0,
            probability=0.4,
            options_hint=["说她在烛光下很美", "帮蜡烛挡风", "假装不在意"],
        ),
    ],
    
    # ========== 雨天约会 ==========
    "rainy_day": [
        ScenarioEvent(
            id="share_umbrella",
            name="共撑一把伞",
            description="只有一把伞，你们需要挨得很近。",
            event_type=EventType.FIXED,
            trigger_stage=2,
            options_hint=["把伞倾向她那边", "说不介意淋一点", "自然地挽住她的手臂"],
        ),
        ScenarioEvent(
            id="cafe_shelter",
            name="咖啡厅避雨",
            description="雨下大了，你们躲进一家小咖啡厅。",
            event_type=EventType.FIXED,
            trigger_stage=3,
            options_hint=["点热饮暖身", "帮她擦干头发", "说喜欢这种意外"],
        ),
        ScenarioEvent(
            id="rain_stops",
            name="雨停了",
            description="雨渐渐停了，空气清新，彩虹若隐若现。",
            event_type=EventType.FIXED,
            trigger_stage=5,
            options_hint=["一起找彩虹", "说想和她再淋一次雨", "感谢这场雨让你们更近"],
        ),
        ScenarioEvent(
            id="puddle_splash",
            name="踩水坑",
            description="她不小心踩到水坑，溅了你一身水。",
            event_type=EventType.RANDOM,
            trigger_stage=0,
            probability=0.3,
            options_hint=["大笑说没关系", "故意也踩一下溅回去", "假装生气逗她"],
        ),
    ],
    
    # ========== 温泉 ==========
    "hot_spring": [
        ScenarioEvent(
            id="first_soak",
            name="初入温泉",
            description="温暖的泉水包裹着你们，舒服得让人放松。",
            event_type=EventType.FIXED,
            trigger_stage=2,
            options_hint=["说这里很舒服", "问她感觉怎么样", "闭眼享受沉默"],
        ),
        ScenarioEvent(
            id="heart_to_heart",
            name="交心时刻",
            description="温泉的氛围让人卸下防备，她开始分享一些心里话。",
            event_type=EventType.FIXED,
            trigger_stage=3,
            options_hint=["认真倾听", "也分享你的故事", "给她安慰"],
        ),
        ScenarioEvent(
            id="starlit_bath",
            name="星空下的温泉",
            description="夜幕降临，星星倒映在温泉水面上。",
            event_type=EventType.FIXED,
            trigger_stage=5,
            options_hint=["说想和她再来", "靠近她一点", "许个愿望"],
        ),
    ],
    
    # ========== 花园约会 ==========
    "flower_garden": [
        ScenarioEvent(
            id="flower_crown",
            name="编花环",
            description="她摘了一些小花，开始编织花环。",
            event_type=EventType.FIXED,
            trigger_stage=2,
            options_hint=["帮她一起编", "静静看着她", "说要帮她戴上"],
        ),
        ScenarioEvent(
            id="butterfly_lands",
            name="蝴蝶停驻",
            description="一只美丽的蝴蝶停在了她的肩膀上。",
            event_type=EventType.FIXED,
            trigger_stage=3,
            options_hint=["轻声让她别动", "拍下这一刻", "小心地帮她赶走"],
        ),
        ScenarioEvent(
            id="sunset_garden",
            name="花园夕阳",
            description="夕阳透过花丛，洒下金色的光芒。",
            event_type=EventType.FIXED,
            trigger_stage=5,
            options_hint=["说她比花还美", "牵起她的手", "摘一朵花送她"],
        ),
    ],
}


# =============================================================================
# 事件服务
# =============================================================================

class ScenarioEventService:
    """场景事件服务"""
    
    def get_events_for_scenario(self, scenario_id: str) -> List[ScenarioEvent]:
        """获取场景的所有事件"""
        return SCENARIO_EVENTS.get(scenario_id, [])
    
    def get_fixed_event_for_stage(
        self, 
        scenario_id: str, 
        stage_num: int,
        current_affection: int = 0,
    ) -> Optional[ScenarioEvent]:
        """获取特定阶段的固定事件"""
        events = self.get_events_for_scenario(scenario_id)
        
        for event in events:
            if (event.event_type == EventType.FIXED and 
                event.trigger_stage == stage_num and
                current_affection >= event.min_affection):
                return event
        
        return None
    
    def roll_random_event(
        self,
        scenario_id: str,
        stage_num: int,
        current_affection: int = 0,
        triggered_events: List[str] = None,
    ) -> Optional[ScenarioEvent]:
        """
        随机触发事件
        
        Args:
            scenario_id: 场景ID
            stage_num: 当前阶段
            current_affection: 当前好感度
            triggered_events: 已触发过的事件ID列表（避免重复）
        
        Returns:
            触发的事件，或 None
        """
        if triggered_events is None:
            triggered_events = []
        
        # 收集所有可能的随机事件（场景专属 + 全局）
        scenario_events = self.get_events_for_scenario(scenario_id)
        all_random_events = [
            e for e in scenario_events 
            if e.event_type in [EventType.RANDOM, EventType.SPECIAL]
        ] + GLOBAL_RANDOM_EVENTS
        
        # 过滤：未触发过、满足好感度、满足阶段
        candidates = []
        for event in all_random_events:
            if event.id in triggered_events:
                continue
            if current_affection < event.min_affection:
                continue
            if event.trigger_stage != 0 and event.trigger_stage != stage_num:
                continue
            candidates.append(event)
        
        # 按概率触发
        for event in candidates:
            if random.random() < event.probability:
                return event
        
        return None
    
    def get_event_prompt_injection(self, event: ScenarioEvent) -> str:
        """
        生成事件的 prompt 注入文本
        
        用于注入到 LLM 的 prompt 中，指导它围绕事件生成剧情
        """
        options_text = ""
        if event.options_hint:
            options_text = f"\n建议选项方向：{' / '.join(event.options_hint)}"
        
        return f"""
【本阶段特殊事件：{event.name}】
{event.description}

请围绕这个事件展开本阶段的剧情。{options_text}
选项应该基于用户对这个事件的不同反应方式。
"""
    
    def build_event_context(
        self,
        scenario_id: str,
        stage_num: int,
        current_affection: int,
        triggered_events: List[str] = None,
    ) -> tuple[Optional[ScenarioEvent], str]:
        """
        构建事件上下文
        
        Returns:
            (event, prompt_injection) - 事件对象和prompt注入文本
        """
        if triggered_events is None:
            triggered_events = []
        
        # 优先检查固定事件
        fixed_event = self.get_fixed_event_for_stage(
            scenario_id, stage_num, current_affection
        )
        
        if fixed_event:
            return fixed_event, self.get_event_prompt_injection(fixed_event)
        
        # 尝试随机事件
        random_event = self.roll_random_event(
            scenario_id, stage_num, current_affection, triggered_events
        )
        
        if random_event:
            return random_event, self.get_event_prompt_injection(random_event)
        
        return None, ""


# 单例
scenario_event_service = ScenarioEventService()
