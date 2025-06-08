"""
Event management handlers
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger
from datetime import datetime, date, timedelta

from app.database.database import get_db
from app.database.crud import event_crud, user_crud, notification_crud
from app.database.models import UserRole, EventType, NotificationType
from app.keyboards.inline import (
    get_events_keyboard, get_event_actions_keyboard, 
    get_event_type_keyboard, get_event_details_keyboard,
    get_events_filter_keyboard
)
from app.keyboards.reply import get_main_menu_keyboard
from app.utils.decorators import require_role, require_auth
from app.states.states import EventStates
from app.services.notification_service import NotificationService

router = Router()


@router.message(F.text == "📅 События")
@require_auth
async def show_events(message: types.Message, user):
    """Show events for user's group"""
    if not user.group_id:
        await message.answer("❌ Вы не состоите ни в одной группе.")
        return
    
    try:
        async for db in get_db():
            events = await event_crud.get_group_events(db, user.group_id, limit=10)
            
            if not events:
                await message.answer(
                    "📅 В вашей группе пока нет событий.",
                    reply_markup=get_events_keyboard(user.role, has_events=False)
                )
                return
            
            # Show recent events
            events_text = f"📅 События группы «{user.group.name}»:\n\n"
            
            for event in events:
                event_emoji = get_event_emoji(event.event_type)
                date_str = event.event_date.strftime("%d.%m.%Y") if event.event_date else "Дата не указана"
                
                events_text += f"{event_emoji} {event.title}\n"
                events_text += f"📅 {date_str}"
                
                if event.start_time:
                    events_text += f" в {event.start_time}"
                
                if event.is_important:
                    events_text += " ⭐"
                
                events_text += "\n\n"
            
            await message.answer(
                events_text,
                reply_markup=get_events_keyboard(user.role, has_events=True)
            )
            
    except Exception as e:
        logger.error(f"Error showing events: {e}")
        await message.answer("❌ Произошла ошибка при загрузке событий.")


@router.callback_query(F.data == "view_all_events")
@require_auth
async def view_all_events(callback: types.CallbackQuery, user):
    """View all events with pagination"""
    try:
        async for db in get_db():
            events = await event_crud.get_group_events(db, user.group_id, limit=20)
            
            if not events:
                await callback.message.edit_text("📅 В группе нет событий.")
                return
            
            events_text = f"📅 Все события ({len(events)}):\n\n"
            
            for i, event in enumerate(events, 1):
                event_emoji = get_event_emoji(event.event_type)
                date_str = event.event_date.strftime("%d.%m") if event.event_date else "Без даты"
                
                events_text += f"{i}. {event_emoji} {event.title}\n"
                events_text += f"   📅 {date_str}"
                
                if event.start_time:
                    events_text += f" в {event.start_time}"
                
                if event.is_important:
                    events_text += " ⭐"
                
                events_text += "\n"
            
            await callback.message.edit_text(
                events_text,
                reply_markup=get_events_filter_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error viewing all events: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "upcoming_events")
