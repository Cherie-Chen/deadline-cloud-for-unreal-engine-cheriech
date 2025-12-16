# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Property-based tests for the integer range expression module."""

import math
import re

from hypothesis import given, settings
from hypothesis import strategies as st

from deadline.unreal_range_expr import (
    RangeExpressionParser,
    RangeExpressionFormatter,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_chunk import (
    ChunkConfiguration,
    ChunkIntTaskParameter,
    RangeConstraint,
)


# Strategy for valid frame numbers (positive integers, reasonable range)
frame_number = st.integers(min_value=1, max_value=100000)

# Strategy for frame lists (non-empty, unique, sorted)
frame_list = st.lists(frame_number, min_size=1, max_size=1000, unique=True).map(sorted)

# Strategy for contiguous ranges
contiguous_range = st.tuples(
    st.integers(min_value=1, max_value=50000), st.integers(min_value=1, max_value=50000)
).map(lambda t: (min(t), max(t)))

# Strategy for chunk sizes (valid chunk sizes are >= 1)
chunk_size = st.integers(min_value=1, max_value=100)


class TestParseFormatRoundTrip:
    """
    **Feature: task-chunking, Property 1: Parse-Format Round Trip**

    *For any* valid integer range expression string, parsing it and then formatting
    the resulting frame list SHALL produce an expression that, when parsed again,
    yields the same set of frame numbers.

    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.6**
    """

    @given(frames=frame_list)
    @settings(max_examples=200)
    def test_parse_format_round_trip(self, frames: list[int]):
        """
        Property 1: Parse-Format Round Trip

        For any list of frames, formatting then parsing should yield the same frames.
        Then formatting again and parsing should still yield the same frames.
        """
        # Format the frame list
        formatted = RangeExpressionFormatter.format_noncontiguous(frames)

        # Parse the formatted string
        parsed = RangeExpressionParser.parse(formatted)

        # The parsed result should equal the original sorted unique frames
        assert parsed == sorted(set(frames))

        # Format again and parse again (full round trip)
        formatted_again = RangeExpressionFormatter.format_noncontiguous(parsed)
        parsed_again = RangeExpressionParser.parse(formatted_again)

        # Should still be the same
        assert parsed_again == parsed


class TestFormatParseRoundTrip:
    """
    **Feature: task-chunking, Property 2: Format-Parse Round Trip**

    *For any* non-empty list of positive integers, formatting it as a range expression
    and then parsing that expression SHALL produce a sorted list containing exactly
    the same integers.

    **Validates: Requirements 3.5, 3.6**
    """

    @given(frames=frame_list)
    @settings(max_examples=200)
    def test_format_parse_round_trip(self, frames: list[int]):
        """
        Property 2: Format-Parse Round Trip

        For any non-empty list of positive integers, formatting then parsing
        should produce a sorted list with exactly the same integers.
        """
        # Format the frame list
        formatted = RangeExpressionFormatter.format_noncontiguous(frames)

        # Parse the formatted string
        parsed = RangeExpressionParser.parse(formatted)

        # The parsed result should equal the original sorted unique frames
        expected = sorted(set(frames))
        assert parsed == expected


class TestContiguousFormatConstraint:
    """
    **Feature: task-chunking, Property 3: Contiguous Format Constraint**

    *For any* contiguous chunk (start frame, end frame where start <= end),
    the formatted output SHALL match the pattern "^\\d+-\\d+$" (digits-hyphen-digits)
    or "^\\d+$" for single frame.

    **Validates: Requirements 1.1, 2.1**
    """

    # Pattern for contiguous format: either "N" or "N-M"
    CONTIGUOUS_PATTERN = re.compile(r"^\d+(-\d+)?$")

    @given(range_tuple=contiguous_range)
    @settings(max_examples=200)
    def test_contiguous_format_constraint(self, range_tuple: tuple[int, int]):
        """
        Property 3: Contiguous Format Constraint

        For any contiguous range, the formatted output should match the pattern
        "^\\d+(-\\d+)?$" (single number or number-hyphen-number).
        """
        start, end = range_tuple

        # Format the contiguous range
        formatted = RangeExpressionFormatter.format_contiguous(start, end)

        # Should match the contiguous pattern
        assert self.CONTIGUOUS_PATTERN.match(
            formatted
        ), f"Formatted output '{formatted}' does not match contiguous pattern"

        # Parse it back and verify it produces the correct range
        parsed = RangeExpressionParser.parse(formatted)
        expected = list(range(start, end + 1))
        assert parsed == expected


class TestNonContiguousParseCorrectness:
    """
    **Feature: task-chunking, Property 6: Non-contiguous Parse Correctness**

    *For any* list of distinct positive integers, formatting as non-contiguous
    and parsing SHALL return a sorted list equal to the sorted input list.

    **Validates: Requirements 1.2, 2.2**
    """

    @given(frames=frame_list)
    @settings(max_examples=200)
    def test_noncontiguous_parse_correctness(self, frames: list[int]):
        """
        Property 6: Non-contiguous Parse Correctness

        For any list of distinct positive integers, formatting as non-contiguous
        and parsing should return a sorted list equal to the sorted input list.
        """
        # Format the frame list as non-contiguous
        formatted = RangeExpressionFormatter.format_noncontiguous(frames)

        # Parse the formatted string
        parsed = RangeExpressionParser.parse(formatted)

        # The parsed result should equal the sorted unique input frames
        expected = sorted(set(frames))
        assert parsed == expected, (
            f"Non-contiguous parse failed: formatted '{formatted}' "
            f"parsed to {parsed}, expected {expected}"
        )


class TestChunkSizeBounds:
    """
    **Feature: task-chunking, Property 5: Chunk Size Bounds**

    *For any* frame range of size N and chunk size C >= 1, each generated chunk
    SHALL contain at most C frames, and the number of chunks SHALL equal ceil(N / C).

    **Validates: Requirements 1.3, 1.4**
    """

    @given(frames=frame_list, size=chunk_size)
    @settings(max_examples=200)
    def test_chunk_size_bounds(self, frames: list[int], size: int):
        """
        Property 5: Chunk Size Bounds

        For any frame range and chunk size >= 1:
        - Each chunk contains at most chunk_size frames
        - Number of chunks equals ceil(N / C)
        """
        # Create chunk configuration and parameter
        config = ChunkConfiguration(
            default_task_count=size,
            range_constraint=RangeConstraint.NONCONTIGUOUS,
        )

        # Format frames as a range expression for input
        range_expr = RangeExpressionFormatter.format_noncontiguous(frames)

        param = ChunkIntTaskParameter(
            name="Frame",
            range_expr=range_expr,
            chunks=config,
        )

        # Generate chunks
        chunk_values = param.generate_chunk_values()

        # Get unique sorted frames (as the parser would return)
        unique_frames = sorted(set(frames))
        n = len(unique_frames)
        expected_chunk_count = math.ceil(n / size)

        # Property: number of chunks equals ceil(N / C)
        assert len(chunk_values) == expected_chunk_count, (
            f"Expected {expected_chunk_count} chunks for {n} frames with "
            f"chunk size {size}, got {len(chunk_values)}"
        )

        # Property: each chunk contains at most chunk_size frames
        for i, chunk_str in enumerate(chunk_values):
            chunk_frames = RangeExpressionParser.parse(chunk_str)
            assert len(chunk_frames) <= size, (
                f"Chunk {i} has {len(chunk_frames)} frames, " f"exceeds max chunk size {size}"
            )
