"""
FSM states for the bot
"""

from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """States for user registration process"""
    waiting_for_name = State()
    waiting_for_name_with_invite = State()
    waiting_for_group = State()
    waiting_for_confirmation = State()


class AdminStates(StatesGroup):
    """States for admin panel operations"""
    searching_user = State()
    creating_broadcast = State()
    waiting_for_broadcast_text = State()
    confirming_broadcast = State()


class GroupStates(StatesGroup):
    """States for group management"""
    waiting_for_group_name = State()
    waiting_for_group_description = State()
    selecting_member = State()
    selecting_setting = State()
    changing_name = State()
    changing_description = State()
    confirming_deletion = State()


class EventStates(StatesGroup):
    """States for event creation and management"""
    waiting_for_title = State()
    waiting_for_type = State()
    waiting_for_description = State()
    waiting_for_date = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()
    waiting_for_deadline = State()
    waiting_for_media = State()
    editing_event = State()


class TopicStates(StatesGroup):
    """States for topic management"""
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_max_selections = State()
    waiting_for_approval_setting = State()
    waiting_for_deadline = State()
    editing_topic = State()
    selecting_topic = State()


class QueueStates(StatesGroup):
    """States for queue management"""
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_max_participants = State()
    waiting_for_date = State()
    waiting_for_start_time = State()
    waiting_for_notes = State()
    editing_queue = State()
    joining_queue = State()


class CalendarStates(StatesGroup):
    """States for calendar operations"""
    selecting_date = State()
    creating_booking = State()
    editing_booking = State()


class NotificationStates(StatesGroup):
    """States for notification settings"""
    waiting_for_time = State()
    configuring_reminders = State()
    setting_custom_schedule = State()


class InviteStates(StatesGroup):
    """States for invite management"""
    creating_invite = State()
    setting_expiration = State()
    setting_max_uses = State()


class SearchStates(StatesGroup):
    """States for search operations"""
    searching_events = State()
    searching_topics = State()
    searching_users = State()
    searching_queues = State()


class FileStates(StatesGroup):
    """States for file operations"""
    uploading_media = State()
    processing_document = State()
    waiting_for_file = State()


class SettingsStates(StatesGroup):
    """States for various settings"""
    updating_profile = State()
    changing_password = State()
    configuring_privacy = State()
    setting_timezone = State()


class ReportStates(StatesGroup):
    """States for reporting and analytics"""
    generating_report = State()
    selecting_period = State()
    choosing_format = State()


class ImportExportStates(StatesGroup):
    """States for import/export operations"""
    importing_data = State()
    exporting_data = State()
    processing_file = State()
    confirming_import = State()
