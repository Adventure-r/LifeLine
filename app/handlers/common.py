"""
Common handlers for basic bot commands
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from loguru import logger

from app.database.database import get_db
from app.database.crud import user_crud
from app.database.models import UserRole
from app.keyboards.reply import get_main_menu_keyboard
from app.utils.decorators import require_auth

router = Router()


@router.message(Command("help"))
async def help_command(message: types.Message):
    """
    Show help information
    """
    help_text = """
🤖 Бот для управления студенческими группами

📋 Основные команды:
/start - Начать работу с ботом
/help - Показать эту справку
/whoami - Информация о вашем профиле
/settings - Настройки уведомлений

👥 Для участников:
• 📅 События - Просмотр событий группы
• 📚 Выбрать тему - Выбор темы для занятий
• 🏃‍♂️ Очередь на защиту - Присоединение к очередям
• 📋 Календарь - Календарь событий
• ⚙️ Настройки - Настройки профиля

👑 Для старост и помощников:
• ➕ Создать событие - Создание новых событий
• 👥 Управление группой - Управление участниками
• 📚 Темы занятий - Управление темами
• 🏃‍♂️ Очереди - Управление очередями
• 🔗 Пригласить (/invite) - Создание ссылок-приглашений

🔧 Для администраторов:
/admin - Панель администратора
/admin_login <код> - Вход как администратор

💡 Советы:
• Используйте кнопки меню для навигации
• Настройте уведомления в разделе "Настройки"
• Обращайтесь к старосте группы за помощью

📞 Поддержка: обратитесь к администратору бота
    """
    
    await message.answer(help_text)


@router.message(Command("about"))
async def about_command(message: types.Message):
    """
    Show information about the bot
    """
    about_text = """
🤖 Telegram Bot для управления студенческими группами

📌 Версия: 1.0.0
🔧 Технологии: Python, aiogram 3.13.1, PostgreSQL, Redis
⚡ Возможности:
• Система ролей и авторизация
• Управление событиями и дедлайнами
• Календарь и бронирование
• Выбор тем занятий
• Очереди на защиту проектов
• Система уведомлений
• Приглашения в группы

👨‍💻 Разработано для упрощения организации учебного процесса
    """
    
    await message.answer(about_text)


@router.message(Command("stats"))
@require_auth
async def stats_command(message: types.Message, user):
    """
    Show user statistics
    """
    try:
        async for db in get_db():
            # Get user statistics
            stats_text = f"📊 Ваша статистика\n\n"
            stats_text += f"👤 Имя: {user.full_name}\n"
            
            if user.group:
                stats_text += f"📚 Группа: {user.group.name}\n"
                
                # Get group statistics
                from app.database.crud import event_crud, topic_crud, queue_crud
                
                events = await event_crud.get_group_events(db, user.group_id, limit=100)
                topics = await topic_crud.get_group_topics(db, user.group_id)
                queues = await queue_crud.get_group_queues(db, user.group_id)
                
                stats_text += f"📅 События в группе: {len(events)}\n"
                stats_text += f"📚 Доступные темы: {len(topics)}\n"
                stats_text += f"🏃‍♂️ Активные очереди: {len(queues)}\n\n"
                
                # User-specific stats
                user_with_topics = await user_crud.get_by_id(db, user.id)
                selected_topics = len(user_with_topics.selected_topics)
                
                stats_text += f"📝 Выбрано тем: {selected_topics}\n"
                
                # Count user's queue entries
                user_entries = []
                for queue in queues:
                    for entry in queue.entries:
                        if entry.user_id == user.id:
                            user_entries.append(entry)
                
                stats_text += f"🏃‍♂️ Участие в очередях: {len(user_entries)}\n"
                
                # Registration date
                reg_date = user.created_at.strftime("%d.%m.%Y")
                stats_text += f"📅 Регистрация: {reg_date}\n"
            else:
                stats_text += "📚 Группа: не указана\n"
            
            await message.answer(stats_text)
            
    except Exception as e:
        logger.error(f"Error showing user stats: {e}")
        await message.answer("❌ Произошла ошибка при загрузке статистики.")


@router.message(Command("menu"))
@require_auth
async def menu_command(message: types.Message, user):
    """
    Show main menu
    """
    await message.answer(
        "📱 Главное меню",
        reply_markup=get_main_menu_keyboard(user.role)
    )


@router.message(F.text == "📱 Главное меню")
@require_auth
async def main_menu_button(message: types.Message, user):
    """
    Handle main menu button
    """
    welcome_text = f"👋 Добро пожаловать, {user.full_name}!\n\n"
    
    if user.group:
        welcome_text += f"📚 Ваша группа: {user.group.name}\n"
    else:
        welcome_text += "📚 Вы не состоите ни в одной группе\n"
    
    role_names = {
        UserRole.ADMIN: "🔧 Администратор",
        UserRole.GROUP_LEADER: "👑 Староста группы",
        UserRole.ASSISTANT: "🤝 Помощник старосты",
        UserRole.MEMBER: "👤 Участник"
    }
    
    welcome_text += f"👑 Роль: {role_names.get(user.role, user.role.value)}\n\n"
    welcome_text += "Выберите действие из меню ниже:"
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(user.role)
    )


@router.message(F.text.in_(["❓ Помощь", "📞 Поддержка"]))
async def help_button(message: types.Message):
    """
    Handle help button
    """
    await help_command(message)


@router.message()
async def unknown_message(message: types.Message):
    """
    Handle unknown messages
    """
    # Check if user is authenticated
    try:
        async for db in get_db():
            user = await user_crud.get_by_telegram_id(db, message.from_user.id)
            
            if not user:
                await message.answer(
                    "👋 Привет! Я бот для управления студенческими группами.\n\n"
                    "Для начала работы выполните команду /start"
                )
                return
            
            # User is authenticated but sent unknown command
            await message.answer(
                "❓ Команда не распознана.\n\n"
                "Используйте кнопки меню или команду /help для справки.",
                reply_markup=get_main_menu_keyboard(user.role)
            )
            
    except Exception as e:
        logger.error(f"Error handling unknown message: {e}")
        await message.answer(
            "❓ Команда не распознана. Используйте /help для справки."
        )


@router.callback_query(F.data == "close")
async def close_message(callback: types.CallbackQuery):
    """
    Close inline message
    """
    await callback.message.delete()


@router.callback_query()
async def unknown_callback(callback: types.CallbackQuery):
    """
    Handle unknown callback queries
    """
    await callback.answer("❓ Неизвестное действие.")
    logger.warning(f"Unknown callback data: {callback.data}")
