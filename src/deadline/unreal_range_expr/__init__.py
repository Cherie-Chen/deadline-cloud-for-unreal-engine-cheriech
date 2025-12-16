# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""
Integer range expression parsing and formatting module.

This module provides utilities for parsing and formatting integer range expressions
used in OpenJD task chunking for frame-based rendering workflows.

Supported formats:
- Single value: "5" -> [5]
- Range: "1-10" -> [1,2,3,4,5,6,7,8,9,10]
- Step range: "1-10:2" -> [1,3,5,7,9]
- Comma-separated: "1,3,5" -> [1,3,5]
- Mixed: "1,3,5-10,15-20:2" -> [1,3,5,6,7,8,9,10,15,17,19]
"""

from .exceptions import RangeExpressionError
from .formatter import RangeExpressionFormatter
from .parser import RangeExpressionParser

__all__ = [
    "RangeExpressionError",
    "RangeExpressionFormatter",
    "RangeExpressionParser",
]
