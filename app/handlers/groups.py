"""
Group management handlers
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger
from datetime import datetime, timedelta

from app.database.database import get_db
from app.database.crud import user_crud, group_crud, invite_token_crud
from app.database.models import UserRole
from app.keyboards.inline import (
    get_group_management_keyboard, get_group_members_keyboard,
    get_member_actions_keyboard, get_invite_settings_keyboard
)
from app.keyboards.reply import get_main_menu_keyboard
from app.utils.decorators import require_role, require_auth
from app.states.states import GroupStates
from app.services.auth_service import AuthService

router = Router()


@router.message(Command("create_group"))
@require_auth
async def create_group_command(message: types.Message, state: FSMContext, user):
    """Start group creation process"""
    if user.role not in [UserRole.ADMIN, UserRole.GROUP_LEADER]:
        await message.answer(
            "❌ У вас нет прав для создания группы.\n"
            "Обратитесь к администратору."
        )
        return
    
    await message.answer(
        "📚 Создание новой группы\n\n"
        "Введите название группы:"
    )
    await state.set_state(GroupStates.waiting_for_group_name)


@router.message(GroupStates.waiting_for_group_name)
@require_auth
async def process_group_name(message: types.Message, state: FSMContext, user):
    """Process group name"""
    try:
        group_name = message.text.strip()
        
        if len(group_name) < 3:
            await message.answer(
                "❌ Название группы должно содержать минимум 3 символа."
            )
            return
        
        if len(group_name) > 100:
            await message.answer(
                "❌ Название группы слишком длинное (максимум 100 символов)."
            )
            return
        
        await state.update_data(group_name=group_name)
        
        await message.answer(
            f"📝 Название группы: {group_name}\n\n"
            "Теперь введите описание группы (или отправьте /skip для пропуска):"
        )
        await state.set_state(GroupStates.waiting_for_group_description)
        
    except Exception as e:
        logger.error(f"Error processing group name: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")


@router.message(GroupStates.waiting_for_group_description)
@require_auth
async def process_group_description(message: types.Message, state: FSMContext, user):
    """Process group description"""
    try:
        data = await state.get_data()
        group_name = data.get('group_name')
        
        description = None
        if message.text.strip() != "/skip":
            description = message.text.strip()
            if len(description) > 500:
                await message.answer(
                    "❌ Описание слишком длинное (максимум 500 символов)."
                )
                return
        
        async for db in get_db():
            # Create group
            group = await group_crud.create_group(
                db,
                name=group_name,
                leader_id=user.id,
                description=description
            )
            
            # Update user role and group
            await user_crud.update(
                db, 
                user.id, 
                role=UserRole.GROUP_LEADER,
                group_id=group.id
            )
            
            success_text = (
                f"✅ Группа «{group_name}» успешно создана!\n\n"
                f"Вы назначены старостой группы.\n"
                f"ID группы: {group.id}\n\n"
                f"Теперь вы можете:\n"
                f"• Приглашать участников (/invite)\n"
                f"• Создавать события\n"
                f"• Управлять группой"
            )
            
            await message.answer(
                success_text,
                reply_markup=get_main_menu_keyboard(UserRole.GROUP_LEADER)
            )
            
            logger.info(f"User {user.full_name} created group '{group_name}'")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error creating group: {e}")
        await message.answer("❌ Произошла ошибка при создании группы.")
        await state.clear()


@router.message(F.text == "👥 Управление группой")
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def manage_group(message: types.Message, user):
    """Show group management menu"""
    if not user.group:
        await message.answer("❌ Вы не состоите ни в одной группе.")
        return
    
    async for db in get_db():
        group = await group_crud.get_with_members(db, user.group_id)
        if not group:
            await message.answer("❌ Группа не найдена.")
            return
        
        member_count = len(group.members)
        
        info_text = (
            f"👥 Управление группой «{group.name}»\n\n"
            f"📊 Информация:\n"
            f"• Участников: {member_count}\n"
            f"• Староста: {group.leader.full_name}\n"
        )
        
        if group.description:
            info_text += f"• Описание: {group.description}\n"
        
        info_text += "\nВыберите действие:"
        
        await message.answer(
            info_text,
            reply_markup=get_group_management_keyboard(user.role)
        )


@router.callback_query(F.data == "group_members")
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def show_group_members(callback: types.CallbackQuery, user):
    """Show group members"""
    try:
        if not user.group:
            await callback.answer("❌ Вы не состоите ни в одной группе.")
            return
        
        async for db in get_db():
            members = await user_crud.get_users_by_group(db, user.group_id)
            
            if not members:
                await callback.message.edit_text(
                    "👥 В группе пока нет участников."
                )
                return
            
            members_text = f"👥 Участники группы ({len(members)}):\n\n"
            
            # Group members by role
            leaders = [m for m in members if m.role == UserRole.GROUP_LEADER]
            assistants = [m for m in members if m.role == UserRole.ASSISTANT]
            regular_members = [m for m in members if m.role == UserRole.MEMBER]
            
            if leaders:
                members_text += "👑 Старосты:\n"
                for member in leaders:
                    members_text += f"• {member.full_name}"
                    if member.username:
                        members_text += f" (@{member.username})"
                    members_text += "\n"
                members_text += "\n"
            
            if assistants:
                members_text += "🤝 Помощники:\n"
                for member in assistants:
                    members_text += f"• {member.full_name}"
                    if member.username:
                        members_text += f" (@{member.username})"
                    members_text += "\n"
                members_text += "\n"
            
            if regular_members:
                members_text += "👤 Участники:\n"
                for member in regular_members:
                    members_text += f"• {member.full_name}"
                    if member.username:
                        members_text += f" (@{member.username})"
                    members_text += "\n"
            
            await callback.message.edit_text(
                members_text,
                reply_markup=get_group_members_keyboard(user.role)
            )
            
    except Exception as e:
        logger.error(f"Error showing group members: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "manage_member")
@require_role(UserRole.GROUP_LEADER)
async def manage_member_start(callback: types.CallbackQuery, state: FSMContext, user):
    """Start member management"""
    await callback.message.edit_text(
        "👤 Управление участником\n\n"
        "Введите имя или username участника для управления:"
    )
    await state.set_state(GroupStates.selecting_member)


@router.message(GroupStates.selecting_member)
@require_role(UserRole.GROUP_LEADER)
async def select_member_to_manage(message: types.Message, state: FSMContext, user):
    """Select member to manage"""
    try:
        search_query = message.text.strip().lower()
        
        async for db in get_db():
            members = await user_crud.get_users_by_group(db, user.group_id)
            
            # Search for member
            found_members = []
            for member in members:
                if (search_query in member.full_name.lower() or 
                    (member.username and search_query in member.username.lower())):
                    found_members.append(member)
            
            if not found_members:
                await message.answer(
                    "❌ Участник не найден.\n"
                    "Попробуйте другое имя или username."
                )
                return
            
            if len(found_members) > 1:
                results_text = f"Найдено несколько участников:\n\n"
                for i, member in enumerate(found_members, 1):
                    results_text += f"{i}. {member.full_name}"
                    if member.username:
                        results_text += f" (@{member.username})"
                    results_text += f" - {member.role.value}\n"
                
                results_text += "\nУточните запрос."
                await message.answer(results_text)
                return
            
            # Found exactly one member
            member = found_members[0]
            
            if member.id == user.id:
                await message.answer("❌ Вы не можете управлять самим собой.")
                await state.clear()
                return
            
            member_info = (
                f"👤 Участник: {member.full_name}\n"
                f"Username: @{member.username or 'не указан'}\n"
                f"Роль: {member.role.value}\n"
                f"Активен: {'Да' if member.is_active else 'Нет'}\n\n"
                f"Выберите действие:"
            )
            
            await message.answer(
                member_info,
                reply_markup=get_member_actions_keyboard(member.id, member.role)
            )
            
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error selecting member: {e}")
        await message.answer("❌ Произошла ошибка.")
        await state.clear()


@router.callback_query(F.data.startswith("member_action:"))
@require_role(UserRole.GROUP_LEADER)
async def handle_member_action(callback: types.CallbackQuery, user):
    """Handle member management actions"""
    try:
        action, member_id = callback.data.split(":")[1], callback.data.split(":")[2]
        
        async for db in get_db():
            member = await user_crud.get_by_id(db, member_id)
            if not member or member.group_id != user.group_id:
                await callback.answer("❌ Участник не найден.")
                return
            
            if action == "make_assistant":
                await user_crud.update_role(db, member_id, UserRole.ASSISTANT)
                await callback.message.edit_text(
                    f"✅ {member.full_name} назначен помощником старосты."
                )
                
            elif action == "remove_assistant":
                await user_crud.update_role(db, member_id, UserRole.MEMBER)
                await callback.message.edit_text(
                    f"✅ {member.full_name} больше не является помощником старосты."
                )
                
            elif action == "remove_member":
                await user_crud.update(db, member_id, group_id=None, role=UserRole.MEMBER)
                await callback.message.edit_text(
                    f"✅ {member.full_name} исключен из группы."
                )
                
                # Notify removed member
                try:
                    from app.services.notification_service import NotificationService
                    notification_service = NotificationService()
                    await notification_service.send_immediate_notification(
                        member.telegram_id,
                        "⚠️ Исключение из группы",
                        f"Вы были исключены из группы «{user.group.name}» старостой."
                    )
                except Exception as e:
                    logger.error(f"Error notifying removed member: {e}")
            
            logger.info(f"Group leader {user.full_name} performed action {action} on {member.full_name}")
            
    except Exception as e:
        logger.error(f"Error handling member action: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.message(Command("invite"))
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def create_invite(message: types.Message, user):
    """Create invite link for group"""
    if not user.group:
        await message.answer("❌ Вы не состоите ни в одной группе.")
        return
    
    await message.answer(
        "🔗 Создание ссылки-приглашения\n\n"
        "Выберите настройки приглашения:",
        reply_markup=get_invite_settings_keyboard()
    )


@router.callback_query(F.data.startswith("invite_settings:"))
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_invite_settings(callback: types.CallbackQuery, user):
    """Process invite settings"""
    try:
        settings = callback.data.split(":")[1]
        
        # Parse settings: format is "duration_uses" (e.g., "24_5" means 24 hours, 5 uses)
        parts = settings.split("_")
        duration_hours = int(parts[0])
        max_uses = int(parts[1]) if parts[1] != "unlimited" else None
        
        async for db in get_db():
            # Generate unique token
            token = AuthService.generate_invite_token()
            expires_at = datetime.now() + timedelta(hours=duration_hours)
            
            # Create invite
            invite = await invite_token_crud.create_invite(
                db,
                group_id=user.group_id,
                created_by=user.id,
                token=token,
                expires_at=expires_at,
                max_uses=max_uses
            )
            
            # Create invite link
            bot_username = (await callback.bot.get_me()).username
            invite_link = f"https://t.me/{bot_username}?start={token}"
            
            expires_text = expires_at.strftime("%d.%m.%Y в %H:%M")
            uses_text = f"{max_uses} использований" if max_uses else "неограничено"
            
            invite_text = (
                f"🔗 Ссылка-приглашение создана!\n\n"
                f"Группа: {user.group.name}\n"
                f"Действует до: {expires_text}\n"
                f"Максимум использований: {uses_text}\n\n"
                f"Ссылка:\n`{invite_link}`\n\n"
                f"Отправьте эту ссылку тем, кого хотите пригласить в группу."
            )
            
            await callback.message.edit_text(
                invite_text,
                parse_mode="Markdown"
            )
            
            logger.info(f"User {user.full_name} created invite for group {user.group.name}")
            
    except Exception as e:
        logger.error(f"Error creating invite: {e}")
        await callback.answer("❌ Произошла ошибка при создании приглашения.")


@router.callback_query(F.data == "group_settings")
@require_role(UserRole.GROUP_LEADER)
async def group_settings(callback: types.CallbackQuery, state: FSMContext, user):
    """Show group settings"""
    await callback.message.edit_text(
        f"⚙️ Настройки группы «{user.group.name}»\n\n"
        "Что вы хотите изменить?\n\n"
        "1. Название группы\n"
        "2. Описание группы\n"
        "3. Удалить группу\n\n"
        "Отправьте номер действия (1-3):"
    )
    await state.set_state(GroupStates.selecting_setting)


@router.message(GroupStates.selecting_setting)
@require_role(UserRole.GROUP_LEADER)
async def handle_group_setting(message: types.Message, state: FSMContext, user):
    """Handle group setting selection"""
    try:
        choice = message.text.strip()
        
        if choice == "1":
            await message.answer(
                "📝 Изменение названия группы\n\n"
                f"Текущее название: {user.group.name}\n\n"
                "Введите новое название:"
            )
            await state.set_state(GroupStates.changing_name)
            
        elif choice == "2":
            await message.answer(
                "📄 Изменение описания группы\n\n"
                f"Текущее описание: {user.group.description or 'не указано'}\n\n"
                "Введите новое описание (или /clear для удаления):"
            )
            await state.set_state(GroupStates.changing_description)
            
        elif choice == "3":
            await message.answer(
                "⚠️ ВНИМАНИЕ: Удаление группы\n\n"
                "Вы уверены, что хотите удалить группу?\n"
                "Это действие нельзя отменить!\n\n"
                "Все участники будут исключены из группы.\n"
                "Все события, темы и очереди будут удалены.\n\n"
                "Для подтверждения введите название группы точно как оно написано:",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete_group")]
                ])
            )
            await state.set_state(GroupStates.confirming_deletion)
            
        else:
            await message.answer(
                "❌ Неверный выбор. Введите номер от 1 до 3."
            )
            
    except Exception as e:
        logger.error(f"Error handling group setting: {e}")
        await message.answer("❌ Произошла ошибка.")
        await state.clear()


@router.message(GroupStates.changing_name)
@require_role(UserRole.GROUP_LEADER)
async def change_group_name(message: types.Message, state: FSMContext, user):
    """Change group name"""
    try:
        new_name = message.text.strip()
        
        if len(new_name) < 3:
            await message.answer(
                "❌ Название должно содержать минимум 3 символа."
            )
            return
        
        if len(new_name) > 100:
            await message.answer(
                "❌ Название слишком длинное (максимум 100 символов)."
            )
            return
        
        async for db in get_db():
            old_name = user.group.name
            await group_crud.update(db, user.group_id, name=new_name)
            
            await message.answer(
                f"✅ Название группы изменено!\n\n"
                f"Было: {old_name}\n"
                f"Стало: {new_name}"
            )
            
            logger.info(f"Group leader {user.full_name} changed group name from '{old_name}' to '{new_name}'")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error changing group name: {e}")
        await message.answer("❌ Произошла ошибка при изменении названия.")
        await state.clear()


@router.message(GroupStates.changing_description)
@require_role(UserRole.GROUP_LEADER)
async def change_group_description(message: types.Message, state: FSMContext, user):
    """Change group description"""
    try:
        new_description = None
        
        if message.text.strip() == "/clear":
            new_description = None
        else:
            new_description = message.text.strip()
            if len(new_description) > 500:
                await message.answer(
                    "❌ Описание слишком длинное (максимум 500 символов)."
                )
                return
        
        async for db in get_db():
            await group_crud.update(db, user.group_id, description=new_description)
            
            if new_description:
                await message.answer(
                    f"✅ Описание группы обновлено:\n\n{new_description}"
                )
            else:
                await message.answer("✅ Описание группы удалено.")
            
            logger.info(f"Group leader {user.full_name} updated group description")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error changing group description: {e}")
        await message.answer("❌ Произошла ошибка при изменении описания.")
        await state.clear()


@router.callback_query(F.data == "cancel_delete_group")
async def cancel_delete_group(callback: types.CallbackQuery, state: FSMContext):
    """Cancel group deletion"""
    await callback.message.edit_text("✅ Удаление группы отменено.")
    await state.clear()


@router.message(GroupStates.confirming_deletion)
@require_role(UserRole.GROUP_LEADER)
async def confirm_group_deletion(message: types.Message, state: FSMContext, user):
    """Confirm group deletion"""
    try:
        confirmation = message.text.strip()
        
        if confirmation != user.group.name:
            await message.answer(
                "❌ Название группы введено неверно. Удаление отменено."
            )
            await state.clear()
            return
        
        async for db in get_db():
            group_name = user.group.name
            group_id = user.group_id
            
            # Get all group members
            members = await user_crud.get_users_by_group(db, group_id)
            
            # Remove all members from group
            for member in members:
                await user_crud.update(db, member.id, group_id=None, role=UserRole.MEMBER)
            
            # Deactivate group
            await group_crud.update(db, group_id, is_active=False)
            
            await message.answer(
                f"✅ Группа «{group_name}» удалена.\n"
                f"Все {len(members)} участников исключены из группы.",
                reply_markup=get_main_menu_keyboard(UserRole.MEMBER)
            )
            
            # Notify all members
            try:
                from app.services.notification_service import NotificationService
                notification_service = NotificationService()
                
                for member in members:
                    if member.id != user.id:  # Don't notify the leader
                        await notification_service.send_immediate_notification(
                            member.telegram_id,
                            "⚠️ Группа удалена",
                            f"Группа «{group_name}» была удалена старостой."
                        )
            except Exception as e:
                logger.error(f"Error notifying members about group deletion: {e}")
            
            logger.info(f"Group leader {user.full_name} deleted group '{group_name}'")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error deleting group: {e}")
        await message.answer("❌ Произошла ошибка при удалении группы.")
        await state.clear()
