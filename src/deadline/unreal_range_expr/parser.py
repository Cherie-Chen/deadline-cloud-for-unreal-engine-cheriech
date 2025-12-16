# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Parser for integer range expressions."""

import re
from typing import List, Match, Optional, Set

from .exceptions import RangeExpressionError


class RangeExpressionParser:
    """Parses integer range expressions into lists of integers."""

    # Pattern for a single range part: number, or number-number, or number-number:step
    _RANGE_PART_PATTERN = re.compile(r"^(-?\d+)(?:-(-?\d+)(?::(\d+))?)?$")

    @staticmethod
    def parse(expr: str) -> list[int]:
        """
        Parse an integer range expression into a sorted list of integers.

        Supported formats:
        - Single value: "5" -> [5]
        - Range: "1-10" -> [1,2,3,4,5,6,7,8,9,10]
        - Step range: "1-10:2" -> [1,3,5,7,9]
        - Comma-separated: "1,3,5" -> [1,3,5]
        - Mixed: "1,3,5-10,15-20:2" -> [1,3,5,6,7,8,9,10,15,17,19]

        Args:
            expr: Integer range expression string

        Returns:
            Sorted list of unique integers

        Raises:
            RangeExpressionError: If expression syntax is invalid
        """
        if not expr or not expr.strip():
            raise RangeExpressionError("Empty range expression")

        expr = expr.strip()
        result: Set[int] = set()
        position = 0

        parts = RangeExpressionParser._split_by_comma(expr)

        for part in parts:
            part_stripped = part.strip()
            if not part_stripped:
                raise RangeExpressionError("Empty range part", position)

            frames = RangeExpressionParser._parse_range_part(part_stripped, position)
            result.update(frames)
            position += len(part) + 1  # +1 for comma

        return sorted(result)

    @staticmethod
    def _split_by_comma(expr: str) -> List[str]:
        """Split expression by commas, handling negative numbers correctly."""
        parts: List[str] = []
        current_part = ""
        i = 0

        while i < len(expr):
            char = expr[i]
            if char == ",":
                parts.append(current_part)
                current_part = ""
            else:
                current_part += char
            i += 1

        if current_part:
            parts.append(current_part)

        return parts

    @staticmethod
    def _parse_range_part(part: str, position: int) -> List[int]:
        """
        Parse a single range part (e.g., "5", "1-10", "1-10:2").

        Args:
            part: The range part string
            position: Position in original expression for error reporting

        Returns:
            List of integers represented by this part

        Raises:
            RangeExpressionError: If the part is invalid
        """
        # Validate characters first
        for i, char in enumerate(part):
            if char not in "0123456789-:":
                raise RangeExpressionError(f"Invalid character '{char}'", position + i)

        match: Optional[Match[str]] = RangeExpressionParser._RANGE_PART_PATTERN.match(part)
        if not match:
            raise RangeExpressionError("Invalid number format", position)

        start_str, end_str, step_str = match.groups()

        try:
            start = int(start_str)
        except ValueError:
            raise RangeExpressionError("Invalid number format", position)

        # Single value case
        if end_str is None:
            return [start]

        try:
            end = int(end_str)
        except ValueError:
            raise RangeExpressionError("Invalid number format", position + len(start_str) + 1)

        # Validate range direction
        if start > end:
            raise RangeExpressionError(f"Invalid range: start {start} > end {end}", position)

        # Parse step if present
        step = 1
        if step_str is not None:
            try:
                step = int(step_str)
            except ValueError:
                raise RangeExpressionError("Invalid step value", position)
            if step <= 0:
                raise RangeExpressionError(f"Invalid step value: {step} must be positive", position)

        # Generate the range
        return list(range(start, end + 1, step))
