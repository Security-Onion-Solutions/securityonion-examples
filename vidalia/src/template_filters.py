from datetime import datetime
from typing import Optional, Union
from markupsafe import Markup

def nl2br(text: Optional[str]) -> str:
    """Convert newlines to HTML <br> tags.
    
    Args:
        text: Text containing newlines
        
    Returns:
        Text with newlines converted to <br> tags
    """
    if not text:
        return ""
    return Markup(text.replace('\n', '<br>\n'))

def format_timestamp(timestamp: Union[str, datetime, None]) -> str:
    """Format timestamp for display.
    
    Args:
        timestamp: Timestamp string in ISO format or datetime object
        
    Returns:
        Formatted timestamp string
    """
    return format_datetime(timestamp)  # Reuse existing datetime formatter

def format_datetime(dt: Union[str, datetime, None]) -> str:
    """Format datetime for display.
    
    Args:
        dt: Datetime string in ISO format or datetime object
        
    Returns:
        Formatted datetime string
    """
    if not dt:
        return ""
        
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return ""
            
    return dt.strftime("%b %d, %Y %H:%M")

def format_severity(severity: Optional[str]) -> str:
    """Format alert severity as Bootstrap badge.
    
    Args:
        severity: Alert severity level
        
    Returns:
        HTML string with formatted badge
    """
    severity = str(severity).lower() if severity else "unknown"
    
    badge_map = {
        "high": "danger",
        "medium": "warning", 
        "low": "info",
        "unknown": "secondary"
    }
    
    badge_type = badge_map.get(severity, "secondary")
    return f'<span class="badge badge-{badge_type}">{severity}</span>'

def format_status(status: Optional[str]) -> str:
    """Format status as Bootstrap badge.
    
    Args:
        status: Status string
        
    Returns:
        HTML string with formatted badge
    """
    status = str(status).lower() if status else "unknown"
    status = status.replace(" ", "_")
    
    badge_map = {
        "closed": "success",
        "open": "primary",
        "in_progress": "warning",
        "unknown": "secondary"
    }
    
    badge_type = badge_map.get(status, "secondary")
    display_status = status.replace("_", " ")
    return f'<span class="badge badge-{badge_type}">{display_status}</span>'

def truncate_text(text: Optional[str], length: int = 50, suffix: str = "...") -> str:
    """Truncate text to specified length.
    
    Args:
        text: Text to truncate
        length: Maximum length before truncation
        suffix: String to append to truncated text
        
    Returns:
        Truncated text string
    """
    if not text:
        return ""
        
    if len(text) <= length:
        return text
        
    if length <= len(suffix):
        return suffix
        
    return text[:length - len(suffix)] + suffix
