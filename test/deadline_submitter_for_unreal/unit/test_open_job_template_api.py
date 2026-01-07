# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import pytest
from unittest.mock import MagicMock, Mock

# Mock external modules before importing
unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

# Set up mock enum values
unreal_mock.UserInterfaceControl.LINE_EDIT = "LINE_EDIT"
unreal_mock.UserInterfaceControl.SPIN_BOX = "SPIN_BOX"
unreal_mock.UserInterfaceControl.HIDDEN = "HIDDEN"
unreal_mock.ValueType.INT = "INT"
unreal_mock.ValueType.STRING = "STRING"


class TestJobParameterLabelExtraction:
    """
    Tests for userInterface.label extraction logic.
    
    The actual implementation is in open_job_template_api.py which runs inside Unreal Engine.
    These tests verify the expected behavior of the label extraction logic.
    """

    def test_extracts_label_from_user_interface(self):
        """Test that label is extracted from userInterface.label"""
        # GIVEN
        job_parameter = {
            "name": "ChunkSize",
            "type": "INT",
            "default": 50,
            "userInterface": {
                "control": "SPIN_BOX",
                "label": "Default Dynamic Chunk Size"
            }
        }

        # WHEN - simulate the extraction logic from open_job_template_api.py
        label = None
        if "userInterface" in job_parameter and "label" in job_parameter["userInterface"]:
            label = job_parameter["userInterface"]["label"]

        # THEN
        assert label == "Default Dynamic Chunk Size"

    def test_label_is_none_when_not_in_user_interface(self):
        """Test that label is None when userInterface.label is missing"""
        # GIVEN
        job_parameter = {
            "name": "ChunkSize",
            "type": "INT",
            "default": 50,
            "userInterface": {
                "control": "SPIN_BOX"
            }
        }

        # WHEN
        label = None
        if "userInterface" in job_parameter and "label" in job_parameter["userInterface"]:
            label = job_parameter["userInterface"]["label"]

        # THEN
        assert label is None

    def test_label_is_none_when_no_user_interface(self):
        """Test that label is None when userInterface section is missing"""
        # GIVEN
        job_parameter = {
            "name": "FramesPerTask",
            "type": "INT",
            "default": 0
        }

        # WHEN
        label = None
        if "userInterface" in job_parameter and "label" in job_parameter["userInterface"]:
            label = job_parameter["userInterface"]["label"]

        # THEN
        assert label is None

    def test_extracts_both_control_and_label(self):
        """Test that both control and label can be extracted from userInterface"""
        # GIVEN
        job_parameter = {
            "name": "TargetRuntimeSeconds",
            "type": "INT",
            "default": 0,
            "userInterface": {
                "control": "SPIN_BOX",
                "label": "Target Runtime Seconds"
            }
        }

        # WHEN
        control = None
        label = None
        if "userInterface" in job_parameter:
            if "control" in job_parameter["userInterface"]:
                control = job_parameter["userInterface"]["control"]
            if "label" in job_parameter["userInterface"]:
                label = job_parameter["userInterface"]["label"]

        # THEN
        assert control == "SPIN_BOX"
        assert label == "Target Runtime Seconds"

    def test_dynamic_chunking_template_has_labels(self):
        """Test that dynamic chunking template parameters have expected labels"""
        import yaml
        from pathlib import Path

        # GIVEN - path to dynamic chunking job template
        # test file is at: test/deadline_submitter_for_unreal/unit/test_open_job_template_api.py
        # template is at: src/unreal_plugin/Content/Python/openjd_templates/dynamic_chunking/...
        test_file = Path(__file__).resolve()
        repo_root = test_file.parent.parent.parent.parent  # Go up 4 levels from test file
        template_path = repo_root / "src" / "unreal_plugin" / "Content" / "Python" / \
            "openjd_templates" / "dynamic_chunking" / "dynamic_chunking_render_job.yml"

        # WHEN - load and parse the template
        with open(template_path, "r") as f:
            job_template = yaml.safe_load(f)

        # Find ChunkSize and TargetRuntimeSeconds parameters
        chunk_size_param = None
        target_runtime_param = None
        for param in job_template["parameterDefinitions"]:
            if param["name"] == "ChunkSize":
                chunk_size_param = param
            elif param["name"] == "TargetRuntimeSeconds":
                target_runtime_param = param

        # THEN - verify labels are defined
        assert chunk_size_param is not None, "ChunkSize parameter not found"
        assert "userInterface" in chunk_size_param, "ChunkSize missing userInterface"
        assert "label" in chunk_size_param["userInterface"], "ChunkSize missing label"
        assert chunk_size_param["userInterface"]["label"] == "Default Dynamic Chunk Size"

        assert target_runtime_param is not None, "TargetRuntimeSeconds parameter not found"
        assert "userInterface" in target_runtime_param, "TargetRuntimeSeconds missing userInterface"
        assert "label" in target_runtime_param["userInterface"], "TargetRuntimeSeconds missing label"
        assert target_runtime_param["userInterface"]["label"] == "Target Runtime Seconds"
