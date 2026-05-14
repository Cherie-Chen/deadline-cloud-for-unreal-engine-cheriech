# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
UE Automation spec test for the pre-submission credentials check.

This script is designed to be invoked from the Unreal Editor automation framework
(DeadlineCloud.Integration.CheckCredentials). It validates that:

1. Authenticated credentials allow submission to proceed
2. Expired credentials block submission in silent mode
3. Auth check exceptions do not block submission
4. submit_jobs() aborts early when credentials are invalid

To run manually from the UE Python console:
    exec(open(r"<plugin_path>/Content/Python/tests/test_check_credentials_spec.py").read())

To run via UE automation:
    UnrealEditor-Cmd.exe <project> -ExecCmds="Automation RunTests DeadlineCloud.Integration.CheckCredentials"
"""

import sys
from unittest.mock import MagicMock, patch

# Results tracking
_results = []


def _report(test_name: str, passed: bool, message: str = ""):
    """Report a test result."""
    status = "PASS" if passed else "FAIL"
    _results.append((test_name, passed, message))
    print(f"[{status}] {test_name}" + (f": {message}" if message else ""))


def test_authenticated_allows_submission():
    """Authenticated credentials should allow submission to proceed."""
    with (
        patch("deadline.unreal_submitter.submitter.check_authentication_status") as mock_auth,
        patch("deadline.unreal_submitter.submitter.config_file") as mock_config,
    ):
        from deadline.client.api import AwsAuthenticationStatus
        from deadline.unreal_submitter.submitter import UnrealSubmitter

        mock_auth.return_value = AwsAuthenticationStatus.AUTHENTICATED
        mock_config.read_config.return_value = MagicMock()

        submitter = UnrealSubmitter(silent_mode=True)
        result = submitter._check_credentials()

        if result is True:
            _report("Authenticated allows submission", True)
        else:
            _report("Authenticated allows submission", False, f"Expected True, got {result}")


def test_expired_blocks_submission_silent_mode():
    """Expired credentials should block submission in silent mode."""
    with (
        patch("deadline.unreal_submitter.submitter.check_authentication_status") as mock_auth,
        patch("deadline.unreal_submitter.submitter.config_file") as mock_config,
    ):
        from deadline.client.api import AwsAuthenticationStatus
        from deadline.unreal_submitter.submitter import UnrealSubmitter

        mock_auth.return_value = AwsAuthenticationStatus.NEEDS_LOGIN
        mock_config.read_config.return_value = MagicMock()

        submitter = UnrealSubmitter(silent_mode=True)
        result = submitter._check_credentials()

        if result is False:
            _report("Expired blocks submission (silent)", True)
        else:
            _report("Expired blocks submission (silent)", False, f"Expected False, got {result}")


def test_exception_does_not_block():
    """Auth check exception should not block submission."""
    with (
        patch("deadline.unreal_submitter.submitter.check_authentication_status") as mock_auth,
        patch("deadline.unreal_submitter.submitter.config_file") as mock_config,
    ):
        from deadline.unreal_submitter.submitter import UnrealSubmitter

        mock_auth.side_effect = Exception("Network timeout")
        mock_config.read_config.return_value = MagicMock()

        submitter = UnrealSubmitter(silent_mode=True)
        result = submitter._check_credentials()

        if result is True:
            _report("Exception does not block", True)
        else:
            _report("Exception does not block", False, f"Expected True, got {result}")


def test_submit_jobs_aborts_on_invalid_credentials():
    """submit_jobs() should abort early when credentials are invalid."""
    with (
        patch("deadline.unreal_submitter.submitter.check_authentication_status") as mock_auth,
        patch("deadline.unreal_submitter.submitter.config_file") as mock_config,
    ):
        from deadline.client.api import AwsAuthenticationStatus
        from deadline.unreal_submitter.submitter import UnrealSubmitter

        mock_auth.return_value = AwsAuthenticationStatus.NEEDS_LOGIN
        mock_config.read_config.return_value = MagicMock()

        submitter = UnrealSubmitter(silent_mode=True)

        # Add a fake job
        mock_job = MagicMock()
        mock_job.name = "TestJob"
        submitter._jobs.append(mock_job)

        with patch("unreal.Paths.project_dir", return_value="/fake/path"):
            result = submitter.submit_jobs()

        if result == [] and len(submitter._jobs) == 0:
            mock_job.create_job_bundle.assert_not_called()
            _report("submit_jobs aborts on invalid credentials", True)
        else:
            _report(
                "submit_jobs aborts on invalid credentials",
                False,
                f"result={result}, jobs_remaining={len(submitter._jobs)}",
            )


def test_configuration_error_blocks_submission():
    """CONFIGURATION_ERROR status should also block submission."""
    with (
        patch("deadline.unreal_submitter.submitter.check_authentication_status") as mock_auth,
        patch("deadline.unreal_submitter.submitter.config_file") as mock_config,
    ):
        from deadline.client.api import AwsAuthenticationStatus
        from deadline.unreal_submitter.submitter import UnrealSubmitter

        mock_auth.return_value = AwsAuthenticationStatus.CONFIGURATION_ERROR
        mock_config.read_config.return_value = MagicMock()

        submitter = UnrealSubmitter(silent_mode=True)
        result = submitter._check_credentials()

        if result is False:
            _report("CONFIGURATION_ERROR blocks submission", True)
        else:
            _report("CONFIGURATION_ERROR blocks submission", False, f"Expected False, got {result}")


def run_all():
    """Run all spec tests and report results."""
    print("\n" + "=" * 60)
    print("DeadlineCloud.Integration.CheckCredentials - Spec Tests")
    print("=" * 60 + "\n")

    test_authenticated_allows_submission()
    test_expired_blocks_submission_silent_mode()
    test_exception_does_not_block()
    test_submit_jobs_aborts_on_invalid_credentials()
    test_configuration_error_blocks_submission()

    print("\n" + "-" * 60)
    passed = sum(1 for _, p, _ in _results if p)
    total = len(_results)
    print(f"Results: {passed}/{total} passed")

    if passed < total:
        failed = [(name, msg) for name, p, msg in _results if not p]
        print("\nFailed tests:")
        for name, msg in failed:
            print(f"  - {name}: {msg}")
        print("-" * 60)
        raise AssertionError(f"{total - passed} test(s) failed")

    print("-" * 60 + "\n")


# Auto-run when executed
if __name__ == "__main__" or "unreal" in sys.modules:
    run_all()
