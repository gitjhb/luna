"""
Story Mode Database Models
==========================

Models for interactive story sessions with branching narratives.
Supports multiple story types: romance, adventure, emotional, etc.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Boolean, Float
from app.models.database.billing_models import Base


class StorySession(Base):
    """
    Story session - tracks a user's progress through an interactive story.
    
    Each session represents one playthrough of a story with:
    - Dynamic LLM-generated scenes
    - User choices that affect the narrative
    - Intimacy rewards based on engagement
    """
    __tablename__ = "story_sessions"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(128), nullable=False, index=True)
    character_id = Column(String(128), nullable=False, index=True)
    
    # Story setup
    story_type = Column(String(50), nullable=False)  # date, adventure, emotional, spicy
    story_title = Column(String(200), nullable=True)
    story_setting = Column(Text, nullable=True)  # Background/scene description
    story_characters = Column(Text, nullable=True)  # Characters involved
    story_style = Column(String(50), default="normal")  # normal, hotter, softer, faster
    story_premise = Column(Text, nullable=True)  # Opening situation
    
    # Progress tracking
    current_segment = Column(Integer, default=0)
    max_segments = Column(Integer, default=10)  # Story ends after this many segments
    
    # Content storage (JSON arrays)
    segments = Column(JSON, default=list)  # List of generated story segments
    choices_made = Column(JSON, default=list)  # List of user choices: {segment_idx, choice, style}
    
    # Status
    status = Column(String(20), default="in_progress", index=True)  # in_progress, completed, abandoned
    ending_type = Column(String(50), nullable=True)  # good_ending, neutral_ending, early_end
    
    # Rewards
    xp_awarded = Column(Integer, default=0)
    intimacy_bonus = Column(Float, default=0.0)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "character_id": self.character_id,
            "story_type": self.story_type,
            "title": self.story_title,
            "setting": self.story_setting,
            "characters": self.story_characters,
            "style": self.story_style,
            "premise": self.story_premise,
            "current_segment": self.current_segment,
            "max_segments": self.max_segments,
            "segments": self.segments or [],
            "choices_made": self.choices_made or [],
            "status": self.status,
            "ending_type": self.ending_type,
            "xp_awarded": self.xp_awarded,
            "intimacy_bonus": self.intimacy_bonus,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class StoryTemplate(Base):
    """
    Predefined story templates for consistent, high-quality narratives.
    
    Templates provide structured story frameworks that the LLM fills in
    with character-specific content.
    """
    __tablename__ = "story_templates"
    
    id = Column(String(36), primary_key=True)
    
    # Template info
    name = Column(String(100), nullable=False)
    name_cn = Column(String(100), nullable=True)  # Chinese name
    story_type = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    description_cn = Column(Text, nullable=True)
    
    # Template content
    setting_prompt = Column(Text, nullable=False)  # Prompt for generating setting
    opening_prompt = Column(Text, nullable=False)  # Prompt for opening scene
    
    # Structure hints (JSON)
    # {key_moments: ["first meeting", "revelation", "climax"], ...}
    structure = Column(JSON, default=dict)
    
    # Metadata
    icon = Column(String(10), default="📖")
    difficulty = Column(String(20), default="normal")  # easy, normal, hard
    estimated_length = Column(Integer, default=10)  # segments
    
    # Requirements
    required_level = Column(Integer, default=1)
    required_stage = Column(String(32), nullable=True)  # intimacy stage
    is_premium = Column(Boolean, default=False)
    
    # Stats
    times_played = Column(Integer, default=0)
    avg_rating = Column(Float, default=0.0)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "name_cn": self.name_cn,
            "story_type": self.story_type,
            "description": self.description,
            "description_cn": self.description_cn,
            "icon": self.icon,
            "difficulty": self.difficulty,
            "estimated_length": self.estimated_length,
            "required_level": self.required_level,
            "required_stage": self.required_stage,
            "is_premium": self.is_premium,
            "times_played": self.times_played,
            "avg_rating": self.avg_rating,
        }
