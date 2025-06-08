"""
Inline keyboards for the bot
"""

from aiogram import types
from typing import List, Optional
from uuid import UUID

from app.database.models import UserRole


def get_groups_keyboard(db) -> types.InlineKeyboardMarkup:
    """Get keyboard with available groups"""
    from app.database.crud import group_crud
    import asyncio
    
    async def _get_groups():
        groups = await group_crud.get_all_active(db)
        return groups
    
    try:
        groups = asyncio.run(_get_groups())
    except:
        groups = []
    
    keyboard = []
    for group in groups:
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"📚 {group.name}",
                callback_data=f"select_group:{group.id}"
            )
        ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirmation_keyboard(group_id: str) -> types.InlineKeyboardMarkup:
    """Get confirmation keyboard for group selection"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"confirm_group:{group_id}"
            ),
            types.InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel_registration"
            )
        ]
    ])


def get_admin_main_keyboard() -> types.InlineKeyboardMarkup:
    """Get admin main menu keyboard"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
            types.InlineKeyboardButton(text="📚 Группы", callback_data="admin_groups")
        ],
        [
            types.InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            types.InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")
        ]
    ])


def get_admin_users_keyboard() -> types.InlineKeyboardMarkup:
    """Get admin users management keyboard"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="admin_search_user")
        ],
        [
            types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")
        ]
    ])


def get_admin_groups_keyboard() -> types.InlineKeyboardMarkup:
    """Get admin groups management keyboard"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="📊 Статистика групп", callback_data="admin_group_stats")
        ],
        [
            types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")
        ]
    ])


def get_user_management_keyboard(user_id: UUID) -> types.InlineKeyboardMarkup:
    """Get user management keyboard for admin"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text="👑 Сделать админом",
                callback_data=f"admin_change_role:{user_id}:admin"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="👥 Сделать старостой",
                callback_data=f"admin_change_role:{user_id}:group_leader"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="👤 Сделать участником",
                callback_data=f"admin_change_role:{user_id}:member"
            )
        ],
        [
            types.InlineKeyboardButton(
                text="🔄 Переключить статус",
                callback_data=f"admin_toggle_user:{user_id}"
            )
        ]
    ])


def get_group_management_keyboard(user_role: UserRole) -> types.InlineKeyboardMarkup:
    """Get group management keyboard"""
    keyboard = [
        [
            types.InlineKeyboardButton(text="👥 Участники", callback_data="group_members")
        ]
    ]
    
    if user_role == UserRole.GROUP_LEADER:
        keyboard.extend([
            [
                types.InlineKeyboardButton(text="👤 Управление участником", callback_data="manage_member")
            ],
            [
                types.InlineKeyboardButton(text="⚙️ Настройки группы", callback_data="group_settings")
            ]
        ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_group_members_keyboard(user_role: UserRole) -> types.InlineKeyboardMarkup:
    """Get group members keyboard"""
    keyboard = []
    
    if user_role == UserRole.GROUP_LEADER:
        keyboard.append([
            types.InlineKeyboardButton(text="👤 Управление участником", callback_data="manage_member")
        ])
    
    keyboard.append([
        types.InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_group_management")
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_member_actions_keyboard(member_id: UUID, member_role: UserRole) -> types.InlineKeyboardMarkup:
    """Get member actions keyboard"""
    keyboard = []
    
    if member_role == UserRole.MEMBER:
        keyboard.append([
            types.InlineKeyboardButton(
                text="🤝 Назначить помощником",
                callback_data=f"member_action:make_assistant:{member_id}"
            )
        ])
    elif member_role == UserRole.ASSISTANT:
        keyboard.append([
            types.InlineKeyboardButton(
                text="👤 Снять с должности помощника",
                callback_data=f"member_action:remove_assistant:{member_id}"
            )
        ])
    
    keyboard.append([
        types.InlineKeyboardButton(
            text="❌ Исключить из группы",
            callback_data=f"member_action:remove_member:{member_id}"
        )
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_invite_settings_keyboard() -> types.InlineKeyboardMarkup:
    """Get invite settings keyboard"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="1 час, 1 исп.", callback_data="invite_settings:1_1"),
            types.InlineKeyboardButton(text="1 час, 5 исп.", callback_data="invite_settings:1_5")
        ],
        [
            types.InlineKeyboardButton(text="24 часа, 10 исп.", callback_data="invite_settings:24_10"),
            types.InlineKeyboardButton(text="24 часа, ∞", callback_data="invite_settings:24_unlimited")
        ],
        [
            types.InlineKeyboardButton(text="7 дней, 20 исп.", callback_data="invite_settings:168_20"),
            types.InlineKeyboardButton(text="7 дней, ∞", callback_data="invite_settings:168_unlimited")
        ]
    ])


