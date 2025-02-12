from app.api.commands.validation import validate_arguments, validate_command_format

def test_validate_command_format():
    """Test basic command format validation."""
    assert validate_command_format("!test") is True
    assert validate_command_format("test") is False
    assert validate_command_format("") is False
    assert validate_command_format("!") is True

def test_validate_arguments():
    """Test argument validation."""
    # Basic argument validation
    assert validate_arguments("!test arg1", required_args=1) is True
    assert validate_arguments("!test", required_args=1) is False
    assert validate_arguments("!test arg1 arg2", required_args=1, optional_args=1) is True
    assert validate_arguments("!test arg1 arg2 arg3", required_args=1, optional_args=1) is False

    # Multi-word argument validation
    assert validate_arguments(
        "!test arg1 word1 word2 word3",
        required_args=1,
        optional_args=1,
        multi_word_arg_index=1
    ) is True
    
    # Multi-word at different positions
    assert validate_arguments(
        "!test arg1 arg2 word1 word2",
        required_args=2,
        optional_args=1,
        multi_word_arg_index=2
    ) is True
    
    # Multi-word with exact required/optional count
    assert validate_arguments(
        "!test arg1 this is a long title",
        required_args=1,
        optional_args=1,
        multi_word_arg_index=1
    ) is True
    
    # No multi-word content
    assert validate_arguments(
        "!test arg1",
        required_args=1,
        optional_args=1,
        multi_word_arg_index=1
    ) is True

def test_escalate_command_validation():
    """Test specific escalate command validation scenarios."""
    # Basic eventid only
    assert validate_arguments(
        "!escalate abc123",
        required_args=1,
        optional_args=1,
        multi_word_arg_index=1
    ) is True
    
    # Eventid with single word title
    assert validate_arguments(
        "!escalate abc123 Title",
        required_args=1,
        optional_args=1,
        multi_word_arg_index=1
    ) is True
    
    # Eventid with multi-word title
    assert validate_arguments(
        "!escalate abc123 Suspicious Activity from IP 1.2.3.4",
        required_args=1,
        optional_args=1,
        multi_word_arg_index=1
    ) is True
    
    # Missing eventid
    assert validate_arguments(
        "!escalate",
        required_args=1,
        optional_args=1,
        multi_word_arg_index=1
    ) is False
