"""
Authentication and registration handlers
"""

from aiogram import Router, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from loguru import logger

from app.database.database import get_db
from app.database.crud import user_crud, group_crud, invite_token_crud
from app.states.states import RegistrationStates
from app.keyboards.inline import get_groups_keyboard, get_confirmation_keyboard
from app.keyboards.reply import get_main_menu_keyboard
from app.services.auth_service import AuthService
from app.utils.decorators import require_auth
from app.database.models import UserRole

router = Router()


@router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    """
    Handle /start command with optional invite token
    """
    try:
        async for db in get_db():
            # Check if user already exists
            user = await user_crud.get_by_telegram_id(db, message.from_user.id)
            
            # Parse invite token from command args
            args = message.text.split()
            invite_token = args[1] if len(args) > 1 else None
            
            if user:
                # Existing user
                if user.group_id:
                    await message.answer(
                        f"👋 Добро пожаловать обратно, {user.full_name}!\n"
                        f"Ваша группа: {user.group.name if user.group else 'Не указана'}",
                        reply_markup=get_main_menu_keyboard(user.role)
                    )
                else:
                    await message.answer(
                        f"👋 Привет, {user.full_name}!\n"
                        "Вы не состоите ни в одной группе. Выберите группу для присоединения:",
                        reply_markup=await get_groups_keyboard(db)
                    )
                return
            
            if invite_token:
                # Registration with invite token
                await handle_invite_registration(message, state, invite_token, db)
            else:
                # Regular registration
                await start_registration(message, state)
                
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


async def handle_invite_registration(message: types.Message, state: FSMContext, 
                                   token: str, db):
    """Handle registration with invite token"""
    try:
        # Validate token
        invite = await invite_token_crud.get_by_token(db, token)
        if not invite or not AuthService.is_token_valid(invite):
            await message.answer(
                "❌ Недействительная или истекшая ссылка приглашения.\n"
                "Обратитесь к старосте группы за новой ссылкой."
            )
            return
        
        # Save invite token to state
        await state.update_data(invite_token=token)
        
        await message.answer(
            f"🎓 Добро пожаловать в группу «{invite.group.name}»!\n\n"
            "Для завершения регистрации введите ваше полное имя (Фамилия Имя Отчество):"
        )
        await state.set_state(RegistrationStates.waiting_for_name_with_invite)
        
    except Exception as e:
        logger.error(f"Error handling invite registration: {e}")
        await message.answer("❌ Произошла ошибка при обработке приглашения.")


async def start_registration(message: types.Message, state: FSMContext):
    """Start regular registration process"""
    await message.answer(
        "👋 Добро пожаловать в систему управления студенческими группами!\n\n"
        "Для начала работы введите ваше полное имя (Фамилия Имя Отчество):"
    )
    await state.set_state(RegistrationStates.waiting_for_name)


@router.message(StateFilter(RegistrationStates.waiting_for_name))
async def process_name(message: types.Message, state: FSMContext):
    """Process user's full name during registration"""
    try:
        full_name = message.text.strip()
        
        if len(full_name) < 5 or len(full_name.split()) < 2:
            await message.answer(
                "❌ Пожалуйста, введите полное имя (минимум имя и фамилия):"
            )
            return
        
        # Save name to state
        await state.update_data(full_name=full_name)
        
        # Show available groups
        async for db in get_db():
            groups_kb = await get_groups_keyboard(db)
            await message.answer(
                f"✅ Имя сохранено: {full_name}\n\n"
                "Теперь выберите вашу группу:",
                reply_markup=groups_kb
            )
            await state.set_state(RegistrationStates.waiting_for_group)
            
    except Exception as e:
        logger.error(f"Error processing name: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")


@router.message(StateFilter(RegistrationStates.waiting_for_name_with_invite))
async def process_name_with_invite(message: types.Message, state: FSMContext):
    """Process user's full name during invite registration"""
    try:
        full_name = message.text.strip()
        
        if len(full_name) < 5 or len(full_name.split()) < 2:
            await message.answer(
                "❌ Пожалуйста, введите полное имя (минимум имя и фамилия):"
            )
            return
        
        # Get data from state
        data = await state.get_data()
        invite_token = data.get('invite_token')
        
        async for db in get_db():
            # Validate token again
            invite = await invite_token_crud.get_by_token(db, invite_token)
            if not invite or not AuthService.is_token_valid(invite):
                await message.answer("❌ Ссылка приглашения более недействительна.")
                await state.clear()
                return
            
            # Create user with group
            user = await user_crud.create_user(
                db,
                telegram_id=message.from_user.id,
                full_name=full_name,
                username=message.from_user.username,
                group_id=invite.group_id
            )
            
            # Use the invite token
            await invite_token_crud.use_token(db, invite_token)
            
            # Notify group leader
            await notify_group_leader(db, user, invite.group)
            
            await message.answer(
                f"✅ Регистрация завершена!\n"
                f"Вы добавлены в группу «{invite.group.name}».\n\n"
                f"Староста группы получил уведомление о вашем присоединении.",
                reply_markup=get_main_menu_keyboard(UserRole.MEMBER)
            )
            
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error processing name with invite: {e}")
        await message.answer("❌ Произошла ошибка при регистрации.")
        await state.clear()


