# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Unit tests for submitter CHUNK[INT] handling.

Tests cover:
- CHUNK[INT] parameter definition mapping (Requirements 4.1)
- UnrealOpenJobStep CHUNK[INT] parameter handling (Requirements 4.4, 7.4)
- ChunkedRenderUnrealOpenJobStep class (Requirements 1.1, 1.2, 1.3, 1.4)
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock unreal module before importing submitter modules
unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (  # noqa: E402
    PARAMETER_DEFINITION_MAPPING,
    OpenJobStepParameterNames,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (  # noqa: E402
    UnrealOpenJobStep,
    UnrealOpenJobStepParameterDefinition,
)


class TestChunkIntParameterDefinitionMapping:
    """Tests for CHUNK[INT] in PARAMETER_DEFINITION_MAPPING.

    Requirements: 4.1
    """

    def test_chunk_int_in_mapping(self):
        """Test that CHUNK[INT] is present in parameter definition mapping."""
        assert "CHUNK[INT]" in PARAMETER_DEFINITION_MAPPING

    def test_chunk_int_descriptor_properties(self):
        """Test CHUNK[INT] descriptor has correct properties."""
        descriptor = PARAMETER_DEFINITION_MAPPING["CHUNK[INT]"]

        assert descriptor.type_name == "CHUNK[INT]"
        assert descriptor.is_chunk_type is True
        # CHUNK[INT] values are passed as strings (e.g., "1-10")
        assert descriptor.python_class is str

    def test_chunk_int_uses_string_task_parameter(self):
        """Test CHUNK[INT] uses STRING task parameter for output."""
        from openjd.model.v2023_09 import StringTaskParameterDefinition

        descriptor = PARAMETER_DEFINITION_MAPPING["CHUNK[INT]"]
        assert descriptor.task_parameter_openjd_class == StringTaskParameterDefinition


class TestUnrealOpenJobStepChunkIntHandling:
    """Tests for UnrealOpenJobStep CHUNK[INT] parameter handling.

    Requirements: 4.4, 7.4
    """

    def _create_chunk_int_template(self, combination=None, range_expr="1-100", chunk_size=10):
        """Helper to create a template with CHUNK[INT] parameter."""
        template = {
            "name": "TestStep",
            "parameterSpace": {
                "taskParameterDefinitions": [
                    {
                        "name": "Frame",
                        "type": "CHUNK[INT]",
                        "range": range_expr,
                        "chunks": {
                            "defaultTaskCount": chunk_size,
                            "rangeConstraint": "CONTIGUOUS",
                        },
                    },
                    {"name": "Handler", "type": "STRING", "range": ["render"]},
                ]
            },
            "script": {"actions": {"onRun": {"command": "test"}}},
        }
        if combination:
            template["parameterSpace"]["combination"] = combination
        return template

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_chunk_int_with_associative_operator_raises_error(self, get_template_object_mock):
        """Test that CHUNK[INT] with associative operator raises ValueError.

        Requirements: 4.4, 7.4
        """
        # GIVEN - template with CHUNK[INT] and associative operator
        get_template_object_mock.return_value = self._create_chunk_int_template(combination="*")

        step = UnrealOpenJobStep(
            file_path="",
            extra_parameters=[
                UnrealOpenJobStepParameterDefinition("Frame", "CHUNK[INT]", ["1-100"]),
                UnrealOpenJobStepParameterDefinition("Handler", "STRING", ["render"]),
            ],
        )

        # WHEN/THEN
        with pytest.raises(ValueError) as exc_info:
            step._build_step_parameter_definition_list()

        assert "CHUNK[INT] parameter cannot be combined with associative operator" in str(
            exc_info.value
        )

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_chunk_int_generates_string_parameters(self, get_template_object_mock):
        """Test that CHUNK[INT] generates STRING task parameters with chunk values.

        Requirements: 1.1, 1.3
        """
        # GIVEN
        get_template_object_mock.return_value = self._create_chunk_int_template(
            range_expr="1-25", chunk_size=10
        )

        step = UnrealOpenJobStep(
            file_path="",
            extra_parameters=[
                UnrealOpenJobStepParameterDefinition("Frame", "CHUNK[INT]", ["1-25"]),
                UnrealOpenJobStepParameterDefinition("Handler", "STRING", ["render"]),
            ],
        )

        # WHEN
        params = step._build_step_parameter_definition_list()

        # THEN
        frame_param = next((p for p in params if p.name == "Frame"), None)
        assert frame_param is not None
        # CHUNK[INT] is converted to STRING
        assert frame_param.type.value == "STRING"
        # Should have 3 chunks: 1-10, 11-20, 21-25
        assert len(frame_param.range) == 3
        assert "1-10" in frame_param.range
        assert "11-20" in frame_param.range
        assert "21-25" in frame_param.range

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_chunk_int_missing_chunks_config_raises_error(self, get_template_object_mock):
        """Test that CHUNK[INT] without chunks config raises ValueError.

        Requirements: 7.4
        """
        # GIVEN - template without chunks configuration
        template = {
            "name": "TestStep",
            "parameterSpace": {
                "taskParameterDefinitions": [
                    {
                        "name": "Frame",
                        "type": "CHUNK[INT]",
                        "range": "1-100",
                        # Missing "chunks" configuration
                    },
                ]
            },
            "script": {"actions": {"onRun": {"command": "test"}}},
        }
        get_template_object_mock.return_value = template

        step = UnrealOpenJobStep(
            file_path="",
            extra_parameters=[
                UnrealOpenJobStepParameterDefinition("Frame", "CHUNK[INT]", ["1-100"]),
            ],
        )

        # WHEN/THEN
        with pytest.raises(ValueError) as exc_info:
            step._build_step_parameter_definition_list()

        assert "must have 'chunks' configuration" in str(exc_info.value)

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_chunk_int_missing_default_task_count_raises_error(self, get_template_object_mock):
        """Test that CHUNK[INT] without defaultTaskCount raises ValueError.

        Requirements: 7.4
        """
        # GIVEN - template without defaultTaskCount
        template = {
            "name": "TestStep",
            "parameterSpace": {
                "taskParameterDefinitions": [
                    {
                        "name": "Frame",
                        "type": "CHUNK[INT]",
                        "range": "1-100",
                        "chunks": {
                            "rangeConstraint": "CONTIGUOUS",
                            # Missing "defaultTaskCount"
                        },
                    },
                ]
            },
            "script": {"actions": {"onRun": {"command": "test"}}},
        }
        get_template_object_mock.return_value = template

        step = UnrealOpenJobStep(
            file_path="",
            extra_parameters=[
                UnrealOpenJobStepParameterDefinition("Frame", "CHUNK[INT]", ["1-100"]),
            ],
        )

        # WHEN/THEN
        with pytest.raises(ValueError) as exc_info:
            step._build_step_parameter_definition_list()

        assert "must have 'defaultTaskCount'" in str(exc_info.value)

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_chunk_int_invalid_range_constraint_raises_error(self, get_template_object_mock):
        """Test that CHUNK[INT] with invalid rangeConstraint raises ValueError.

        Requirements: 7.4
        """
        # GIVEN - template with invalid rangeConstraint
        template = {
            "name": "TestStep",
            "parameterSpace": {
                "taskParameterDefinitions": [
                    {
                        "name": "Frame",
                        "type": "CHUNK[INT]",
                        "range": "1-100",
                        "chunks": {
                            "defaultTaskCount": 10,
                            "rangeConstraint": "INVALID",
                        },
                    },
                ]
            },
            "script": {"actions": {"onRun": {"command": "test"}}},
        }
        get_template_object_mock.return_value = template

        step = UnrealOpenJobStep(
            file_path="",
            extra_parameters=[
                UnrealOpenJobStepParameterDefinition("Frame", "CHUNK[INT]", ["1-100"]),
            ],
        )

        # WHEN/THEN
        with pytest.raises(ValueError) as exc_info:
            step._build_step_parameter_definition_list()

        assert "rangeConstraint must be CONTIGUOUS or NONCONTIGUOUS" in str(exc_info.value)

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_chunk_int_noncontiguous_generates_correct_format(self, get_template_object_mock):
        """Test that NONCONTIGUOUS range constraint generates correct format.

        Requirements: 1.2
        """
        # GIVEN
        template = {
            "name": "TestStep",
            "parameterSpace": {
                "taskParameterDefinitions": [
                    {
                        "name": "Frame",
                        "type": "CHUNK[INT]",
                        "range": "1-10:2",  # [1, 3, 5, 7, 9]
                        "chunks": {
                            "defaultTaskCount": 3,
                            "rangeConstraint": "NONCONTIGUOUS",
                        },
                    },
                ]
            },
            "script": {"actions": {"onRun": {"command": "test"}}},
        }
        get_template_object_mock.return_value = template

        step = UnrealOpenJobStep(
            file_path="",
            extra_parameters=[
                UnrealOpenJobStepParameterDefinition("Frame", "CHUNK[INT]", ["1-10:2"]),
            ],
        )

        # WHEN
        params = step._build_step_parameter_definition_list()

        # THEN
        frame_param = next((p for p in params if p.name == "Frame"), None)
        assert frame_param is not None
        # Should have 2 chunks: [1,3,5] and [7,9]
        assert len(frame_param.range) == 2
        assert "1,3,5" in frame_param.range
        assert "7,9" in frame_param.range


class TestOpenJobStepParameterNames:
    """Tests for CHUNK[INT] related parameter names."""

    def test_frame_chunk_parameter_name(self):
        """Test FRAME_CHUNK parameter name is defined."""
        assert hasattr(OpenJobStepParameterNames, "FRAME_CHUNK")
        assert OpenJobStepParameterNames.FRAME_CHUNK == "Frame"

    def test_range_constraint_parameter_name(self):
        """Test RANGE_CONSTRAINT parameter name is defined."""
        assert hasattr(OpenJobStepParameterNames, "RANGE_CONSTRAINT")
        assert OpenJobStepParameterNames.RANGE_CONSTRAINT == "RangeConstraint"
