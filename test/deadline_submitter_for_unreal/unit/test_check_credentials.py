# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for the pre-submission credentials check in UnrealSubmitter."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, Mock, patch

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.submitter import UnrealSubmitter  # noqa: E402


class TestCheckCredentials:
    """Tests for UnrealSubmitter._check_credentials()"""

    def setup_method(self):
        """Reset the unreal mock state before each test."""
        unreal_mock.reset_mock()
        # Ensure AppReturnType comparisons work predictably
        unreal_mock.AppReturnType.YES = "YES"
        unreal_mock.AppReturnType.NO = "NO"

    @patch("deadline.unreal_submitter.submitter.check_authentication_status")
    @patch("deadline.unreal_submitter.submitter.config_file")
    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    def test_returns_true_when_authenticated(
        self,
        mock_telemetry_client: Mock,
        mock_config_file: Mock,
        mock_check_auth: Mock,
    ):
        """When credentials are valid, _check_credentials returns True without showing dialogs."""
        from deadline.client.api import AwsAuthenticationStatus

        mock_check_auth.return_value = AwsAuthenticationStatus.AUTHENTICATED
        mock_config_file.read_config.return_value = MagicMock()

        submitter = UnrealSubmitter()
        result = submitter._check_credentials()

        assert result is True

    @patch("deadline.unreal_submitter.submitter.check_authentication_status")
    @patch("deadline.unreal_submitter.submitter.config_file")
    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    def test_returns_false_in_silent_mode_when_not_authenticated(
        self,
        mock_telemetry_client: Mock,
        mock_config_file: Mock,
        mock_check_auth: Mock,
    ):
        """In silent mode, returns False without showing dialogs when creds are expired."""
        from deadline.client.api import AwsAuthenticationStatus

        mock_check_auth.return_value = AwsAuthenticationStatus.NEEDS_LOGIN
        mock_config_file.read_config.return_value = MagicMock()

        submitter = UnrealSubmitter(silent_mode=True)
        result = submitter._check_credentials()

        assert result is False

    @patch("deadline.unreal_submitter.submitter.check_authentication_status")
    @patch("deadline.unreal_submitter.submitter.config_file")
    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    def test_shows_login_dialog_when_not_authenticated(
        self,
        mock_telemetry_client: Mock,
        mock_config_file: Mock,
        mock_check_auth: Mock,
    ):
        """When creds are expired, shows a Yes/No dialog asking to open DCM."""
        from deadline.client.api import AwsAuthenticationStatus

        mock_check_auth.return_value = AwsAuthenticationStatus.NEEDS_LOGIN
        mock_config_file.read_config.return_value = MagicMock()

        # User clicks "No" — decline to log in
        unreal_mock.EditorDialog.show_message.return_value = "NO"

        submitter = UnrealSubmitter(silent_mode=False)
        result = submitter._check_credentials()

        assert result is False
        # Verify dialog was shown with login prompt
        call_args_list = unreal_mock.EditorDialog.show_message.call_args_list
        assert len(call_args_list) >= 1
        first_call = call_args_list[0]
        message = first_call.kwargs.get("message", "")
        assert "expired" in message or "not configured" in message

    @patch("deadline.unreal_submitter.submitter.login")
    @patch("deadline.unreal_submitter.submitter.check_authentication_status")
    @patch("deadline.unreal_submitter.submitter.config_file")
    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    def test_login_success_returns_true(
        self,
        mock_telemetry_client: Mock,
        mock_config_file: Mock,
        mock_check_auth: Mock,
        mock_login: Mock,
    ):
        """When user accepts login prompt and login succeeds, returns True."""
        from deadline.client.api import AwsAuthenticationStatus

        mock_check_auth.return_value = AwsAuthenticationStatus.NEEDS_LOGIN
        mock_config_file.read_config.return_value = MagicMock()

        # User clicks "Yes"
        unreal_mock.EditorDialog.show_message.return_value = "YES"
        # Login succeeds
        mock_login.return_value = "Login as user@example.com"

        submitter = UnrealSubmitter(silent_mode=False)
        result = submitter._check_credentials()

        assert result is True
        mock_login.assert_called_once()

    @patch("deadline.unreal_submitter.submitter.login")
    @patch("deadline.unreal_submitter.submitter.check_authentication_status")
    @patch("deadline.unreal_submitter.submitter.config_file")
    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    def test_login_failure_returns_false(
        self,
        mock_telemetry_client: Mock,
        mock_config_file: Mock,
        mock_check_auth: Mock,
        mock_login: Mock,
    ):
        """When user accepts login prompt but login fails, returns False."""
        from deadline.client.api import AwsAuthenticationStatus

        mock_check_auth.return_value = AwsAuthenticationStatus.NEEDS_LOGIN
        mock_config_file.read_config.return_value = MagicMock()

        # User clicks "Yes"
        unreal_mock.EditorDialog.show_message.return_value = "YES"
        # Login fails (returns None/empty)
        mock_login.return_value = None

        submitter = UnrealSubmitter(silent_mode=False)
        result = submitter._check_credentials()

        assert result is False
        mock_login.assert_called_once()

    @patch("deadline.unreal_submitter.submitter.check_authentication_status")
    @patch("deadline.unreal_submitter.submitter.config_file")
    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    def test_returns_true_when_check_raises_exception(
        self,
        mock_telemetry_client: Mock,
        mock_config_file: Mock,
        mock_check_auth: Mock,
    ):
        """When auth check itself throws, don't block — return True and let submission fail naturally."""
        mock_check_auth.side_effect = Exception("Network error")
        mock_config_file.read_config.return_value = MagicMock()

        submitter = UnrealSubmitter()
        result = submitter._check_credentials()

        # Should not block submission
        assert result is True

    @patch("deadline.unreal_submitter.submitter.check_authentication_status")
    @patch("deadline.unreal_submitter.submitter.config_file")
    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    def test_handles_configuration_error_status(
        self,
        mock_telemetry_client: Mock,
        mock_config_file: Mock,
        mock_check_auth: Mock,
    ):
        """CONFIGURATION_ERROR status should also trigger the login dialog."""
        from deadline.client.api import AwsAuthenticationStatus

        mock_check_auth.return_value = AwsAuthenticationStatus.CONFIGURATION_ERROR
        mock_config_file.read_config.return_value = MagicMock()

        # User declines login
        unreal_mock.EditorDialog.show_message.return_value = "NO"

        submitter = UnrealSubmitter(silent_mode=False)
        result = submitter._check_credentials()

        assert result is False