@router.callback_query(F.data.startswith("select_group:"))
async def select_group(callback: types.CallbackQuery, state: FSMContext):
    """Handle group selection"""
    try:
        group_id = callback.data.split(":")[1]
        data = await state.get_data()
        full_name = data.get('full_name')
        
        if not full_name:
            await callback.answer("❌ Ошибка: имя не найдено. Начните регистрацию заново.")
            await state.clear()
            return
        
        async for db in get_db():
            group = await group_crud.get_by_id(db, group_id)
            if not group:
                await callback.answer("❌ Группа не найдена.")
                return
            
            # Show confirmation
            await callback.message.edit_text(
                f"📚 Вы выбрали группу: {group.name}\n\n"
                f"После подтверждения староста группы получит уведомление "
                f"о вашем запросе на присоединение.",
                reply_markup=get_confirmation_keyboard(group_id)
            )
            
            await state.update_data(group_id=group_id)
            await state.set_state(RegistrationStates.waiting_for_confirmation)
            
    except Exception as e:
        logger.error(f"Error selecting group: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data.startswith("confirm_group:"))
async def confirm_group(callback: types.CallbackQuery, state: FSMContext):
    """Confirm group selection and complete registration"""
    try:
        group_id = callback.data.split(":")[1]
        data = await state.get_data()
        full_name = data.get('full_name')
        
        async for db in get_db():
            # Create user without group (pending approval)
            user = await user_crud.create_user(
                db,
                telegram_id=callback.from_user.id,
                full_name=full_name,
                username=callback.from_user.username
            )
            
            group = await group_crud.get_by_id(db, group_id)
            
            # Notify group leader about join request
            await notify_group_leader_about_request(db, user, group)
            
            await callback.message.edit_text(
                f"✅ Заявка отправлена!\n\n"
                f"Ваша заявка на присоединение к группе «{group.name}» "
                f"отправлена старосте. Ожидайте подтверждения."
            )
            
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error confirming group: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "cancel_registration")
async def cancel_registration(callback: types.CallbackQuery, state: FSMContext):
    """Cancel registration process"""
    await callback.message.edit_text("❌ Регистрация отменена.")
    await state.clear()


@router.message(Command("admin_login"))
async def admin_login(message: types.Message):
    """Handle admin login with code"""
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer(
                "❌ Неверный формат команды.\n"
                "Использование: /admin_login <код>"
            )
            return
        
        admin_code = args[1]
        
        if not AuthService.verify_admin_code(admin_code):
            await message.answer("❌ Неверный код администратора.")
            return
        
        async for db in get_db():
            user = await user_crud.get_by_telegram_id(db, message.from_user.id)
            
            if not user:
                await message.answer(
                    "❌ Вы не зарегистрированы в системе.\n"
                    "Сначала выполните команду /start"
                )
                return
            
            # Update user role to admin
            await user_crud.update_role(db, user.id, UserRole.ADMIN)
            
            await message.answer(
                "✅ Вы успешно авторизованы как администратор!",
                reply_markup=get_main_menu_keyboard(UserRole.ADMIN)
            )
            
            logger.info(f"User {user.full_name} ({user.telegram_id}) became admin")
            
    except Exception as e:
        logger.error(f"Error in admin login: {e}")
        await message.answer("❌ Произошла ошибка при авторизации.")


async def notify_group_leader(db, user, group):
    """Notify group leader about new member"""
    try:
        from app.services.notification_service import NotificationService
        
        leader = await user_crud.get_by_id(db, group.leader_id)
        if leader:
            notification_service = NotificationService()
            await notification_service.send_immediate_notification(
                leader.telegram_id,
                "👥 Новый участник",
                f"Пользователь {user.full_name} присоединился к группе «{group.name}» "
                f"по ссылке-приглашению."
            )
    except Exception as e:
        logger.error(f"Error notifying group leader: {e}")


async def notify_group_leader_about_request(db, user, group):
    """Notify group leader about join request"""
    try:
        from app.services.notification_service import NotificationService
        
        leader = await user_crud.get_by_id(db, group.leader_id)
        if leader:
            notification_service = NotificationService()
            await notification_service.send_immediate_notification(
                leader.telegram_id,
                "📨 Заявка на присоединение",
                f"Пользователь {user.full_name} (@{user.username or 'без username'}) "
                f"хочет присоединиться к группе «{group.name}».\n\n"
                f"Используйте меню управления группой для одобрения заявки."
            )
    except Exception as e:
        logger.error(f"Error notifying about join request: {e}")


@router.message(Command("whoami"))
@require_auth
async def whoami(message: types.Message, user):
    """Show current user info"""
    group_info = f"Группа: {user.group.name}" if user.group else "Группа: не указана"
    role_names = {
        UserRole.ADMIN: "Администратор",
        UserRole.GROUP_LEADER: "Староста",
        UserRole.ASSISTANT: "Помощник старосты",
        UserRole.MEMBER: "Участник"
    }
    
    await message.answer(
        f"👤 Информация о вас:\n\n"
        f"Имя: {user.full_name}\n"
        f"Роль: {role_names.get(user.role, user.role)}\n"
        f"{group_info}\n"
        f"Telegram ID: {user.telegram_id}"
    )
