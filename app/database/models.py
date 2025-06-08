"""
SQLAlchemy models for the application
"""

from datetime import datetime, date
from typing import Optional, List
from enum import Enum

from sqlalchemy import (
    String, Integer, DateTime, Date, Boolean, Text, 
    ForeignKey, Table, Column, Index, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ENUM
import uuid


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class UserRole(str, Enum):
    """User roles in the system"""
    ADMIN = "admin"
    GROUP_LEADER = "group_leader"
    ASSISTANT = "assistant"
    MEMBER = "member"


class EventType(str, Enum):
    """Event types"""
    LECTURE = "lecture"
    SEMINAR = "seminar"
    LAB = "lab"
    EXAM = "exam"
    DEADLINE = "deadline"
    MEETING = "meeting"
    OTHER = "other"


class NotificationType(str, Enum):
    """Notification types"""
    EVENT_CREATED = "event_created"
    EVENT_UPDATED = "event_updated"
    DEADLINE_REMINDER = "deadline_reminder"
    TOPIC_AVAILABLE = "topic_available"
    QUEUE_OPENED = "queue_opened"
    GROUP_INVITE = "group_invite"


# Association table for many-to-many relationship between users and topics
user_topics = Table(
    'user_topics',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE')),
    Column('topic_id', UUID(as_uuid=True), ForeignKey('topics.id', ondelete='CASCADE')),
    Column('selected_at', DateTime, default=func.now()),
    Column('approved', Boolean, default=False),
    Index('idx_user_topics_user_id', 'user_id'),
    Index('idx_user_topics_topic_id', 'topic_id')
)


class User(Base):
    """User model"""
    __tablename__ = 'users'
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(ENUM(UserRole), default=UserRole.MEMBER)
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('groups.id'), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Notification settings
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    deadline_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    event_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_time: Mapped[Optional[str]] = mapped_column(String(5), default="09:00")  # HH:MM format
    
    # Relationships
    group: Mapped[Optional["Group"]] = relationship("Group", back_populates="members")
    led_groups: Mapped[List["Group"]] = relationship("Group", foreign_keys="Group.leader_id", back_populates="leader")
    created_events: Mapped[List["Event"]] = relationship("Event", back_populates="creator")
    queue_entries: Mapped[List["QueueEntry"]] = relationship("QueueEntry", back_populates="user")
    selected_topics: Mapped[List["Topic"]] = relationship("Topic", secondary=user_topics, back_populates="selected_by")
    viewed_events: Mapped[List["UserEventView"]] = relationship("UserEventView", back_populates="user")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user")
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, full_name='{self.full_name}', role={self.role})>"


class Group(Base):
    """Group model"""
    __tablename__ = 'groups'
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    leader_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    leader: Mapped["User"] = relationship("User", foreign_keys=[leader_id], back_populates="led_groups")
    members: Mapped[List["User"]] = relationship("User", foreign_keys="User.group_id", back_populates="group")
    events: Mapped[List["Event"]] = relationship("Event", back_populates="group")
    topics: Mapped[List["Topic"]] = relationship("Topic", back_populates="group")
    queues: Mapped[List["Queue"]] = relationship("Queue", back_populates="group")
    invite_tokens: Mapped[List["InviteToken"]] = relationship("InviteToken", back_populates="group")
    
    def __repr__(self):
        return f"<Group(name='{self.name}', leader_id={self.leader_id})>"


class Event(Base):
    """Event model"""
    __tablename__ = 'events'
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_type: Mapped[EventType] = mapped_column(ENUM(EventType), default=EventType.OTHER)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('groups.id'), nullable=False)
    creator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Dates and times
    event_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    start_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM format
    end_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM format
    
    # Deadline specific fields
    deadline_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deadline_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Properties
    is_important: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Media
    has_media: Mapped[bool] = mapped_column(Boolean, default=False)
    media_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # photo, video, document
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="events")
    creator: Mapped["User"] = relationship("User", back_populates="created_events")
    viewed_by: Mapped[List["UserEventView"]] = relationship("UserEventView", back_populates="event")
    
    # Indexes
    __table_args__ = (
        Index('idx_events_group_id', 'group_id'),
        Index('idx_events_event_date', 'event_date'),
        Index('idx_events_deadline_end', 'deadline_end'),
    )
    
    def __repr__(self):
        return f"<Event(title='{self.title}', type={self.event_type}, group_id={self.group_id})>"


class UserEventView(Base):
    """Track which events users have viewed"""
    __tablename__ = 'user_event_views'
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    viewed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="viewed_events")
    event: Mapped["Event"] = relationship("Event", back_populates="viewed_by")
    
    __table_args__ = (
        Index('idx_user_event_views_user_id', 'user_id'),
        Index('idx_user_event_views_event_id', 'event_id'),
    )


class Topic(Base):
    """Topic model for class topics selection"""
    __tablename__ = 'topics'
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('groups.id'), nullable=False)
    max_selections: Mapped[int] = mapped_column(Integer, default=1)  # How many people can select this topic
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="topics")
    selected_by: Mapped[List["User"]] = relationship("User", secondary=user_topics, back_populates="selected_topics")
    
    def __repr__(self):
        return f"<Topic(title='{self.title}', group_id={self.group_id})>"


class Queue(Base):
    """Queue model for defense queues"""
    __tablename__ = 'queues'
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('groups.id'), nullable=False)
    max_participants: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    queue_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    start_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM format
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="queues")
    entries: Mapped[List["QueueEntry"]] = relationship("QueueEntry", back_populates="queue", order_by="QueueEntry.position")
    
    def __repr__(self):
        return f"<Queue(title='{self.title}', group_id={self.group_id})>"


class QueueEntry(Base):
    """Individual queue entry"""
    __tablename__ = 'queue_entries'
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    queue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('queues.id', ondelete='CASCADE'), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    queue: Mapped["Queue"] = relationship("Queue", back_populates="entries")
    user: Mapped["User"] = relationship("User", back_populates="queue_entries")
    
    __table_args__ = (
        Index('idx_queue_entries_queue_id', 'queue_id'),
        Index('idx_queue_entries_position', 'position'),
    )
    
    def __repr__(self):
        return f"<QueueEntry(queue_id={self.queue_id}, user_id={self.user_id}, position={self.position})>"


class InviteToken(Base):
    """Invite tokens for group joining"""
    __tablename__ = 'invite_tokens'
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('groups.id'), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uses_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="invite_tokens")
    
    def __repr__(self):
        return f"<InviteToken(token='{self.token[:8]}...', group_id={self.group_id})>"


class Notification(Base):
    """Notification model"""
    __tablename__ = 'notifications'
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(ENUM(NotificationType), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Related object IDs for context
    related_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    related_topic_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    related_queue_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    
    __table_args__ = (
        Index('idx_notifications_user_id', 'user_id'),
        Index('idx_notifications_scheduled_for', 'scheduled_for'),
        Index('idx_notifications_is_sent', 'is_sent'),
    )
    
    def __repr__(self):
        return f"<Notification(type={self.notification_type}, user_id={self.user_id}, is_sent={self.is_sent})>"
