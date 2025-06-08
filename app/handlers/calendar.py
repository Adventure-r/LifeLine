"""
Calendar and booking handlers
"""

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger
from datetime import datetime, date, timedelta
import calendar

from app.database.database import get_db
from app.database.crud import event_crud, user_crud
from app.database.models import UserRole
from app.keyboards.inline import get_calendar_keyboard, get_calendar_navigation_keyboard
from app.utils.decorators import require_auth
from app.states.states import CalendarStates

router = Router()


@router.message(F.text == "📋 Календарь")
@require_auth
async def show_calendar(message: types.Message, user):
    """Show calendar for current month"""
    if not user.group_id:
        await message.answer("❌ Вы не состоите ни в одной группе.")
        return
    
    try:
        today = date.today()
        await send_calendar(message, user, today.year, today.month)
        
    except Exception as e:
        logger.error(f"Error showing calendar: {e}")
        await message.answer("❌ Произошла ошибка при загрузке календаря.")


async def send_calendar(message: types.Message, user, year: int, month: int):
    """Send calendar for specified month"""
    try:
        async for db in get_db():
            # Get events for the month
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
            
            # Get all events for the month
            month_events = {}
            for day in range(1, end_date.day + 1):
                check_date = date(year, month, day)
                day_events = await event_crud.get_events_by_date(db, user.group_id, check_date)
                if day_events:
                    month_events[day] = day_events
            
            # Build calendar text
            calendar_text = f"📋 Календарь - {get_month_name(month)} {year}\n\n"
            
            # Calendar header
            calendar_text += "Пн Вт Ср Чт Пт Сб Вс\n"
            
            # Get calendar data
            cal = calendar.monthcalendar(year, month)
            
            for week in cal:
                week_line = ""
                for day in week:
                    if day == 0:
                        week_line += "   "
                    else:
                        if day in month_events:
                            week_line += f"{day:2d}●"  # Mark days with events
                        else:
                            week_line += f"{day:2d} "
                    week_line += " "
                calendar_text += week_line + "\n"
            
            calendar_text += "\n● - дни с событиями\n"
            
            # Show today's events if current month
            today = date.today()
            if year == today.year and month == today.month and today.day in month_events:
                calendar_text += f"\n📅 События сегодня ({today.day}.{today.month}):\n"
                for event in month_events[today.day]:
                    event_emoji = get_event_emoji(event.event_type)
                    calendar_text += f"{event_emoji} {event.title}"
                    if event.start_time:
                        calendar_text += f" в {event.start_time}"
                    calendar_text += "\n"
            
            # Show upcoming events in this month
            upcoming_in_month = []
            for day, events in month_events.items():
                event_date = date(year, month, day)
                if event_date >= today:
                    upcoming_in_month.extend([(event_date, event) for event in events])
            
            if upcoming_in_month:
                upcoming_in_month.sort(key=lambda x: x[0])
                calendar_text += f"\n📆 Предстоящие события:\n"
                for event_date, event in upcoming_in_month[:5]:  # Show max 5
                    event_emoji = get_event_emoji(event.event_type)
                    calendar_text += f"{event_emoji} {event_date.day}.{event_date.month} - {event.title}\n"
                
                if len(upcoming_in_month) > 5:
                    calendar_text += f"... и ещё {len(upcoming_in_month) - 5} событий\n"
            
            keyboard = get_calendar_navigation_keyboard(year, month, list(month_events.keys()))
            
            if hasattr(message, 'edit_text'):
                await message.edit_text(calendar_text, reply_markup=keyboard)
            else:
                await message.answer(calendar_text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error sending calendar: {e}")
        await message.answer("❌ Произошла ошибка при загрузке календаря.")


@router.callback_query(F.data.startswith("calendar_nav:"))
@require_auth
async def navigate_calendar(callback: types.CallbackQuery, user):
    """Navigate calendar months"""
    try:
        action, year, month = callback.data.split(":")[1:]
        year, month = int(year), int(month)
        
        if action == "prev":
            if month == 1:
                year -= 1
                month = 12
            else:
                month -= 1
        elif action == "next":
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1
        
        await send_calendar(callback.message, user, year, month)
        
    except Exception as e:
        logger.error(f"Error navigating calendar: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data.startswith("calendar_day:"))
@require_auth
async def show_day_events(callback: types.CallbackQuery, user):
    """Show events for specific day"""
    try:
        year, month, day = callback.data.split(":")[1:]
        year, month, day = int(year), int(month), int(day)
        
        event_date = date(year, month, day)
        
        async for db in get_db():
            day_events = await event_crud.get_events_by_date(db, user.group_id, event_date)
            
            date_str = event_date.strftime("%d.%m.%Y")
            
            if not day_events:
                await callback.message.edit_text(
                    f"📅 {date_str}\n\nНа этот день событий нет.",
                    reply_markup=get_calendar_keyboard(year, month)
                )
                return
            
            events_text = f"📅 События на {date_str}:\n\n"
            
            for i, event in enumerate(day_events, 1):
                event_emoji = get_event_emoji(event.event_type)
                events_text += f"{i}. {event_emoji} {event.title}\n"
                
                if event.start_time:
                    time_str = event.start_time
                    if event.end_time:
                        time_str += f" - {event.end_time}"
                    events_text += f"   🕐 {time_str}\n"
                
                if event.description:
                    # Show first 50 characters of description
                    desc = event.description[:50]
                    if len(event.description) > 50:
                        desc += "..."
                    events_text += f"   📄 {desc}\n"
                
                if event.is_important:
                    events_text += "   ⭐ Важное\n"
                
                events_text += "\n"
            
            await callback.message.edit_text(
                events_text,
                reply_markup=get_calendar_keyboard(year, month)
            )
            
    except Exception as e:
        logger.error(f"Error showing day events: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data.startswith("back_to_calendar:"))
@require_auth
async def back_to_calendar(callback: types.CallbackQuery, user):
    """Go back to calendar view"""
    try:
        year, month = callback.data.split(":")[1:]
        year, month = int(year), int(month)
        
        await send_calendar(callback.message, user, year, month)
        
    except Exception as e:
        logger.error(f"Error going back to calendar: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "calendar_today")
@require_auth
async def show_today_calendar(callback: types.CallbackQuery, user):
    """Show today's calendar"""
    try:
        today = date.today()
        await send_calendar(callback.message, user, today.year, today.month)
        
    except Exception as e:
        logger.error(f"Error showing today's calendar: {e}")
        await callback.answer("❌ Произошла ошибка.")


@router.callback_query(F.data == "calendar_week")
@require_auth
async def show_week_view(callback: types.CallbackQuery, user):
    """Show week view"""
    try:
        if not user.group_id:
            await callback.answer("❌ Вы не состоите ни в одной группе.")
            return
        
        today = date.today()
        
        # Get start of week (Monday)
        start_of_week = today - timedelta(days=today.weekday())
        
        async for db in get_db():
            week_text = f"📅 Неделя {start_of_week.strftime('%d.%m')} - {(start_of_week + timedelta(days=6)).strftime('%d.%m.%Y')}\n\n"
            
            for i in range(7):
                day = start_of_week + timedelta(days=i)
                day_name = get_day_name(i)
                
                day_events = await event_crud.get_events_by_date(db, user.group_id, day)
                
                week_text += f"{day_name} {day.strftime('%d.%m')}"
                
                if day == today:
                    week_text += " (сегодня)"
                
                week_text += ":\n"
                
                if day_events:
                    for event in day_events:
                        event_emoji = get_event_emoji(event.event_type)
                        week_text += f"  {event_emoji} {event.title}"
                        if event.start_time:
                            week_text += f" в {event.start_time}"
                        if event.is_important:
                            week_text += " ⭐"
                        week_text += "\n"
                else:
                    week_text += "  Событий нет\n"
                
                week_text += "\n"
            
            await callback.message.edit_text(
                week_text,
                reply_markup=get_calendar_keyboard(today.year, today.month)
            )
            
    except Exception as e:
        logger.error(f"Error showing week view: {e}")
        await callback.answer("❌ Произошла ошибка.")


def get_month_name(month: int) -> str:
    """Get month name in Russian"""
    months = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }
    return months.get(month, str(month))


def get_day_name(weekday: int) -> str:
    """Get day name in Russian"""
    days = {
        0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт",
        4: "Пт", 5: "Сб", 6: "Вс"
    }
    return days.get(weekday, str(weekday))


def get_event_emoji(event_type) -> str:
    """Get emoji for event type"""
    from app.database.models import EventType
    
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
