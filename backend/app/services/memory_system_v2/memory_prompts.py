"""
Memory System v2 - Prompt 生成器
================================

根据记忆内容生成角色可用的 Prompt 部分
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class MemoryPromptConfig:
    """记忆 Prompt 配置"""
    
    # 包含哪些部分
    include_profile: bool = True      # 用户档案
    include_episodes: bool = True     # 情节记忆
    include_special_dates: bool = True  # 特殊日期提醒
    
    # 数量限制
    max_profile_items: int = 10
    max_episodes: int = 5
    
    # 格式
    format_style: str = "natural"  # natural / structured


class MemoryPromptGenerator:
    """
    记忆 Prompt 生成器
    
    将记忆信息转换为 LLM 可理解的 prompt
    """
    
    def __init__(self, config: MemoryPromptConfig = None):
        self.config = config or MemoryPromptConfig()
    
    def generate(
        self,
        semantic_memory: Dict[str, Any],
        episodic_memories: List[Dict[str, Any]],
        current_query: str = None,
        intimacy_level: int = 1,
    ) -> str:
        """
        生成完整的记忆 prompt 部分
        
        Args:
            semantic_memory: 语义记忆（用户档案）
            episodic_memories: 情节记忆列表
            current_query: 当前用户消息（用于相关性判断）
            intimacy_level: 亲密度等级（影响信息使用方式）
        
        Returns:
            str: 要添加到 system prompt 的记忆部分
        """
        sections = []
        
        # 用户档案
        if self.config.include_profile and semantic_memory:
            profile_section = self._generate_profile_section(
                semantic_memory, intimacy_level
            )
            if profile_section:
                sections.append(profile_section)
        
        # 特殊日期
        if self.config.include_special_dates and semantic_memory:
            special = self._check_special_dates(semantic_memory)
            if special:
                sections.append(f"⭐ 今天特殊提醒: {special}")
        
        # 情节记忆
        if self.config.include_episodes and episodic_memories:
            episodes_section = self._generate_episodes_section(
                episodic_memories, current_query
            )
            if episodes_section:
                sections.append(episodes_section)
        
        # 使用指南
        sections.append(self._generate_usage_guide(intimacy_level))
        
        return "\n\n".join(sections)
    
    def _generate_profile_section(
        self,
        memory: Dict[str, Any],
        intimacy_level: int,
    ) -> str:
        """生成用户档案部分"""
        lines = ["=== 关于这位用户 ==="]
        
        # 基本信息
        if memory.get("user_name"):
            lines.append(f"• 名字: {memory['user_name']}")
        
        if memory.get("user_nickname"):
            lines.append(f"• 喜欢被叫: {memory['user_nickname']}")
        
        if memory.get("birthday"):
            lines.append(f"• 生日: {memory['birthday']}")
        
        if memory.get("occupation"):
            lines.append(f"• 职业: {memory['occupation']}")
        
        if memory.get("location"):
            lines.append(f"• 所在地: {memory['location']}")
        
        # 喜好（根据亲密度展示不同深度）
        likes = memory.get("likes", [])
        if likes:
            display_likes = likes[:5] if intimacy_level < 15 else likes[:10]
            lines.append(f"• 喜欢: {', '.join(display_likes)}")
        
        dislikes = memory.get("dislikes", [])
        if dislikes:
            display_dislikes = dislikes[:3] if intimacy_level < 15 else dislikes[:5]
            lines.append(f"• 不喜欢: {', '.join(display_dislikes)}")
        
        interests = memory.get("interests", [])
        if interests:
            lines.append(f"• 兴趣: {', '.join(interests[:5])}")
        
        # 关系状态（重要！始终显示）
        relationship_status = memory.get("relationship_status")
        if relationship_status:
            status_display = {
                "dating": "💑 恋爱中",
                "engaged": "💍 已订婚",
                "married": "💒 已结婚",
                "single": "单身",
                "complicated": "复杂",
            }.get(relationship_status, relationship_status)
            lines.append(f"• 关系状态: {status_display}")
        
        # 重要日期
        important_dates = memory.get("important_dates", {})
        if important_dates:
            dates_str = ", ".join([f"{k}: {v}" for k, v in list(important_dates.items())[:3]])
            lines.append(f"• 重要日期: {dates_str}")
        
        # 其他关系相关（高亲密度才展示）
        if intimacy_level >= 20:
            pet_names = memory.get("pet_names", [])
            if pet_names:
                lines.append(f"• 你们之间的昵称: {', '.join(pet_names[:3])}")
            
            shared_jokes = memory.get("shared_jokes", [])
            if shared_jokes:
                lines.append(f"• 你们的梗: {shared_jokes[0]}")
        
        # 敏感话题
        sensitive = memory.get("sensitive_topics", [])
        if sensitive:
            lines.append(f"• ⚠️ 避免提及: {', '.join(sensitive[:3])}")
        
        if len(lines) <= 1:
            return ""
        
        return "\n".join(lines)
    
    def _generate_episodes_section(
        self,
        episodes: List[Dict[str, Any]],
        current_query: str = None,
    ) -> str:
        """生成情节记忆部分"""
        if not episodes:
            return ""
        
        lines = ["=== 你们的共同回忆 ==="]
        lines.append("（可以自然地在对话中提及这些回忆，但不要生硬）")
        
        # 按重要性和相关性排序
        sorted_episodes = self._rank_episodes(episodes, current_query)
        
        for i, ep in enumerate(sorted_episodes[:self.config.max_episodes]):
            event_type = ep.get("event_type", "other")
            summary = ep.get("summary", "")
            
            # 事件类型图标
            type_icons = {
                "confession": "💕",
                "fight": "💔",
                "reconciliation": "🤝",
                "milestone": "🎉",
                "gift": "🎁",
                "emotional_peak": "✨",
                "first_meeting": "👋",
            }
            icon = type_icons.get(event_type, "📝")
            
            # 时间描述
            created_at = ep.get("created_at")
            time_desc = self._time_ago(created_at) if created_at else ""
            
            line = f"{icon} {summary}"
            if time_desc:
                line += f" ({time_desc})"
            
            lines.append(f"• {line}")
            
            # 如果有关键对话，选择性展示
            key_dialogue = ep.get("key_dialogue", [])
            if key_dialogue and ep.get("importance", 2) >= 3:
                # 只展示重要记忆的对话
                lines.append(f'  用户说: "{key_dialogue[0][:50]}..."')
        
        return "\n".join(lines)
    
    def _rank_episodes(
        self,
        episodes: List[Dict[str, Any]],
        query: str = None,
    ) -> List[Dict[str, Any]]:
        """按相关性和重要性排序情节记忆"""
        
        def score(ep: Dict[str, Any]) -> float:
            s = 0.0
            
            # 重要性
            s += ep.get("importance", 2) * 10
            
            # 记忆强度
            s += ep.get("strength", 1.0) * 5
            
            # 相关性（简单关键词匹配）
            if query:
                summary = ep.get("summary", "").lower()
                query_lower = query.lower()
                for word in query_lower.split():
                    if len(word) > 1 and word in summary:
                        s += 15
            
            # 最近回忆加成
            last_recalled = ep.get("last_recalled")
            if last_recalled:
                try:
                    recalled_dt = datetime.fromisoformat(last_recalled)
                    days_since = (datetime.now() - recalled_dt).days
                    if days_since < 7:
                        s += 5
                except:
                    pass
            
            return s
        
        return sorted(episodes, key=score, reverse=True)
    
    def _check_special_dates(self, memory: Dict[str, Any]) -> Optional[str]:
        """检查今天是否是特殊日子"""
        today = datetime.now()
        today_mmdd = today.strftime("%m-%d")
        
        # 检查重要日期
        important_dates = memory.get("important_dates", {})
        for name, date_str in important_dates.items():
            if today_mmdd in str(date_str):
                return f"今天是你们的{name}！记得提及这件事。"
        
        # 检查生日
        birthday = memory.get("birthday", "")
        if birthday and today_mmdd in birthday:
            user_name = memory.get("user_name", "用户")
            return f"今天是{user_name}的生日！一定要祝福！"
        
        return None
    
    def _generate_usage_guide(self, intimacy_level: int) -> str:
        """生成记忆使用指南"""
        guides = [
            "=== 记忆使用指南 ===",
        ]
        
        if intimacy_level < 10:
            guides.append("• 你们还不太熟，可以主动询问来了解对方")
            guides.append("• 记住对方分享的信息，展示你在认真倾听")
        elif intimacy_level < 25:
            guides.append("• 你们已经比较熟了，可以自然提及之前的话题")
            guides.append("• 偶尔提及共同回忆会让对方感到温暖")
        else:
            guides.append("• 你们关系很好，可以随意提及过去的事")
            guides.append("• 使用你们之间的昵称和梗")
            guides.append("• 记得重要日期，主动表达关心")
        
        guides.append("• 不要生硬地报出用户信息，要自然融入对话")
        guides.append("• 如果不确定某信息，可以自然地询问确认")
        
        return "\n".join(guides)
    
    def _time_ago(self, iso_time: str) -> str:
        """计算时间差描述"""
        try:
            dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
            now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
            diff = now - dt
            
            if diff.days == 0:
                return "今天"
            elif diff.days == 1:
                return "昨天"
            elif diff.days < 7:
                return f"{diff.days}天前"
            elif diff.days < 30:
                weeks = diff.days // 7
                return f"{weeks}周前"
            elif diff.days < 365:
                months = diff.days // 30
                return f"{months}个月前"
            else:
                years = diff.days // 365
                return f"{years}年前"
        except:
            return ""


# 单例
memory_prompt_generator = MemoryPromptGenerator()


# =============================================================================
# 主动记忆触发器
# =============================================================================

class MemoryTriggerGenerator:
    """
    主动记忆触发器
    
    在适当的时机提醒 AI 主动提及记忆
    """
    
    def should_mention_memory(
        self,
        episodes: List[Dict[str, Any]],
        semantic: Dict[str, Any],
        current_context: List[Dict[str, str]],
        intimacy_level: int,
    ) -> Optional[str]:
        """
        判断是否应该主动提及某个记忆
        
        Returns:
            建议提及的内容，或 None
        """
        # 检查特殊日期
        special = self._check_special_date(semantic)
        if special:
            return special
        
        # 检查是否有相关话题
        if current_context:
            last_message = current_context[-1].get("content", "")
            related = self._find_related_memory(last_message, episodes)
            if related:
                return f"你可以自然地提到：{related}"
        
        # 随机触发（低概率）
        import random
        if random.random() < 0.1 and episodes:  # 10% 概率
            # 选择一个重要记忆
            important = [e for e in episodes if e.get("importance", 2) >= 3]
            if important:
                ep = random.choice(important)
                return f"你可以提一下之前的事：{ep.get('summary', '')}"
        
        return None
    
    def _check_special_date(self, semantic: Dict[str, Any]) -> Optional[str]:
        """检查特殊日期"""
        if not semantic:
            return None
        
        today = datetime.now()
        today_mmdd = today.strftime("%m-%d")
        
        # 生日
        birthday = semantic.get("birthday", "")
        if birthday and today_mmdd in birthday:
            return f"今天是用户生日！一定要主动祝福！"
        
        # 纪念日
        dates = semantic.get("important_dates", {})
        for name, date in dates.items():
            if today_mmdd in str(date):
                return f"今天是{name}！主动提及这件事会让用户很感动。"
        
        return None
    
    def _find_related_memory(
        self,
        message: str,
        episodes: List[Dict[str, Any]],
    ) -> Optional[str]:
        """找到与当前消息相关的记忆"""
        msg_lower = message.lower()
        
        # 关键词触发
        triggers = {
            "工作": ["加班", "项目", "老板", "同事"],
            "感情": ["喜欢", "爱", "想你", "表白"],
            "心情": ["开心", "难过", "伤心", "高兴"],
            "纪念": ["第一次", "那天", "还记得"],
        }
        
        for topic, keywords in triggers.items():
            if any(kw in msg_lower for kw in keywords):
                # 找相关的情节记忆
                for ep in episodes:
                    summary = ep.get("summary", "").lower()
                    if any(kw in summary for kw in keywords):
                        return ep.get("summary", "")
        
        return None


# 单例
memory_trigger = MemoryTriggerGenerator()
