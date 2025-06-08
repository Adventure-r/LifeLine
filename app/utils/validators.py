"""
Validation functions and utilities
"""

import re
import html
from datetime import datetime, date, time
from typing import Optional, Union, List
from urllib.parse import urlparse
from loguru import logger


def validate_email(email: str) -> bool:
    """
    Validate email address format
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if valid email format
    """
    try:
        if not email or len(email) > 254:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    except Exception as e:
        logger.error(f"Error validating email: {e}")
        return False


def validate_phone(phone: str) -> bool:
    """
    Validate phone number format (Russian format)
    
    Args:
        phone: Phone number to validate
        
    Returns:
        bool: True if valid phone format
    """
    try:
        if not phone:
            return False
        
        # Remove all non-digit characters
        cleaned = re.sub(r'\D', '', phone)
        
        # Check length and format for Russian numbers
        if len(cleaned) == 11 and cleaned.startswith(('7', '8')):
            return True
        elif len(cleaned) == 10 and not cleaned.startswith('0'):
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error validating phone: {e}")
        return False


def validate_username(username: str) -> bool:
    """
    Validate username format (Telegram style)
    
    Args:
        username: Username to validate
        
    Returns:
        bool: True if valid username format
    """
    try:
        if not username:
            return False
        
        # Remove @ if present
        username = username.lstrip('@')
        
        # Telegram username rules: 5-32 characters, alphanumeric + underscore, 
        # must start with letter, can't end with underscore
        if len(username) < 5 or len(username) > 32:
            return False
        
        pattern = r'^[a-zA-Z][a-zA-Z0-9_]*[a-zA-Z0-9]$'
        return bool(re.match(pattern, username))
    except Exception as e:
        logger.error(f"Error validating username: {e}")
        return False


def validate_password(password: str) -> tuple[bool, List[str]]:
    """
    Validate password strength
    
    Args:
        password: Password to validate
        
    Returns:
        tuple: (is_valid, list_of_errors)
    """
    try:
        errors = []
        
        if not password:
            errors.append("Пароль не может быть пустым")
            return False, errors
        
        if len(password) < 8:
            errors.append("Пароль должен содержать минимум 8 символов")
        
        if len(password) > 128:
            errors.append("Пароль слишком длинный (максимум 128 символов)")
        
        if not re.search(r'[a-z]', password):
            errors.append("Пароль должен содержать строчные буквы")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Пароль должен содержать заглавные буквы")
        
        if not re.search(r'\d', password):
            errors.append("Пароль должен содержать цифры")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Пароль должен содержать специальные символы")
        
        return len(errors) == 0, errors
    except Exception as e:
        logger.error(f"Error validating password: {e}")
        return False, ["Ошибка при проверке пароля"]


def validate_group_name(name: str) -> tuple[bool, Optional[str]]:
    """
    Validate group name
    
    Args:
        name: Group name to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        if not name:
            return False, "Название группы не может быть пустым"
        
        name = name.strip()
        
        if len(name) < 3:
            return False, "Название группы должно содержать минимум 3 символа"
        
        if len(name) > 100:
            return False, "Название группы слишком длинное (максимум 100 символов)"
        
        # Check for invalid characters
        if re.search(r'[<>"\']', name):
            return False, "Название группы содержит недопустимые символы"
        
        return True, None
    except Exception as e:
        logger.error(f"Error validating group name: {e}")
        return False, "Ошибка при проверке названия группы"


def validate_event_title(title: str) -> tuple[bool, Optional[str]]:
    """
    Validate event title
    
    Args:
        title: Event title to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        if not title:
            return False, "Название события не может быть пустым"
        
        title = title.strip()
        
        if len(title) < 3:
            return False, "Название события должно содержать минимум 3 символа"
        
        if len(title) > 255:
            return False, "Название события слишком длинное (максимум 255 символов)"
        
        # Check for invalid characters
        if re.search(r'[<>"\']', title):
            return False, "Название события содержит недопустимые символы"
        
        return True, None
    except Exception as e:
        logger.error(f"Error validating event title: {e}")
        return False, "Ошибка при проверке названия события"


