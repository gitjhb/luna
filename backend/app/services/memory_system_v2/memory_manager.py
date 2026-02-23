"""
Memory System v2 - 分层记忆系统
==============================

三层架构：
1. 工作记忆 (Working Memory) - 当前对话上下文
2. 情节记忆 (Episodic Memory) - 重要事件和对话
3. 语义记忆 (Semantic Memory) - 用户特征和偏好

让 AI 角色真正"记住"用户
"""

import asyncio
import logging
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


# =============================================================================
# 数据结构定义
# =============================================================================

class MemoryType(Enum):
    """记忆类型"""
    EPISODIC = "episodic"    # 情节记忆（事件）
    SEMANTIC = "semantic"     # 语义记忆（特征）
    EMOTIONAL = "emotional"   # 情感记忆（情绪高点/低点）


class MemoryImportance(Enum):
    """记忆重要性"""
    LOW = 1       # 普通对话
    MEDIUM = 2    # 有价值信息
    HIGH = 3      # 重要事件
    CRITICAL = 4  # 里程碑时刻


@dataclass
class EpisodicMemory:
    """情节记忆 - 一个具体事件"""
    memory_id: str
    user_id: str
    character_id: str
    
    # 内容
    event_type: str          # first_meeting / confession / fight / gift / milestone
    summary: str             # 事件摘要
    key_dialogue: List[str]  # 关键对话（最多3句）
    emotion_state: str       # 当时的情绪状态
    
    # 元数据
    importance: MemoryImportance
    created_at: datetime
    last_recalled: Optional[datetime] = None
    recall_count: int = 0
    
    # 衰减
    strength: float = 1.0    # 记忆强度 0.0-1.0，会随时间衰减
    
    def to_prompt_text(self) -> str:
        """转换为 prompt 可用的文本"""
        dialogue_text = "\n".join([f'  "{d}"' for d in self.key_dialogue[:2]])
        return f"[{self.event_type}] {self.summary}\n{dialogue_text}"


@dataclass
class SemanticMemory:
    """语义记忆 - 用户特征"""
    user_id: str
    character_id: str
    
    # 基本信息
    user_name: Optional[str] = None
    user_nickname: Optional[str] = None  # 用户希望被叫的昵称
    birthday: Optional[str] = None
    occupation: Optional[str] = None
    location: Optional[str] = None
    
    # 偏好
    likes: List[str] = field(default_factory=list)      # 喜欢的东西
    dislikes: List[str] = field(default_factory=list)   # 讨厌的东西
    interests: List[str] = field(default_factory=list)  # 兴趣爱好
    
    # 性格特征（AI 观察到的）
    personality_traits: List[str] = field(default_factory=list)
    communication_style: Optional[str] = None  # 沟通风格
    
    # 关系相关
    relationship_status: Optional[str] = None  # 单身/恋爱中
    pet_names: List[str] = field(default_factory=list)  # 互相的昵称
    important_dates: Dict[str, str] = field(default_factory=dict)  # 纪念日等
    shared_jokes: List[str] = field(default_factory=list)  # 共同的梗
    
    # 敏感话题
    sensitive_topics: List[str] = field(default_factory=list)  # 避免提及的话题
    
    # 更新时间
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_prompt_text(self) -> str:
        """转换为 prompt 可用的文本"""
        parts = []
        
        if self.user_name:
            parts.append(f"用户名字: {self.user_name}")
        if self.user_nickname:
            parts.append(f"用户喜欢被叫: {self.user_nickname}")
        if self.birthday:
            parts.append(f"生日: {self.birthday}")
        if self.occupation:
            parts.append(f"职业: {self.occupation}")
        if self.likes:
            parts.append(f"喜欢: {', '.join(self.likes[:5])}")
        if self.dislikes:
            parts.append(f"不喜欢: {', '.join(self.dislikes[:5])}")
        if self.interests:
            parts.append(f"兴趣: {', '.join(self.interests[:5])}")
        if self.pet_names:
            parts.append(f"你们之间的昵称: {', '.join(self.pet_names[:3])}")
        if self.important_dates:
            dates = [f"{k}: {v}" for k, v in list(self.important_dates.items())[:3]]
            parts.append(f"重要日期: {', '.join(dates)}")
        if self.sensitive_topics:
            parts.append(f"避免提及: {', '.join(self.sensitive_topics[:3])}")
        
        return "\n".join(parts)


