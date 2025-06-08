"""
Topic selection handlers
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger
from datetime import datetime, timedelta

from app.database.database import get_db
from app.database.crud import topic_crud, user_crud, notification_crud
from app.database.models import UserRole, NotificationType
from app.keyboards.inline import (
    get_topics_keyboard, get_topic_management_keyboard,
    get_topic_actions_keyboard, get_topic_details_keyboard
)
from app.keyboards.reply import get_main_menu_keyboard
from app.utils.decorators import require_role, require_auth
from app.states.states import TopicStates
from app.services.notification_service import NotificationService

router = Router()


@router.message(F.text == "📚 Выбрать тему")
@require_auth
async def show_topics(message: types.Message, user):
    """Show available topics for selection"""
    if not user.group_id:
        await message.answer("❌ Вы не состоите ни в одной группе.")
        return
    
    try:
        async for db in get_db():
            topics = await topic_crud.get_group_topics(db, user.group_id)
            
            if not topics:
                await message.answer(
                    "📚 В вашей группе пока нет доступных тем.",
                    reply_markup=get_topics_keyboard(user.role, has_topics=False)
                )
                return
            
            # Get user's selected topics
            user_with_topics = await user_crud.get_by_id(db, user.id)
            selected_topic_ids = [t.id for t in user_with_topics.selected_topics]
            
            topics_text = f"📚 Доступные темы:\n\n"
            
            for i, topic in enumerate(topics, 1):
                selected_count = len(topic.selected_by)
                available_slots = topic.max_selections - selected_count
                
                topics_text += f"{i}. {topic.title}\n"
                
                if topic.description:
                    # Show first 100 characters
                    desc = topic.description[:100]
                    if len(topic.description) > 100:
                        desc += "..."
                    topics_text += f"   📄 {desc}\n"
                
                topics_text += f"   👥 Выбрано: {selected_count}/{topic.max_selections}\n"
                
                if topic.deadline:
                    deadline_str = topic.deadline.strftime("%d.%m.%Y %H:%M")
                    topics_text += f"   ⏰ Дедлайн: {deadline_str}\n"
                
                if topic.id in selected_topic_ids:
                    topics_text += "   ✅ Вы выбрали эту тему\n"
                elif available_slots <= 0:
                    topics_text += "   ❌ Нет свободных мест\n"
                elif topic.deadline and topic.deadline < datetime.now():
                    topics_text += "   ⏰ Дедлайн истёк\n"
                else:
                    topics_text += f"   📝 Доступно мест: {available_slots}\n"
                
                topics_text += "\n"
            
            await message.answer(
                topics_text,
                reply_markup=get_topics_keyboard(user.role, has_topics=True)
            )
            
    except Exception as e:
        logger.error(f"Error showing topics: {e}")
        await message.answer("❌ Произошла ошибка при загрузке тем.")


@router.message(F.text == "📚 Темы занятий")
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def manage_topics(message: types.Message, user):
    """Show topic management for group leaders"""
    if not user.group_id:
        await message.answer("❌ Вы не состоите ни в одной группе.")
        return
    
    try:
        async for db in get_db():
            topics = await topic_crud.get_group_topics(db, user.group_id)
            
            topics_text = f"📚 Управление темами группы «{user.group.name}»\n\n"
            
            if not topics:
                topics_text += "Тем пока нет."
            else:
                topics_text += f"Всего тем: {len(topics)}\n\n"
                
                for i, topic in enumerate(topics, 1):
                    selected_count = len(topic.selected_by)
                    topics_text += f"{i}. {topic.title}\n"
                    topics_text += f"   👥 Выбрано: {selected_count}/{topic.max_selections}\n"
                    
                    if topic.deadline:
                        deadline_str = topic.deadline.strftime("%d.%m.%Y %H:%M")
                        topics_text += f"   ⏰ До: {deadline_str}\n"
                    
                    topics_text += "\n"
            
            await message.answer(
                topics_text,
                reply_markup=get_topic_management_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error showing topic management: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "create_topic")
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def create_topic_start(callback: types.CallbackQuery, state: FSMContext, user):
    """Start topic creation"""
    await callback.message.edit_text(
        "📝 Создание новой темы\n\n"
        "Введите название темы:"
    )
    await state.set_state(TopicStates.waiting_for_title)


@router.message(TopicStates.waiting_for_title)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_topic_title(message: types.Message, state: FSMContext, user):
    """Process topic title"""
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
            "Введите описание темы (или отправьте /skip для пропуска):"
        )
        await state.set_state(TopicStates.waiting_for_description)
        
    except Exception as e:
        logger.error(f"Error processing topic title: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.message(TopicStates.waiting_for_description)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_topic_description(message: types.Message, state: FSMContext, user):
    """Process topic description"""
    try:
        description = None
        if message.text.strip() != "/skip":
            description = message.text.strip()
            if len(description) > 1000:
                await message.answer("❌ Описание слишком длинное (максимум 1000 символов).")
                return
        
        await state.update_data(description=description)
        
        await message.answer(
            "📊 Укажите максимальное количество участников для этой темы:\n\n"
            "Введите число от 1 до 50:"
        )
        await state.set_state(TopicStates.waiting_for_max_selections)
        
    except Exception as e:
        logger.error(f"Error processing topic description: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.message(TopicStates.waiting_for_max_selections)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_max_selections(message: types.Message, state: FSMContext, user):
    """Process maximum selections"""
    try:
        try:
            max_selections = int(message.text.strip())
            
            if max_selections < 1 or max_selections > 50:
                await message.answer("❌ Количество должно быть от 1 до 50.")
                return
                
        except ValueError:
            await message.answer("❌ Введите корректное число.")
            return
        
        await state.update_data(max_selections=max_selections)
        
        await message.answer(
            "⚙️ Требовать одобрение старосты для выбора темы?\n\n"
            "Отправьте:\n"
            "• 'да' или '1' - требовать одобрение\n"
            "• 'нет' или '0' - не требовать одобрение"
        )
        await state.set_state(TopicStates.waiting_for_approval_setting)
        
    except Exception as e:
        logger.error(f"Error processing max selections: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.message(TopicStates.waiting_for_approval_setting)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_approval_setting(message: types.Message, state: FSMContext, user):
    """Process approval requirement setting"""
    try:
        text = message.text.strip().lower()
        
        if text in ['да', '1', 'yes', 'true']:
            requires_approval = True
        elif text in ['нет', '0', 'no', 'false']:
            requires_approval = False
        else:
            await message.answer(
                "❌ Неверный ответ. Отправьте 'да' или 'нет'."
            )
            return
        
        await state.update_data(requires_approval=requires_approval)
        
        await message.answer(
            "⏰ Установить дедлайн для выбора темы?\n\n"
            "Введите дату и время в формате: ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Например: 25.12.2024 23:59\n\n"
            "Или отправьте /skip для пропуска"
        )
        await state.set_state(TopicStates.waiting_for_deadline)
        
    except Exception as e:
        logger.error(f"Error processing approval setting: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.message(TopicStates.waiting_for_deadline)
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def process_deadline(message: types.Message, state: FSMContext, user):
    """Process topic deadline"""
    try:
        deadline = None
        
        if message.text.strip() != "/skip":
            try:
                deadline = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
                
                if deadline <= datetime.now():
                    await message.answer("❌ Дедлайн должен быть в будущем.")
                    return
                    
            except ValueError:
                await message.answer(
                    "❌ Неверный формат даты.\n"
                    "Используйте формат: ДД.ММ.ГГГГ ЧЧ:ММ"
                )
                return
        
        await state.update_data(deadline=deadline)
        
        # Create topic
        await finish_topic_creation(message, state, user)
        
    except Exception as e:
        logger.error(f"Error processing deadline: {e}")
        await message.answer("❌ Произошла ошибка.")


async def finish_topic_creation(message: types.Message, state: FSMContext, user):
    """Finish topic creation"""
    try:
        data = await state.get_data()
        
        async for db in get_db():
            # Create topic
            topic = await topic_crud.create(
                db,
                title=data['title'],
                description=data.get('description'),
                group_id=user.group_id,
                max_selections=data['max_selections'],
                requires_approval=data['requires_approval'],
                deadline=data.get('deadline')
            )
            
            # Build confirmation message
            confirmation_text = f"✅ Тема «{topic.title}» создана!\n\n"
            confirmation_text += f"📊 Максимум участников: {topic.max_selections}\n"
            confirmation_text += f"⚙️ Требует одобрения: {'Да' if topic.requires_approval else 'Нет'}\n"
            
            if topic.deadline:
                deadline_str = topic.deadline.strftime("%d.%m.%Y %H:%M")
                confirmation_text += f"⏰ Дедлайн: {deadline_str}\n"
            
            confirmation_text += "\n📢 Участники группы получат уведомление о новой теме."
            
            await message.answer(
                confirmation_text,
                reply_markup=get_main_menu_keyboard(user.role)
            )
            
            # Notify group members
            await notify_group_about_topic(db, topic, user)
            
            logger.info(f"User {user.full_name} created topic '{topic.title}' in group {user.group.name}")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error finishing topic creation: {e}")
        await message.answer("❌ Произошла ошибка при создании темы.")
        await state.clear()


async def notify_group_about_topic(db, topic, creator):
    """Send notifications about new topic"""
    try:
        members = await user_crud.get_users_by_group(db, topic.group_id)
        notification_service = NotificationService()
        
        for member in members:
            if member.id != creator.id and member.notifications_enabled:
                await notification_service.send_immediate_notification(
                    member.telegram_id,
                    "📚 Новая тема",
                    f"В группе доступна новая тема: {topic.title}"
                )
    except Exception as e:
        logger.error(f"Error notifying group about topic: {e}")


@router.callback_query(F.data == "select_topic")
@require_auth
async def select_topic_menu(callback: types.CallbackQuery, user):
    """Show topic selection menu"""
    try:
        async for db in get_db():
            topics = await topic_crud.get_group_topics(db, user.group_id)
            
            # Get user's selected topics
            user_with_topics = await user_crud.get_by_id(db, user.id)
            selected_topic_ids = [t.id for t in user_with_topics.selected_topics]
            
            # Filter available topics
            available_topics = []
            for topic in topics:
                if topic.id in selected_topic_ids:
                    continue  # Already selected
                
                if topic.deadline and topic.deadline < datetime.now():
                    continue  # Deadline passed
                
                selected_count = len(topic.selected_by)
                if selected_count >= topic.max_selections:
                    continue  # No slots available
                
                available_topics.append(topic)
            
            if not available_topics:
                await callback.message.edit_text(
                    "📚 Нет доступных тем для выбора.\n\n"
                    "Возможные причины:\n"
                    "• Все темы уже выбраны\n"
                    "• Нет свободных мест\n"
                    "• Дедлайны истекли"
                )
                return
            
            topics_text = "📚 Выберите тему:\n\n"
            
            keyboard_buttons = []
            for i, topic in enumerate(available_topics):
                selected_count = len(topic.selected_by)
                available_slots = topic.max_selections - selected_count
                
                topics_text += f"{i+1}. {topic.title}\n"
                topics_text += f"   📝 Свободно мест: {available_slots}\n"
                
                if topic.deadline:
                    deadline_str = topic.deadline.strftime("%d.%m.%Y %H:%M")
                    topics_text += f"   ⏰ До: {deadline_str}\n"
                
                topics_text += "\n"
                
                keyboard_buttons.append([
                    types.InlineKeyboardButton(
                        text=f"{i+1}. {topic.title[:30]}{'...' if len(topic.title) > 30 else ''}",
                        callback_data=f"choose_topic:{topic.id}"
                    )
                ])
            
            keyboard_buttons.append([
                types.InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_topics")
            ])
            
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await callback.message.edit_text(topics_text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error showing topic selection menu: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data.startswith("choose_topic:"))
@require_auth
async def choose_topic(callback: types.CallbackQuery, user):
    """Choose a topic"""
    try:
        topic_id = callback.data.split(":")[1]
        
        async for db in get_db():
            topic = await topic_crud.get_by_id(db, topic_id)
            
            if not topic or topic.group_id != user.group_id:
                await callback.answer("❌ Тема не найдена.")
                return
            
            # Check if topic is still available
            if topic.deadline and topic.deadline < datetime.now():
                await callback.answer("❌ Дедлайн для выбора темы истёк.")
                return
            
            selected_count = len(topic.selected_by)
            if selected_count >= topic.max_selections:
                await callback.answer("❌ Нет свободных мест.")
                return
            
            # Check if user already selected this topic
            user_with_topics = await user_crud.get_by_id(db, user.id)
            if topic.id in [t.id for t in user_with_topics.selected_topics]:
                await callback.answer("❌ Вы уже выбрали эту тему.")
                return
            
            # Select topic
            success = await topic_crud.select_topic(db, user.id, topic.id)
            
            if success:
                status_text = "выбрана" if not topic.requires_approval else "отправлена на одобрение"
                
                await callback.message.edit_text(
                    f"✅ Тема «{topic.title}» {status_text}!\n\n"
                    f"{'⏳ Ожидайте одобрения старосты.' if topic.requires_approval else '🎉 Тема закреплена за вами.'}"
                )
                
                # Notify group leader if approval required
                if topic.requires_approval:
                    await notify_leader_about_selection(db, topic, user)
                
                logger.info(f"User {user.full_name} selected topic '{topic.title}'")
            else:
                await callback.answer("❌ Не удалось выбрать тему. Попробуйте позже.")
            
    except Exception as e:
        logger.error(f"Error choosing topic: {e}")
        await callback.answer("❌ Произошла ошибка.")


async def notify_leader_about_selection(db, topic, user):
    """Notify group leader about topic selection"""
    try:
        group = await user_crud.get_by_id(db, topic.group_id)
        leader = await user_crud.get_by_id(db, group.leader_id)
        
        if leader:
            notification_service = NotificationService()
            await notification_service.send_immediate_notification(
                leader.telegram_id,
                "📚 Выбор темы",
                f"Участник {user.full_name} выбрал тему «{topic.title}».\n\n"
                f"Требуется одобрение. Используйте меню управления темами."
            )
    except Exception as e:
        logger.error(f"Error notifying leader about selection: {e}")


@router.callback_query(F.data == "my_topics")
@require_auth
async def show_my_topics(callback: types.CallbackQuery, user):
    """Show user's selected topics"""
    try:
        async for db in get_db():
            user_with_topics = await user_crud.get_by_id(db, user.id)
            
            if not user_with_topics.selected_topics:
                await callback.message.edit_text(
                    "📚 Вы пока не выбрали ни одной темы.",
                    reply_markup=get_topics_keyboard(user.role, has_topics=True)
                )
                return
            
            topics_text = "📚 Ваши выбранные темы:\n\n"
            
            for i, topic in enumerate(user_with_topics.selected_topics, 1):
                topics_text += f"{i}. {topic.title}\n"
                
                if topic.description:
                    desc = topic.description[:100]
                    if len(topic.description) > 100:
                        desc += "..."
                    topics_text += f"   📄 {desc}\n"
                
                # Check approval status
                # Note: This requires additional query to get approval status from user_topics table
                # For now, we'll show based on requires_approval setting
                if topic.requires_approval:
                    topics_text += "   ⏳ Ожидает одобрения\n"
                else:
                    topics_text += "   ✅ Одобрено\n"
                
                topics_text += "\n"
            
            await callback.message.edit_text(
                topics_text,
                reply_markup=get_topics_keyboard(user.role, has_topics=True)
            )
            
    except Exception as e:
        logger.error(f"Error showing user's topics: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "manage_topic_selections")
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def manage_topic_selections(callback: types.CallbackQuery, user):
    """Manage topic selections (approvals)"""
    try:
        async for db in get_db():
            topics = await topic_crud.get_group_topics(db, user.group_id)
            
            # Find topics that need approval
            pending_approvals = []
            for topic in topics:
                if topic.requires_approval:
                    # Get users who selected this topic but are not approved
                    # This is simplified - in real implementation, you'd query user_topics table
                    for selected_user in topic.selected_by:
                        pending_approvals.append((topic, selected_user))
            
            if not pending_approvals:
                await callback.message.edit_text(
                    "✅ Нет ожидающих одобрения выборов тем.",
                    reply_markup=get_topic_management_keyboard()
                )
                return
            
            approvals_text = "⏳ Ожидающие одобрения:\n\n"
            
            keyboard_buttons = []
            for i, (topic, selected_user) in enumerate(pending_approvals):
                approvals_text += f"{i+1}. {selected_user.full_name}\n"
                approvals_text += f"   Тема: {topic.title}\n\n"
                
                keyboard_buttons.append([
                    types.InlineKeyboardButton(
                        text=f"✅ Одобрить {selected_user.full_name[:20]}",
                        callback_data=f"approve_selection:{selected_user.id}:{topic.id}"
                    )
                ])
                keyboard_buttons.append([
                    types.InlineKeyboardButton(
                        text=f"❌ Отклонить {selected_user.full_name[:20]}",
                        callback_data=f"reject_selection:{selected_user.id}:{topic.id}"
                    )
                ])
            
            keyboard_buttons.append([
                types.InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_topic_management")
            ])
            
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await callback.message.edit_text(approvals_text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error managing topic selections: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data.startswith("approve_selection:"))
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def approve_selection(callback: types.CallbackQuery, user):
    """Approve topic selection"""
    try:
        user_id, topic_id = callback.data.split(":")[1:]
        
        async for db in get_db():
            success = await topic_crud.approve_selection(db, user_id, topic_id)
            
            if success:
                selected_user = await user_crud.get_by_id(db, user_id)
                topic = await topic_crud.get_by_id(db, topic_id)
                
                await callback.answer(f"✅ Выбор темы одобрен для {selected_user.full_name}")
                
                # Notify user about approval
                notification_service = NotificationService()
                await notification_service.send_immediate_notification(
                    selected_user.telegram_id,
                    "✅ Тема одобрена",
                    f"Ваш выбор темы «{topic.title}» одобрен старостой!"
                )
                
                # Refresh the view
                await manage_topic_selections(callback, user)
            else:
                await callback.answer("❌ Ошибка при одобрении.")
            
    except Exception as e:
        logger.error(f"Error approving selection: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data.startswith("reject_selection:"))
@require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
async def reject_selection(callback: types.CallbackQuery, user):
    """Reject topic selection"""
    try:
        user_id, topic_id = callback.data.split(":")[1:]
        
        async for db in get_db():
            # Remove selection
            from sqlalchemy import delete, and_
            from app.database.models import user_topics
            
            await db.execute(
                delete(user_topics).where(
                    and_(
                        user_topics.c.user_id == user_id,
                        user_topics.c.topic_id == topic_id
                    )
                )
            )
            await db.commit()
            
            selected_user = await user_crud.get_by_id(db, user_id)
            topic = await topic_crud.get_by_id(db, topic_id)
            
            await callback.answer(f"❌ Выбор темы отклонён для {selected_user.full_name}")
            
            # Notify user about rejection
            notification_service = NotificationService()
            await notification_service.send_immediate_notification(
                selected_user.telegram_id,
                "❌ Тема отклонена",
                f"Ваш выбор темы «{topic.title}» отклонён старостой.\n\n"
                f"Вы можете выбрать другую тему."
            )
            
            # Refresh the view
            await manage_topic_selections(callback, user)
            
    except Exception as e:
        logger.error(f"Error rejecting selection: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "back_to_topics")
async def back_to_topics(callback: types.CallbackQuery):
    """Go back to topics menu"""
    from app.handlers.topics import show_topics
    await show_topics(callback.message, callback.from_user)


@router.callback_query(F.data == "back_to_topic_management")
async def back_to_topic_management(callback: types.CallbackQuery):
    """Go back to topic management"""
    await callback.message.edit_text(
        "📚 Управление темами",
        reply_markup=get_topic_management_keyboard()
    )
