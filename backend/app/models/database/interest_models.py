"""
User Interests Database Models
==============================

Store user interests/hobbies with predefined interest tags.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.database.billing_models import Base


# Association table for user-interest many-to-many relationship
user_interests = Table(
    'user_interests',
    Base.metadata,
    Column('user_id', String(64), ForeignKey('interest_users.user_id'), primary_key=True),
    Column('interest_id', Integer, ForeignKey('interests.id'), primary_key=True),
    Column('created_at', DateTime, server_default=func.now())
)


class Interest(Base):
    """Predefined interest tags."""
    __tablename__ = "interests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Interest info
    name = Column(String(50), unique=True, nullable=False)  # e.g., "gaming", "music"
    display_name = Column(String(100), nullable=False)  # e.g., "游戏", "音乐"
    icon = Column(String(50), nullable=True)  # Emoji or icon name
    category = Column(String(50), nullable=True)  # e.g., "entertainment", "sports"
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    users = relationship("InterestUser", secondary=user_interests, back_populates="interests")


class InterestUser(Base):
    """User interests tracking (separate from main user to avoid circular imports)."""
    __tablename__ = "interest_users"
    
    user_id = Column(String(64), primary_key=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    interests = relationship("Interest", secondary=user_interests, back_populates="users")