@dataclass
class MemoryContext:
    """记忆上下文 - 传递给 LLM 的记忆信息"""
    # 工作记忆
    working_memory: List[Dict[str, str]]  # 最近的对话
    
    # 情节记忆
    relevant_episodes: List[EpisodicMemory]  # 相关的事件
    recent_episodes: List[EpisodicMemory]    # 最近的事件
    
    # 语义记忆
    user_profile: SemanticMemory
    
    # 今日特殊
    today_special: Optional[str] = None  # 今天是否是特殊日子
    
    def to_prompt_section(self) -> str:
        """生成完整的记忆 prompt 部分"""
        sections = []
        
        # 用户档案
        if self.user_profile:
            profile_text = self.user_profile.to_prompt_text()
            if profile_text:
                sections.append(f"=== 关于用户 ===\n{profile_text}")
        
        # 今日特殊
        if self.today_special:
            sections.append(f"⭐ 今天特殊: {self.today_special}")
        
        # 共同回忆
        if self.relevant_episodes or self.recent_episodes:
            memory_lines = []
            
            # 相关记忆（根据当前话题检索）
            for ep in self.relevant_episodes[:3]:
                memory_lines.append(f"• {ep.summary}")
            
            # 最近记忆
            for ep in self.recent_episodes[:2]:
                if ep not in self.relevant_episodes:
                    memory_lines.append(f"• (最近) {ep.summary}")
            
            if memory_lines:
                sections.append(f"=== 你们的回忆 ===\n" + "\n".join(memory_lines))
        
        return "\n\n".join(sections)


# =============================================================================
# 记忆提取器 - 从对话中提取记忆
# =============================================================================