@require_auth
async def view_upcoming_events(callback: types.CallbackQuery, user):
    """View upcoming events"""
    try:
        async for db in get_db():
            events = await event_crud.get_upcoming_events(db, user.group_id)
            
            if not events:
                await callback.message.edit_text(
                    "📅 Предстоящих событий нет.",
                    reply_markup=get_events_filter_keyboard()
                )
                return
            
            events_text = "📅 Предстоящие события:\n\n"
            
            for event in events:
                event_emoji = get_event_emoji(event.event_type)
                
                if event.event_date:
                    date_str = event.event_date.strftime("%d.%m.%Y")
                    days_left = (event.event_date - date.today()).days
                    
                    if days_left == 0:
                        date_info = f"{date_str} (сегодня)"
                    elif days_left == 1:
                        date_info = f"{date_str} (завтра)"
                    elif days_left > 0:
                        date_info = f"{date_str} (через {days_left} дн.)"
                    else:
                        continue  # Skip past events
                        
                elif event.deadline_end:
                    deadline_str = event.deadline_end.strftime("%d.%m.%Y %H:%M")
                    hours_left = (event.deadline_end - datetime.now()).total_seconds() / 3600
                    
                    if hours_left > 24:
                        days_left = int(hours_left / 24)
                        date_info = f"до {deadline_str} (через {days_left} дн.)"
                    elif hours_left > 0:
                        date_info = f"до {deadline_str} (через {int(hours_left)} ч.)"
                    else:
                        continue
                else:
                    date_info = "Дата не указана"
                
                events_text += f"{event_emoji} {event.title}\n"
                events_text += f"📅 {date_info}"
                
                if event.start_time:
                    events_text += f" в {event.start_time}"
                
                if event.is_important:
                    events_text += " ⭐"
                
                events_text += "\n\n"
            
            await callback.message.edit_text(
                events_text,
                reply_markup=get_events_filter_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error viewing upcoming events: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.message(F.text == "➕ Создать событие")
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def create_event_start(message: types.Message, state: FSMContext, user):
    """Start event creation"""
    if not user.group_id:
        await message.answer("❌ Вы не состоите ни в одной группе.")
        return
    
    await message.answer(
        "📝 Создание нового события\n\n"
        "Введите название события:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(EventStates.waiting_for_title)


@router.message(EventStates.waiting_for_title)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_event_title(message: types.Message, state: FSMContext, user):
    """Process event title"""
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
            "Теперь выберите тип события:",
            reply_markup=get_event_type_keyboard()
        )
        await state.set_state(EventStates.waiting_for_type)
        
    except Exception as e:
        logger.error(f"Error processing event title: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.callback_query(F.data.startswith("event_type:"))
async def process_event_type(callback: types.CallbackQuery, state: FSMContext):
    """Process event type selection"""
    try:
        event_type = callback.data.split(":")[1]
        await state.update_data(event_type=event_type)
        
        type_names = {
            "lecture": "Лекция",
            "seminar": "Семинар", 
            "lab": "Лабораторная работа",
            "exam": "Экзамен",
            "deadline": "Дедлайн",
            "meeting": "Собрание",
            "other": "Другое"
        }
        
        await callback.message.edit_text(
            f"✅ Тип события: {type_names.get(event_type, event_type)}\n\n"
            "Введите описание события (или отправьте /skip для пропуска):"
        )
        await state.set_state(EventStates.waiting_for_description)
        
    except Exception as e:
        logger.error(f"Error processing event type: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.message(EventStates.waiting_for_description)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_event_description(message: types.Message, state: FSMContext, user):
    """Process event description"""
    try:
        description = None
        if message.text.strip() != "/skip":
            description = message.text.strip()
            if len(description) > 1000:
                await message.answer("❌ Описание слишком длинное (максимум 1000 символов).")
                return
        
        await state.update_data(description=description)
        
        data = await state.get_data()
        event_type = data.get('event_type')
        
        if event_type == "deadline":
            await message.answer(
                "📅 Укажите дату и время окончания дедлайна:\n\n"
                "Формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
                "Например: 25.12.2024 23:59"
            )
            await state.set_state(EventStates.waiting_for_deadline)
        else:
            await message.answer(
                "📅 Укажите дату события:\n\n"
                "Формат: ДД.ММ.ГГГГ\n"
                "Например: 25.12.2024\n"
                "Или отправьте /skip для пропуска"
            )
            await state.set_state(EventStates.waiting_for_date)
        
    except Exception as e:
        logger.error(f"Error processing event description: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.message(EventStates.waiting_for_deadline)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_deadline_date(message: types.Message, state: FSMContext, user):
    """Process deadline date and time"""
    try:
        date_str = message.text.strip()
        
        try:
            deadline_end = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
            
            if deadline_end <= datetime.now():
                await message.answer("❌ Дедлайн должен быть в будущем.")
                return
                
        except ValueError:
            await message.answer(
                "❌ Неверный формат даты.\n"
                "Используйте формат: ДД.ММ.ГГГГ ЧЧ:ММ"
            )
            return
        
        await state.update_data(deadline_end=deadline_end)
        
        await message.answer(
            "📝 Хотите добавить медиафайл к событию?\n\n"
            "Отправьте фото, видео или документ, либо нажмите /skip",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_media")]
            ])
        )
        await state.set_state(EventStates.waiting_for_media)
        
    except Exception as e:
        logger.error(f"Error processing deadline date: {e}")
        await message.answer("❌ Произошла ошибка при обработке даты.")


@router.message(EventStates.waiting_for_date)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_event_date(message: types.Message, state: FSMContext, user):
    """Process event date"""
    try:
        event_date = None
        
        if message.text.strip() != "/skip":
            date_str = message.text.strip()
            
            try:
                event_date = datetime.strptime(date_str, "%d.%m.%Y").date()
            except ValueError:
                await message.answer(
                    "❌ Неверный формат даты.\n"
                    "Используйте формат: ДД.ММ.ГГГГ"
                )
                return
        
        await state.update_data(event_date=event_date)
        
        if event_date:
            await message.answer(
                f"✅ Дата события: {event_date.strftime('%d.%m.%Y')}\n\n"
                "Укажите время начала события:\n\n"
                "Формат: ЧЧ:ММ\n"
                "Например: 09:30\n"
                "Или отправьте /skip для пропуска"
            )
            await state.set_state(EventStates.waiting_for_start_time)
        else:
            await message.answer(
                "📝 Хотите добавить медиафайл к событию?\n\n"
                "Отправьте фото, видео или документ, либо нажмите /skip",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_media")]
                ])
            )
            await state.set_state(EventStates.waiting_for_media)
        
    except Exception as e:
        logger.error(f"Error processing event date: {e}")
        await message.answer("❌ Произошла ошибка при обработке даты.")


