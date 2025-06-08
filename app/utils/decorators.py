"""
Decorators for authentication, authorization and other utilities
"""

import functools
import time
from typing import Callable, Any, Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from app.database.models import UserRole
from app.database.database import get_db
from app.database.crud import user_crud


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require user authentication
    
    Usage:
        @require_auth
        async def handler(message, user):
            # user object is guaranteed to exist
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract user from kwargs (added by AuthMiddleware)
        user = kwargs.get('user')
        
        if not user:
            # Find message/callback object to respond
            message_obj = None
            for arg in args:
                if hasattr(arg, 'answer'):
                    message_obj = arg
                    break
                elif hasattr(arg, 'message') and hasattr(arg.message, 'answer'):
                    message_obj = arg.message
                    break
            
            if message_obj:
                await message_obj.answer(
                    "❌ Вы не авторизованы в системе.\n"
                    "Выполните команду /start для регистрации."
                )
            return
        
        # Call original function with user parameter
        return await func(*args, **kwargs)
    
    return wrapper


def require_role(*required_roles: UserRole):
    """
    Decorator to require specific user roles
    
    Usage:
        @require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)
        async def handler(message, user):
            # user is guaranteed to have one of the required roles
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('user')
            
            if not user:
                # Find message/callback object to respond
                message_obj = None
                for arg in args:
                    if hasattr(arg, 'answer'):
                        message_obj = arg
                        break
                    elif hasattr(arg, 'message') and hasattr(arg.message, 'answer'):
                        message_obj = arg.message
                        break
                
                if message_obj:
                    await message_obj.answer(
                        "❌ Вы не авторизованы в системе.\n"
                        "Выполните команду /start для регистрации."
                    )
                return
            
            if user.role not in required_roles:
                # Find message/callback object to respond
                message_obj = None
                for arg in args:
                    if hasattr(arg, 'answer'):
                        message_obj = arg
                        break
                    elif hasattr(arg, 'message') and hasattr(arg.message, 'answer'):
                        message_obj = arg.message
                        break
                
                role_names = {
                    UserRole.ADMIN: "Администратор",
                    UserRole.GROUP_LEADER: "Староста",
                    UserRole.ASSISTANT: "Помощник старосты",
                    UserRole.MEMBER: "Участник"
                }
                
                required_names = [role_names.get(role, role.value) for role in required_roles]
                
                if message_obj:
                    await message_obj.answer(
                        f"❌ Недостаточно прав доступа.\n"
                        f"Требуется роль: {', '.join(required_names)}"
                    )
                return
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_group_membership(func: Callable) -> Callable:
    """
    Decorator to require user to be member of a group
    
    Usage:
        @require_group_membership
        async def handler(message, user):
            # user is guaranteed to be in a group
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        user = kwargs.get('user')
        
        if not user:
            return await require_auth(func)(*args, **kwargs)
        
        if not user.group_id:
            # Find message/callback object to respond
            message_obj = None
            for arg in args:
                if hasattr(arg, 'answer'):
                    message_obj = arg
                    break
                elif hasattr(arg, 'message') and hasattr(arg.message, 'answer'):
                    message_obj = arg.message
                    break
            
            if message_obj:
                await message_obj.answer(
                    "❌ Вы не состоите ни в одной группе.\n"
                    "Обратитесь к старосте для получения приглашения."
                )
            return
        
        return await func(*args, **kwargs)
    
    return wrapper