class TestSubmitJobsCredentialCheck:
    """Tests that submit_jobs() calls _check_credentials() and aborts on failure."""

    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    def test_submit_jobs_aborts_when_credentials_invalid(
        self,
        mock_telemetry_client: Mock,
    ):
        """submit_jobs() returns empty list and clears jobs when creds check fails."""
        submitter = UnrealSubmitter(silent_mode=True)

        # Add a fake job
        mock_job = MagicMock()
        mock_job.name = "TestJob"
        submitter._jobs.append(mock_job)

        # Mock _check_credentials to return False
        with patch.object(submitter, "_check_credentials", return_value=False):
            with patch("unreal.Paths.project_dir", return_value="/project/path"):
                result = submitter.submit_jobs()

        # No jobs submitted
        assert result == []
        # Jobs list cleared
        assert len(submitter._jobs) == 0
        # create_job_bundle was never called
        mock_job.create_job_bundle.assert_not_called()

    @patch("subprocess.Popen")
    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    def test_submit_jobs_proceeds_when_credentials_valid(
        self,
        mock_telemetry_client: Mock,
        mock_popen: Mock,
    ):
        """submit_jobs() proceeds normally when creds check passes."""
        submitter = UnrealSubmitter(silent_mode=True)

        # Add a fake job
        mock_job = MagicMock()
        mock_job.name = "TestJob"
        mock_job.create_job_bundle.return_value = "/path/to/bundle"
        submitter._jobs.append(mock_job)

        # Mock subprocess
        process_mock = Mock()
        process_mock.stdout.readline.side_effect = [
            '{"type": "job_created", "job_id": "job-abc123"}\n',
            "",
        ]
        process_mock.returncode = 0
        process_mock.stderr.read.return_value = ""
        mock_popen.return_value = process_mock

        # Mock _check_credentials to return True
        with patch.object(submitter, "_check_credentials", return_value=True):
            with patch("unreal.Paths.project_dir", return_value="/project/path"):
                result = submitter.submit_jobs()

        # Job was submitted
        assert "job-abc123" in result
        mock_job.create_job_bundle.assert_called_once()
