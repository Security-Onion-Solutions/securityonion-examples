from ...models.chat_users import ChatService
from functools import wraps
from typing import Callable, Optional, List, Dict, Any
from fastapi import HTTPException

def validate_command_format(command: str) -> bool:
    """Validate basic command format."""
    if not command or not command.startswith('!'):
        return False
    return True

def validate_arguments(
    command: str, 
    required_args: int = 0,
    optional_args: int = 0,
    multi_word_arg_index: Optional[int] = None
) -> bool:
    """
    Validate command arguments.
    
    Args:
        command: The command string to validate
        required_args: Number of required arguments
        optional_args: Number of optional arguments
        multi_word_arg_index: If specified, everything after this position is treated as one argument
    """
    parts = command.split()
    
    # Remove command name from parts
    parts = parts[1:]
    
    # If multi_word_arg_index is specified and within range
    if multi_word_arg_index is not None and multi_word_arg_index < len(parts):
        # Reconstruct parts list with everything after index as one argument
        new_parts = parts[:multi_word_arg_index]
        remaining = " ".join(parts[multi_word_arg_index:])
        if remaining:
            new_parts.append(remaining)
        parts = new_parts
    
    # Check required args
    if len(parts) < required_args:
        return False
        
    # Check total args (required + optional)
    if len(parts) > (required_args + optional_args):
        return False
        
    return True

def validate_types(
    args: List[str],
    types: List[Callable[[str], Any]]
) -> bool:
    """Validate argument types."""
    if len(args) != len(types):
        return False
    for arg, type_func in zip(args, types):
        try:
            type_func(arg)
        except (ValueError, TypeError):
            return False
    return True

def command_validator(
    required_args: int = 0,
    optional_args: int = 0,
    arg_types: Optional[List[Callable[[str], Any]]] = None,
    multi_word_arg_index: Optional[int] = None
):
    """Decorator for command validation."""
    def decorator(func):
        @wraps(func)
        async def wrapper(command: str, *args, **kwargs):
            # Validate command format
            if not validate_command_format(command):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid command format. Commands must start with '!'"
                )
            
            # Validate argument count
            if not validate_arguments(command, required_args, optional_args, multi_word_arg_index):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid number of arguments. Expected {required_args} required and {optional_args} optional arguments"
                )
            
            # Validate argument types if specified
            if arg_types:
                parts = command.split()[1:]  # Skip command name
                if not validate_types(parts, arg_types):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid argument types"
                    )
            
            return await func(command, *args, **kwargs)
        return wrapper
    return decorator

def sanitize_input(input_str: str) -> str:
    """Basic input sanitization."""
    return input_str.strip()
