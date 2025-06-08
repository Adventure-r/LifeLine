"""
Queue management handlers
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger
from datetime import datetime, date, timedelta

from app.database.database import get_db
from app.database.crud import queue_crud, user_crud, notification_crud
from app.database.models import UserRole
from app.keyboards.inline import (
    get_queues_keyboard, get_queue_management_keyboard,
    get_queue_actions_keyboard, get_queue_details_keyboard
)
from app.keyboards.reply import get_main_menu_keyboard
from app.utils.decorators import require_role, require_auth
from app.states.states import QueueStates
from app.services.notification_service import NotificationService

router = Router()


@router.message(F.text == "🏃‍♂️ Очередь на защиту")
@require_auth
async def show_queues(message: types.Message, user):
    """Show available queues"""
    if not user.group_id:
        await message.answer("❌ Вы не состоите ни в одной группе.")
        return
    
    try:
        async for db in get_db():
            queues = await queue_crud.get_group_queues(db, user.group_id)
            
            if not queues:
                await message.answer(
                    "🏃‍♂️ В вашей группе пока нет очередей на защиту.",
                    reply_markup=get_queues_keyboard(user.role, has_queues=False)
                )
                return
            
            queues_text = f"🏃‍♂️ Очереди на защиту:\n\n"
            
            for i, queue in enumerate(queues, 1):
                participants_count = len(queue.entries)
                
                queues_text += f"{i}. {queue.title}\n"
                
                if queue.description:
                    # Show first 100 characters
                    desc = queue.description[:100]
                    if len(queue.description) > 100:
                        desc += "..."
                    queues_text += f"   📄 {desc}\n"
                
                queues_text += f"   👥 Участников: {participants_count}"
                if queue.max_participants:
                    queues_text += f"/{queue.max_participants}"
                queues_text += "\n"
                
                if queue.queue_date:
                    date_str = queue.queue_date.strftime("%d.%m.%Y")
                    queues_text += f"   📅 Дата: {date_str}"
                    
                    if queue.start_time:
                        queues_text += f" в {queue.start_time}"
                    queues_text += "\n"
                
                # Check if user is in this queue
                user_entry = next((entry for entry in queue.entries if entry.user_id == user.id), None)
                if user_entry:
                    queues_text += f"   📍 Ваша позиция: {user_entry.position}\n"
                elif queue.max_participants and participants_count >= queue.max_participants:
                    queues_text += "   ❌ Очередь заполнена\n"
                else:
                    queues_text += "   📝 Можно присоединиться\n"
                
                queues_text += "\n"
            
            await message.answer(
                queues_text,
                reply_markup=get_queues_keyboard(user.role, has_queues=True)
            )
            
    except Exception as e:
        logger.error(f"Error showing queues: {e}")
        await message.answer("❌ Произошла ошибка при загрузке очередей.")


@router.message(F.text == "🏃‍♂️ Очереди")
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def manage_queues(message: types.Message, user):
    """Show queue management for group leaders"""
    if not user.group_id:
        await message.answer("❌ Вы не состоите ни в одной группе.")
        return
    
    try:
        async for db in get_db():
            queues = await queue_crud.get_group_queues(db, user.group_id)
            
            queues_text = f"🏃‍♂️ Управление очередями группы «{user.group.name}»\n\n"
            
            if not queues:
                queues_text += "Очередей пока нет."
            else:
                queues_text += f"Всего очередей: {len(queues)}\n\n"
                
                for i, queue in enumerate(queues, 1):
                    participants_count = len(queue.entries)
                    queues_text += f"{i}. {queue.title}\n"
                    queues_text += f"   👥 Участников: {participants_count}"
                    
                    if queue.max_participants:
                        queues_text += f"/{queue.max_participants}"
                    queues_text += "\n"
                    
                    if queue.queue_date:
                        date_str = queue.queue_date.strftime("%d.%m.%Y")
                        queues_text += f"   📅 {date_str}"
                        if queue.start_time:
                            queues_text += f" в {queue.start_time}"
                        queues_text += "\n"
                    
                    queues_text += "\n"
            
            await message.answer(
                queues_text,
                reply_markup=get_queue_management_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error showing queue management: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "create_queue")
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def create_queue_start(callback: types.CallbackQuery, state: FSMContext, user):
    """Start queue creation"""
    await callback.message.edit_text(
        "📝 Создание новой очереди\n\n"
        "Введите название очереди:"
    )
    await state.set_state(QueueStates.waiting_for_title)


@router.message(QueueStates.waiting_for_title)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_queue_title(message: types.Message, state: FSMContext, user):
    """Process queue title"""
    try:
        title = message.text.strip()
        
        if len(title) < 3:
            await message.answer("❌ Название должно содержать минимум 3 символа.")
            return
        
        if len(title) > 255:
            await message.answer("❌ Название слишком длинное (максимум 255 символов).")
            return
        
        await state.update_data(title=title)
        
        await message.answer(
            f"✅ Название: {title}\n\n"
            "Введите описание очереди (или отправьте /skip для пропуска):"
        )
        await state.set_state(QueueStates.waiting_for_description)
        
    except Exception as e:
        logger.error(f"Error processing queue title: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.message(QueueStates.waiting_for_description)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_queue_description(message: types.Message, state: FSMContext, user):
    """Process queue description"""
    try:
        description = None
        if message.text.strip() != "/skip":
            description = message.text.strip()
            if len(description) > 1000:
                await message.answer("❌ Описание слишком длинное (максимум 1000 символов).")
                return
        
        await state.update_data(description=description)
        
        await message.answer(
            "📊 Укажите максимальное количество участников очереди:\n\n"
            "Введите число от 1 до 100, или отправьте /skip для неограниченной очереди:"
        )
        await state.set_state(QueueStates.waiting_for_max_participants)
        
    except Exception as e:
        logger.error(f"Error processing queue description: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.message(QueueStates.waiting_for_max_participants)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_max_participants(message: types.Message, state: FSMContext, user):
    """Process maximum participants"""
    try:
        max_participants = None
        
        if message.text.strip() != "/skip":
            try:
                max_participants = int(message.text.strip())
                
                if max_participants < 1 or max_participants > 100:
                    await message.answer("❌ Количество должно быть от 1 до 100.")
                    return
                    
            except ValueError:
                await message.answer("❌ Введите корректное число или /skip.")
                return
        
        await state.update_data(max_participants=max_participants)
        
        await message.answer(
            "📅 Укажите дату очереди:\n\n"
            "Формат: ДД.ММ.ГГГГ\n"
            "Например: 25.12.2024\n"
            "Или отправьте /skip для пропуска"
        )
        await state.set_state(QueueStates.waiting_for_date)
        
    except Exception as e:
        logger.error(f"Error processing max participants: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.message(QueueStates.waiting_for_date)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_queue_date(message: types.Message, state: FSMContext, user):
    """Process queue date"""
    try:
        queue_date = None
        
        if message.text.strip() != "/skip":
            try:
                queue_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
                
                if queue_date < date.today():
                    await message.answer("❌ Дата не может быть в прошлом.")
                    return
                    
            except ValueError:
                await message.answer(
                    "❌ Неверный формат даты.\n"
                    "Используйте формат: ДД.ММ.ГГГГ"
                )
                return
        
        await state.update_data(queue_date=queue_date)
        
        if queue_date:
            await message.answer(
                f"✅ Дата: {queue_date.strftime('%d.%m.%Y')}\n\n"
                "Укажите время начала очереди:\n\n"
                "Формат: ЧЧ:ММ\n"
                "Например: 09:00\n"
                "Или отправьте /skip для пропуска"
            )
            await state.set_state(QueueStates.waiting_for_start_time)
        else:
            await finish_queue_creation(message, state, user)
        
    except Exception as e:
        logger.error(f"Error processing queue date: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.message(QueueStates.waiting_for_start_time)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_start_time(message: types.Message, state: FSMContext, user):
    """Process queue start time"""
    try:
        start_time = None
        
        if message.text.strip() != "/skip":
            try:
                # Validate time format
                datetime.strptime(message.text.strip(), "%H:%M")
                start_time = message.text.strip()
            except ValueError:
                await message.answer(
                    "❌ Неверный формат времени.\n"
                    "Используйте формат: ЧЧ:ММ"
                )
                return
        
        await state.update_data(start_time=start_time)
        await finish_queue_creation(message, state, user)
        
    except Exception as e:
        logger.error(f"Error processing start time: {e}")
        await message.answer("❌ Произошла ошибка.")


async def finish_queue_creation(message: types.Message, state: FSMContext, user):
    """Finish queue creation"""
    try:
        data = await state.get_data()
        
        async for db in get_db():
            # Create queue
            queue = await queue_crud.create(
                db,
                title=data['title'],
                description=data.get('description'),
                group_id=user.group_id,
                max_participants=data.get('max_participants'),
                queue_date=data.get('queue_date'),
                start_time=data.get('start_time')
            )
            
            # Build confirmation message
            confirmation_text = f"✅ Очередь «{queue.title}» создана!\n\n"
            
            if queue.max_participants:
                confirmation_text += f"📊 Максимум участников: {queue.max_participants}\n"
            else:
                confirmation_text += "📊 Количество участников: неограничено\n"
            
            if queue.queue_date:
                confirmation_text += f"📅 Дата: {queue.queue_date.strftime('%d.%m.%Y')}\n"
            
            if queue.start_time:
                confirmation_text += f"🕐 Время: {queue.start_time}\n"
            
            confirmation_text += "\n📢 Участники группы получат уведомление о новой очереди."
            
            await message.answer(
                confirmation_text,
                reply_markup=get_main_menu_keyboard(user.role)
            )
            
            # Notify group members
            await notify_group_about_queue(db, queue, user)
            
            logger.info(f"User {user.full_name} created queue '{queue.title}' in group {user.group.name}")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error finishing queue creation: {e}")
        await message.answer("❌ Произошла ошибка при создании очереди.")
        await state.clear()


async def notify_group_about_queue(db, queue, creator):
    """Send notifications about new queue"""
    try:
        members = await user_crud.get_users_by_group(db, queue.group_id)
        notification_service = NotificationService()
        
        for member in members:
            if member.id != creator.id and member.notifications_enabled:
                message = f"В группе открыта новая очередь: {queue.title}"
                
                if queue.queue_date:
                    message += f"\n📅 {queue.queue_date.strftime('%d.%m.%Y')}"
                    
                if queue.start_time:
                    message += f" в {queue.start_time}"
                
                await notification_service.send_immediate_notification(
                    member.telegram_id,
                    "🏃‍♂️ Новая очередь",
                    message
                )
    except Exception as e:
        logger.error(f"Error notifying group about queue: {e}")


@router.callback_query(F.data == "join_queue_menu")
@require_auth
async def join_queue_menu(callback: types.CallbackQuery, user):
    """Show queue joining menu"""
    try:
        async for db in get_db():
            queues = await queue_crud.get_group_queues(db, user.group_id)
            
            # Filter available queues
            available_queues = []
            for queue in queues:
                # Check if user is already in queue
                user_in_queue = any(entry.user_id == user.id for entry in queue.entries)
                if user_in_queue:
                    continue
                
                # Check if queue is full
                if queue.max_participants and len(queue.entries) >= queue.max_participants:
                    continue
                
                available_queues.append(queue)
            
            if not available_queues:
                await callback.message.edit_text(
                    "🏃‍♂️ Нет доступных очередей для присоединения.\n\n"
                    "Возможные причины:\n"
                    "• Вы уже состоите во всех очередях\n"
                    "• Все очереди заполнены"
                )
                return
            
            queues_text = "🏃‍♂️ Выберите очередь для присоединения:\n\n"
            
            keyboard_buttons = []
            for i, queue in enumerate(available_queues):
                participants_count = len(queue.entries)
                
                queues_text += f"{i+1}. {queue.title}\n"
                queues_text += f"   👥 Участников: {participants_count}"
                if queue.max_participants:
                    queues_text += f"/{queue.max_participants}"
                queues_text += "\n"
                
                if queue.queue_date:
                    date_str = queue.queue_date.strftime("%d.%m.%Y")
                    queues_text += f"   📅 {date_str}"
                    if queue.start_time:
                        queues_text += f" в {queue.start_time}"
                    queues_text += "\n"
                
                queues_text += "\n"
                
                keyboard_buttons.append([
                    types.InlineKeyboardButton(
                        text=f"{i+1}. {queue.title[:30]}{'...' if len(queue.title) > 30 else ''}",
                        callback_data=f"join_queue:{queue.id}"
                    )
                ])
            
            keyboard_buttons.append([
                types.InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_queues")
            ])
            
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await callback.message.edit_text(queues_text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error showing join queue menu: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data.startswith("join_queue:"))
@require_auth
async def join_queue(callback: types.CallbackQuery, user):
    """Join a queue"""
    try:
        queue_id = callback.data.split(":")[1]
        
        async for db in get_db():
            queue = await queue_crud.get_by_id(db, queue_id)
            
            if not queue or queue.group_id != user.group_id:
                await callback.answer("❌ Очередь не найдена.")
                return
            
            # Check if user is already in queue
            user_in_queue = any(entry.user_id == user.id for entry in queue.entries)
            if user_in_queue:
                await callback.answer("❌ Вы уже состоите в этой очереди.")
                return
            
            # Check if queue is full
            if queue.max_participants and len(queue.entries) >= queue.max_participants:
                await callback.answer("❌ Очередь заполнена.")
                return
            
            # Join queue
            entry = await queue_crud.join_queue(db, queue_id, user.id)
            
            if entry:
                await callback.message.edit_text(
                    f"✅ Вы присоединились к очереди «{queue.title}»!\n\n"
                    f"📍 Ваша позиция: {entry.position}\n"
                    f"👥 Всего участников: {len(queue.entries) + 1}"
                )
                
                logger.info(f"User {user.full_name} joined queue '{queue.title}' at position {entry.position}")
            else:
                await callback.answer("❌ Не удалось присоединиться к очереди.")
            
    except Exception as e:
        logger.error(f"Error joining queue: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "my_queues")
@require_auth
async def show_my_queues(callback: types.CallbackQuery, user):
    """Show user's queues"""
    try:
        async for db in get_db():
            # Get all queues where user participates
            user_entries = await user_crud.get_user_queue_entries(db, user.id)
            
            if not user_entries:
                await callback.message.edit_text(
                    "🏃‍♂️ Вы не состоите ни в одной очереди.",
                    reply_markup=get_queues_keyboard(user.role, has_queues=True)
                )
                return
            
            queues_text = "🏃‍♂️ Ваши очереди:\n\n"
            
            for entry in user_entries:
                queue = entry.queue
                queues_text += f"📝 {queue.title}\n"
                queues_text += f"📍 Позиция: {entry.position}\n"
                
                if queue.queue_date:
                    date_str = queue.queue_date.strftime("%d.%m.%Y")
                    queues_text += f"📅 Дата: {date_str}"
                    if queue.start_time:
                        queues_text += f" в {queue.start_time}"
                    queues_text += "\n"
                
                if entry.notes:
                    queues_text += f"📝 Заметки: {entry.notes}\n"
                
                queues_text += "\n"
            
            await callback.message.edit_text(
                queues_text,
                reply_markup=get_queues_keyboard(user.role, has_queues=True)
            )
            
    except Exception as e:
        logger.error(f"Error showing user's queues: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data.startswith("queue_details:"))
@require_auth
async def show_queue_details(callback: types.CallbackQuery, user):
    """Show detailed queue information"""
    try:
        queue_id = callback.data.split(":")[1]
        
        async for db in get_db():
            queue = await queue_crud.get_by_id(db, queue_id)
            
            if not queue or queue.group_id != user.group_id:
                await callback.answer("❌ Очередь не найдена.")
                return
            
            # Build details message
            details_text = f"📋 Детали очереди\n\n"
            details_text += f"📝 Название: {queue.title}\n"
            
            if queue.description:
                details_text += f"📄 Описание: {queue.description}\n"
            
            participants_count = len(queue.entries)
            details_text += f"👥 Участников: {participants_count}"
            if queue.max_participants:
                details_text += f"/{queue.max_participants}"
            details_text += "\n"
            
            if queue.queue_date:
                date_str = queue.queue_date.strftime("%d.%m.%Y")
                details_text += f"📅 Дата: {date_str}\n"
            
            if queue.start_time:
                details_text += f"🕐 Время: {queue.start_time}\n"
            
            # Show queue positions
            if queue.entries:
                details_text += f"\n📋 Порядок очереди:\n"
                for entry in sorted(queue.entries, key=lambda x: x.position):
                    details_text += f"{entry.position}. {entry.user.full_name}"
                    if entry.notes:
                        details_text += f" ({entry.notes})"
                    details_text += "\n"
            
            keyboard = get_queue_details_keyboard(queue.id, user.role, user.id)
            
            await callback.message.edit_text(
                details_text,
                reply_markup=keyboard
            )
            
    except Exception as e:
        logger.error(f"Error showing queue details: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data.startswith("leave_queue:"))
@require_auth
async def leave_queue(callback: types.CallbackQuery, user):
    """Leave a queue"""
    try:
        queue_id = callback.data.split(":")[1]
        
        async for db in get_db():
            queue = await queue_crud.get_by_id(db, queue_id)
            
            if not queue or queue.group_id != user.group_id:
                await callback.answer("❌ Очередь не найдена.")
                return
            
            # Leave queue
            success = await queue_crud.leave_queue(db, queue_id, user.id)
            
            if success:
                await callback.message.edit_text(
                    f"✅ Вы покинули очередь «{queue.title}».\n"
                    f"Позиции остальных участников автоматически обновлены."
                )
                
                logger.info(f"User {user.full_name} left queue '{queue.title}'")
            else:
                await callback.answer("❌ Вы не состоите в этой очереди.")
            
    except Exception as e:
        logger.error(f"Error leaving queue: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "back_to_queues")
async def back_to_queues(callback: types.CallbackQuery):
    """Go back to queues menu"""
    from app.handlers.queues import show_queues
    await show_queues(callback.message, callback.from_user)
