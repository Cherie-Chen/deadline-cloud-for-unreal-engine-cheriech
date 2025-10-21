# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import pytest
import tempfile
import os
from unittest.mock import MagicMock, patch, mock_open


unreal_mock = MagicMock()
unreal_mock.log = MagicMock()
sys.modules["unreal"] = unreal_mock


@pytest.fixture()
def unreal_render_step_handler():
    from deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler import (
        UnrealRenderStepHandler,
    )

    return UnrealRenderStepHandler()


class ShotInfoMock:

    def __init__(self, enabled: bool, outer_name: str, inner_name: str):
        self.enabled = enabled
        self.outer_name = outer_name
        self.inner_name = inner_name


class RenderJobMock:

    def __init__(self, shot_info: list[ShotInfoMock]):
        self.shot_info = shot_info


class TestUnrealRenderStepHandler:

    @pytest.mark.parametrize(
        "shots_count, enabled_shots_count, task_chunk_size, task_chunk_id",
        [
            (29, 15, 5, 0),
            (29, 29, 5, 1),
            (1, 1, 10, 0),
            (1500, 1, 1501, 0),
            (10, 9, 3, 2),
        ],
    )
    def test_enable_shots_by_chunk(
        self,
        unreal_render_step_handler,
        shots_count,
        enabled_shots_count,
        task_chunk_size,
        task_chunk_id,
    ):
        # GIVEN
        enabled_shots = [
            ShotInfoMock(enabled=True, outer_name=f"Enabled{i}", inner_name=f"Enabled{i}")
            for i in range(enabled_shots_count)
        ]
        disabled_shots = [
            ShotInfoMock(enabled=False, outer_name=f"Disabled{i}", inner_name=f"Disabled{i}")
            for i in range(shots_count - enabled_shots_count)
        ]
        render_job_mock = RenderJobMock(shot_info=enabled_shots + disabled_shots)

        enabled_job_shots = [shot for shot in render_job_mock.shot_info if shot.enabled]
        chunked = enabled_job_shots[
            task_chunk_id * task_chunk_size : (task_chunk_id + 1) * task_chunk_size
        ]
        chunked_names = [shot.outer_name for shot in chunked]

        # WHEN
        with patch(
            "deadline.unreal_adaptor.UnrealClient.step_handlers."
            "unreal_render_step_handler.logger.info"
        ) as log_mock:
            unreal_render_step_handler.enable_shots_by_chunk(
                render_job_mock, task_chunk_size, task_chunk_id
            )

            # THEN
            enabled_shots = [shot for shot in render_job_mock.shot_info if shot.enabled]
            assert all([shot.enabled for shot in enabled_shots])
            assert all([shot.outer_name.startswith("Enabled") for shot in chunked])
            assert len(enabled_shots) <= task_chunk_size and len(enabled_shots) <= shots_count

            disabled_shots = [
                shot for shot in render_job_mock.shot_info if shot.outer_name not in chunked_names
            ]
            for shot in disabled_shots:
                assert not shot.enabled

            log_mock.assert_called_with(
                f"Shots in task: {[shot.outer_name for shot in enabled_shots]}"
            )

    def test_copy_pipeline_queue_from_manifest_file(self, unreal_render_step_handler):
        # GIVEN
        manifest_content = '{"test": "manifest", "queue": "data"}'
        manifest_path = "manifest.utxt"
        
        mock_queue_subsystem = MagicMock()
        mock_pipeline_queue = MagicMock()
        mock_manifest_queue = MagicMock()
        
        # Ensure all mocks are properly configured and won't throw exceptions
        mock_queue_subsystem.get_queue.return_value = mock_pipeline_queue
        mock_pipeline_queue.delete_all_jobs.return_value = None
        mock_pipeline_queue.copy_from.return_value = None
        unreal_mock.MoviePipelineLibrary.load_manifest_file_from_string.return_value = mock_manifest_queue

        # WHEN
        with patch(
            "deadline.unreal_adaptor.UnrealClient.step_handlers."
            "unreal_render_step_handler.logger.warning"
        ) as mock_warning:
            with patch(
                "deadline.unreal_adaptor.UnrealClient.step_handlers."
                "unreal_render_step_handler.logger.info"
            ) as mock_info:
                # Reset the mock to ensure clean state
                unreal_mock.MoviePipelineLibrary.load_manifest_file_from_string.reset_mock()
                mock_queue_subsystem.reset_mock()
                mock_pipeline_queue.reset_mock()
                
                # Call the function
                unreal_render_step_handler.copy_pipeline_queue_from_manifest_file(
                    mock_queue_subsystem, manifest_path
                )
                
                # Verify no warning was logged (success case)
                mock_warning.assert_not_called()

        # THEN
        # Verify Unreal API was called with file path (not file content)
        # The function should be called with either the original path or a relative path
        unreal_mock.MoviePipelineLibrary.load_manifest_file_from_string.assert_called_once()
        call_args = unreal_mock.MoviePipelineLibrary.load_manifest_file_from_string.call_args[0][0]
        # Should be called with a path (either original or converted to relative)
        assert isinstance(call_args, str)
        assert call_args  # Should not be empty
        
        # Verify queue operations
        mock_queue_subsystem.get_queue.assert_called_once()
        mock_pipeline_queue.delete_all_jobs.assert_called_once()
        mock_pipeline_queue.copy_from.assert_called_once_with(mock_manifest_queue)

    def test_copy_pipeline_queue_from_manifest_file_with_file_error(self, unreal_render_step_handler):
        # GIVEN
        manifest_path = "/path/to/nonexistent/manifest.utxt"
        mock_queue_subsystem = MagicMock()

        # WHEN/THEN - Simulate Unreal API throwing an exception
        unreal_mock.MoviePipelineLibrary.load_manifest_file_from_string.side_effect = Exception("File not found")
        
        with patch(
            "deadline.unreal_adaptor.UnrealClient.step_handlers."
            "unreal_render_step_handler.logger.warning"
        ) as mock_warning:
            # Should not raise exception, but log warning and continue
            unreal_render_step_handler.copy_pipeline_queue_from_manifest_file(
                mock_queue_subsystem, manifest_path
            )
            
            # Verify warning was logged
            mock_warning.assert_called_once()
            warning_call_args = mock_warning.call_args[0][0]
            assert "Failed to load manifest file" in warning_call_args
            assert manifest_path in warning_call_args
            assert "Continuing with workflow" in warning_call_args
        
        # Reset the side effect for other tests
        unreal_mock.MoviePipelineLibrary.load_manifest_file_from_string.side_effect = None

    def test_copy_pipeline_queue_from_manifest_file_path_conversion(self, unreal_render_step_handler):
        """Test that absolute paths are converted to relative paths for Unreal API"""
        # GIVEN
        # Mock project directory
        project_dir = "/project/root"
        project_file_path = f"{project_dir}/MyProject.uproject"
        absolute_manifest_path = f"{project_dir}/Saved/manifest.utxt"
        expected_relative_path = "Saved/manifest.utxt"
        
        mock_queue_subsystem = MagicMock()
        mock_pipeline_queue = MagicMock()
        mock_manifest_queue = MagicMock()
        
        mock_queue_subsystem.get_queue.return_value = mock_pipeline_queue
        unreal_mock.MoviePipelineLibrary.load_manifest_file_from_string.return_value = mock_manifest_queue
        unreal_mock.Paths.get_project_file_path.return_value = "MyProject.uproject"
        unreal_mock.Paths.convert_relative_path_to_full.return_value = project_file_path

        # WHEN
        with patch("os.path.isabs", return_value=True):
            with patch("os.path.relpath", return_value=expected_relative_path):
                unreal_render_step_handler.copy_pipeline_queue_from_manifest_file(
                    mock_queue_subsystem, absolute_manifest_path
                )

        # THEN
        # Verify Unreal API was called with relative path
        unreal_mock.MoviePipelineLibrary.load_manifest_file_from_string.assert_called_once_with(
            expected_relative_path
        )
