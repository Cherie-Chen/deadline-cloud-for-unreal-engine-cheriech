# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Exceptions for the integer range expression module."""

from typing import Optional


class RangeExpressionError(Exception):
    """
    Raised when parsing or formatting an integer range expression fails.

    Attributes:
        message: Human-readable error description
        position: Optional character position where the error occurred
    """

    def __init__(self, message: str, position: Optional[int] = None):
        self.message = message
        self.position = position
        if position is not None:
            super().__init__(f"{message} at position {position}")
        else:
            super().__init__(message)
