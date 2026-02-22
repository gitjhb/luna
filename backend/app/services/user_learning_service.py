"""
User Learning Service
=====================

Learns and tracks user communication preferences, activity patterns, and topic interests.
Migrated from Mio's user-learning.js to Luna.

Features:
- Analyze user speaking style via LLM
- Track activity patterns (when user is active)
- Build topic interest graph
- Generate style hints for prompt building
- Determine optimal times for proactive messages

Usage:
    from app.services.user_learning_service import user_learning_service
    
    # After each conversation
    await user_learning_service.process_conversation(user_id, messages)
    
    # Get style hints for prompts
    hints = await user_learning_service.generate_style_hints(user_id)
    
    # Check if good time to message
    is_good = await user_learning_service.is_good_time_to_message(user_id)
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from app.core.redis import get_redis
from app.services.llm_service import GrokService, MiniLLMService

logger = logging.getLogger(__name__)

# Time slot definitions
TIME_SLOTS = {
    "morning": [6, 7, 8, 9, 10, 11],
    "afternoon": [12, 13, 14, 15, 16, 17],
    "evening": [18, 19, 20, 21],
    "night": [22, 23, 0, 1, 2, 3, 4, 5],
}

TIME_SLOT_NAMES = {
    "morning": "早上",
    "afternoon": "下午",
    "evening": "晚上",
    "night": "深夜",
}

# Analysis thresholds
MIN_MESSAGES_FOR_ANALYSIS = 5
ANALYSIS_INTERVAL = 50  # Analyze style every N messages
MIN_MESSAGES_FOR_ACTIVITY = 10  # Min messages before activity analysis is reliable


class UserLearningService:
    """
    Service for learning and tracking user preferences.
    
    Uses Redis for fast caching with periodic database persistence.
    Uses LLM for style analysis.
    """
    
    def __init__(self):
        self.mini_llm = MiniLLMService()
        self._cache_ttl = 86400 * 365  # 1 year cache
    
    # =========================================================================
    # Core Data Access (Redis-backed with DB fallback)
    # =========================================================================
    
    async def _get_learning_data(self, user_id: str) -> Optional[Dict]:
        """Get all learning data for a user from Redis cache."""
        redis = await get_redis()
        cache_key = f"user_learning:{user_id}"
        
        data = await redis.get(cache_key)
        if data:
            if isinstance(data, str):
                return json.loads(data)
            return data
        return None
    
    async def _save_learning_data(self, user_id: str, data: Dict) -> None:
        """Save learning data to Redis cache."""
        redis = await get_redis()
        cache_key = f"user_learning:{user_id}"
        
        data["updated_at"] = datetime.utcnow().isoformat()
        
        if isinstance(data, dict):
            await redis.set(cache_key, json.dumps(data), ex=self._cache_ttl)
        else:
            await redis.set(cache_key, data, ex=self._cache_ttl)
    
    # =========================================================================
    # Style Analysis (LLM-based)
    # =========================================================================
    
    async def analyze_user_style(
        self,
        user_id: str,
        messages: List[Dict[str, str]]
    ) -> Optional[Dict]:
        """
        Analyze user's speaking style using LLM.
        
        Args:
            user_id: User ID
            messages: List of messages with 'role' and 'content'
        
        Returns:
            Style analysis dict or None if insufficient data
        """
        # Filter to user messages only
        user_messages = [
            m["content"] for m in messages 
            if m.get("role") == "user" and m.get("content")
        ][-20:]  # Last 20 messages
        
        if len(user_messages) < MIN_MESSAGES_FOR_ANALYSIS:
            return None
        
        try:
            prompt = f"""分析这个用户的说话风格特征。

用户消息样本：
{chr(10).join(f'{i+1}. {m}' for i, m in enumerate(user_messages))}

用 JSON 格式返回分析结果：
{{
  "messageLength": "short|medium|long",
  "emojiUsage": "none|rare|moderate|frequent",
  "tone": "formal|casual|playful|romantic",
  "punctuation": "minimal|normal|expressive",
  "commonPhrases": ["常用词1", "常用词2"],
  "communicationStyle": "direct|indirect|expressive",
  "emotionalExpression": "reserved|moderate|expressive",
  "topicPreferences": ["话题1", "话题2"]
}}

