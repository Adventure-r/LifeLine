"""
Notification settings handlers
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger
from datetime import datetime, time

from app.database.database import get_db
from app.database.crud import user_crud, notification_crud
from app.database.models import UserRole
from app.keyboards.inline import get_notification_settings_keyboard, get_time_selection_keyboard
from app.keyboards.reply import get_main_menu_keyboard
from app.utils.decorators import require_auth
from app.states.states import NotificationStates

router = Router()


@router.message(F.text == "⚙️ Настройки")
@require_auth
async def show_settings(message: types.Message, user):
    """Show user settings"""
    try:
        settings_text = f"⚙️ Настройки пользователя\n\n"
        settings_text += f"👤 Имя: {user.full_name}\n"
        settings_text += f"🆔 Telegram ID: {user.telegram_id}\n"
        
        if user.group:
            settings_text += f"📚 Группа: {user.group.name}\n"
        else:
            settings_text += "📚 Группа: не указана\n"
        
        role_names = {
            UserRole.ADMIN: "Администратор",
            UserRole.GROUP_LEADER: "Староста",
            UserRole.ASSISTANT: "Помощник старосты",
            UserRole.MEMBER: "Участник"
        }
        settings_text += f"👑 Роль: {role_names.get(user.role, user.role.value)}\n\n"
        
        settings_text += "📱 Настройки уведомлений:\n"
        settings_text += f"• Уведомления: {'✅ Включены' if user.notifications_enabled else '❌ Отключены'}\n"
        settings_text += f"• О событиях: {'✅ Включены' if user.event_notifications else '❌ Отключены'}\n"
        settings_text += f"• О дедлайнах: {'✅ Включены' if user.deadline_reminders else '❌ Отключены'}\n"
        settings_text += f"• Время уведомлений: {user.notification_time or 'не указано'}\n"
        
        await message.answer(
            settings_text,
            reply_markup=get_notification_settings_keyboard(user)
        )
        
    except Exception as e:
        logger.error(f"Error showing settings: {e}")
        await message.answer("❌ Произошла ошибка при загрузке настроек.")


@router.callback_query(F.data == "toggle_notifications")
@require_auth
async def toggle_notifications(callback: types.CallbackQuery, user):
    """Toggle all notifications"""
    try:
        async for db in get_db():
            new_status = not user.notifications_enabled
            
            await user_crud.update_notification_settings(
                db, 
                user.id, 
                {"notifications_enabled": new_status}
            )
            
            status_text = "включены" if new_status else "отключены"
            await callback.answer(f"✅ Уведомления {status_text}")
            
            # Refresh settings view
            updated_user = await user_crud.get_by_id(db, user.id)
            await refresh_settings_view(callback.message, updated_user)
            
    except Exception as e:
        logger.error(f"Error toggling notifications: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "toggle_event_notifications")
@require_auth
async def toggle_event_notifications(callback: types.CallbackQuery, user):
    """Toggle event notifications"""
    try:
        async for db in get_db():
            new_status = not user.event_notifications
            
            await user_crud.update_notification_settings(
                db, 
                user.id, 
                {"event_notifications": new_status}
            )
            
            status_text = "включены" if new_status else "отключены"
            await callback.answer(f"✅ Уведомления о событиях {status_text}")
            
            # Refresh settings view
            updated_user = await user_crud.get_by_id(db, user.id)
            await refresh_settings_view(callback.message, updated_user)
            
    except Exception as e:
        logger.error(f"Error toggling event notifications: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "toggle_deadline_reminders")
@require_auth
async def toggle_deadline_reminders(callback: types.CallbackQuery, user):
    """Toggle deadline reminders"""
    try:
        async for db in get_db():
            new_status = not user.deadline_reminders
            
            await user_crud.update_notification_settings(
                db, 
                user.id, 
                {"deadline_reminders": new_status}
            )
            
            status_text = "включены" if new_status else "отключены"
            await callback.answer(f"✅ Напоминания о дедлайнах {status_text}")
            
            # Refresh settings view
            updated_user = await user_crud.get_by_id(db, user.id)
            await refresh_settings_view(callback.message, updated_user)
            
    except Exception as e:
        logger.error(f"Error toggling deadline reminders: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "set_notification_time")
@require_auth
async def set_notification_time(callback: types.CallbackQuery, user):
    """Set notification time"""
    await callback.message.edit_text(
        "🕐 Выберите время для ежедневных уведомлений:\n\n"
        "Это время будет использоваться для отправки напоминаний о дедлайнах и важных событиях.",
        reply_markup=get_time_selection_keyboard()
    )


@router.callback_query(F.data.startswith("set_time:"))
@require_auth
async def process_time_selection(callback: types.CallbackQuery, user):
    """Process time selection"""
    try:
        selected_time = callback.data.split(":")[1]
        
        async for db in get_db():
            await user_crud.update_notification_settings(
                db, 
                user.id, 
                {"notification_time": selected_time}
            )
            
            await callback.answer(f"✅ Время уведомлений установлено: {selected_time}")
            
            # Refresh settings view
            updated_user = await user_crud.get_by_id(db, user.id)
            await refresh_settings_view(callback.message, updated_user)
            
    except Exception as e:
        logger.error(f"Error setting notification time: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "custom_time")
@require_auth
async def custom_time_input(callback: types.CallbackQuery, state: FSMContext, user):
    """Start custom time input"""
    await callback.message.edit_text(
        "🕐 Введите время в формате ЧЧ:ММ\n\n"
        "Например: 09:30"
    )
    await state.set_state(NotificationStates.waiting_for_time)


@router.message(NotificationStates.waiting_for_time)
@require_auth
async def process_custom_time(message: types.Message, state: FSMContext, user):
    """Process custom time input"""
    try:
        time_str = message.text.strip()
        
        try:
            # Validate time format
            time_obj = datetime.strptime(time_str, "%H:%M").time()
            
            async for db in get_db():
                await user_crud.update_notification_settings(
                    db, 
                    user.id, 
                    {"notification_time": time_str}
                )
                
                await message.answer(
                    f"✅ Время уведомлений установлено: {time_str}",
                    reply_markup=get_main_menu_keyboard(user.role)
                )
                
                logger.info(f"User {user.full_name} set notification time to {time_str}")
            
        except ValueError:
            await message.answer(
                "❌ Неверный формат времени.\n"
                "Используйте формат ЧЧ:ММ (например: 09:30)"
            )
            return
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error processing custom time: {e}")
        await message.answer("❌ Произошла ошибка.")
        await state.clear()


@router.callback_query(F.data == "notification_history")
@require_auth
async def show_notification_history(callback: types.CallbackQuery, user):
    """Show notification history"""
    try:
        async for db in get_db():
            # Get recent notifications for user
            notifications = await notification_crud.get_user_notifications(
                db, user.id, limit=10
            )
            
            if not notifications:
                await callback.message.edit_text(
                    "📱 История уведомлений пуста.",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_settings")]
                    ])
                )
                return
            
            history_text = "📱 История уведомлений:\n\n"
            
            for notification in notifications:
                sent_date = notification.sent_at or notification.created_at
                date_str = sent_date.strftime("%d.%m.%Y %H:%M")
                
                status = "✅ Отправлено" if notification.is_sent else "⏳ Ожидает"
                
                history_text += f"📅 {date_str}\n"
                history_text += f"📝 {notification.title}\n"
                history_text += f"📊 {status}\n\n"
            
            await callback.message.edit_text(
                history_text,
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_settings")]
                ])
            )
            
    except Exception as e:
        logger.error(f"Error showing notification history: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "test_notification")
@require_auth
async def send_test_notification(callback: types.CallbackQuery, user):
    """Send test notification"""
    try:
        if not user.notifications_enabled:
            await callback.answer("❌ Уведомления отключены. Включите их в настройках.")
            return
        
        from app.services.notification_service import NotificationService
        notification_service = NotificationService()
        
        await notification_service.send_immediate_notification(
            user.telegram_id,
            "🧪 Тестовое уведомление",
            f"Это тестовое уведомление отправлено в {datetime.now().strftime('%H:%M')}.\n\n"
            f"Ваши уведомления работают корректно! ✅"
        )
        
        await callback.answer("✅ Тестовое уведомление отправлено!")
        
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        await callback.answer("❌ Ошибка при отправке тестового уведомления.")


@router.callback_query(F.data == "reset_settings")
@require_auth
async def reset_settings(callback: types.CallbackQuery, user):
    """Reset notification settings to default"""
    await callback.message.edit_text(
        "⚠️ Сброс настроек\n\n"
        "Вы уверены, что хотите сбросить все настройки уведомлений к значениям по умолчанию?\n\n"
        "Будут восстановлены:\n"
        "• Уведомления: включены\n"
        "• О событиях: включены\n"
        "• О дедлайнах: включены\n"
        "• Время: 09:00",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Сбросить", callback_data="confirm_reset"),
                types.InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_settings")
            ]
        ])
    )


@router.callback_query(F.data == "confirm_reset")
@require_auth
async def confirm_reset_settings(callback: types.CallbackQuery, user):
    """Confirm settings reset"""
    try:
        async for db in get_db():
            await user_crud.update_notification_settings(
                db, 
                user.id, 
                {
                    "notifications_enabled": True,
                    "event_notifications": True,
                    "deadline_reminders": True,
                    "notification_time": "09:00"
                }
            )
            
            await callback.answer("✅ Настройки сброшены к значениям по умолчанию")
            
            # Refresh settings view
            updated_user = await user_crud.get_by_id(db, user.id)
            await refresh_settings_view(callback.message, updated_user)
            
            logger.info(f"User {user.full_name} reset notification settings")
            
    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: types.CallbackQuery):
    """Go back to settings menu"""
    from app.handlers.notifications import show_settings
    await show_settings(callback.message, callback.from_user)


async def refresh_settings_view(message: types.Message, user):
    """Refresh settings view with updated data"""
    try:
        settings_text = f"⚙️ Настройки пользователя\n\n"
        settings_text += f"👤 Имя: {user.full_name}\n"
        settings_text += f"🆔 Telegram ID: {user.telegram_id}\n"
        
        if user.group:
            settings_text += f"📚 Группа: {user.group.name}\n"
        else:
            settings_text += "📚 Группа: не указана\n"
        
        role_names = {
            UserRole.ADMIN: "Администратор",
            UserRole.GROUP_LEADER: "Староста",
            UserRole.ASSISTANT: "Помощник старосты",
            UserRole.MEMBER: "Участник"
        }
        settings_text += f"👑 Роль: {role_names.get(user.role, user.role.value)}\n\n"
        
        settings_text += "📱 Настройки уведомлений:\n"
        settings_text += f"• Уведомления: {'✅ Включены' if user.notifications_enabled else '❌ Отключены'}\n"
        settings_text += f"• О событиях: {'✅ Включены' if user.event_notifications else '❌ Отключены'}\n"
        settings_text += f"• О дедлайнах: {'✅ Включены' if user.deadline_reminders else '❌ Отключены'}\n"
        settings_text += f"• Время уведомлений: {user.notification_time or 'не указано'}\n"
        
        await message.edit_text(
            settings_text,
            reply_markup=get_notification_settings_keyboard(user)
        )
        
    except Exception as e:
        logger.error(f"Error refreshing settings view: {e}")


@router.message(Command("settings"))
@require_auth
async def settings_command(message: types.Message, user):
    """Handle /settings command"""
    await show_settings(message, user)