def validate_topic_title(title: str) -> tuple[bool, Optional[str]]:
    """
    Validate topic title
    
    Args:
        title: Topic title to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        if not title:
            return False, "Название темы не может быть пустым"
        
        title = title.strip()
        
        if len(title) < 3:
            return False, "Название темы должно содержать минимум 3 символа"
        
        if len(title) > 255:
            return False, "Название темы слишком длинное (максимум 255 символов)"
        
        # Check for invalid characters
        if re.search(r'[<>"\']', title):
            return False, "Название темы содержит недопустимые символы"
        
        return True, None
    except Exception as e:
        logger.error(f"Error validating topic title: {e}")
        return False, "Ошибка при проверке названия темы"


def validate_queue_title(title: str) -> tuple[bool, Optional[str]]:
    """
    Validate queue title
    
    Args:
        title: Queue title to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        if not title:
            return False, "Название очереди не может быть пустым"
        
        title = title.strip()
        
        if len(title) < 3:
            return False, "Название очереди должно содержать минимум 3 символа"
        
        if len(title) > 255:
            return False, "Название очереди слишком длинное (максимум 255 символов)"
        
        # Check for invalid characters
        if re.search(r'[<>"\']', title):
            return False, "Название очереди содержит недопустимые символы"
        
        return True, None
    except Exception as e:
        logger.error(f"Error validating queue title: {e}")
        return False, "Ошибка при проверке названия очереди"


def validate_time_format(time_str: str) -> tuple[bool, Optional[str]]:
    """
    Validate time format (HH:MM)
    
    Args:
        time_str: Time string to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        if not time_str:
            return False, "Время не может быть пустым"
        
        pattern = r'^([0-1][0-9]|2[0-3]):([0-5][0-9])$'
        if not re.match(pattern, time_str):
            return False, "Неверный формат времени. Используйте ЧЧ:ММ"
        
        # Additional validation
        hours, minutes = map(int, time_str.split(':'))
        
        if hours > 23:
            return False, "Часы должны быть от 00 до 23"
        
        if minutes > 59:
            return False, "Минуты должны быть от 00 до 59"
        
        return True, None
    except Exception as e:
        logger.error(f"Error validating time format: {e}")
        return False, "Ошибка при проверке формата времени"


def validate_date_format(date_str: str) -> tuple[bool, Optional[str]]:
    """
    Validate date format (DD.MM.YYYY)
    
    Args:
        date_str: Date string to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        if not date_str:
            return False, "Дата не может быть пустой"
        
        pattern = r'^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.(\d{4})$'
        if not re.match(pattern, date_str):
            return False, "Неверный формат даты. Используйте ДД.ММ.ГГГГ"
        
        # Try to parse the date
        try:
            day, month, year = map(int, date_str.split('.'))
            date(year, month, day)
        except ValueError:
            return False, "Некорректная дата"
        
        return True, None
    except Exception as e:
        logger.error(f"Error validating date format: {e}")
        return False, "Ошибка при проверке формата даты"


def validate_datetime_format(datetime_str: str) -> tuple[bool, Optional[str]]:
    """
    Validate datetime format (DD.MM.YYYY HH:MM)
    
    Args:
        datetime_str: DateTime string to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        if not datetime_str:
            return False, "Дата и время не могут быть пустыми"
        
        pattern = r'^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.(\d{4}) ([0-1][0-9]|2[0-3]):([0-5][0-9])$'
        if not re.match(pattern, datetime_str):
            return False, "Неверный формат даты и времени. Используйте ДД.ММ.ГГГГ ЧЧ:ММ"
        
        # Try to parse the datetime
        try:
            datetime.strptime(datetime_str, "%d.%m.%Y %H:%M")
        except ValueError:
            return False, "Некорректная дата и время"
        
        return True, None
    except Exception as e:
        logger.error(f"Error validating datetime format: {e}")
        return False, "Ошибка при проверке формата даты и времени"


def validate_media_file(file_size: int, file_type: str, filename: str = None) -> tuple[bool, Optional[str]]:
    """
    Validate media file
    
    Args:
        file_size: File size in bytes
        file_type: File type (photo, video, document)
        filename: Optional filename
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        # Size limits (in bytes)
        size_limits = {
            'photo': 10 * 1024 * 1024,      # 10 MB
            'video': 50 * 1024 * 1024,      # 50 MB
            'document': 20 * 1024 * 1024,   # 20 MB
        }
        
        max_size = size_limits.get(file_type, 10 * 1024 * 1024)
        
        if file_size > max_size:
            return False, f"Файл слишком большой. Максимум {max_size // (1024 * 1024)} МБ"
        
        # Validate file extension if filename provided
        if filename:
            allowed_extensions = {
                'photo': {'jpg', 'jpeg', 'png', 'gif', 'webp'},
                'video': {'mp4', 'avi', 'mkv', 'mov', 'wmv'},
                'document': {'pdf', 'doc', 'docx', 'txt', 'rtf', 'xls', 'xlsx', 'ppt', 'pptx'}
            }
            
            extension = filename.split('.')[-1].lower() if '.' in filename else ''
            allowed = allowed_extensions.get(file_type, set())
            
            if allowed and extension not in allowed:
                return False, f"Неподдерживаемый тип файла. Разрешены: {', '.join(allowed)}"
        
        return True, None
    except Exception as e:
        logger.error(f"Error validating media file: {e}")
        return False, "Ошибка при проверке медиафайла"