只返回 JSON："""

            response = await self.mini_llm.analyze(
                system_prompt="你是一个用户行为分析专家。分析用户的沟通风格。",
                user_message=prompt,
                temperature=0.3,
                max_tokens=300
            )
            
            # Extract JSON from response
            json_match = response.strip()
            if json_match.startswith("```"):
                # Remove markdown code blocks
                json_match = json_match.split("```")[1]
                if json_match.startswith("json"):
                    json_match = json_match[4:]
            
            # Find JSON object
            start = json_match.find("{")
            end = json_match.rfind("}") + 1
            if start >= 0 and end > start:
                json_match = json_match[start:end]
                return json.loads(json_match)
            
        except json.JSONDecodeError as e:
            logger.warning(f"[UserLearning] Failed to parse style JSON: {e}")
        except Exception as e:
            logger.error(f"[UserLearning] Style analysis error: {e}")
        
        return None
    
    async def update_speaking_style(
        self,
        user_id: str,
        messages: List[Dict[str, str]]
    ) -> Optional[Dict]:
        """
        Update user's speaking style based on new messages.
        
        Merges new analysis with existing data.
        """
        style = await self.analyze_user_style(user_id, messages)
        if not style:
            return None
        
        learning = await self._get_learning_data(user_id) or {}
        old_style = learning.get("speaking_style", {})
        
        # Merge styles
        new_style = {
            **old_style,
            **style,
            "analysis_count": old_style.get("analysis_count", 0) + 1,
            "last_analysis": datetime.utcnow().isoformat(),
        }
        
        # Merge common phrases (deduplicate, keep top 10)
        if style.get("commonPhrases") and old_style.get("commonPhrases"):
            all_phrases = list(set(
                style["commonPhrases"] + old_style.get("commonPhrases", [])
            ))
            new_style["commonPhrases"] = all_phrases[:10]
        
        # Merge topic preferences
        if style.get("topicPreferences") and old_style.get("topicPreferences"):
            all_topics = list(set(
                style["topicPreferences"] + old_style.get("topicPreferences", [])
            ))
            new_style["topicPreferences"] = all_topics[:10]
        
        learning["speaking_style"] = new_style
        await self._save_learning_data(user_id, learning)
        
        logger.info(f"[UserLearning] Updated style for {user_id}: tone={new_style.get('tone')}")
        return new_style
    
    # =========================================================================
    # Activity Pattern Tracking
    # =========================================================================
    
    async def record_activity_time(
        self,
        user_id: str,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record when a user sends a message.
        
        Used to learn their typical active times.
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        learning = await self._get_learning_data(user_id) or {}
        schedule = learning.get("schedule", {
            "hourly_activity": [0] * 24,
            "weekday_activity": [0] * 7,
            "total_messages": 0,
            "last_active": None,
        })
        
        # Update counters
        hour = timestamp.hour
        day = timestamp.weekday()  # 0=Monday, 6=Sunday
        
        hourly = schedule.get("hourly_activity", [0] * 24)
        weekday = schedule.get("weekday_activity", [0] * 7)
        
        # Ensure arrays are correct length
        if len(hourly) != 24:
            hourly = [0] * 24
        if len(weekday) != 7:
            weekday = [0] * 7
        
        hourly[hour] = hourly[hour] + 1
        weekday[day] = weekday[day] + 1
        
        schedule["hourly_activity"] = hourly
        schedule["weekday_activity"] = weekday
        schedule["total_messages"] = schedule.get("total_messages", 0) + 1
        schedule["last_active"] = timestamp.isoformat()
        
        learning["schedule"] = schedule
        await self._save_learning_data(user_id, learning)
    
    async def get_peak_activity_times(self, user_id: str) -> Optional[Dict]:
        """
        Get user's most active time periods.
        
        Returns:
            Dict with peak_hours, preferred_slots, total_messages
        """
        learning = await self._get_learning_data(user_id)
        if not learning or "schedule" not in learning:
            return None
        
        schedule = learning["schedule"]
        hourly = schedule.get("hourly_activity", [0] * 24)
        total = sum(hourly)
        
        if total < MIN_MESSAGES_FOR_ACTIVITY:
            return None
        
        # Find top 3 peak hours
        indexed = [(count, hour) for hour, count in enumerate(hourly)]
        indexed.sort(reverse=True)
        peak_hours = [hour for count, hour in indexed[:3] if count > 0]
        
        # Determine preferred time slots
        preferred_slots = []
        for slot_name, hours in TIME_SLOTS.items():
            if any(h in hours for h in peak_hours):
                preferred_slots.append(slot_name)
        
        return {
            "peak_hours": peak_hours,
            "preferred_slots": preferred_slots,
            "total_messages": total,
        }
    
    # =========================================================================
    # Topic Interest Tracking
    # =========================================================================
    
    async def record_topic_interest(
        self,
        user_id: str,
        topic: str,
        category: Optional[str] = None,
        weight: float = 1.0
    ) -> None:
        """
        Record user's interest in a topic.
        
        Args:
            user_id: User ID
            topic: Topic name
            category: Optional category (entertainment, sports, etc.)
            weight: Weight to add (default 1.0)
        """
        learning = await self._get_learning_data(user_id) or {}
        preferences = learning.get("preferences", {})
        topics = preferences.get("topics", {})
        
        topic_lower = topic.lower().strip()
        if topic_lower not in topics:
            topics[topic_lower] = {
                "score": 0,
                "category": category,
                "count": 0,
                "last_mentioned": None,
            }
        
        topics[topic_lower]["score"] = topics[topic_lower].get("score", 0) + weight
        topics[topic_lower]["count"] = topics[topic_lower].get("count", 0) + 1
        topics[topic_lower]["last_mentioned"] = datetime.utcnow().isoformat()
        if category:
            topics[topic_lower]["category"] = category
        
        preferences["topics"] = topics
        learning["preferences"] = preferences
        await self._save_learning_data(user_id, learning)
    
    async def get_top_interests(
        self,
        user_id: str,
        limit: int = 10,
        category: Optional[str] = None
    ) -> List[Dict]:
        """
        Get user's top interests sorted by score.
        
        Args:
            user_id: User ID
            limit: Max number of interests to return
            category: Filter by category (optional)
        
        Returns:
            List of topic dicts with score, count, category
        """
        learning = await self._get_learning_data(user_id)
        if not learning or "preferences" not in learning:
            return []
        
        topics = learning["preferences"].get("topics", {})
        
        # Convert to list and filter
        interests = []
        for topic, data in topics.items():
            if category and data.get("category") != category:
                continue
            interests.append({
                "topic": topic,
                "score": data.get("score", 0),
                "count": data.get("count", 0),
                "category": data.get("category"),
                "last_mentioned": data.get("last_mentioned"),
            })
        
        # Sort by score descending
        interests.sort(key=lambda x: x["score"], reverse=True)
        return interests[:limit]
    
    # =========================================================================
    # Prompt Integration
    # =========================================================================
    
    async def generate_style_hints(self, user_id: str) -> str:
        """
        Generate style hints for the AI prompt based on learned preferences.
        
        Returns a formatted string to append to system prompts.
        """
        learning = await self._get_learning_data(user_id)
        if not learning:
            return ""
        
        hints = []
        style = learning.get("speaking_style", {})
        
        # Message length
        length = style.get("messageLength")
        if length == "short":
            hints.append("用户喜欢简短消息，回复也简洁些")
        elif length == "long":
            hints.append("用户发消息比较长，可以多聊一点")
        
        # Emoji usage
        emoji = style.get("emojiUsage")
        if emoji == "frequent":
            hints.append("用户喜欢用表情，你也可以多用一些")
        elif emoji in ("none", "rare"):
            hints.append("用户很少用表情，你也不要用太多")
        
        # Tone
        tone = style.get("tone")
        if tone == "playful":
            hints.append("用户喜欢开玩笑，可以更活泼些")
        elif tone == "romantic":
            hints.append("用户比较浪漫，可以甜一点")
        elif tone == "formal":
            hints.append("用户比较正式，保持礼貌得体")
        
        # Common phrases
        phrases = style.get("commonPhrases", [])
        if phrases:
            hints.append(f"用户常用的词：{', '.join(phrases[:5])}")
        
        # Activity patterns
        activity = await self.get_peak_activity_times(user_id)
        if activity and activity.get("preferred_slots"):
            slots = [TIME_SLOT_NAMES.get(s, s) for s in activity["preferred_slots"]]
            hints.append(f"用户通常在{', '.join(slots)}活跃")
        
        # Top interests
        interests = await self.get_top_interests(user_id, limit=3)
        if interests:
            topics = [i["topic"] for i in interests]
            hints.append(f"用户感兴趣的话题：{', '.join(topics)}")
        
        if not hints:
            return ""
        
        return "\n\n## 用户习惯（参考）\n" + "\n".join(f"- {h}" for h in hints)
    
    # =========================================================================
    # Proactive Messaging
    # =========================================================================
    
    async def is_good_time_to_message(self, user_id: str) -> bool:
        """
        Determine if now is a good time to send a proactive message.
        
        Based on user's activity patterns.
        """
        activity = await self.get_peak_activity_times(user_id)
        
        if not activity or activity.get("total_messages", 0) < 20:
            return True  # Not enough data, default to yes
        
        current_hour = datetime.utcnow().hour
        peak_hours = activity.get("peak_hours", [])
        
        # Check if current time is near peak hours (±2 hours)
        for peak in peak_hours:
            diff = abs(current_hour - peak)
            if diff <= 2 or diff >= 22:  # Handle midnight wrap
                return True
        
        # Not peak time, but not late night either
        if 8 <= current_hour <= 22:
            return True
        
        return False
    
    # =========================================================================
    # Main Processing Entry Point
    # =========================================================================
    
    async def process_conversation(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Process a conversation to update learning data.
        
        Call this after each conversation/message exchange.
        
        Args:
            user_id: User ID
            messages: List of messages with 'role' and 'content'
            timestamp: Optional timestamp for activity recording
        """
        # Record activity time
        await self.record_activity_time(user_id, timestamp)
        
        # Check if we need to run style analysis
        learning = await self._get_learning_data(user_id) or {}
        total_messages = learning.get("schedule", {}).get("total_messages", 0)
        last_analysis = learning.get("speaking_style", {}).get("analysis_count", 0)
        
        # Analyze every ANALYSIS_INTERVAL messages
        if total_messages >= (last_analysis + 1) * ANALYSIS_INTERVAL:
            await self.update_speaking_style(user_id, messages)
    
    # =========================================================================
    # Full Profile Access
    # =========================================================================
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get complete learned profile for a user.
        
        Returns all learning data in a structured format.
        """
        learning = await self._get_learning_data(user_id)
        if not learning:
            return {
                "user_id": user_id,
                "has_data": False,
                "style": None,
                "activity": None,
                "interests": [],
            }
        
        activity = await self.get_peak_activity_times(user_id)
        interests = await self.get_top_interests(user_id, limit=10)
        
        return {
            "user_id": user_id,
            "has_data": True,
            "style": learning.get("speaking_style"),
            "activity": activity,
            "interests": interests,
            "schedule": learning.get("schedule"),
            "updated_at": learning.get("updated_at"),
        }
    
    async def apply_feedback(
        self,
        user_id: str,
        feedback_type: str,
        feedback_value: Any
    ) -> bool:
        """
        Apply manual feedback/correction to user learning data.
        
        Args:
            user_id: User ID
            feedback_type: Type of feedback (style_tone, style_length, etc.)
            feedback_value: Value to set
        
        Returns:
            True if successful
        """
        learning = await self._get_learning_data(user_id) or {}
        
        # Map feedback types to data paths
        feedback_map = {
            "style_tone": ("speaking_style", "tone"),
            "style_length": ("speaking_style", "messageLength"),
            "style_emoji": ("speaking_style", "emojiUsage"),
            "style_expression": ("speaking_style", "emotionalExpression"),
        }
        
        if feedback_type not in feedback_map:
            logger.warning(f"[UserLearning] Unknown feedback type: {feedback_type}")
            return False
        
        section, key = feedback_map[feedback_type]
        
        if section not in learning:
            learning[section] = {}
        
        learning[section][key] = feedback_value
        learning[section]["manual_override"] = True
        learning[section]["last_feedback"] = datetime.utcnow().isoformat()
        
        await self._save_learning_data(user_id, learning)
        logger.info(f"[UserLearning] Applied feedback for {user_id}: {feedback_type}={feedback_value}")
        return True
    
    async def clear_user_data(self, user_id: str) -> bool:
        """
        Clear all learning data for a user.
        
        Use with caution - this removes all learned preferences.
        """
        redis = await get_redis()
        cache_key = f"user_learning:{user_id}"
        await redis.delete(cache_key)
        logger.info(f"[UserLearning] Cleared all data for {user_id}")
        return True


# =============================================================================
# Singleton Instance
# =============================================================================

user_learning_service = UserLearningService()
