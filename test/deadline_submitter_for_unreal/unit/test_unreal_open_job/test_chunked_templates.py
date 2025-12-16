# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Unit tests for CHUNK[INT] OpenJD template structure validation.

These tests verify that the chunked render templates are correctly structured
according to the OpenJD specification for task chunking (RFC 0001).

Requirements validated:
- 4.1: CHUNK[INT] type is present in step template
- 4.2: chunks configuration with defaultTaskCount and rangeConstraint
- 4.3: targetRuntimeSeconds in chunks configuration
- 4.4: No associative operator combination with CHUNK[INT]
"""

import os
import yaml
import pytest


# Path to the openjd_templates directory
TEMPLATES_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    "..",
    "src",
    "unreal_plugin",
    "Content",
    "Python",
    "openjd_templates",
)


class TestChunkedRenderStepTemplate:
    """Tests for dynamic_chunking_render_step.yml template structure."""

    @pytest.fixture
    def step_template(self) -> dict:
        """Load the chunked render step template."""
        template_path = os.path.join(
            TEMPLATES_DIR, "dynamic_chunking", "dynamic_chunking_render_step.yml"
        )
        with open(template_path, "r") as f:
            return yaml.safe_load(f)

    def test_template_has_name(self, step_template: dict):
        """Verify template has a name field."""
        assert "name" in step_template
        assert step_template["name"] == "Render"

    def test_template_has_parameter_space(self, step_template: dict):
        """Verify template has parameterSpace with taskParameterDefinitions."""
        assert "parameterSpace" in step_template
        assert "taskParameterDefinitions" in step_template["parameterSpace"]

    def test_frame_parameter_has_chunk_int_type(self, step_template: dict):
        """
        Verify Frame parameter has type CHUNK[INT].

        Validates: Requirements 4.1
        """
        task_params = step_template["parameterSpace"]["taskParameterDefinitions"]
        frame_param = next((p for p in task_params if p["name"] == "Frame"), None)

        assert frame_param is not None, "Frame parameter not found"
        assert frame_param["type"] == "CHUNK[INT]", "Frame parameter must have type CHUNK[INT]"

    def test_frame_parameter_has_range_reference(self, step_template: dict):
        """Verify Frame parameter references Frames job parameter."""
        task_params = step_template["parameterSpace"]["taskParameterDefinitions"]
        frame_param = next((p for p in task_params if p["name"] == "Frame"), None)

        assert frame_param is not None
        assert "range" in frame_param
        assert "{{Param.Frames}}" in frame_param["range"]

    def test_chunks_configuration_present(self, step_template: dict):
        """
        Verify chunks configuration is present with required fields.

        Validates: Requirements 4.2
        """
        task_params = step_template["parameterSpace"]["taskParameterDefinitions"]
        frame_param = next((p for p in task_params if p["name"] == "Frame"), None)

        assert frame_param is not None
        assert "chunks" in frame_param, "chunks configuration must be present"

        chunks = frame_param["chunks"]
        assert "defaultTaskCount" in chunks, "defaultTaskCount must be in chunks config"
        assert "rangeConstraint" in chunks, "rangeConstraint must be in chunks config"

    def test_chunks_default_task_count(self, step_template: dict):
        """Verify defaultTaskCount references job parameter."""
        task_params = step_template["parameterSpace"]["taskParameterDefinitions"]
        frame_param = next((p for p in task_params if p["name"] == "Frame"), None)
        chunks = frame_param["chunks"]

        # With TASK_CHUNKING extension, chunks config references job parameters
        assert chunks["defaultTaskCount"] == "{{Param.ChunkSize}}"

    def test_chunks_target_runtime_seconds(self, step_template: dict):
        """
        Verify targetRuntimeSeconds references job parameter.

        Validates: Requirements 4.3
        """
        task_params = step_template["parameterSpace"]["taskParameterDefinitions"]
        frame_param = next((p for p in task_params if p["name"] == "Frame"), None)
        chunks = frame_param["chunks"]

        assert "targetRuntimeSeconds" in chunks
        # With TASK_CHUNKING extension, chunks config references job parameters
        assert chunks["targetRuntimeSeconds"] == "{{Param.TargetRuntime}}"

    def test_chunks_range_constraint_valid(self, step_template: dict):
        """Verify rangeConstraint references job parameter."""
        task_params = step_template["parameterSpace"]["taskParameterDefinitions"]
        frame_param = next((p for p in task_params if p["name"] == "Frame"), None)
        chunks = frame_param["chunks"]

        # With TASK_CHUNKING extension, chunks config references job parameters
        assert chunks["rangeConstraint"] == "{{Param.RangeConstraint}}"

    def test_no_associative_operator_with_chunk_int(self, step_template: dict):
        """
        Verify CHUNK[INT] parameter is not combined with associative operator.

        Validates: Requirements 4.4
        """
        param_space = step_template["parameterSpace"]

        # Check that there's no combination field at the parameterSpace level
        # that would indicate associative operator usage
        assert "combination" not in param_space or param_space.get("combination") != "*"

    def test_run_data_contains_frame_chunk(self, step_template: dict):
        """Verify runData embedded file passes frame_chunk parameter."""
        embedded_files = step_template["script"]["embeddedFiles"]
        run_data = next((f for f in embedded_files if f["name"] == "runData"), None)

        assert run_data is not None, "runData embedded file not found"
        assert "frame_chunk" in run_data["data"]
        assert "{{Task.Param.Frame}}" in run_data["data"]

    def test_run_data_contains_handler(self, step_template: dict):
        """Verify runData embedded file passes handler parameter."""
        embedded_files = step_template["script"]["embeddedFiles"]
        run_data = next((f for f in embedded_files if f["name"] == "runData"), None)

        assert run_data is not None
        assert "handler" in run_data["data"]
        assert "{{Task.Param.Handler}}" in run_data["data"]

    def test_handler_parameter_present(self, step_template: dict):
        """Verify Handler parameter is present for adaptor routing."""
        task_params = step_template["parameterSpace"]["taskParameterDefinitions"]
        handler_param = next((p for p in task_params if p["name"] == "Handler"), None)

        assert handler_param is not None
        assert handler_param["type"] == "STRING"

    def test_queue_manifest_path_parameter_present(self, step_template: dict):
        """Verify QueueManifestPath parameter is present."""
        task_params = step_template["parameterSpace"]["taskParameterDefinitions"]
        queue_param = next((p for p in task_params if p["name"] == "QueueManifestPath"), None)

        assert queue_param is not None
        assert queue_param["type"] == "PATH"


class TestChunkedRenderJobTemplate:
    """Tests for dynamic_chunking_render_job.yml template structure."""

    @pytest.fixture
    def job_template(self) -> dict:
        """Load the chunked render job template."""
        template_path = os.path.join(
            TEMPLATES_DIR, "dynamic_chunking", "dynamic_chunking_render_job.yml"
        )
        with open(template_path, "r") as f:
            return yaml.safe_load(f)

    def test_template_has_specification_version(self, job_template: dict):
        """Verify template has correct specification version."""
        assert "specificationVersion" in job_template
        assert job_template["specificationVersion"] == "jobtemplate-2023-09"

    def test_template_has_name(self, job_template: dict):
        """Verify template has a name field."""
        assert "name" in job_template
        assert job_template["name"] == "RenderJob"

    def test_frames_parameter_present(self, job_template: dict):
        """
        Verify Frames parameter is present with STRING type.

        Validates: Requirements 6.1
        """
        params = job_template["parameterDefinitions"]
        frames_param = next((p for p in params if p["name"] == "Frames"), None)

        assert frames_param is not None, "Frames parameter not found"
        assert frames_param["type"] == "STRING"

    def test_chunk_size_parameter_present(self, job_template: dict):
        """
        Verify ChunkSize parameter is present with INT type.

        Validates: Requirements 6.1
        """
        params = job_template["parameterDefinitions"]
        chunk_size_param = next((p for p in params if p["name"] == "ChunkSize"), None)

        assert chunk_size_param is not None, "ChunkSize parameter not found"
        assert chunk_size_param["type"] == "INT"

    def test_chunk_size_has_min_value(self, job_template: dict):
        """Verify ChunkSize has minValue of 1."""
        params = job_template["parameterDefinitions"]
        chunk_size_param = next((p for p in params if p["name"] == "ChunkSize"), None)

        assert chunk_size_param is not None
        assert chunk_size_param.get("minValue", 0) >= 1

    def test_target_runtime_parameter_present(self, job_template: dict):
        """
        Verify TargetRuntime parameter is present with INT type.

        Validates: Requirements 6.2
        """
        params = job_template["parameterDefinitions"]
        target_runtime_param = next((p for p in params if p["name"] == "TargetRuntime"), None)

        assert target_runtime_param is not None, "TargetRuntime parameter not found"
        assert target_runtime_param["type"] == "INT"

    def test_target_runtime_has_min_value(self, job_template: dict):
        """Verify TargetRuntime has minValue of 0."""
        params = job_template["parameterDefinitions"]
        target_runtime_param = next((p for p in params if p["name"] == "TargetRuntime"), None)

        assert target_runtime_param is not None
        assert target_runtime_param.get("minValue", -1) >= 0

    def test_project_file_path_parameter_present(self, job_template: dict):
        """Verify ProjectFilePath parameter is present."""
        params = job_template["parameterDefinitions"]
        project_param = next((p for p in params if p["name"] == "ProjectFilePath"), None)

        assert project_param is not None
        assert project_param["type"] == "PATH"

    def test_conda_packages_parameter_present(self, job_template: dict):
        """Verify CondaPackages parameter is present."""
        params = job_template["parameterDefinitions"]
        conda_param = next((p for p in params if p["name"] == "CondaPackages"), None)

        assert conda_param is not None
        assert conda_param["type"] == "STRING"

    def test_conda_channels_parameter_present(self, job_template: dict):
        """Verify CondaChannels parameter is present."""
        params = job_template["parameterDefinitions"]
        channels_param = next((p for p in params if p["name"] == "CondaChannels"), None)

        assert channels_param is not None
        assert channels_param["type"] == "STRING"