class MemoryExtractor:
    """
    记忆提取器 v2 - "隐形场记"模式
    
    使用 LLM 语义理解从对话中提取：
    1. 用户信息（语义记忆）
    2. 重要事件（情节记忆）
    
    核心优势：
    - 跨语言：中/英/日/法...统一处理
    - 语境感知：能区分"亲了"vs"想亲但被拒"vs"梦到亲了"
    - 否定句识别："别亲我"不会误判为亲密事件
    """
    
    # 轻量级预筛选关键词（只用于决定是否需要调用LLM场记）
    # 如果消息里没有这些词，大概率是闲聊，可以跳过场记
    POTENTIAL_EVENT_HINTS = [
        # 亲密行为
        "亲", "吻", "kiss", "抱", "hug", "牵手", "hold", "摸",
        # 情感表达
        "爱", "喜欢", "love", "讨厌", "hate", "生气", "angry", "想你", "miss",
        # 关系变化
        "分手", "break", "在一起", "together", "结婚", "marry", "求婚", "propose",
        "女朋友", "男朋友", "girlfriend", "boyfriend", "老婆", "老公", "wife", "husband",
        # 重要时刻
        "第一次", "first", "纪念", "anniversary", "生日", "birthday",
        # 礼物/惊喜
        "礼物", "gift", "送你", "惊喜", "surprise",
        # 道歉/和解
        "对不起", "sorry", "原谅", "forgive", "我错了",
        # 情绪高点
        "最开心", "最幸福", "最难过", "happiest", "saddest",
    ]
    
    def __init__(self, llm_service=None):
        self.llm = llm_service
    
    def _needs_scene_analysis(self, message: str, assistant_response: str = "") -> bool:
        """
        快速预筛选：判断是否需要调用 LLM 场记
        
        策略：如果消息或回复里包含潜在事件关键词，才调用场记
        这样可以节省 90% 的闲聊消息的 LLM 调用
        """
        combined = (message + " " + (assistant_response or "")).lower()
        return any(hint in combined for hint in self.POTENTIAL_EVENT_HINTS)
    
    async def extract_from_message(
        self,
        message: str,
        context: List[Dict[str, str]],
        current_semantic: SemanticMemory,
        assistant_response: str = "",
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        从消息中提取记忆（场记模式）
        
        返回:
            (semantic_updates, episodic_event)
        """
        # 快速预筛选
        if not self._needs_scene_analysis(message, assistant_response):
            logger.debug(f"Skipping scene analysis for: {message[:50]}...")
            return {}, None
        
        # 调用 LLM 场记
        if not self.llm:
            logger.warning("No LLM service available for scene analysis")
            return {}, None
        
        try:
            result = await self._scene_supervisor_extract(
                message, assistant_response, context, current_semantic
            )
            return result.get("semantic", {}), result.get("episodic")
        except Exception as e:
            logger.warning(f"Scene analysis failed: {e}")
            return {}, None
    
    async def _scene_supervisor_extract(
        self,
        user_message: str,
        assistant_response: str,
        context: List[Dict[str, str]],
        current_semantic: SemanticMemory,
    ) -> Dict[str, Any]:
        """
        LLM 场记分析 - 语义级记忆提取
        
        这是核心的"隐形场记"，负责：
        1. 判断是否发生了重要事件
        2. 提取用户信息更新
        3. 区分真实事件 vs 梦境/假设/否定
        """
        # 构建对话上下文
        dialogue_lines = []
        for m in context[-3:]:
            role = "用户" if m.get("role") == "user" else "Luna"
            dialogue_lines.append(f"{role}: {m.get('content', '')[:150]}")
        dialogue_lines.append(f"用户: {user_message}")
        if assistant_response:
            dialogue_lines.append(f"Luna: {assistant_response[:200]}")
        
        dialogue_str = "\n".join(dialogue_lines)
        
        current_info = current_semantic.to_prompt_text() if current_semantic else "无已知信息"
        
        prompt = f"""# Role
你是 Luna 恋爱游戏的后台剧情分析师（场记）。

# 已知用户信息
{current_info}

# 本轮对话
{dialogue_str}

# Task
分析以上对话，提取：
1. **用户信息更新**（名字、生日、职业、喜好等新信息）
2. **重要事件**（如果有的话）

# 重要规则
- 只记录**实际发生**的事件，不记录"想要但没发生"的
- 梦境、回忆、假设、否定句 = 不算实际发生
- "亲我" + "不要" = rejection（求欢被拒），不是 intimate
- "亲我" + "*亲了*" = intimate（实际发生）
- 跨语言统一：无论中英日法，输出标准化字段

# Event Types
- confession: 表白、说"我爱你"
- intimate: 亲吻、拥抱、牵手等实际发生的亲密行为
- rejection: 一方求亲密/求爱被拒绝
- fight: 吵架、冷战、说狠话
- reconciliation: 道歉、和好
- milestone: 第一次约会、一周年、一百天等
- gift: 送礼物、收礼物
- proposal: 求婚

# Output (JSON only, no markdown)
{{
  "semantic": {{
    "user_name": "提取到的名字或null",
    "birthday": "生日或null",
    "occupation": "职业或null", 
    "likes": ["喜欢的东西"],
    "dislikes": ["不喜欢的东西"],
    "relationship_status": "dating/engaged/married/single 或 null",
    "important_dates": {{"纪念日名称": "MM-DD"}},
    "pet_names": ["昵称"]
  }},
  "episodic": {{
    "event_found": true/false,
    "actually_happened": true/false,
    "event_type": "confession/intimate/rejection/fight/reconciliation/milestone/gift/proposal",
    "sub_type": "first_kiss/hug/holding_hands/...",
    "summary": "一句话描述发生了什么（用中文）",
    "importance": 1-4,
    "is_first_time": true/false
  }}
}}

null 的字段可以省略。如果没有重要事件，episodic 里只需要 {{"event_found": false}}。"""

        result = await self.llm.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0,  # 场记要稳定输出
            max_tokens=500,
        )
        
        response = result["choices"][0]["message"]["content"]
        logger.debug(f"Scene supervisor response: {response[:200]}")
        
        # 解析 JSON
        try:
            # 提取 JSON（可能有 markdown 包裹）
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                # 清理空值
                semantic = {k: v for k, v in data.get("semantic", {}).items() if v}
                episodic = data.get("episodic", {})
                
                # 只有实际发生的事件才记录
                if not episodic.get("event_found") or not episodic.get("actually_happened", True):
                    episodic = None
                else:
                    # 标记为需要记录
                    episodic["is_important"] = True
                
                return {"semantic": semantic, "episodic": episodic}
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse scene supervisor JSON: {e}")
        
        return {"semantic": {}, "episodic": None}


# =============================================================================
# 记忆检索器 - 找到相关记忆
# =============================================================================

class MemoryRetriever:
    """
    记忆检索器
    
    根据当前对话内容，找到最相关的记忆
    使用 pgvector 语义搜索 + 关键词匹配混合策略
    """
    
    def __init__(self, llm_service=None, vector_service=None):
        self.llm = llm_service
        self._vector_service = vector_service
    
    @property
    def vector_service(self):
        """Lazy load vector service to avoid circular imports."""
        if self._vector_service is None:
            try:
                from app.services.vector_service import vector_service
                self._vector_service = vector_service
            except Exception as e:
                logger.warning(f"Could not load vector_service: {e}")
        return self._vector_service
    
    async def retrieve_relevant(
        self,
        query: str,
        episodes: List[EpisodicMemory],
        top_k: int = 5,
        user_id: str = None,
        character_id: str = None,
    ) -> List[EpisodicMemory]:
        """
        检索相关的情节记忆
        
        策略:
        1. 首先尝试 pgvector 语义搜索（如果可用）
        2. 回退到关键词匹配
        3. 合并结果并去重
        """
        if not episodes:
            return []
        
        results = []
        vector_memory_ids = set()
        
        # 1. 尝试语义搜索（pgvector）
        if user_id and character_id and self.vector_service:
            try:
                vector_results = await self.vector_service.search_similar_episodes(
                    user_id=user_id,
                    character_id=character_id,
                    query_text=query,
                    top_k=top_k,
                    min_similarity=0.3,
                )
                
                # 将 vector 结果转换为 EpisodicMemory 对象
                episode_map = {ep.memory_id: ep for ep in episodes}
                for vr in vector_results:
                    if vr["memory_id"] in episode_map:
                        results.append(episode_map[vr["memory_id"]])
                        vector_memory_ids.add(vr["memory_id"])
                        logger.debug(f"Vector match: {vr['summary'][:50]} (sim={vr['similarity']:.2f})")
                
                if results:
                    logger.info(f"pgvector found {len(results)} relevant memories")
                    
            except Exception as e:
                logger.warning(f"Vector search failed, falling back to keyword: {e}")
        
        # 2. 关键词匹配（回退或补充）
        if len(results) < top_k:
            keyword_results = self._keyword_match(query, episodes, top_k - len(results))
            # 添加未在 vector 结果中的记忆
            for ep in keyword_results:
                if ep.memory_id not in vector_memory_ids:
                    results.append(ep)
        
        return results[:top_k]
    
    def _keyword_match(
        self,
        query: str,
        episodes: List[EpisodicMemory],
        top_k: int,
    ) -> List[EpisodicMemory]:
        """关键词匹配（回退方法）"""
        scored = []
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        for ep in episodes:
            score = 0
            
            # 摘要匹配
            summary_lower = ep.summary.lower()
            for word in query_words:
                if len(word) > 1 and word in summary_lower:
                    score += 2
            
            # 关键词匹配
            for dialogue in ep.key_dialogue:
                dialogue_lower = dialogue.lower()
                for word in query_words:
                    if len(word) > 1 and word in dialogue_lower:
                        score += 1
            
            # 重要性加成
            score += ep.importance.value
            
            # 记忆强度加成
            score *= ep.strength
            
            # 最近被回忆加成
            if ep.last_recalled:
                days_since = (datetime.now() - ep.last_recalled).days
                if days_since < 7:
                    score += 1
            
            scored.append((score, ep))
        
        # 排序并返回 top_k
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [ep for _, ep in scored[:top_k]]
    
    async def get_recent_episodes(
        self,
        episodes: List[EpisodicMemory],
        days: int = 7,
        limit: int = 5,
    ) -> List[EpisodicMemory]:
        """获取最近的情节记忆"""
        cutoff = datetime.now() - timedelta(days=days)
        
        recent = [ep for ep in episodes if ep.created_at > cutoff]
        recent.sort(key=lambda x: x.created_at, reverse=True)
        
        return recent[:limit]
    
    def check_special_date(
        self,
        semantic: SemanticMemory,
    ) -> Optional[str]:
        """检查今天是否是特殊日子"""
        if not semantic or not semantic.important_dates:
            return None
        
        today = datetime.now()
        today_str = today.strftime("%m-%d")
        
        for name, date_str in semantic.important_dates.items():
            # 尝试匹配 MM-DD 格式
            try:
                if today_str in date_str or date_str in today_str:
                    return f"今天是{name}！"
            except:
                continue
        
        # 检查生日
        if semantic.birthday:
            if today_str in semantic.birthday:
                return "今天是用户的生日！"
        
        return None


# =============================================================================
# 记忆管理器 - 主入口
# =============================================================================

class MemoryManager:
    """
    记忆管理器 - 统一管理三层记忆
    
    主要功能:
    1. 从对话中提取并存储记忆
    2. 检索相关记忆用于生成回复
    3. 管理记忆的衰减和强化
    """
    
    def __init__(self, db_service=None, llm_service=None):
        self.db = db_service
        self.llm = llm_service
        self.extractor = MemoryExtractor(llm_service)
        self.retriever = MemoryRetriever(llm_service)
        
        # 内存缓存
        self._semantic_cache: Dict[str, SemanticMemory] = {}
        self._episodic_cache: Dict[str, List[EpisodicMemory]] = {}
    
    def _cache_key(self, user_id: str, character_id: str) -> str:
        return f"{user_id}:{character_id}"
    
    # =========================================================================
    # 主要 API
    # =========================================================================
    
    async def process_conversation(
        self,
        user_id: str,
        character_id: str,
        user_message: str,
        assistant_response: str,
        context: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        处理一轮对话，提取并存储记忆
        
        应在每次对话后调用
        """
        key = self._cache_key(user_id, character_id)
        
        # 获取当前语义记忆
        semantic = await self.get_semantic_memory(user_id, character_id)
        
        # 提取记忆（场记模式：同时分析用户消息和AI回复）
        semantic_updates, episodic_event = await self.extractor.extract_from_message(
            user_message, context, semantic, assistant_response
        )
        
        result = {
            "semantic_updated": False,
            "episodic_created": False,
            "updates": {},
        }
        
        # 更新语义记忆
        if semantic_updates:
            await self._update_semantic(user_id, character_id, semantic_updates)
            result["semantic_updated"] = True
            result["updates"]["semantic"] = semantic_updates
        
        # 创建情节记忆
        if episodic_event and episodic_event.get("is_important", True):
            episode = await self._create_episode(
                user_id, character_id,
                episodic_event, user_message, assistant_response
            )
            if episode:
                result["episodic_created"] = True
                result["updates"]["episodic"] = {
                    "event_type": episode.event_type,
                    "summary": episode.summary,
                }
        
        return result
    
    async def get_memory_context(
        self,
        user_id: str,
        character_id: str,
        current_message: str,
        working_memory: List[Dict[str, str]],
    ) -> MemoryContext:
        """
        获取记忆上下文，用于生成回复
        
        应在调用 LLM 前调用
        """
        # 获取语义记忆
        semantic = await self.get_semantic_memory(user_id, character_id)
        
        # 获取情节记忆
        episodes = await self.get_episodic_memories(user_id, character_id)
        
        # 检索相关记忆（使用 pgvector 语义搜索）
        relevant = await self.retriever.retrieve_relevant(
            current_message, episodes, top_k=3,
            user_id=user_id, character_id=character_id
        )
        
        # 获取最近记忆
        recent = await self.retriever.get_recent_episodes(episodes, days=7, limit=2)
        
        # 检查特殊日期
        special = self.retriever.check_special_date(semantic)
        
        return MemoryContext(
            working_memory=working_memory,
            relevant_episodes=relevant,
            recent_episodes=recent,
            user_profile=semantic,
            today_special=special,
        )
    
    async def get_semantic_memory(
        self,
        user_id: str,
        character_id: str,
    ) -> SemanticMemory:
        """获取语义记忆"""
        key = self._cache_key(user_id, character_id)
        
        # 检查缓存
        if key in self._semantic_cache:
            return self._semantic_cache[key]
        
        # 从数据库加载
        if self.db:
            try:
                data = await self.db.get_semantic_memory(user_id, character_id)
                if data:
                    semantic = self._dict_to_semantic(data)
                    self._semantic_cache[key] = semantic
                    return semantic
            except Exception as e:
                logger.error(f"Failed to load semantic memory: {e}")
        
        # 返回空的
        semantic = SemanticMemory(user_id=user_id, character_id=character_id)
        self._semantic_cache[key] = semantic
        return semantic
    
    async def get_episodic_memories(
        self,
        user_id: str,
        character_id: str,
    ) -> List[EpisodicMemory]:
        """获取情节记忆列表"""
        key = self._cache_key(user_id, character_id)
        
        # 检查缓存
        if key in self._episodic_cache:
            return self._episodic_cache[key]
        
        # 从数据库加载
        if self.db:
            try:
                data_list = await self.db.get_episodic_memories(user_id, character_id)
                episodes = [self._dict_to_episode(d) for d in data_list]
                self._episodic_cache[key] = episodes
                return episodes
            except Exception as e:
                logger.error(f"Failed to load episodic memories: {e}")
        
        self._episodic_cache[key] = []
        return []
    
    # =========================================================================
    # 内部方法
    # =========================================================================
    
    async def _update_semantic(
        self,
        user_id: str,
        character_id: str,
        updates: Dict[str, Any],
    ):
        """更新语义记忆"""
        key = self._cache_key(user_id, character_id)
        semantic = await self.get_semantic_memory(user_id, character_id)
        
        # 应用更新
        for field, value in updates.items():
            if field == "likes" and isinstance(value, list):
                semantic.likes = list(set(semantic.likes + value))[:20]
            elif field == "dislikes" and isinstance(value, list):
                semantic.dislikes = list(set(semantic.dislikes + value))[:20]
            elif field == "interests" and isinstance(value, list):
                semantic.interests = list(set(semantic.interests + value))[:20]
            elif field == "pet_names" and isinstance(value, list):
                semantic.pet_names = list(set(semantic.pet_names + value))[:10]
            elif field == "important_dates" and isinstance(value, dict):
                # 合并重要日期
                if not semantic.important_dates:
                    semantic.important_dates = {}
                semantic.important_dates.update(value)
            elif field == "relationship_status" and value:
                # 关系状态只在有值时更新（不覆盖为空）
                semantic.relationship_status = value
                logger.info(f"Relationship status updated: {value} for user {user_id}")
            elif hasattr(semantic, field):
                setattr(semantic, field, value)
        
        semantic.updated_at = datetime.now()
        self._semantic_cache[key] = semantic
        
        # 持久化
        if self.db:
            try:
                await self.db.save_semantic_memory(user_id, character_id, self._semantic_to_dict(semantic))
            except Exception as e:
                logger.error(f"Failed to save semantic memory: {e}")
    
    async def _create_episode(
        self,
        user_id: str,
        character_id: str,
        event_data: Dict[str, Any],
        user_message: str,
        assistant_response: str,
    ) -> Optional[EpisodicMemory]:
        """创建情节记忆"""
        key = self._cache_key(user_id, character_id)
        
        # 生成 ID
        memory_id = hashlib.md5(
            f"{user_id}:{character_id}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        # 确定重要性
        importance_map = {
            "confession": MemoryImportance.CRITICAL,
            "fight": MemoryImportance.HIGH,
            "reconciliation": MemoryImportance.HIGH,
            "milestone": MemoryImportance.CRITICAL,
            "gift": MemoryImportance.MEDIUM,
            "emotional_peak": MemoryImportance.HIGH,
        }
        importance = importance_map.get(
            event_data.get("event_type", "other"),
            MemoryImportance.MEDIUM
        )
        
        # 如果有 LLM 提供的重要性评分
        if event_data.get("importance"):
            importance = MemoryImportance(min(event_data["importance"], 4))
        
        episode = EpisodicMemory(
            memory_id=memory_id,
            user_id=user_id,
            character_id=character_id,
            event_type=event_data.get("event_type", "other"),
            summary=event_data.get("summary", user_message[:50]),
            key_dialogue=[
                user_message[:200],
                assistant_response[:200] if assistant_response else "",
            ],
            emotion_state=event_data.get("emotion_state", "neutral"),
            importance=importance,
            created_at=datetime.now(),
            strength=1.0,
        )
        
        # 添加到缓存
        if key not in self._episodic_cache:
            self._episodic_cache[key] = []
        self._episodic_cache[key].append(episode)
        
        # 限制数量
        self._episodic_cache[key] = self._episodic_cache[key][-100:]
        
        # 持久化
        if self.db:
            try:
                await self.db.save_episodic_memory(user_id, character_id, self._episode_to_dict(episode))
            except Exception as e:
                logger.error(f"Failed to save episodic memory: {e}")
        
        # 生成并保存 embedding（用于语义搜索）
        try:
            from app.services.vector_service import vector_service
            # 组合摘要和关键对话作为 embedding 文本
            embed_text = episode.summary
            if episode.key_dialogue:
                embed_text += " " + " ".join(episode.key_dialogue[:2])
            
            embedding = await vector_service.embed_text(embed_text)
            await vector_service.save_episode_embedding(memory_id, embedding)
            logger.debug(f"Saved embedding for episode {memory_id}")
        except Exception as e:
            logger.warning(f"Failed to save episode embedding (non-critical): {e}")
        
        logger.info(f"Created episodic memory: {episode.event_type} - {episode.summary}")
        return episode
    
    # =========================================================================
    # 记忆衰减
    # =========================================================================
    
    async def apply_memory_decay(
        self,
        user_id: str,
        character_id: str,
        days_passed: float,
    ):
        """
        应用记忆衰减
        
        规则:
        - 普通记忆每天衰减 5%
        - 重要记忆衰减更慢
        - 被回忆的记忆会强化
        - 强度低于 0.3 的记忆会被删除
        """
        episodes = await self.get_episodic_memories(user_id, character_id)
        
        for ep in episodes:
            # 根据重要性计算衰减率
            decay_rates = {
                MemoryImportance.LOW: 0.05,
                MemoryImportance.MEDIUM: 0.03,
                MemoryImportance.HIGH: 0.02,
                MemoryImportance.CRITICAL: 0.01,
            }
            daily_decay = decay_rates.get(ep.importance, 0.05)
            
            # 应用衰减
            ep.strength *= (1 - daily_decay) ** days_passed
            ep.strength = max(0.1, ep.strength)  # 最低 0.1
        
        # 删除太弱的记忆（保留重要的）
        kept = [
            ep for ep in episodes
            if ep.strength >= 0.3 or ep.importance.value >= 3
        ]
        
        key = self._cache_key(user_id, character_id)
        self._episodic_cache[key] = kept
    
    async def recall_memory(
        self,
        user_id: str,
        character_id: str,
        memory_id: str,
    ):
        """
        回忆一个记忆（强化它）
        
        当 AI 提到某个记忆时调用
        """
        episodes = await self.get_episodic_memories(user_id, character_id)
        
        for ep in episodes:
            if ep.memory_id == memory_id:
                ep.last_recalled = datetime.now()
                ep.recall_count += 1
                # 强化记忆
                ep.strength = min(1.0, ep.strength + 0.1)
                break
    
    # =========================================================================
    # 序列化
    # =========================================================================
    
    def _semantic_to_dict(self, semantic: SemanticMemory) -> Dict[str, Any]:
        return {
            "user_id": semantic.user_id,
            "character_id": semantic.character_id,
            "user_name": semantic.user_name,
            "user_nickname": semantic.user_nickname,
            "birthday": semantic.birthday,
            "occupation": semantic.occupation,
            "location": semantic.location,
            "likes": semantic.likes,
            "dislikes": semantic.dislikes,
            "interests": semantic.interests,
            "personality_traits": semantic.personality_traits,
            "communication_style": semantic.communication_style,
            "relationship_status": semantic.relationship_status,
            "pet_names": semantic.pet_names,
            "important_dates": semantic.important_dates,
            "shared_jokes": semantic.shared_jokes,
            "sensitive_topics": semantic.sensitive_topics,
            "updated_at": semantic.updated_at.isoformat(),
        }
    
    def _dict_to_semantic(self, data: Dict[str, Any]) -> SemanticMemory:
        return SemanticMemory(
            user_id=data.get("user_id", ""),
            character_id=data.get("character_id", ""),
            user_name=data.get("user_name"),
            user_nickname=data.get("user_nickname"),
            birthday=data.get("birthday"),
            occupation=data.get("occupation"),
            location=data.get("location"),
            likes=data.get("likes", []),
            dislikes=data.get("dislikes", []),
            interests=data.get("interests", []),
            personality_traits=data.get("personality_traits", []),
            communication_style=data.get("communication_style"),
            relationship_status=data.get("relationship_status"),
            pet_names=data.get("pet_names", []),
            important_dates=data.get("important_dates", {}),
            shared_jokes=data.get("shared_jokes", []),
            sensitive_topics=data.get("sensitive_topics", []),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
        )
    
    def _episode_to_dict(self, episode: EpisodicMemory) -> Dict[str, Any]:
        return {
            "memory_id": episode.memory_id,
            "user_id": episode.user_id,
            "character_id": episode.character_id,
            "event_type": episode.event_type,
            "summary": episode.summary,
            "key_dialogue": episode.key_dialogue,
            "emotion_state": episode.emotion_state,
            "importance": episode.importance.value,
            "created_at": episode.created_at.isoformat(),
            "last_recalled": episode.last_recalled.isoformat() if episode.last_recalled else None,
            "recall_count": episode.recall_count,
            "strength": episode.strength,
        }
    
    def _dict_to_episode(self, data: Dict[str, Any]) -> EpisodicMemory:
        return EpisodicMemory(
            memory_id=data.get("memory_id", ""),
            user_id=data.get("user_id", ""),
            character_id=data.get("character_id", ""),
            event_type=data.get("event_type", "other"),
            summary=data.get("summary", ""),
            key_dialogue=data.get("key_dialogue", []),
            emotion_state=data.get("emotion_state", "neutral"),
            importance=MemoryImportance(data.get("importance", 2)),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            last_recalled=datetime.fromisoformat(data["last_recalled"]) if data.get("last_recalled") else None,
            recall_count=data.get("recall_count", 0),
            strength=data.get("strength", 1.0),
        )


# 单例
memory_manager = MemoryManager()