@router.message(EventStates.waiting_for_start_time)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_start_time(message: types.Message, state: FSMContext, user):
    """Process event start time"""
    try:
        start_time = None
        
        if message.text.strip() != "/skip":
            time_str = message.text.strip()
            
            try:
                # Validate time format
                datetime.strptime(time_str, "%H:%M")
                start_time = time_str
            except ValueError:
                await message.answer(
                    "❌ Неверный формат времени.\n"
                    "Используйте формат: ЧЧ:ММ"
                )
                return
        
        await state.update_data(start_time=start_time)
        
        if start_time:
            await message.answer(
                f"✅ Время начала: {start_time}\n\n"
                "Укажите время окончания события:\n\n"
                "Формат: ЧЧ:ММ\n"
                "Или отправьте /skip для пропуска"
            )
            await state.set_state(EventStates.waiting_for_end_time)
        else:
            await message.answer(
                "📝 Хотите добавить медиафайл к событию?\n\n"
                "Отправьте фото, видео или документ, либо нажмите /skip",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_media")]
                ])
            )
            await state.set_state(EventStates.waiting_for_media)
        
    except Exception as e:
        logger.error(f"Error processing start time: {e}")
        await message.answer("❌ Произошла ошибка при обработке времени.")


@router.message(EventStates.waiting_for_end_time)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_end_time(message: types.Message, state: FSMContext, user):
    """Process event end time"""
    try:
        end_time = None
        
        if message.text.strip() != "/skip":
            time_str = message.text.strip()
            
            try:
                # Validate time format
                datetime.strptime(time_str, "%H:%M")
                end_time = time_str
                
                # Check if end time is after start time
                data = await state.get_data()
                start_time = data.get('start_time')
                
                if start_time and end_time:
                    start_dt = datetime.strptime(start_time, "%H:%M")
                    end_dt = datetime.strptime(end_time, "%H:%M")
                    
                    if end_dt <= start_dt:
                        await message.answer(
                            "❌ Время окончания должно быть позже времени начала."
                        )
                        return
                        
            except ValueError:
                await message.answer(
                    "❌ Неверный формат времени.\n"
                    "Используйте формат: ЧЧ:ММ"
                )
                return
        
        await state.update_data(end_time=end_time)
        
        await message.answer(
            "📝 Хотите добавить медиафайл к событию?\n\n"
            "Отправьте фото, видео или документ, либо нажмите /skip",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_media")]
            ])
        )
        await state.set_state(EventStates.waiting_for_media)
        
    except Exception as e:
        logger.error(f"Error processing end time: {e}")
        await message.answer("❌ Произошла ошибка при обработке времени.")


@router.callback_query(F.data == "skip_media")
async def skip_media(callback: types.CallbackQuery, state: FSMContext):
    """Skip media upload"""
    await finish_event_creation(callback.message, state, callback.from_user.id)