def log_action(action_name: str):
    """
    Decorator to log user actions
    
    Usage:
        @log_action("create_event")
        async def create_event_handler(message, user):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('user')
            
            # Extract basic info for logging
            user_info = "Unknown"
            if user:
                user_info = f"{user.full_name} ({user.telegram_id})"
            
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                execution_time = time.time() - start_time
                logger.info(
                    f"Action '{action_name}' completed by {user_info}",
                    extra={
                        'action': action_name,
                        'user_id': str(user.id) if user else None,
                        'telegram_id': user.telegram_id if user else None,
                        'execution_time': round(execution_time, 3),
                        'status': 'success'
                    }
                )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Action '{action_name}' failed for {user_info}: {str(e)}",
                    extra={
                        'action': action_name,
                        'user_id': str(user.id) if user else None,
                        'telegram_id': user.telegram_id if user else None,
                        'execution_time': round(execution_time, 3),
                        'status': 'error',
                        'error': str(e)
                    }
                )
                raise
        
        return wrapper
    return decorator


def rate_limit(max_calls: int = 10, time_window: int = 60):
    """
    Decorator to implement rate limiting
    
    Args:
        max_calls: Maximum number of calls allowed
        time_window: Time window in seconds
    
    Usage:
        @rate_limit(max_calls=5, time_window=60)
        async def handler(message, user):
            pass
    """
    call_history: Dict[int, List[datetime]] = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('user')
            
            if not user:
                return await func(*args, **kwargs)
            
            user_id = user.telegram_id
            now = datetime.now()
            
            # Initialize or clean up call history for user
            if user_id not in call_history:
                call_history[user_id] = []
            
            # Remove old calls outside time window
            cutoff = now - timedelta(seconds=time_window)
            call_history[user_id] = [
                call_time for call_time in call_history[user_id] 
                if call_time > cutoff
            ]
            
            # Check if rate limit exceeded
            if len(call_history[user_id]) >= max_calls:
                # Find message/callback object to respond
                message_obj = None
                for arg in args:
                    if hasattr(arg, 'answer'):
                        message_obj = arg
                        break
                    elif hasattr(arg, 'message') and hasattr(arg.message, 'answer'):
                        message_obj = arg.message
                        break
                
                if message_obj:
                    await message_obj.answer(
                        f"❌ Превышен лимит запросов.\n"
                        f"Максимум {max_calls} запросов в {time_window} секунд.\n"
                        f"Попробуйте позже."
                    )
                
                logger.warning(
                    f"Rate limit exceeded for user {user.full_name} ({user_id})",
                    extra={
                        'user_id': str(user.id),
                        'telegram_id': user_id,
                        'rate_limit': f"{max_calls}/{time_window}s",
                        'current_calls': len(call_history[user_id])
                    }
                )
                return
            
            # Record this call
            call_history[user_id].append(now)
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def handle_errors(error_message: str = "❌ Произошла ошибка. Попробуйте позже."):
    """
    Decorator to handle exceptions gracefully
    
    Usage:
        @handle_errors("Ошибка при создании события")
        async def create_event(message, user):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                
                # Find message/callback object to respond
                message_obj = None
                for arg in args:
                    if hasattr(arg, 'answer'):
                        message_obj = arg
                        break
                    elif hasattr(arg, 'message') and hasattr(arg.message, 'answer'):
                        message_obj = arg.message
                        break
                
                if message_obj:
                    await message_obj.answer(error_message)
        
        return wrapper
    return decorator


def admin_only(func: Callable) -> Callable:
    """
    Decorator to restrict access to admin users only
    
    Usage:
        @admin_only
        async def admin_function(message, user):
            pass
    """
    return require_role(UserRole.ADMIN)(func)


def group_leader_only(func: Callable) -> Callable:
    """
    Decorator to restrict access to group leaders only
    
    Usage:
        @group_leader_only
        async def leader_function(message, user):
            pass
    """
    return require_role(UserRole.GROUP_LEADER)(func)


def group_staff_only(func: Callable) -> Callable:
    """
    Decorator to restrict access to group leaders and assistants only
    
    Usage:
        @group_staff_only
        async def staff_function(message, user):
            pass
    """
    return require_role(UserRole.GROUP_LEADER, UserRole.ASSISTANT)(func)


def measure_performance(func: Callable) -> Callable:
    """
    Decorator to measure function performance
    
    Usage:
        @measure_performance
        async def slow_function():
            pass
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if execution_time > 1.0:  # Log slow operations
                logger.warning(
                    f"Slow operation detected: {func.__name__}",
                    extra={
                        'function': func.__name__,
                        'execution_time': round(execution_time, 3),
                        'threshold': 1.0
                    }
                )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Function {func.__name__} failed after {execution_time:.3f}s: {e}"
            )
            raise
    
    return wrapper


def cache_result(expire_seconds: int = 300):
    """
    Simple in-memory cache decorator
    
    Args:
        expire_seconds: Cache expiration time in seconds
    
    Usage:
        @cache_result(expire_seconds=600)
        async def expensive_function(param):
            pass
    """
    cache: Dict[str, Dict[str, Any]] = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            now = time.time()
            
            # Check if cached result exists and is not expired
            if cache_key in cache:
                cached_data = cache[cache_key]
                if now - cached_data['timestamp'] < expire_seconds:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached_data['result']
                else:
                    # Remove expired cache entry
                    del cache[cache_key]
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache[cache_key] = {
                'result': result,
                'timestamp': now
            }
            
            logger.debug(f"Cache miss for {func.__name__}, result cached")
            return result
        
        return wrapper
    return decorator


def validate_input(validator_func: Callable):
    """
    Decorator to validate input parameters
    
    Usage:
        def validate_event_data(title, description):
            if not title or len(title) < 3:
                raise ValueError("Title too short")
            return True
        
        @validate_input(validate_event_data)
        async def create_event(title, description):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Extract parameters for validation
                # This is a simplified implementation
                validator_func(*args[1:], **kwargs)  # Skip self/message parameter
                return await func(*args, **kwargs)
            except ValueError as e:
                logger.warning(f"Input validation failed for {func.__name__}: {e}")
                
                # Find message/callback object to respond
                message_obj = None
                for arg in args:
                    if hasattr(arg, 'answer'):
                        message_obj = arg
                        break
                    elif hasattr(arg, 'message') and hasattr(arg.message, 'answer'):
                        message_obj = arg.message
                        break
                
                if message_obj:
                    await message_obj.answer(f"❌ Ошибка валидации: {str(e)}")
        
        return wrapper
    return decorator
