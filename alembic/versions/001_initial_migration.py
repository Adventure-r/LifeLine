"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types
    user_role_enum = postgresql.ENUM('admin', 'group_leader', 'assistant', 'member', name='userrole')
    user_role_enum.create(op.get_bind())
    
    event_type_enum = postgresql.ENUM('lecture', 'seminar', 'lab', 'exam', 'deadline', 'meeting', 'other', name='eventtype')
    event_type_enum.create(op.get_bind())
    
    notification_type_enum = postgresql.ENUM('event_created', 'event_updated', 'deadline_reminder', 'topic_available', 'queue_opened', 'group_invite', name='notificationtype')
    notification_type_enum.create(op.get_bind())
    
    # Create groups table
    op.create_table('groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('leader_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('telegram_id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('role', user_role_enum, nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('notifications_enabled', sa.Boolean(), nullable=False),
        sa.Column('deadline_reminders', sa.Boolean(), nullable=False),
        sa.Column('event_notifications', sa.Boolean(), nullable=False),
        sa.Column('notification_time', sa.String(length=5), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    op.create_index(op.f('ix_users_telegram_id'), 'users', ['telegram_id'], unique=True)
    
    # Add foreign key for group leader
    op.create_foreign_key('fk_groups_leader_id', 'groups', 'users', ['leader_id'], ['id'])
    
    # Create events table
    op.create_table('events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_type', event_type_enum, nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_date', sa.Date(), nullable=True),
        sa.Column('start_time', sa.String(length=5), nullable=True),
        sa.Column('end_time', sa.String(length=5), nullable=True),
        sa.Column('deadline_start', sa.DateTime(), nullable=True),
        sa.Column('deadline_end', sa.DateTime(), nullable=True),
        sa.Column('is_important', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('has_media', sa.Boolean(), nullable=False),
        sa.Column('media_file_id', sa.String(length=255), nullable=True),
        sa.Column('media_type', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_events_group_id', 'events', ['group_id'], unique=False)
    op.create_index('idx_events_event_date', 'events', ['event_date'], unique=False)
    op.create_index('idx_events_deadline_end', 'events', ['deadline_end'], unique=False)
    
    # Create topics table
    op.create_table('topics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('max_selections', sa.Integer(), nullable=False),
        sa.Column('requires_approval', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create queues table
    op.create_table('queues',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('max_participants', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('queue_date', sa.Date(), nullable=True),
        sa.Column('start_time', sa.String(length=5), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create invite_tokens table
    op.create_table('invite_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('uses_count', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )
    op.create_index(op.f('ix_invite_tokens_token'), 'invite_tokens', ['token'], unique=True)
    
    # Create notifications table
    op.create_table('notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notification_type', notification_type_enum, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_sent', sa.Boolean(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('scheduled_for', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('related_event_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('related_topic_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('related_queue_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_notifications_user_id', 'notifications', ['user_id'], unique=False)
    op.create_index('idx_notifications_scheduled_for', 'notifications', ['scheduled_for'], unique=False)
    op.create_index('idx_notifications_is_sent', 'notifications', ['is_sent'], unique=False)
    
    # Create queue_entries table
    op.create_table('queue_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('queue_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['queue_id'], ['queues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_queue_entries_queue_id', 'queue_entries', ['queue_id'], unique=False)
    op.create_index('idx_queue_entries_position', 'queue_entries', ['position'], unique=False)
    
    # Create user_event_views table
    op.create_table('user_event_views',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('viewed_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_event_views_user_id', 'user_event_views', ['user_id'], unique=False)
    op.create_index('idx_user_event_views_event_id', 'user_event_views', ['event_id'], unique=False)
    
    # Create user_topics table (many-to-many relationship)
    op.create_table('user_topics',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('selected_at', sa.DateTime(), nullable=False),
        sa.Column('approved', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'topic_id')
    )
    op.create_index('idx_user_topics_user_id', 'user_topics', ['user_id'], unique=False)
    op.create_index('idx_user_topics_topic_id', 'user_topics', ['topic_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('user_topics')
    op.drop_table('user_event_views')
    op.drop_table('queue_entries')
    op.drop_table('notifications')
    op.drop_table('invite_tokens')
    op.drop_table('queues')
    op.drop_table('topics')
    op.drop_table('events')
    op.drop_table('users')
    op.drop_table('groups')
    
    # Drop ENUM types
    op.execute('DROP TYPE IF EXISTS notificationtype')
    op.execute('DROP TYPE IF EXISTS eventtype')
    op.execute('DROP TYPE IF EXISTS userrole')