def get_events_keyboard(user_role: UserRole, has_events: bool = True) -> types.InlineKeyboardMarkup:
    """Get events keyboard"""
    keyboard = []
    
    if has_events:
        keyboard.extend([
            [
                types.InlineKeyboardButton(text="📋 Все события", callback_data="view_all_events"),
                types.InlineKeyboardButton(text="📅 Предстоящие", callback_data="upcoming_events")
            ]
        ])
    
    if user_role in [UserRole.GROUP_LEADER, UserRole.ASSISTANT]:
        keyboard.append([
            types.InlineKeyboardButton(text="➕ Создать событие", callback_data="create_event")
        ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_event_actions_keyboard(event_id: UUID, user_role: UserRole, is_creator: bool = False) -> types.InlineKeyboardMarkup:
    """Get event actions keyboard"""
    keyboard = []
    
    if user_role in [UserRole.GROUP_LEADER, UserRole.ASSISTANT]:
        if is_creator or user_role == UserRole.GROUP_LEADER:
            keyboard.extend([
                [
                    types.InlineKeyboardButton(
                        text="⭐ Важное",
                        callback_data=f"mark_important:{event_id}"
                    ),
                    types.InlineKeyboardButton(
                        text="✏️ Редактировать",
                        callback_data=f"edit_event:{event_id}"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="❌ Удалить",
                        callback_data=f"delete_event:{event_id}"
                    )
                ]
            ])
    
    keyboard.append([
        types.InlineKeyboardButton(text="✅ Просмотрено", callback_data=f"mark_viewed:{event_id}")
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_event_type_keyboard() -> types.InlineKeyboardMarkup:
    """Get event type selection keyboard"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="📚 Лекция", callback_data="event_type:lecture"),
            types.InlineKeyboardButton(text="💬 Семинар", callback_data="event_type:seminar")
        ],
        [
            types.InlineKeyboardButton(text="🔬 Лабораторная", callback_data="event_type:lab"),
            types.InlineKeyboardButton(text="📝 Экзамен", callback_data="event_type:exam")
        ],
        [
            types.InlineKeyboardButton(text="⏰ Дедлайн", callback_data="event_type:deadline"),
            types.InlineKeyboardButton(text="👥 Собрание", callback_data="event_type:meeting")
        ],
        [
            types.InlineKeyboardButton(text="📌 Другое", callback_data="event_type:other")
        ]
    ])


def get_event_details_keyboard(event_id: UUID, user_role: UserRole, is_creator: bool = False) -> types.InlineKeyboardMarkup:
    """Get event details keyboard"""
    keyboard = []
    
    if user_role in [UserRole.GROUP_LEADER, UserRole.ASSISTANT]:
        if is_creator or user_role == UserRole.GROUP_LEADER:
            keyboard.append([
                types.InlineKeyboardButton(
                    text="⭐ Переключить важность",
                    callback_data=f"mark_important:{event_id}"
                )
            ])
            keyboard.append([
                types.InlineKeyboardButton(
                    text="❌ Удалить событие",
                    callback_data=f"delete_event:{event_id}"
                )
            ])
    
    keyboard.append([
        types.InlineKeyboardButton(text="🔙 К событиям", callback_data="back_to_events")
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_events_filter_keyboard() -> types.InlineKeyboardMarkup:
    """Get events filter keyboard"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="📋 Все события", callback_data="view_all_events"),
            types.InlineKeyboardButton(text="📅 Предстоящие", callback_data="upcoming_events")
        ],
        [
            types.InlineKeyboardButton(text="⭐ Важные", callback_data="important_events"),
            types.InlineKeyboardButton(text="✅ Просмотренные", callback_data="viewed_events")
        ],
        [
            types.InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_events")
        ]
    ])


def get_calendar_keyboard(year: int, month: int) -> types.InlineKeyboardMarkup:
    """Get calendar keyboard"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="📅 Сегодня", callback_data="calendar_today"),
            types.InlineKeyboardButton(text="📋 Неделя", callback_data="calendar_week")
        ],
        [
            types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_calendar:{year}:{month}")
        ]
    ])


def get_calendar_navigation_keyboard(year: int, month: int, event_days: List[int]) -> types.InlineKeyboardMarkup:
    """Get calendar navigation keyboard"""
    keyboard = [
        [
            types.InlineKeyboardButton(text="◀️", callback_data=f"calendar_nav:prev:{year}:{month}"),
            types.InlineKeyboardButton(text="▶️", callback_data=f"calendar_nav:next:{year}:{month}")
        ]
    ]
    
    # Add buttons for days with events
    if event_days:
        day_buttons = []
        for day in sorted(event_days):
            day_buttons.append(
                types.InlineKeyboardButton(
                    text=f"{day}●",
                    callback_data=f"calendar_day:{year}:{month}:{day}"
                )
            )
            
            # Add row every 4 buttons
            if len(day_buttons) == 4:
                keyboard.append(day_buttons)
                day_buttons = []
        
        # Add remaining buttons
        if day_buttons:
            keyboard.append(day_buttons)
    
    keyboard.extend([
        [
            types.InlineKeyboardButton(text="📅 Сегодня", callback_data="calendar_today"),
            types.InlineKeyboardButton(text="📋 Неделя", callback_data="calendar_week")
        ]
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_topics_keyboard(user_role: UserRole, has_topics: bool = True) -> types.InlineKeyboardMarkup:
    """Get topics keyboard"""
    keyboard = []
    
    if has_topics:
        keyboard.extend([
            [
                types.InlineKeyboardButton(text="📝 Выбрать тему", callback_data="select_topic"),
                types.InlineKeyboardButton(text="📚 Мои темы", callback_data="my_topics")
            ]
        ])
    
    if user_role in [UserRole.GROUP_LEADER, UserRole.ASSISTANT]:
        keyboard.append([
            types.InlineKeyboardButton(text="⚙️ Управление темами", callback_data="manage_topics")
        ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_topic_management_keyboard() -> types.InlineKeyboardMarkup:
    """Get topic management keyboard"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="➕ Создать тему", callback_data="create_topic")
        ],
        [
            types.InlineKeyboardButton(text="✅ Одобрить выборы", callback_data="manage_topic_selections")
        ],
        [
            types.InlineKeyboardButton(text="📋 Все темы", callback_data="view_all_topics")
        ]
    ])


