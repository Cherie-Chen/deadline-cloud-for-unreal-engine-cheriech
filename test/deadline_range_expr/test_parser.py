# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Unit tests for the RangeExpressionParser class."""

import pytest

from deadline.unreal_range_expr import RangeExpressionParser, RangeExpressionError


class TestParserBasicCases:
    """Test basic parsing functionality."""

    def test_single_value(self):
        """Test parsing a single value."""
        assert RangeExpressionParser.parse("5") == [5]
        assert RangeExpressionParser.parse("0") == [0]
        assert RangeExpressionParser.parse("100") == [100]

    def test_simple_range(self):
        """Test parsing a simple range."""
        assert RangeExpressionParser.parse("1-5") == [1, 2, 3, 4, 5]
        assert RangeExpressionParser.parse("10-15") == [10, 11, 12, 13, 14, 15]

    def test_step_range(self):
        """Test parsing a range with step."""
        assert RangeExpressionParser.parse("1-10:2") == [1, 3, 5, 7, 9]
        assert RangeExpressionParser.parse("7-20:2") == [7, 9, 11, 13, 15, 17, 19]
        assert RangeExpressionParser.parse("0-10:3") == [0, 3, 6, 9]

    def test_comma_separated(self):
        """Test parsing comma-separated values."""
        assert RangeExpressionParser.parse("1,3,5") == [1, 3, 5]
        assert RangeExpressionParser.parse("10,20,30") == [10, 20, 30]

    def test_mixed_format(self):
        """Test parsing mixed formats."""
        assert RangeExpressionParser.parse("1,3,5-10") == [1, 3, 5, 6, 7, 8, 9, 10]
        assert RangeExpressionParser.parse("1-3,5,7-20:2") == [1, 2, 3, 5, 7, 9, 11, 13, 15, 17, 19]

    def test_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        assert RangeExpressionParser.parse("  5  ") == [5]
        assert RangeExpressionParser.parse("1-5") == [1, 2, 3, 4, 5]

    def test_duplicate_removal(self):
        """Test that duplicates are removed."""
        assert RangeExpressionParser.parse("1,1,2,2,3") == [1, 2, 3]
        assert RangeExpressionParser.parse("1-5,3-7") == [1, 2, 3, 4, 5, 6, 7]


class TestParserEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_input_raises_error(self):
        """Test that empty input raises RangeExpressionError."""
        with pytest.raises(RangeExpressionError) as exc_info:
            RangeExpressionParser.parse("")
        assert "Empty range expression" in str(exc_info.value)

    def test_whitespace_only_raises_error(self):
        """Test that whitespace-only input raises RangeExpressionError."""
        with pytest.raises(RangeExpressionError) as exc_info:
            RangeExpressionParser.parse("   ")
        assert "Empty range expression" in str(exc_info.value)

    def test_single_frame_same_start_end(self):
        """Test parsing a range where start equals end."""
        assert RangeExpressionParser.parse("5-5") == [5]

    def test_negative_numbers(self):
        """Test parsing negative numbers."""
        assert RangeExpressionParser.parse("-5") == [-5]
        assert RangeExpressionParser.parse("-10--5") == [-10, -9, -8, -7, -6, -5]
        assert RangeExpressionParser.parse("-3,0,3") == [-3, 0, 3]

    def test_invalid_character_raises_error(self):
        """Test that invalid characters raise RangeExpressionError with position."""
        with pytest.raises(RangeExpressionError) as exc_info:
            RangeExpressionParser.parse("1-5a")
        assert "Invalid character 'a'" in str(exc_info.value)
        assert "position" in str(exc_info.value)

    def test_invalid_character_position(self):
        """Test that error position is correct for invalid characters."""
        with pytest.raises(RangeExpressionError) as exc_info:
            RangeExpressionParser.parse("1,2,3x")
        error = exc_info.value
        assert error.position is not None
        assert "Invalid character 'x'" in error.message

    def test_invalid_range_start_greater_than_end(self):
        """Test that start > end raises RangeExpressionError."""
        with pytest.raises(RangeExpressionError) as exc_info:
            RangeExpressionParser.parse("10-5")
        assert "Invalid range: start 10 > end 5" in str(exc_info.value)

    def test_invalid_step_zero(self):
        """Test that step of 0 raises RangeExpressionError."""
        with pytest.raises(RangeExpressionError) as exc_info:
            RangeExpressionParser.parse("1-10:0")
        assert "Invalid step value" in str(exc_info.value)
        assert "must be positive" in str(exc_info.value)

    def test_empty_range_part_raises_error(self):
        """Test that empty range parts raise RangeExpressionError."""
        with pytest.raises(RangeExpressionError) as exc_info:
            RangeExpressionParser.parse("1,,3")
        assert "Empty range part" in str(exc_info.value)

    def test_special_characters_raise_error(self):
        """Test that special characters raise RangeExpressionError."""
        invalid_inputs = ["1-5!", "1@3", "1#5", "1$5", "1%5", "1^5", "1&5", "1*5"]
        for invalid_input in invalid_inputs:
            with pytest.raises(RangeExpressionError):
                RangeExpressionParser.parse(invalid_input)


class TestParserErrorMessages:
    """Test error message formatting with position info."""

    def test_error_includes_position(self):
        """Test that errors include position information."""
        with pytest.raises(RangeExpressionError) as exc_info:
            RangeExpressionParser.parse("1-5x")
        error = exc_info.value
        assert error.position is not None
        assert "at position" in str(error)

    def test_error_message_format(self):
        """Test the format of error messages."""
        with pytest.raises(RangeExpressionError) as exc_info:
            RangeExpressionParser.parse("abc")
        error = exc_info.value
        assert error.message is not None
        assert len(error.message) > 0

    def test_empty_expression_error_no_position(self):
        """Test that empty expression error has no position."""
        with pytest.raises(RangeExpressionError) as exc_info:
            RangeExpressionParser.parse("")
        error = exc_info.value
        assert error.position is None
        assert "Empty range expression" in error.message
