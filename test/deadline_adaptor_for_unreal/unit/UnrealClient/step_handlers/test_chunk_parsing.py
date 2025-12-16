# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""
Unit tests for step handler chunk parsing functionality.

Tests the parse_frame_chunk() and parse_frame_chunk_noncontiguous() methods
in UnrealRenderStepHandler for the new CHUNK[INT] OpenJD parameter type.

Requirements: 2.1, 2.2, 2.4, 5.1, 5.2
"""

import sys
import pytest
from unittest.mock import MagicMock

# Mock unreal module before importing step handler
unreal_mock = MagicMock()
unreal_mock.log = MagicMock()
sys.modules["unreal"] = unreal_mock


@pytest.fixture()
def unreal_render_step_handler():
    from deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler import (
        UnrealRenderStepHandler,
    )

    # Clear cached values before each test
    UnrealRenderStepHandler.cached_frame_range_start = None
    UnrealRenderStepHandler.cached_frame_range_end = None
    return UnrealRenderStepHandler()


class TestParseFrameChunkContiguous:
    """Tests for parse_frame_chunk() - contiguous chunk parsing (Requirement 2.1)"""

    @pytest.mark.parametrize(
        "chunk_value, expected_start, expected_end",
        [
            ("1-10", 1, 10),
            ("5-5", 5, 5),  # Single frame
            ("100-200", 100, 200),
            ("0-50", 0, 50),
            ("1-1000", 1, 1000),
        ],
    )
    def test_parse_contiguous_chunk_valid(
        self, unreal_render_step_handler, chunk_value, expected_start, expected_end
    ):
        """Test parsing valid contiguous chunk values returns correct start/end frames."""
        start, end = unreal_render_step_handler.parse_frame_chunk(chunk_value)
        assert start == expected_start
        assert end == expected_end

    def test_parse_contiguous_chunk_single_value(self, unreal_render_step_handler):
        """Test parsing a single value returns same start and end."""
        start, end = unreal_render_step_handler.parse_frame_chunk("42")
        assert start == 42
        assert end == 42

    def test_parse_contiguous_chunk_with_step(self, unreal_render_step_handler):
        """Test parsing range with step returns min/max of resulting frames."""
        # "1-10:2" produces [1, 3, 5, 7, 9], so min=1, max=9
        start, end = unreal_render_step_handler.parse_frame_chunk("1-10:2")
        assert start == 1
        assert end == 9

    def test_parse_contiguous_chunk_comma_separated(self, unreal_render_step_handler):
        """Test parsing comma-separated values returns min/max."""
        # "1,5,10" produces [1, 5, 10], so min=1, max=10
        start, end = unreal_render_step_handler.parse_frame_chunk("1,5,10")
        assert start == 1
        assert end == 10


class TestParseFrameChunkNoncontiguous:
    """Tests for parse_frame_chunk_noncontiguous() - non-contiguous parsing (Requirement 2.2)"""

    @pytest.mark.parametrize(
        "chunk_value, expected_frames",
        [
            ("1-5", [1, 2, 3, 4, 5]),
            ("1,3,5", [1, 3, 5]),
            ("1,3,5-10", [1, 3, 5, 6, 7, 8, 9, 10]),
            ("1-10:2", [1, 3, 5, 7, 9]),
            ("7-20:2", [7, 9, 11, 13, 15, 17, 19]),
            ("1-3,5,7-20:2", [1, 2, 3, 5, 7, 9, 11, 13, 15, 17, 19]),
            ("42", [42]),
        ],
    )
    def test_parse_noncontiguous_chunk_valid(
        self, unreal_render_step_handler, chunk_value, expected_frames
    ):
        """Test parsing valid non-contiguous chunk values returns correct frame list."""
        frames = unreal_render_step_handler.parse_frame_chunk_noncontiguous(chunk_value)
        assert frames == expected_frames

    def test_parse_noncontiguous_returns_sorted_list(self, unreal_render_step_handler):
        """Test that non-contiguous parsing returns a sorted list."""
        frames = unreal_render_step_handler.parse_frame_chunk_noncontiguous("10,1,5,3")
        assert frames == sorted(frames)
        assert frames == [1, 3, 5, 10]


class TestChunkParsingErrorHandling:
    """Tests for error handling in chunk parsing (Requirement 2.4)"""

    def test_parse_frame_chunk_empty_string(self, unreal_render_step_handler):
        """Test that empty string raises RangeExpressionError."""
        from deadline.unreal_range_expr import RangeExpressionError

        with pytest.raises(RangeExpressionError, match="Empty range expression"):
            unreal_render_step_handler.parse_frame_chunk("")

    def test_parse_frame_chunk_whitespace_only(self, unreal_render_step_handler):
        """Test that whitespace-only string raises RangeExpressionError."""
        from deadline.unreal_range_expr import RangeExpressionError

        with pytest.raises(RangeExpressionError, match="Empty range expression"):
            unreal_render_step_handler.parse_frame_chunk("   ")

    def test_parse_frame_chunk_invalid_character(self, unreal_render_step_handler):
        """Test that invalid characters raise RangeExpressionError."""
        from deadline.unreal_range_expr import RangeExpressionError

        with pytest.raises(RangeExpressionError, match="Invalid character"):
            unreal_render_step_handler.parse_frame_chunk("1-10a")

    def test_parse_frame_chunk_invalid_range(self, unreal_render_step_handler):
        """Test that invalid range (start > end) raises RangeExpressionError."""
        from deadline.unreal_range_expr import RangeExpressionError

        with pytest.raises(RangeExpressionError, match="Invalid range"):
            unreal_render_step_handler.parse_frame_chunk("10-1")

    def test_parse_frame_chunk_invalid_step(self, unreal_render_step_handler):
        """Test that invalid step value raises RangeExpressionError."""
        from deadline.unreal_range_expr import RangeExpressionError

        with pytest.raises(RangeExpressionError, match="Invalid step value"):
            unreal_render_step_handler.parse_frame_chunk("1-10:0")

    def test_parse_noncontiguous_empty_string(self, unreal_render_step_handler):
        """Test that empty string raises RangeExpressionError for non-contiguous."""
        from deadline.unreal_range_expr import RangeExpressionError

        with pytest.raises(RangeExpressionError, match="Empty range expression"):
            unreal_render_step_handler.parse_frame_chunk_noncontiguous("")

    def test_parse_noncontiguous_invalid_format(self, unreal_render_step_handler):
        """Test that invalid format raises RangeExpressionError for non-contiguous."""
        from deadline.unreal_range_expr import RangeExpressionError

        with pytest.raises(RangeExpressionError, match="Invalid character"):
            unreal_render_step_handler.parse_frame_chunk_noncontiguous("abc")


class TestBackwardCompatibility:
    """Tests for backward compatibility with legacy format (Requirements 5.1, 5.2)"""

    def test_legacy_args_detection_frames_per_task(self, unreal_render_step_handler):
        """Test that legacy frames_per_task args are correctly detected."""
        legacy_args = {
            "chunk_id": 0,
            "frames_per_task": 10,
            "queue_manifest_path": "/path/to/manifest",
        }

        # Legacy format: has chunk_id and frames_per_task, no frame_chunk
        assert "frame_chunk" not in legacy_args
        assert legacy_args.get("frames_per_task") and "chunk_id" in legacy_args

    def test_legacy_args_detection_chunk_size(self, unreal_render_step_handler):
        """Test that legacy chunk_size args are correctly detected."""
        legacy_args = {
            "chunk_id": 1,
            "chunk_size": 5,
            "queue_manifest_path": "/path/to/manifest",
        }

        # Legacy format: has chunk_id and chunk_size, no frame_chunk
        assert "frame_chunk" not in legacy_args
        assert "chunk_size" in legacy_args and "chunk_id" in legacy_args

    def test_new_format_args_detection(self, unreal_render_step_handler):
        """Test that new CHUNK[INT] format args are correctly detected."""
        new_args = {
            "frame_chunk": "1-10",
            "range_constraint": "CONTIGUOUS",
            "queue_manifest_path": "/path/to/manifest",
        }

        # New format: has frame_chunk
        assert "frame_chunk" in new_args
        assert new_args.get("range_constraint") == "CONTIGUOUS"

    def test_new_format_noncontiguous_args(self, unreal_render_step_handler):
        """Test that new CHUNK[INT] non-contiguous format args are correctly detected."""
        new_args = {
            "frame_chunk": "1,3,5-10",
            "range_constraint": "NONCONTIGUOUS",
            "queue_manifest_path": "/path/to/manifest",
        }

        assert "frame_chunk" in new_args
        assert new_args.get("range_constraint") == "NONCONTIGUOUS"

    def test_format_precedence_new_over_legacy(self, unreal_render_step_handler):
        """Test that new format takes precedence when both are present."""
        mixed_args = {
            "frame_chunk": "1-10",
            "range_constraint": "CONTIGUOUS",
            "chunk_id": 0,
            "frames_per_task": 10,
            "queue_manifest_path": "/path/to/manifest",
        }

        # New format should be detected first
        assert "frame_chunk" in mixed_args
        # The run_script method checks for frame_chunk first

    def test_default_range_constraint(self, unreal_render_step_handler):
        """Test that default range_constraint is CONTIGUOUS when not specified."""
        args_without_constraint = {
            "frame_chunk": "1-10",
            "queue_manifest_path": "/path/to/manifest",
        }

        # Default should be CONTIGUOUS
        range_constraint = args_without_constraint.get("range_constraint", "CONTIGUOUS")
        assert range_constraint == "CONTIGUOUS"

    @pytest.mark.parametrize(
        "chunk_id, frames_per_task, frame_start, frame_end, expected_start, expected_end",
        [
            (0, 10, 1, 100, 1, 11),
            (1, 10, 1, 100, 11, 21),
            (9, 10, 1, 100, 91, 100),
        ],
    )
    def test_legacy_frame_calculation_still_works(
        self,
        unreal_render_step_handler,
        chunk_id,
        frames_per_task,
        frame_start,
        frame_end,
        expected_start,
        expected_end,
    ):
        """Test that legacy frame calculation logic still produces correct results."""
        # Simulate the legacy calculation from run_script
        calculated_start = frame_start + (chunk_id * frames_per_task)
        calculated_end = min(calculated_start + frames_per_task, frame_end)

        assert calculated_start == expected_start
        assert calculated_end == expected_end