@router.message(EventStates.waiting_for_media, F.photo)
@router.message(EventStates.waiting_for_media, F.video)
@router.message(EventStates.waiting_for_media, F.document)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_media(message: types.Message, state: FSMContext, user):
    """Process media file"""
    try:
        media_file_id = None
        media_type = None
        
        if message.photo:
            media_file_id = message.photo[-1].file_id
            media_type = "photo"
        elif message.video:
            media_file_id = message.video.file_id
            media_type = "video"
        elif message.document:
            media_file_id = message.document.file_id
            media_type = "document"
        
        await state.update_data(
            media_file_id=media_file_id,
            media_type=media_type,
            has_media=True
        )
        
        await finish_event_creation(message, state, message.from_user.id)
        
    except Exception as e:
        logger.error(f"Error processing media: {e}")
        await message.answer("❌ Произошла ошибка при обработке файла.")


async def finish_event_creation(message: types.Message, state: FSMContext, user_id: int):
    """Finish event creation"""
    try:
        data = await state.get_data()
        
        async for db in get_db():
            user = await user_crud.get_by_telegram_id(db, user_id)
            
            # Create event
            event_data = {
                'title': data['title'],
                'description': data.get('description'),
                'event_type': EventType(data['event_type']),
                'group_id': user.group_id,
                'creator_id': user.id,
                'event_date': data.get('event_date'),
                'start_time': data.get('start_time'),
                'end_time': data.get('end_time'),
                'deadline_end': data.get('deadline_end'),
                'has_media': data.get('has_media', False),
                'media_file_id': data.get('media_file_id'),
                'media_type': data.get('media_type')
            }
            
            event = await event_crud.create_event(db, **event_data)
            
            # Send confirmation message
            confirmation_text = f"✅ Событие «{event.title}» создано!\n\n"
            
            if event.event_date:
                confirmation_text += f"📅 Дата: {event.event_date.strftime('%d.%m.%Y')}\n"
            
            if event.start_time:
                confirmation_text += f"🕐 Время: {event.start_time}"
                if event.end_time:
                    confirmation_text += f" - {event.end_time}"
                confirmation_text += "\n"
            
            if event.deadline_end:
                confirmation_text += f"⏰ Дедлайн: {event.deadline_end.strftime('%d.%m.%Y %H:%M')}\n"
            
            confirmation_text += "\n📢 Участники группы получат уведомление о новом событии."
            
            await message.answer(
                confirmation_text,
                reply_markup=get_main_menu_keyboard(user.role)
            )
            
            # Send notifications to group members
            await notify_group_about_event(db, event, user)
            
            logger.info(f"User {user.full_name} created event '{event.title}' in group {user.group.name}")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error finishing event creation: {e}")
        await message.answer("❌ Произошла ошибка при создании события.")
        await state.clear()


async def notify_group_about_event(db, event, creator):
    """Send notifications about new event"""
    try:
        members = await user_crud.get_users_by_group(db, event.group_id)
        notification_service = NotificationService()
        
        for member in members:
            if member.id != creator.id and member.event_notifications:
                title = "📅 Новое событие"
                message = f"В группе «{event.group.name}» создано новое событие:\n\n{event.title}"
                
                if event.event_date:
                    message += f"\n📅 {event.event_date.strftime('%d.%m.%Y')}"
                
                if event.start_time:
                    message += f" в {event.start_time}"
                
                await notification_service.send_immediate_notification(
                    member.telegram_id, title, message
                )
    except Exception as e:
        logger.error(f"Error notifying group about event: {e}")


