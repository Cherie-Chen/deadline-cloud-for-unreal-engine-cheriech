# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Chunk configuration module for OpenJD CHUNK[INT] task parameters."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from deadline.unreal_range_expr import (
    RangeExpressionFormatter,
    RangeExpressionParser,
)


class RangeConstraint(Enum):
    """Specifies whether chunks must be contiguous or can be non-contiguous."""

    CONTIGUOUS = "CONTIGUOUS"
    NONCONTIGUOUS = "NONCONTIGUOUS"


@dataclass
class ChunkConfiguration:
    """
    Configuration for CHUNK[INT] task parameters.

    Attributes:
        default_task_count: Number of frames to combine into a single chunk.
            Must be at least 1.
        range_constraint: Specifies output format (CONTIGUOUS or NONCONTIGUOUS).
        target_runtime_seconds: Optional hint to scheduler for desired chunk
            execution time. Must be non-negative if specified.
    """

    default_task_count: int
    range_constraint: RangeConstraint
    target_runtime_seconds: Optional[int] = None

    def validate(self) -> None:
        """
        Validate configuration values.

        Raises:
            ValueError: If defaultTaskCount < 1 or targetRuntimeSeconds < 0
        """
        if self.default_task_count < 1:
            raise ValueError("defaultTaskCount must be at least 1")
        if self.target_runtime_seconds is not None and self.target_runtime_seconds < 0:
            raise ValueError("targetRuntimeSeconds must be non-negative")


@dataclass
class ChunkIntTaskParameter:
    """
    Represents a CHUNK[INT] task parameter.

    Attributes:
        name: Parameter name
        range_expr: Frame range expression (e.g., "1-100" or "1,5,10-50")
        chunks: Chunk configuration
    """

    name: str
    range_expr: str
    chunks: ChunkConfiguration

    def generate_chunk_values(self) -> List[str]:
        """
        Generate the list of chunk value strings for task parameters.

        Divides the frame range into chunks based on default_task_count and
        formats output according to range_constraint.

        Returns:
            List of chunk strings (e.g., ["1-10", "11-20", "21-25"] for
            CONTIGUOUS or ["1,3,5", "7,9,11"] for NONCONTIGUOUS)

        Raises:
            RangeExpressionError: If range_expr is invalid
            ValueError: If chunk configuration is invalid
        """
        self.chunks.validate()

        # Parse the range expression into a list of frames
        frames = RangeExpressionParser.parse(self.range_expr)

        if not frames:
            return []

        chunk_size = self.chunks.default_task_count
        chunk_values: List[str] = []

        # Divide frames into chunks
        for i in range(0, len(frames), chunk_size):
            chunk_frames = frames[i : i + chunk_size]

            if self.chunks.range_constraint == RangeConstraint.CONTIGUOUS:
                # Format as "start-end"
                chunk_str = RangeExpressionFormatter.format_contiguous(
                    chunk_frames[0], chunk_frames[-1]
                )
            else:
                # Format as non-contiguous expression
                chunk_str = RangeExpressionFormatter.format_noncontiguous(chunk_frames)

            chunk_values.append(chunk_str)

        return chunk_values
