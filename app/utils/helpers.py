"""
Helper functions and utilities
"""

import re
import uuid
import hashlib
import mimetypes
from datetime import datetime, date, time, timedelta
from typing import Optional, Union, List, Dict, Any
from urllib.parse import urlparse
import pytz
from loguru import logger

from app.config import settings


def format_datetime(dt: datetime, format_string: str = "%d.%m.%Y %H:%M") -> str:
    """
    Format datetime object to string
    
    Args:
        dt: DateTime object
        format_string: Format string
        
    Returns:
        str: Formatted datetime string
    """
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=settings.timezone_obj)
        return dt.strftime(format_string)
    except Exception as e:
        logger.error(f"Error formatting datetime: {e}")
        return str(dt)


def format_date(d: date, format_string: str = "%d.%m.%Y") -> str:
    """
    Format date object to string
    
    Args:
        d: Date object
        format_string: Format string
        
    Returns:
        str: Formatted date string
    """
    try:
        return d.strftime(format_string)
    except Exception as e:
        logger.error(f"Error formatting date: {e}")
        return str(d)


def format_time(t: time, format_string: str = "%H:%M") -> str:
    """
    Format time object to string
    
    Args:
        t: Time object
        format_string: Format string
        
    Returns:
        str: Formatted time string
    """
    try:
        return t.strftime(format_string)
    except Exception as e:
        logger.error(f"Error formatting time: {e}")
        return str(t)


def parse_datetime(dt_string: str, format_string: str = "%d.%m.%Y %H:%M") -> Optional[datetime]:
    """
    Parse datetime string to datetime object
    
    Args:
        dt_string: DateTime string
        format_string: Format string
        
    Returns:
        datetime: Parsed datetime object or None if failed
    """
    try:
        return datetime.strptime(dt_string, format_string)
    except Exception as e:
        logger.error(f"Error parsing datetime '{dt_string}': {e}")
        return None


def parse_date(date_string: str, format_string: str = "%d.%m.%Y") -> Optional[date]:
    """
    Parse date string to date object
    
    Args:
        date_string: Date string
        format_string: Format string
        
    Returns:
        date: Parsed date object or None if failed
    """
    try:
        return datetime.strptime(date_string, format_string).date()
    except Exception as e:
        logger.error(f"Error parsing date '{date_string}': {e}")
        return None


def parse_time(time_string: str, format_string: str = "%H:%M") -> Optional[time]:
    """
    Parse time string to time object
    
    Args:
        time_string: Time string
        format_string: Format string
        
    Returns:
        time: Parsed time object or None if failed
    """
    try:
        return datetime.strptime(time_string, format_string).time()
    except Exception as e:
        logger.error(f"Error parsing time '{time_string}': {e}")
        return None


def get_user_timezone(timezone_name: str = None) -> pytz.BaseTzInfo:
    """
    Get user timezone object
    
    Args:
        timezone_name: Timezone name (defaults to app timezone)
        
    Returns:
        pytz.BaseTzInfo: Timezone object
    """
    try:
        if timezone_name:
            return pytz.timezone(timezone_name)
        return settings.timezone_obj
    except Exception as e:
        logger.error(f"Error getting timezone '{timezone_name}': {e}")
        return pytz.UTC


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Formatted size string
    """
    try:
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    except Exception as e:
        logger.error(f"Error formatting file size: {e}")
        return "Unknown"


def generate_pagination_text(
    current_page: int, 
    total_pages: int, 
    items_per_page: int, 
    total_items: int
) -> str:
    """
    Generate pagination information text
    
    Args:
        current_page: Current page number (1-based)
        total_pages: Total number of pages
        items_per_page: Items per page
        total_items: Total number of items
        
    Returns:
        str: Pagination text
    """
    try:
        if total_items == 0:
            return "Нет элементов для отображения"
        
        start_item = (current_page - 1) * items_per_page + 1
        end_item = min(current_page * items_per_page, total_items)
        
        return f"Показано {start_item}-{end_item} из {total_items} (стр. {current_page}/{total_pages})"
    except Exception as e:
        logger.error(f"Error generating pagination text: {e}")
        return ""


def escape_markdown(text: str) -> str:
    """
    Escape markdown special characters
    
    Args:
        text: Text to escape
        
    Returns:
        str: Escaped text
    """
    try:
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
    except Exception as e:
        logger.error(f"Error escaping markdown: {e}")
        return text


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        str: Truncated text
    """
    try:
        if not text:
            return ""
        
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    except Exception as e:
        logger.error(f"Error truncating text: {e}")
        return text


