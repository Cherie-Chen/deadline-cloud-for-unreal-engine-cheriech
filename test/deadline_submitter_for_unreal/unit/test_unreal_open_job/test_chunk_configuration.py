# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Unit tests for chunk configuration validation.

Tests cover:
- ChunkConfiguration validation (Requirements 7.1, 7.2)
- RangeConstraint enum values
- ChunkIntTaskParameter chunk generation (Requirements 6.1, 6.2, 6.3)
"""

import pytest

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_chunk import (
    ChunkConfiguration,
    ChunkIntTaskParameter,
    RangeConstraint,
)


class TestRangeConstraint:
    """Tests for RangeConstraint enum."""

    def test_contiguous_value(self):
        """Test CONTIGUOUS enum has correct string value."""
        assert RangeConstraint.CONTIGUOUS.value == "CONTIGUOUS"

    def test_noncontiguous_value(self):
        """Test NONCONTIGUOUS enum has correct string value."""
        assert RangeConstraint.NONCONTIGUOUS.value == "NONCONTIGUOUS"


class TestChunkConfigurationValidation:
    """Tests for ChunkConfiguration.validate() method.

    Requirements: 7.1, 7.2
    """

    def test_valid_configuration_passes(self):
        """Test that valid configuration passes validation."""
        config = ChunkConfiguration(
            default_task_count=10,
            range_constraint=RangeConstraint.CONTIGUOUS,
            target_runtime_seconds=300,
        )
        # Should not raise
        config.validate()

    def test_valid_configuration_without_target_runtime(self):
        """Test that configuration without target_runtime_seconds passes."""
        config = ChunkConfiguration(
            default_task_count=5,
            range_constraint=RangeConstraint.NONCONTIGUOUS,
        )
        # Should not raise
        config.validate()

    def test_invalid_default_task_count_zero(self):
        """Test that defaultTaskCount of 0 raises ValueError.

        Requirements: 7.1
        """
        config = ChunkConfiguration(
            default_task_count=0,
            range_constraint=RangeConstraint.CONTIGUOUS,
        )
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        assert "defaultTaskCount must be at least 1" in str(exc_info.value)

    def test_invalid_default_task_count_negative(self):
        """Test that negative defaultTaskCount raises ValueError.

        Requirements: 7.1
        """
        config = ChunkConfiguration(
            default_task_count=-5,
            range_constraint=RangeConstraint.CONTIGUOUS,
        )
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        assert "defaultTaskCount must be at least 1" in str(exc_info.value)

    def test_invalid_target_runtime_negative(self):
        """Test that negative targetRuntimeSeconds raises ValueError.

        Requirements: 7.2 (implied - validation of configuration values)
        """
        config = ChunkConfiguration(
            default_task_count=10,
            range_constraint=RangeConstraint.CONTIGUOUS,
            target_runtime_seconds=-100,
        )
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        assert "targetRuntimeSeconds must be non-negative" in str(exc_info.value)

    def test_target_runtime_zero_is_valid(self):
        """Test that targetRuntimeSeconds of 0 is valid."""
        config = ChunkConfiguration(
            default_task_count=10,
            range_constraint=RangeConstraint.CONTIGUOUS,
            target_runtime_seconds=0,
        )
        # Should not raise
        config.validate()

    def test_default_task_count_one_is_valid(self):
        """Test that defaultTaskCount of 1 is valid (minimum)."""
        config = ChunkConfiguration(
            default_task_count=1,
            range_constraint=RangeConstraint.NONCONTIGUOUS,
        )
        # Should not raise
        config.validate()


class TestChunkIntTaskParameterGeneration:
    """Tests for ChunkIntTaskParameter.generate_chunk_values() method.

    Requirements: 6.1, 6.2, 6.3
    """

    def test_generate_contiguous_chunks(self):
        """Test generating contiguous chunk values.

        Requirements: 6.1
        """
        config = ChunkConfiguration(
            default_task_count=10,
            range_constraint=RangeConstraint.CONTIGUOUS,
        )
        param = ChunkIntTaskParameter(
            name="Frame",
            range_expr="1-25",
            chunks=config,
        )

        chunks = param.generate_chunk_values()

        assert len(chunks) == 3
        assert chunks[0] == "1-10"
        assert chunks[1] == "11-20"
        assert chunks[2] == "21-25"

    def test_generate_noncontiguous_chunks(self):
        """Test generating non-contiguous chunk values.

        Requirements: 6.1
        """
        config = ChunkConfiguration(
            default_task_count=5,
            range_constraint=RangeConstraint.NONCONTIGUOUS,
        )
        param = ChunkIntTaskParameter(
            name="Frame",
            range_expr="1-12",
            chunks=config,
        )

        chunks = param.generate_chunk_values()

        assert len(chunks) == 3
        # Non-contiguous format optimizes consecutive sequences
        assert chunks[0] == "1-5"
        assert chunks[1] == "6-10"
        assert chunks[2] == "11-12"

    def test_generate_chunks_with_step_range(self):
        """Test chunk generation with step range expression.

        Requirements: 6.1
        """
        config = ChunkConfiguration(
            default_task_count=3,
            range_constraint=RangeConstraint.NONCONTIGUOUS,
        )
        param = ChunkIntTaskParameter(
            name="Frame",
            range_expr="1-10:2",  # [1, 3, 5, 7, 9]
            chunks=config,
        )

        chunks = param.generate_chunk_values()

        assert len(chunks) == 2
        # First chunk: [1, 3, 5]
        assert chunks[0] == "1,3,5"
        # Second chunk: [7, 9]
        assert chunks[1] == "7,9"

    def test_generate_chunks_validates_configuration(self):
        """Test that generate_chunk_values validates configuration first.

        Requirements: 6.3
        """
        config = ChunkConfiguration(
            default_task_count=0,  # Invalid
            range_constraint=RangeConstraint.CONTIGUOUS,
        )
        param = ChunkIntTaskParameter(
            name="Frame",
            range_expr="1-10",
            chunks=config,
        )

        with pytest.raises(ValueError) as exc_info:
            param.generate_chunk_values()
        assert "defaultTaskCount must be at least 1" in str(exc_info.value)

    def test_generate_chunks_single_frame(self):
        """Test chunk generation with single frame."""
        config = ChunkConfiguration(
            default_task_count=10,
            range_constraint=RangeConstraint.CONTIGUOUS,
        )
        param = ChunkIntTaskParameter(
            name="Frame",
            range_expr="5",  # Single frame
            chunks=config,
        )

        chunks = param.generate_chunk_values()

        assert len(chunks) == 1
        # Single frame is formatted as just the number, not "5-5"
        assert chunks[0] == "5"

    def test_generate_chunks_exact_division(self):
        """Test chunk generation when frames divide evenly.

        Requirements: 6.1
        """
        config = ChunkConfiguration(
            default_task_count=5,
            range_constraint=RangeConstraint.CONTIGUOUS,
        )
        param = ChunkIntTaskParameter(
            name="Frame",
            range_expr="1-20",
            chunks=config,
        )

        chunks = param.generate_chunk_values()

        assert len(chunks) == 4
        assert chunks[0] == "1-5"
        assert chunks[1] == "6-10"
        assert chunks[2] == "11-15"
        assert chunks[3] == "16-20"

    def test_generate_chunks_with_target_runtime(self):
        """Test that target_runtime_seconds doesn't affect chunk generation.

        Requirements: 6.2
        """
        config = ChunkConfiguration(
            default_task_count=5,
            range_constraint=RangeConstraint.CONTIGUOUS,
            target_runtime_seconds=600,
        )
        param = ChunkIntTaskParameter(
            name="Frame",
            range_expr="1-10",
            chunks=config,
        )

        chunks = param.generate_chunk_values()

        # target_runtime_seconds is a hint to scheduler, doesn't affect generation
        assert len(chunks) == 2
        assert chunks[0] == "1-5"
        assert chunks[1] == "6-10"

    def test_generate_chunks_invalid_range_expression(self):
        """Test that invalid range expression raises error.

        Requirements: 6.3
        """
        from deadline.unreal_range_expr import RangeExpressionError

        config = ChunkConfiguration(
            default_task_count=5,
            range_constraint=RangeConstraint.CONTIGUOUS,
        )
        param = ChunkIntTaskParameter(
            name="Frame",
            range_expr="invalid-range-expr!",
            chunks=config,
        )

        with pytest.raises(RangeExpressionError):
            param.generate_chunk_values()
