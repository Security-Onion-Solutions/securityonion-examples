import pytest
from datetime import datetime
from src.template_filters import (
    format_datetime,
    format_severity,
    format_status,
    truncate_text,
    nl2br,
    format_timestamp
)

def test_format_datetime():
    """Test datetime formatting filter."""
    # Test with ISO format string
    dt_str = "2023-01-01T12:30:45Z"
    result = format_datetime(dt_str)
    assert "Jan 01, 2023" in result
    assert "12:30" in result

    # Test with datetime object
    dt_obj = datetime(2023, 1, 1, 12, 30, 45)
    result = format_datetime(dt_obj)
    assert "Jan 01, 2023" in result
    assert "12:30" in result

    # Test with None
    assert format_datetime(None) == ""

def test_format_severity():
    """Test alert severity formatting."""
    # Test various severity levels
    assert "badge-danger" in format_severity("high")
    assert "badge-warning" in format_severity("medium")
    assert "badge-info" in format_severity("low")
    assert "badge-secondary" in format_severity("unknown")
    
    # Test case insensitivity
    assert "badge-danger" in format_severity("HIGH")
    
    # Test invalid severity
    assert "badge-secondary" in format_severity("invalid")
    
    # Test None
    assert "badge-secondary" in format_severity(None)

def test_format_status():
    """Test status formatting filter."""
    # Test various status values
    assert "badge-success" in format_status("closed")
    assert "badge-primary" in format_status("open")
    assert "badge-warning" in format_status("in_progress")
    assert "badge-secondary" in format_status("unknown")
    
    # Test case insensitivity
    assert "badge-success" in format_status("CLOSED")
    
    # Test with spaces
    assert "badge-warning" in format_status("in progress")
    
    # Test invalid status
    assert "badge-secondary" in format_status("invalid")
    
    # Test None
    assert "badge-secondary" in format_status(None)

def test_nl2br():
    """Test newline to <br> conversion."""
    # Test basic newline conversion
    assert nl2br("line1\nline2") == "line1<br>\nline2"
    
    # Test multiple newlines
    assert nl2br("line1\n\nline3") == "line1<br>\n<br>\nline3"
    
    # Test with None
    assert nl2br(None) == ""
    
    # Test empty string
    assert nl2br("") == ""

def test_format_timestamp():
    """Test timestamp formatting."""
    # Test with ISO format string
    ts_str = "2023-01-01T12:30:45Z"
    result = format_timestamp(ts_str)
    assert "Jan 01, 2023" in result
    assert "12:30" in result
    
    # Test with datetime object
    ts_obj = datetime(2023, 1, 1, 12, 30, 45)
    result = format_timestamp(ts_obj)
    assert "Jan 01, 2023" in result
    assert "12:30" in result
    
    # Test with None
    assert format_timestamp(None) == ""
    
    # Test with invalid format
    assert format_timestamp("invalid") == ""

def test_truncate_text():
    """Test text truncation filter."""
    # Test short text (no truncation needed)
    short_text = "Short text"
    assert truncate_text(short_text, length=20) == short_text
    
    # Test long text
    long_text = "This is a very long text that needs to be truncated"
    result = truncate_text(long_text, length=20)
    assert len(result) <= 23  # 20 chars + "..."
    assert result.endswith("...")
    assert result.startswith("This is a very")
    
    # Test with custom suffix
    result = truncate_text(long_text, length=20, suffix=">>>")
    assert result.endswith(">>>")
    
    # Test with None
    assert truncate_text(None) == ""
    
    # Test with empty string
    assert truncate_text("") == ""
    
    # Test with length shorter than suffix
    assert truncate_text("test", length=2) == "..."