def validate_text_length(text: str, min_length: int = 0, max_length: int = 1000, field_name: str = "Текст") -> tuple[bool, Optional[str]]:
    """
    Validate text length
    
    Args:
        text: Text to validate
        min_length: Minimum length
        max_length: Maximum length
        field_name: Field name for error messages
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        if not text and min_length > 0:
            return False, f"{field_name} не может быть пустым"
        
        if text and len(text) < min_length:
            return False, f"{field_name} должен содержать минимум {min_length} символов"
        
        if text and len(text) > max_length:
            return False, f"{field_name} слишком длинный (максимум {max_length} символов)"
        
        return True, None
    except Exception as e:
        logger.error(f"Error validating text length: {e}")
        return False, f"Ошибка при проверке длины {field_name.lower()}"


def validate_positive_integer(value: Union[str, int], field_name: str = "Значение", min_value: int = 1, max_value: int = None) -> tuple[bool, Optional[str]]:
    """
    Validate positive integer value
    
    Args:
        value: Value to validate
        field_name: Field name for error messages
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        if isinstance(value, str):
            if not value.isdigit():
                return False, f"{field_name} должно быть числом"
            value = int(value)
        
        if not isinstance(value, int):
            return False, f"{field_name} должно быть числом"
        
        if value < min_value:
            return False, f"{field_name} должно быть не менее {min_value}"
        
        if max_value is not None and value > max_value:
            return False, f"{field_name} должно быть не более {max_value}"
        
        return True, None
    except Exception as e:
        logger.error(f"Error validating positive integer: {e}")
        return False, f"Ошибка при проверке {field_name.lower()}"


def sanitize_html(text: str) -> str:
    """
    Sanitize HTML in text (escape dangerous characters)
    
    Args:
        text: Text to sanitize
        
    Returns:
        str: Sanitized text
    """
    try:
        if not text:
            return text
        
        return html.escape(text)
    except Exception as e:
        logger.error(f"Error sanitizing HTML: {e}")
        return text


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        str: Sanitized filename
    """
    try:
        if not filename:
            return "untitled"
        
        # Remove or replace dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip(' .')
        
        # Limit length
        if len(sanitized) > 255:
            name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
            sanitized = name[:255-len(ext)-1] + '.' + ext if ext else sanitized[:255]
        
        # Ensure filename is not empty
        if not sanitized:
            sanitized = "untitled"
        
        return sanitized
    except Exception as e:
        logger.error(f"Error sanitizing filename: {e}")
        return "untitled"


def validate_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate URL format
    
    Args:
        url: URL to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        if not url:
            return False, "URL не может быть пустым"
        
        # Basic URL pattern
        pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
        
        if not re.match(pattern, url):
            return False, "Неверный формат URL"
        
        # Additional validation using urlparse
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False, "Неполный URL"
        except Exception:
            return False, "Некорректный URL"
        
        return True, None
    except Exception as e:
        logger.error(f"Error validating URL: {e}")
        return False, "Ошибка при проверке URL"


def validate_telegram_id(telegram_id: Union[str, int]) -> tuple[bool, Optional[str]]:
    """
    Validate Telegram user ID
    
    Args:
        telegram_id: Telegram ID to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        if isinstance(telegram_id, str):
            if not telegram_id.isdigit():
                return False, "Telegram ID должен содержать только цифры"
            telegram_id = int(telegram_id)
        
        if not isinstance(telegram_id, int):
            return False, "Telegram ID должен быть числом"
        
        if telegram_id <= 0:
            return False, "Telegram ID должен быть положительным числом"
        
        # Telegram user IDs are typically quite large
        if telegram_id < 1000:
            return False, "Некорректный Telegram ID"
        
        return True, None
    except Exception as e:
        logger.error(f"Error validating Telegram ID: {e}")
        return False, "Ошибка при проверке Telegram ID"


def validate_full_name(full_name: str) -> tuple[bool, Optional[str]]:
    """
    Validate full name format
    
    Args:
        full_name: Full name to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        if not full_name:
            return False, "Полное имя не может быть пустым"
        
        full_name = full_name.strip()
        
        if len(full_name) < 5:
            return False, "Полное имя должно содержать минимум 5 символов"
        
        if len(full_name) > 100:
            return False, "Полное имя слишком длинное (максимум 100 символов)"
        
        # Check for at least 2 words (name and surname)
        words = full_name.split()
        if len(words) < 2:
            return False, "Укажите как минимум имя и фамилию"
        
        # Check for valid characters (letters, spaces, hyphens)
        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s\-]+$', full_name):
            return False, "Полное имя может содержать только буквы, пробелы и дефисы"
        
        return True, None
    except Exception as e:
        logger.error(f"Error validating full name: {e}")
        return False, "Ошибка при проверке полного имени"