def get_topic_actions_keyboard(topic_id: UUID, user_role: UserRole) -> types.InlineKeyboardMarkup:
    """Get topic actions keyboard"""
    keyboard = []
    
    if user_role in [UserRole.GROUP_LEADER, UserRole.ASSISTANT]:
        keyboard.extend([
            [
                types.InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data=f"edit_topic:{topic_id}"
                ),
                types.InlineKeyboardButton(
                    text="❌ Удалить",
                    callback_data=f"delete_topic:{topic_id}"
                )
            ]
        ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_topic_details_keyboard(topic_id: UUID, user_role: UserRole) -> types.InlineKeyboardMarkup:
    """Get topic details keyboard"""
    keyboard = []
    
    if user_role in [UserRole.GROUP_LEADER, UserRole.ASSISTANT]:
        keyboard.append([
            types.InlineKeyboardButton(
                text="👥 Управление выборами",
                callback_data=f"manage_topic_selections:{topic_id}"
            )
        ])
    
    keyboard.append([
        types.InlineKeyboardButton(text="🔙 К темам", callback_data="back_to_topics")
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_queues_keyboard(user_role: UserRole, has_queues: bool = True) -> types.InlineKeyboardMarkup:
    """Get queues keyboard"""
    keyboard = []
    
    if has_queues:
        keyboard.extend([
            [
                types.InlineKeyboardButton(text="🏃‍♂️ Присоединиться", callback_data="join_queue_menu"),
                types.InlineKeyboardButton(text="📋 Мои очереди", callback_data="my_queues")
            ]
        ])
    
    if user_role in [UserRole.GROUP_LEADER, UserRole.ASSISTANT]:
        keyboard.append([
            types.InlineKeyboardButton(text="⚙️ Управление очередями", callback_data="manage_queues")
        ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_queue_management_keyboard() -> types.InlineKeyboardMarkup:
    """Get queue management keyboard"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="➕ Создать очередь", callback_data="create_queue")
        ],
        [
            types.InlineKeyboardButton(text="📋 Все очереди", callback_data="view_all_queues")
        ]
    ])


def get_queue_actions_keyboard(queue_id: UUID, user_role: UserRole) -> types.InlineKeyboardMarkup:
    """Get queue actions keyboard"""
    keyboard = []
    
    if user_role in [UserRole.GROUP_LEADER, UserRole.ASSISTANT]:
        keyboard.extend([
            [
                types.InlineKeyboardButton(
                    text="👥 Управление участниками",
                    callback_data=f"manage_queue_members:{queue_id}"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data=f"edit_queue:{queue_id}"
                ),
                types.InlineKeyboardButton(
                    text="❌ Удалить",
                    callback_data=f"delete_queue:{queue_id}"
                )
            ]
        ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_queue_details_keyboard(queue_id: UUID, user_role: UserRole, user_id: UUID) -> types.InlineKeyboardMarkup:
    """Get queue details keyboard"""
    keyboard = []
    
    # Add leave queue button (will be shown only if user is in queue)
    keyboard.append([
        types.InlineKeyboardButton(
            text="❌ Покинуть очередь",
            callback_data=f"leave_queue:{queue_id}"
        )
    ])
    
    if user_role in [UserRole.GROUP_LEADER, UserRole.ASSISTANT]:
        keyboard.append([
            types.InlineKeyboardButton(
                text="👥 Управление участниками",
                callback_data=f"manage_queue_members:{queue_id}"
            )
        ])
    
    keyboard.append([
        types.InlineKeyboardButton(text="🔙 К очередям", callback_data="back_to_queues")
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_notification_settings_keyboard(user) -> types.InlineKeyboardMarkup:
    """Get notification settings keyboard"""
    notifications_text = "🔕 Выключить" if user.notifications_enabled else "🔔 Включить"
    events_text = "🔕 Выключить события" if user.event_notifications else "🔔 Включить события"
    deadlines_text = "🔕 Выключить дедлайны" if user.deadline_reminders else "🔔 Включить дедлайны"
    
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text=notifications_text, callback_data="toggle_notifications")
        ],
        [
            types.InlineKeyboardButton(text=events_text, callback_data="toggle_event_notifications"),
            types.InlineKeyboardButton(text=deadlines_text, callback_data="toggle_deadline_reminders")
        ],
        [
            types.InlineKeyboardButton(text="🕐 Время уведомлений", callback_data="set_notification_time")
        ],
        [
            types.InlineKeyboardButton(text="📱 История", callback_data="notification_history"),
            types.InlineKeyboardButton(text="🧪 Тест", callback_data="test_notification")
        ],
        [
            types.InlineKeyboardButton(text="🔄 Сбросить", callback_data="reset_settings")
        ]
    ])


def get_time_selection_keyboard() -> types.InlineKeyboardMarkup:
    """Get time selection keyboard"""
    times = ["07:00", "08:00", "09:00", "10:00", "18:00", "19:00", "20:00", "21:00"]
    
    keyboard = []
    for i in range(0, len(times), 2):
        row = []
        for j in range(2):
            if i + j < len(times):
                time_str = times[i + j]
                row.append(
                    types.InlineKeyboardButton(
                        text=time_str,
                        callback_data=f"set_time:{time_str}"
                    )
                )
        keyboard.append(row)
    
    keyboard.append([
        types.InlineKeyboardButton(text="⏰ Свое время", callback_data="custom_time")
    ])
    keyboard.append([
        types.InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_settings")
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)