def get_file_extension(filename: str) -> Optional[str]:
    """
    Get file extension from filename
    
    Args:
        filename: Filename
        
    Returns:
        str: File extension (without dot) or None
    """
    try:
        if not filename:
            return None
        
        _, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        return ext.lower() if ext else None
    except Exception as e:
        logger.error(f"Error getting file extension: {e}")
        return None


def is_valid_url(url: str) -> bool:
    """
    Validate URL format
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if valid URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception as e:
        logger.error(f"Error validating URL: {e}")
        return False


def generate_uuid() -> str:
    """
    Generate UUID string
    
    Returns:
        str: UUID string
    """
    return str(uuid.uuid4())


def hash_string(text: str, algorithm: str = "sha256") -> str:
    """
    Hash string using specified algorithm
    
    Args:
        text: Text to hash
        algorithm: Hash algorithm (md5, sha1, sha256, etc.)
        
    Returns:
        str: Hashed string
    """
    try:
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(text.encode('utf-8'))
        return hash_obj.hexdigest()
    except Exception as e:
        logger.error(f"Error hashing string: {e}")
        return text


def validate_telegram_id(telegram_id: Union[str, int]) -> bool:
    """
    Validate Telegram user ID format
    
    Args:
        telegram_id: Telegram ID to validate
        
    Returns:
        bool: True if valid
    """
    try:
        if isinstance(telegram_id, str):
            telegram_id = int(telegram_id)
        
        # Telegram user IDs are positive integers
        return isinstance(telegram_id, int) and telegram_id > 0
    except (ValueError, TypeError):
        return False


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human readable format
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        str: Formatted duration
    """
    try:
        if seconds < 60:
            return f"{seconds} сек."
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} мин."
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours} ч. {minutes} мин."
            return f"{hours} ч."
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            if hours > 0:
                return f"{days} дн. {hours} ч."
            return f"{days} дн."
    except Exception as e:
        logger.error(f"Error formatting duration: {e}")
        return f"{seconds} сек."


def get_time_ago(dt: datetime) -> str:
    """
    Get human readable time ago string
    
    Args:
        dt: DateTime object
        
    Returns:
        str: Time ago string
    """
    try:
        now = datetime.now()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=settings.timezone_obj)
        if now.tzinfo is None:
            now = now.replace(tzinfo=settings.timezone_obj)
        
        diff = now - dt
        
        if diff.days > 0:
            if diff.days == 1:
                return "вчера"
            elif diff.days < 7:
                return f"{diff.days} дн. назад"
            elif diff.days < 30:
                weeks = diff.days // 7
                return f"{weeks} нед. назад"
            elif diff.days < 365:
                months = diff.days // 30
                return f"{months} мес. назад"
            else:
                years = diff.days // 365
                return f"{years} г. назад"
        
        seconds = diff.seconds
        if seconds < 60:
            return "только что"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} мин. назад"
        else:
            hours = seconds // 3600
            return f"{hours} ч. назад"
    except Exception as e:
        logger.error(f"Error getting time ago: {e}")
        return "неизвестно"


def get_mime_type(filename: str) -> Optional[str]:
    """
    Get MIME type from filename
    
    Args:
        filename: Filename
        
    Returns:
        str: MIME type or None
    """
    try:
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type
    except Exception as e:
        logger.error(f"Error getting MIME type: {e}")
        return None


def is_image_file(filename: str) -> bool:
    """
    Check if file is an image based on extension
    
    Args:
        filename: Filename
        
    Returns:
        bool: True if image file
    """
    try:
        mime_type = get_mime_type(filename)
        return mime_type is not None and mime_type.startswith('image/')
    except Exception:
        return False


