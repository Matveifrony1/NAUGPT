import pytest
from utils import ValidationUtils, ContextUtils, TextUtils


class TestValidationUtils:
    """Tests for input validation utilities"""

    @pytest.mark.parametrize(
        "group_name, expected",
        [
            ("Б-171-22-1-ІР", True),
            ("М-301-24-2-КІТ", True),
            ("Б-999-99-9-ХХХ", True),

            # Invalid cases
            ("Б171-22-1-ІР", False),
            ("Б-171-22-ІР", False),
            ("INVALID", False),
            ("", False),

            # Lowercase input (function converts to uppercase)
            ("б-171-22-1-ір", True),
        ],
    )
    def test_validate_group_format(self, group_name, expected):
        assert ValidationUtils.validate_group_format(group_name) == expected

    def test_validate_user_name(self):
        assert ValidationUtils.validate_user_name("") is False
        assert ValidationUtils.validate_user_name("a") is False
        assert ValidationUtils.validate_user_name("John Doe") is True
        assert ValidationUtils.validate_user_name("a" * 100) is False


class TestTextUtils:
    """Tests for text-related utilities"""

    def test_extract_group_name(self):
        text = "My group is Б-171-22-1-ІР and we study CS."
        assert TextUtils.extract_group_name(text) == "Б-171-22-1-ІР"

    def test_extract_group_name_not_found(self):
        text = "There is no group mentioned here."
        assert TextUtils.extract_group_name(text) is None


class TestContextUtils:
    """Tests for context (dialogue history) utilities"""

    def test_count_tokens_approximation(self):
        text = "SampleText" * 10
        tokens = ContextUtils.count_tokens(text)

        assert tokens > 0
        assert tokens == len(text) // 4

    def test_truncate_messages_keeps_all_when_tokens_allow(self):
        """If max_tokens is large enough, no messages should be removed."""
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(10)]

        truncated = ContextUtils.truncate_messages(messages, max_tokens=50)

        assert truncated[-1]["content"] == "Message 9"
        assert len(truncated) == len(messages)

    def test_truncate_messages_returns_empty_when_not_enough_tokens(self):
        """If max_tokens is too small, result may legitimately be empty."""
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(10)]

        truncated = ContextUtils.truncate_messages(messages, max_tokens=1)

        # With max_tokens=1, even the last message doesn't fit (2 tokens), so result is empty.
        assert truncated == []