@router.callback_query(F.data.startswith("event_details:"))
@require_auth
async def show_event_details(callback: types.CallbackQuery, user):
    """Show detailed event information"""
    try:
        event_id = callback.data.split(":")[1]
        
        async for db in get_db():
            event = await event_crud.get_by_id(db, event_id)
            
            if not event or event.group_id != user.group_id:
                await callback.answer("❌ Событие не найдено.")
                return
            
            # Mark as viewed
            await event_crud.mark_as_viewed(db, user.id, event.id)
            
            # Build details message
            details_text = f"📋 Детали события\n\n"
            details_text += f"📝 Название: {event.title}\n"
            details_text += f"🏷️ Тип: {get_event_type_name(event.event_type)}\n"
            
            if event.description:
                details_text += f"📄 Описание: {event.description}\n"
            
            if event.event_date:
                details_text += f"📅 Дата: {event.event_date.strftime('%d.%m.%Y')}\n"
            
            if event.start_time:
                details_text += f"🕐 Время: {event.start_time}"
                if event.end_time:
                    details_text += f" - {event.end_time}"
                details_text += "\n"
            
            if event.deadline_end:
                details_text += f"⏰ Дедлайн: {event.deadline_end.strftime('%d.%m.%Y %H:%M')}\n"
            
            details_text += f"👤 Создатель: {event.creator.full_name}\n"
            details_text += f"📊 Важное: {'Да' if event.is_important else 'Нет'}\n"
            
            keyboard = get_event_details_keyboard(event.id, user.role, event.creator_id == user.id)
            
            if event.has_media and event.media_file_id:
                # Send media first, then details
                if event.media_type == "photo":
                    await callback.bot.send_photo(
                        callback.message.chat.id,
                        event.media_file_id,
                        caption=details_text,
                        reply_markup=keyboard
                    )
                elif event.media_type == "video":
                    await callback.bot.send_video(
                        callback.message.chat.id,
                        event.media_file_id,
                        caption=details_text,
                        reply_markup=keyboard
                    )
                elif event.media_type == "document":
                    await callback.bot.send_document(
                        callback.message.chat.id,
                        event.media_file_id,
                        caption=details_text,
                        reply_markup=keyboard
                    )
                
                # Delete the original message
                await callback.message.delete()
            else:
                await callback.message.edit_text(
                    details_text,
                    reply_markup=keyboard
                )
            
    except Exception as e:
        logger.error(f"Error showing event details: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data.startswith("mark_important:"))
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def toggle_event_importance(callback: types.CallbackQuery, user):
    """Toggle event importance"""
    try:
        event_id = callback.data.split(":")[1]
        
        async for db in get_db():
            event = await event_crud.get_by_id(db, event_id)
            
            if not event or event.group_id != user.group_id:
                await callback.answer("❌ Событие не найдено.")
                return
            
            # Toggle importance
            new_importance = not event.is_important
            await event_crud.update(db, event_id, is_important=new_importance)
            
            status = "важным" if new_importance else "обычным"
            await callback.answer(f"✅ Событие помечено как {status}.")
            
            # Refresh the details view
            await show_event_details(callback, user)
            
    except Exception as e:
        logger.error(f"Error toggling event importance: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data.startswith("delete_event:"))
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def delete_event(callback: types.CallbackQuery, user):
    """Delete event"""
    try:
        event_id = callback.data.split(":")[1]
        
        async for db in get_db():
            event = await event_crud.get_by_id(db, event_id)
            
            if not event or event.group_id != user.group_id:
                await callback.answer("❌ Событие не найдено.")
                return
            
            # Check permissions
            if event.creator_id != user.id and user.role != UserRole.GROUP_LEADER:
                await callback.answer("❌ Вы можете удалять только свои события.")
                return
            
            # Delete event
            await event_crud.update(db, event_id, is_active=False)
            
            await callback.message.edit_text(
                f"✅ Событие «{event.title}» удалено."
            )
            
            logger.info(f"User {user.full_name} deleted event '{event.title}'")
            
    except Exception as e:
        logger.error(f"Error deleting event: {e}")
        await callback.answer("❌ Произошла ошибка.")


def get_event_emoji(event_type: EventType) -> str:
    """Get emoji for event type"""
    emoji_map = {
        EventType.LECTURE: "📚",
        EventType.SEMINAR: "💬",
        EventType.LAB: "🔬",
        EventType.EXAM: "📝",
        EventType.DEADLINE: "⏰",
        EventType.MEETING: "👥",
        EventType.OTHER: "📌"
    }
    return emoji_map.get(event_type, "📌")


def get_event_type_name(event_type: EventType) -> str:
    """Get human-readable event type name"""
    type_names = {
        EventType.LECTURE: "Лекция",
        EventType.SEMINAR: "Семинар",
        EventType.LAB: "Лабораторная работа",
        EventType.EXAM: "Экзамен",
        EventType.DEADLINE: "Дедлайн",
        EventType.MEETING: "Собрание",
        EventType.OTHER: "Другое"
    }
    return type_names.get(event_type, str(event_type))