def is_video_file(filename: str) -> bool:
    """
    Check if file is a video based on extension
    
    Args:
        filename: Filename
        
    Returns:
        bool: True if video file
    """
    try:
        mime_type = get_mime_type(filename)
        return mime_type is not None and mime_type.startswith('video/')
    except Exception:
        return False


def is_document_file(filename: str) -> bool:
    """
    Check if file is a document based on extension
    
    Args:
        filename: Filename
        
    Returns:
        bool: True if document file
    """
    try:
        document_extensions = {
            'pdf', 'doc', 'docx', 'txt', 'rtf', 'odt',
            'xls', 'xlsx', 'ods', 'ppt', 'pptx', 'odp'
        }
        ext = get_file_extension(filename)
        return ext in document_extensions if ext else False
    except Exception:
        return False


def clean_phone_number(phone: str) -> str:
    """
    Clean and format phone number
    
    Args:
        phone: Phone number string
        
    Returns:
        str: Cleaned phone number
    """
    try:
        # Remove all non-digit characters
        cleaned = re.sub(r'\D', '', phone)
        
        # Add country code if missing (assuming Russian numbers)
        if cleaned.startswith('8') and len(cleaned) == 11:
            cleaned = '7' + cleaned[1:]
        elif len(cleaned) == 10:
            cleaned = '7' + cleaned
        
        return cleaned
    except Exception as e:
        logger.error(f"Error cleaning phone number: {e}")
        return phone


def format_phone_number(phone: str) -> str:
    """
    Format phone number for display
    
    Args:
        phone: Phone number string
        
    Returns:
        str: Formatted phone number
    """
    try:
        cleaned = clean_phone_number(phone)
        
        if len(cleaned) == 11 and cleaned.startswith('7'):
            return f"+7 ({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:9]}-{cleaned[9:11]}"
        
        return phone
    except Exception as e:
        logger.error(f"Error formatting phone number: {e}")
        return phone


def generate_random_string(length: int = 8, chars: str = None) -> str:
    """
    Generate random string
    
    Args:
        length: String length
        chars: Characters to use (defaults to alphanumeric)
        
    Returns:
        str: Random string
    """
    import string
    import secrets
    
    try:
        if chars is None:
            chars = string.ascii_letters + string.digits
        
        return ''.join(secrets.choice(chars) for _ in range(length))
    except Exception as e:
        logger.error(f"Error generating random string: {e}")
        return "random"


def chunks(lst: List[Any], n: int) -> List[List[Any]]:
    """
    Split list into chunks of size n
    
    Args:
        lst: List to split
        n: Chunk size
        
    Returns:
        List[List]: List of chunks
    """
    try:
        for i in range(0, len(lst), n):
            yield lst[i:i + n]
    except Exception as e:
        logger.error(f"Error splitting list into chunks: {e}")
        return [lst]


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert value to integer
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        int: Converted integer or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        float: Converted float or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def get_week_bounds(dt: datetime = None) -> tuple[datetime, datetime]:
    """
    Get start and end of week for given datetime
    
    Args:
        dt: DateTime object (defaults to now)
        
    Returns:
        tuple: (week_start, week_end)
    """
    try:
        if dt is None:
            dt = datetime.now()
        
        # Start of week (Monday)
        start = dt - timedelta(days=dt.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # End of week (Sunday)
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        return start, end
    except Exception as e:
        logger.error(f"Error getting week bounds: {e}")
        now = datetime.now()
        return now, now


def get_month_bounds(dt: datetime = None) -> tuple[datetime, datetime]:
    """
    Get start and end of month for given datetime
    
    Args:
        dt: DateTime object (defaults to now)
        
    Returns:
        tuple: (month_start, month_end)
    """
    try:
        if dt is None:
            dt = datetime.now()
        
        # Start of month
        start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # End of month
        if dt.month == 12:
            next_month = dt.replace(year=dt.year + 1, month=1, day=1)
        else:
            next_month = dt.replace(month=dt.month + 1, day=1)
        
        end = next_month - timedelta(microseconds=1)
        
        return start, end
    except Exception as e:
        logger.error(f"Error getting month bounds: {e}")
        now = datetime.now()
        return now, now
