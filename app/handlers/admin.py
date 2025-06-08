"""
Admin panel handlers
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger

from app.database.database import get_db
from app.database.crud import user_crud, group_crud, event_crud
from app.database.models import UserRole
from app.keyboards.inline import (
    get_admin_main_keyboard, get_admin_users_keyboard, 
    get_admin_groups_keyboard, get_user_management_keyboard
)
from app.utils.decorators import require_role
from app.states.states import AdminStates

router = Router()


@router.message(Command("admin"))
@require_role(UserRole.ADMIN)
async def admin_panel(message: types.Message, user):
    """Show admin panel"""
    await message.answer(
        "🔧 Панель администратора",
        reply_markup=get_admin_main_keyboard()
    )


@router.callback_query(F.data == "admin_users")
@require_role(UserRole.ADMIN)
async def admin_users(callback: types.CallbackQuery, user):
    """Show users management"""
    try:
        async for db in get_db():
            # Get statistics
            all_users = await user_crud.get_all_users(db)
            admins_count = len([u for u in all_users if u.role == UserRole.ADMIN])
            leaders_count = len([u for u in all_users if u.role == UserRole.GROUP_LEADER])
            members_count = len([u for u in all_users if u.role == UserRole.MEMBER])
            
            stats_text = (
                f"👥 Управление пользователями\n\n"
                f"📊 Статистика:\n"
                f"Всего пользователей: {len(all_users)}\n"
                f"Администраторы: {admins_count}\n"
                f"Старосты: {leaders_count}\n"
                f"Участники: {members_count}\n\n"
                f"Выберите действие:"
            )
            
            await callback.message.edit_text(
                stats_text,
                reply_markup=get_admin_users_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error in admin_users: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "admin_groups")
@require_role(UserRole.ADMIN)
async def admin_groups(callback: types.CallbackQuery, user):
    """Show groups management"""
    try:
        async for db in get_db():
            groups = await group_crud.get_all_active(db)
            
            groups_text = f"📚 Управление группами\n\n"
            groups_text += f"Всего активных групп: {len(groups)}\n\n"
            
            if groups:
                groups_text += "Список групп:\n"
                for group in groups[:10]:  # Show first 10 groups
                    member_count = len(group.members) if hasattr(group, 'members') else 0
                    groups_text += f"• {group.name} ({member_count} участников)\n"
                
                if len(groups) > 10:
                    groups_text += f"... и ещё {len(groups) - 10} групп\n"
            
            await callback.message.edit_text(
                groups_text,
                reply_markup=get_admin_groups_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error in admin_groups: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "admin_stats")
@require_role(UserRole.ADMIN)
async def admin_stats(callback: types.CallbackQuery, user):
    """Show system statistics"""
    try:
        async for db in get_db():
            # Gather statistics
            users = await user_crud.get_all_users(db)
            groups = await group_crud.get_all_active(db)
            
            # Count events from last 30 days
            from datetime import datetime, timedelta
            recent_events = []
            for group in groups:
                group_events = await event_crud.get_group_events(db, group.id, limit=100)
                recent_events.extend([
                    e for e in group_events 
                    if e.created_at > datetime.now() - timedelta(days=30)
                ])
            
            stats_text = (
                f"📊 Статистика системы\n\n"
                f"👥 Пользователи: {len(users)}\n"
                f"📚 Активные группы: {len(groups)}\n"
                f"📅 События за месяц: {len(recent_events)}\n\n"
                f"📈 Распределение ролей:\n"
                f"• Администраторы: {len([u for u in users if u.role == UserRole.ADMIN])}\n"
                f"• Старосты: {len([u for u in users if u.role == UserRole.GROUP_LEADER])}\n"
                f"• Помощники: {len([u for u in users if u.role == UserRole.ASSISTANT])}\n"
                f"• Участники: {len([u for u in users if u.role == UserRole.MEMBER])}\n\n"
            )
            
            # Top groups by member count
            groups_with_members = []
            for group in groups:
                member_count = await user_crud.get_group_member_count(db, group.id)
                groups_with_members.append((group, member_count))
            
            groups_with_members.sort(key=lambda x: x[1], reverse=True)
            
            if groups_with_members:
                stats_text += "🏆 Самые большие группы:\n"
                for group, count in groups_with_members[:5]:
                    stats_text += f"• {group.name}: {count} участников\n"
            
            await callback.message.edit_text(
                stats_text,
                reply_markup=get_admin_main_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "admin_search_user")
@require_role(UserRole.ADMIN)
async def admin_search_user(callback: types.CallbackQuery, state: FSMContext, user):
    """Start user search"""
    await callback.message.edit_text(
        "🔍 Поиск пользователя\n\n"
        "Введите имя пользователя или его Telegram ID для поиска:"
    )
    await state.set_state(AdminStates.searching_user)


@router.message(AdminStates.searching_user)
@require_role(UserRole.ADMIN)
async def process_user_search(message: types.Message, state: FSMContext, user):
    """Process user search query"""
    try:
        search_query = message.text.strip()
        
        async for db in get_db():
            found_users = []
            
            # Search by Telegram ID if query is numeric
            if search_query.isdigit():
                user_by_id = await user_crud.get_by_telegram_id(db, int(search_query))
                if user_by_id:
                    found_users.append(user_by_id)
            
            # Search by name
            all_users = await user_crud.get_all_users(db)
            name_matches = [
                u for u in all_users 
                if search_query.lower() in u.full_name.lower()
            ]
            
            # Combine results and remove duplicates
            for u in name_matches:
                if u not in found_users:
                    found_users.append(u)
            
            if not found_users:
                await message.answer(
                    "❌ Пользователи не найдены.\n"
                    "Попробуйте другой запрос или нажмите /admin для возврата в панель."
                )
                await state.clear()
                return
            
            # Show results
            if len(found_users) == 1:
                found_user = found_users[0]
                await show_user_details(message, found_user, db)
            else:
                results_text = f"🔍 Найдено пользователей: {len(found_users)}\n\n"
                for i, u in enumerate(found_users[:10], 1):
                    group_name = u.group.name if u.group else "Без группы"
                    results_text += (
                        f"{i}. {u.full_name}\n"
                        f"   ID: {u.telegram_id}\n"
                        f"   Группа: {group_name}\n"
                        f"   Роль: {u.role.value}\n\n"
                    )
                
                if len(found_users) > 10:
                    results_text += f"... и ещё {len(found_users) - 10} пользователей"
                
                await message.answer(results_text)
            
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error in user search: {e}")
        await message.answer("❌ Произошла ошибка при поиске.")
        await state.clear()


async def show_user_details(message: types.Message, target_user, db):
    """Show detailed user information"""
    try:
        group_info = target_user.group.name if target_user.group else "Не указана"
        
        role_names = {
            UserRole.ADMIN: "Администратор",
            UserRole.GROUP_LEADER: "Староста",
            UserRole.ASSISTANT: "Помощник старосты",
            UserRole.MEMBER: "Участник"
        }
        
        details_text = (
            f"👤 Информация о пользователе\n\n"
            f"Имя: {target_user.full_name}\n"
            f"Username: @{target_user.username or 'не указан'}\n"
            f"Telegram ID: {target_user.telegram_id}\n"
            f"Роль: {role_names.get(target_user.role, target_user.role.value)}\n"
            f"Группа: {group_info}\n"
            f"Активен: {'Да' if target_user.is_active else 'Нет'}\n"
            f"Регистрация: {target_user.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Настройки уведомлений:\n"
            f"• Включены: {'Да' if target_user.notifications_enabled else 'Нет'}\n"
            f"• О событиях: {'Да' if target_user.event_notifications else 'Нет'}\n"
            f"• О дедлайнах: {'Да' if target_user.deadline_reminders else 'Нет'}\n"
            f"• Время: {target_user.notification_time or 'не указано'}"
        )
        
        # Get user management keyboard
        keyboard = get_user_management_keyboard(target_user.id)
        
        await message.answer(details_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing user details: {e}")
        await message.answer("❌ Произошла ошибка при получении информации о пользователе.")


@router.callback_query(F.data.startswith("admin_change_role:"))
@require_role(UserRole.ADMIN)
async def admin_change_role(callback: types.CallbackQuery, user):
    """Change user role"""
    try:
        user_id, new_role = callback.data.split(":")[1], callback.data.split(":")[2]
        
        async for db in get_db():
            target_user = await user_crud.get_by_id(db, user_id)
            if not target_user:
                await callback.answer("❌ Пользователь не найден.")
                return
            
            # Update role
            await user_crud.update_role(db, user_id, UserRole(new_role))
            
            role_names = {
                UserRole.ADMIN: "Администратор",
                UserRole.GROUP_LEADER: "Староста", 
                UserRole.ASSISTANT: "Помощник старосты",
                UserRole.MEMBER: "Участник"
            }
            
            await callback.message.edit_text(
                f"✅ Роль пользователя {target_user.full_name} "
                f"изменена на «{role_names.get(UserRole(new_role), new_role)}»"
            )
            
            logger.info(f"Admin {user.full_name} changed role of {target_user.full_name} to {new_role}")
            
    except Exception as e:
        logger.error(f"Error changing user role: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data.startswith("admin_toggle_user:"))
@require_role(UserRole.ADMIN)
async def admin_toggle_user(callback: types.CallbackQuery, user):
    """Toggle user active status"""
    try:
        user_id = callback.data.split(":")[1]
        
        async for db in get_db():
            target_user = await user_crud.get_by_id(db, user_id)
            if not target_user:
                await callback.answer("❌ Пользователь не найден.")
                return
            
            # Toggle active status
            new_status = not target_user.is_active
            await user_crud.update(db, user_id, is_active=new_status)
            
            status_text = "активирован" if new_status else "деактивирован"
            
            await callback.message.edit_text(
                f"✅ Пользователь {target_user.full_name} {status_text}"
            )
            
            logger.info(f"Admin {user.full_name} {'activated' if new_status else 'deactivated'} {target_user.full_name}")
            
    except Exception as e:
        logger.error(f"Error toggling user status: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "admin_broadcast")
@require_role(UserRole.ADMIN)
async def admin_broadcast(callback: types.CallbackQuery, state: FSMContext, user):
    """Start broadcast message creation"""
    await callback.message.edit_text(
        "📢 Рассылка сообщения\n\n"
        "Введите текст сообщения для рассылки всем пользователям:\n\n"
        "⚠️ Сообщение будет отправлено всем активным пользователям системы!"
    )
    await state.set_state(AdminStates.creating_broadcast)


@router.message(AdminStates.creating_broadcast)
@require_role(UserRole.ADMIN)
async def process_broadcast(message: types.Message, state: FSMContext, user):
    """Process and send broadcast message"""
    try:
        broadcast_text = message.text.strip()
        
        if len(broadcast_text) < 10:
            await message.answer(
                "❌ Сообщение слишком короткое. Минимум 10 символов."
            )
            return
        
        async for db in get_db():
            # Get all active users
            all_users = await user_crud.get_all_users(db)
            active_users = [u for u in all_users if u.is_active and u.notifications_enabled]
            
            # Send confirmation
            await message.answer(
                f"📢 Подтверждение рассылки\n\n"
                f"Текст сообщения:\n{broadcast_text}\n\n"
                f"Получатели: {len(active_users)} активных пользователей\n\n"
                f"Отправить рассылку?",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                    [
                        types.InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_broadcast"),
                        types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")
                    ]
                ])
            )
            
            # Save broadcast data to state
            await state.update_data(
                broadcast_text=broadcast_text,
                recipient_count=len(active_users)
            )
            
    except Exception as e:
        logger.error(f"Error processing broadcast: {e}")
        await message.answer("❌ Произошла ошибка при подготовке рассылки.")
        await state.clear()


@router.callback_query(F.data == "confirm_broadcast")
@require_role(UserRole.ADMIN)
async def confirm_broadcast(callback: types.CallbackQuery, state: FSMContext, user):
    """Confirm and send broadcast"""
    try:
        data = await state.get_data()
        broadcast_text = data.get('broadcast_text')
        
        if not broadcast_text:
            await callback.answer("❌ Ошибка: текст сообщения не найден.")
            await state.clear()
            return
        
        await callback.message.edit_text("📤 Отправка рассылки...")
        
        async for db in get_db():
            from app.services.notification_service import NotificationService
            notification_service = NotificationService()
            
            # Get all active users
            all_users = await user_crud.get_all_users(db)
            active_users = [u for u in all_users if u.is_active and u.notifications_enabled]
            
            # Send to all users
            sent_count = 0
            failed_count = 0
            
            for target_user in active_users:
                try:
                    await notification_service.send_immediate_notification(
                        target_user.telegram_id,
                        "📢 Системное сообщение",
                        f"{broadcast_text}\n\n👤 От: Администрация"
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send broadcast to {target_user.telegram_id}: {e}")
                    failed_count += 1
            
            result_text = (
                f"✅ Рассылка завершена!\n\n"
                f"Отправлено: {sent_count} сообщений\n"
                f"Ошибок: {failed_count}\n"
                f"Всего получателей: {len(active_users)}"
            )
            
            await callback.message.edit_text(result_text)
            
            logger.info(f"Admin {user.full_name} sent broadcast to {sent_count} users")
            
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error sending broadcast: {e}")
        await callback.answer("❌ Произошла ошибка при отправке рассылки.")
        await state.clear()


@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: types.CallbackQuery, state: FSMContext):
    """Cancel broadcast"""
    await callback.message.edit_text("❌ Рассылка отменена.")
    await state.clear()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    """Go back to admin main menu"""
    await callback.message.edit_text(
        "🔧 Панель администратора",
        reply_markup=get_admin_main_keyboard()
    )
