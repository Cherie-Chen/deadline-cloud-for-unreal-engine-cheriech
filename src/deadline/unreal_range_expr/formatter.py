# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Formatter for integer range expressions."""

from typing import List


class RangeExpressionFormatter:
    """Formats lists of integers into range expressions."""

    @staticmethod
    def format_contiguous(start: int, end: int) -> str:
        """
        Format a contiguous range as "start-end".

        Args:
            start: Start frame (inclusive)
            end: End frame (inclusive)

        Returns:
            Range string like "1-10" or "5" for single frame

        Raises:
            ValueError: If start > end
        """
        if start > end:
            raise ValueError(f"Invalid range: start {start} > end {end}")

        return RangeExpressionFormatter._format_range(start, end)

    @staticmethod
    def format_noncontiguous(frames: List[int]) -> str:
        """
        Format a list of frames as an optimized range expression.

        Consecutive sequences are collapsed into ranges.

        Examples:
            - [1, 2, 3, 5, 7, 9, 11, 13, 15, 17, 19] -> "1-3,5,7,9,11,13,15,17,19"
            - [7, 9, 11, 13, 15, 17, 19] -> "7,9,11,13,15,17,19"
            - [1, 2, 3, 4, 5] -> "1-5"

        Note:
            This formatter does NOT detect step patterns (e.g., it won't output "7-20:2").
            It only collapses consecutive integers into ranges.

        Args:
            frames: List of frame numbers

        Returns:
            Range expression like "1,3,5-10,15"

        Raises:
            ValueError: If frames list is empty
        """
        if not frames:
            raise ValueError("Cannot format empty frame list")

        # Sort and deduplicate
        sorted_frames = sorted(set(frames))

        # Group consecutive frames into ranges
        ranges: List[str] = []
        range_start = sorted_frames[0]
        range_end = sorted_frames[0]

        for frame in sorted_frames[1:]:
            if frame == range_end + 1:
                # Extend current range
                range_end = frame
            else:
                # End current range and start new one
                ranges.append(RangeExpressionFormatter._format_range(range_start, range_end))
                range_start = frame
                range_end = frame

        # Don't forget the last range
        ranges.append(RangeExpressionFormatter._format_range(range_start, range_end))

        return ",".join(ranges)

    @staticmethod
    def _format_range(start: int, end: int) -> str:
        """Format a single range or value."""
        if start == end:
            return str(start)
        return f"{start}-{end}"
