"""
Reply keyboards for the bot
"""

from aiogram import types
from app.database.models import UserRole


def get_main_menu_keyboard(role: UserRole) -> types.ReplyKeyboardMarkup:
    """
    Get main menu keyboard based on user role
    """
    keyboard = []
    
    # Common buttons for all users
    keyboard.extend([
        [types.KeyboardButton(text="📅 События")],
        [types.KeyboardButton(text="📚 Выбрать тему"), types.KeyboardButton(text="🏃‍♂️ Очередь на защиту")],
        [types.KeyboardButton(text="📋 Календарь")]
    ])
    
    # Additional buttons for group leaders and assistants
    if role in [UserRole.GROUP_LEADER, UserRole.ASSISTANT]:
        keyboard.extend([
            [types.KeyboardButton(text="➕ Создать событие")],
            [types.KeyboardButton(text="👥 Управление группой"), types.KeyboardButton(text="📚 Темы занятий")],
            [types.KeyboardButton(text="🏃‍♂️ Очереди")]
        ])
    
    # Additional buttons for group leaders only
    if role == UserRole.GROUP_LEADER:
        keyboard.append([types.KeyboardButton(text="🔗 Пригласить")])
    
    # Additional buttons for admins
    if role == UserRole.ADMIN:
        keyboard.extend([
            [types.KeyboardButton(text="🔧 Админ панель")],
            [types.KeyboardButton(text="➕ Создать событие")],
            [types.KeyboardButton(text="👥 Управление группой"), types.KeyboardButton(text="📚 Темы занятий")],
            [types.KeyboardButton(text="🏃‍♂️ Очереди"), types.KeyboardButton(text="🔗 Пригласить")]
        ])
    
    # Common bottom buttons
    keyboard.extend([
        [types.KeyboardButton(text="⚙️ Настройки"), types.KeyboardButton(text="❓ Помощь")]
    ])
    
    return types.ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def remove_keyboard() -> types.ReplyKeyboardRemove:
    """
    Remove reply keyboard
    """
    return types.ReplyKeyboardRemove()


def get_yes_no_keyboard() -> types.ReplyKeyboardMarkup:
    """
    Get simple yes/no keyboard
    """
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="✅ Да"), types.KeyboardButton(text="❌ Нет")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_skip_keyboard() -> types.ReplyKeyboardMarkup:
    """
    Get keyboard with skip button
    """
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="⏭️ Пропустить")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_cancel_keyboard() -> types.ReplyKeyboardMarkup:
    """
    Get keyboard with cancel button
    """
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_back_keyboard() -> types.ReplyKeyboardMarkup:
    """
    Get keyboard with back button
    """
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
