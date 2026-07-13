# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for the pre-GUI hook orchestration in ``UnrealSubmitter``.

``UnrealSubmitter.submit_jobs`` runs pre-GUI submission hooks before building each job bundle
(the submission-time analog of Maya/Nuke's "before the dialog opens" hook point, since Unreal
has no submission dialog). These tests cover the orchestration ``_run_pre_gui_hooks`` /
``_unreal_hook_confirmation`` — env-only sourcing, the auto_accept/silent confirm policy, and
the once-per-queue prompt.

``UnrealSubmitter`` imports ``deadline.client.ui.pre_gui_hooks`` (ships in deadline-cloud 0.60.1+)
lazily inside ``_run_pre_gui_hooks``. To keep these tests runnable on the sandbox's older
deadline-cloud, each test injects a stub into ``sys.modules`` via ``patch.dict`` (the same pattern
this suite uses for ``P4``) exposing a fake ``PreGuiHookContext`` and a ``run_pre_gui_hooks`` mock
we assert against. deadline-cloud owns and tests the real hook execution.
"""

import sys
import types
from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import MagicMock, Mock, patch

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.client.exceptions import DeadlineOperationCanceled  # noqa: E402
from deadline.unreal_submitter.submitter import UnrealSubmitter  # noqa: E402


@dataclass
class _FakePreGuiHookContext:
    """Stand-in for deadline-cloud's PreGuiHookContext so we can assert what the submitter passed."""

    bundle_dir: Optional[str] = None
    job_name: str = ""
    parameters: dict = field(default_factory=dict)
    submitter_name: str = "JobBundle"
    priority: int = 50
    farm_id: Optional[str] = None
    queue_id: Optional[str] = None
    storage_profile_id: Optional[str] = None


def _stub_pre_gui_hooks(run_mock: Mock):
    """Build a stub ``deadline.client.ui.pre_gui_hooks`` module wrapping the given run mock."""
    stub = types.ModuleType("deadline.client.ui.pre_gui_hooks")
    stub.PreGuiHookContext = _FakePreGuiHookContext  # type: ignore[attr-defined]
    stub.run_pre_gui_hooks = run_mock  # type: ignore[attr-defined]
    return {"deadline.client.ui.pre_gui_hooks": stub}


def _make_job(name: str = "JobA") -> Mock:
    job = Mock()
    job.name = name
    job.apply_pre_gui_output = MagicMock()
    return job


@patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
class TestRunPreGuiHooks:
    @patch("deadline.unreal_submitter.submitter.get_setting", return_value="false")
    @patch("deadline.unreal_submitter.submitter.str2bool", return_value=False)
    def test_env_only_context_passed_and_output_applied(
        self, _str2bool: Mock, _get_setting: Mock, _telemetry: Mock
    ):
        """Hooks run env-only (bundle_dir=None, submitter_name='unreal') and output is applied."""
        run_mock = MagicMock(return_value={"name": "hooked"})
        submitter = UnrealSubmitter()
        job = _make_job("JobA")
        submitter._jobs.append(job)

        with patch.dict(sys.modules, _stub_pre_gui_hooks(run_mock)):
            submitter._run_pre_gui_hooks()

        run_mock.assert_called_once()
        context = run_mock.call_args.args[0]
        assert context.bundle_dir is None
        assert context.submitter_name == "unreal"
        assert context.job_name == "JobA"
        job.apply_pre_gui_output.assert_called_once_with({"name": "hooked"})

    @patch("deadline.unreal_submitter.submitter.get_setting", return_value="true")
    @patch("deadline.unreal_submitter.submitter.str2bool", return_value=True)
    def test_auto_accept_skips_confirm_callback(
        self, _str2bool: Mock, _get_setting: Mock, _telemetry: Mock
    ):
        """When settings.auto_accept is set, no confirm_callback is passed (hooks run unprompted)."""
        run_mock = MagicMock(return_value={})
        submitter = UnrealSubmitter()
        submitter._jobs.append(_make_job())

        with patch.dict(sys.modules, _stub_pre_gui_hooks(run_mock)):
            submitter._run_pre_gui_hooks()

        assert run_mock.call_args.kwargs["confirm_callback"] is None

    @patch("deadline.unreal_submitter.submitter.get_setting", return_value="false")
    @patch("deadline.unreal_submitter.submitter.str2bool", return_value=False)
    def test_confirm_callback_used_when_not_auto_accept(
        self, _str2bool: Mock, _get_setting: Mock, _telemetry: Mock
    ):
        """Without auto_accept, the Unreal-native confirmation callback is passed."""
        run_mock = MagicMock(return_value={})
        submitter = UnrealSubmitter()
        submitter._jobs.append(_make_job())

        with patch.dict(sys.modules, _stub_pre_gui_hooks(run_mock)):
            submitter._run_pre_gui_hooks()

        assert run_mock.call_args.kwargs["confirm_callback"] == submitter._unreal_hook_confirmation

    @patch("deadline.unreal_submitter.submitter.get_setting", return_value="false")
    @patch("deadline.unreal_submitter.submitter.str2bool", return_value=False)
    def test_only_first_job_prompts(self, _str2bool: Mock, _get_setting: Mock, _telemetry: Mock):
        """The confirmation prompt is shown once; later jobs run without a callback."""
        run_mock = MagicMock(return_value={})
        submitter = UnrealSubmitter()
        submitter._jobs.extend([_make_job("A"), _make_job("B"), _make_job("C")])

        with patch.dict(sys.modules, _stub_pre_gui_hooks(run_mock)):
            submitter._run_pre_gui_hooks()

        callbacks = [c.kwargs["confirm_callback"] for c in run_mock.call_args_list]
        assert callbacks[0] == submitter._unreal_hook_confirmation
        assert callbacks[1] is None and callbacks[2] is None


@patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
class TestPreGuiHookConfirmCallback:
    """The auto_accept branch of the confirm-callback selection, tested headlessly."""

    @patch("deadline.unreal_submitter.submitter.get_setting", return_value="true")
    @patch("deadline.unreal_submitter.submitter.str2bool", return_value=True)
    def test_confirm_callback_none_when_auto_accept_enabled(
        self, _str2bool: Mock, mock_get_setting: Mock, _telemetry: Mock
    ):
        """With settings.auto_accept enabled, hooks run without a confirmation prompt."""
        submitter = UnrealSubmitter()

        assert submitter._pre_gui_hook_confirm_callback() is None
        mock_get_setting.assert_called_once_with("settings.auto_accept")

    @patch("deadline.unreal_submitter.submitter.get_setting", return_value="false")
    @patch("deadline.unreal_submitter.submitter.str2bool", return_value=False)
    def test_confirm_callback_prompts_when_auto_accept_disabled(
        self, _str2bool: Mock, _get_setting: Mock, _telemetry: Mock
    ):
        """With settings.auto_accept disabled, the Unreal-native confirmation callback is used."""
        submitter = UnrealSubmitter()

        assert submitter._pre_gui_hook_confirm_callback() == submitter._unreal_hook_confirmation


@patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
class TestUnrealHookConfirmation:
    def test_silent_mode_auto_proceeds(self, _telemetry: Mock):
        """In silent mode there is no UI to prompt in, so confirmation proceeds without asking."""
        submitter = UnrealSubmitter(silent_mode=True)

        assert submitter._unreal_hook_confirmation([]) is True

    # These tests stub deadline-cloud's _generate_hooks_confirmation_message so they don't depend
    # on the installed deadline-cloud version's signature; the message text is deadline-cloud's
    # responsibility. They also patch submitter.unreal directly, since each test module in this
    # suite binds its own module-global `unreal` stub and whichever imports `submitter` first fixes
    # `submitter.unreal` to that object — so this file's `unreal_mock` may not be the one used.
    @patch("deadline.client.job_bundle._hooks._generate_hooks_confirmation_message")
    @patch("deadline.unreal_submitter.submitter.unreal")
    def test_yes_reply_proceeds(self, submitter_unreal: Mock, gen_msg: Mock, _telemetry: Mock):
        """A YES reply from the Unreal dialog proceeds; source_label is passed through."""
        gen_msg.return_value = "hooks msg"
        submitter = UnrealSubmitter(silent_mode=False)
        source = MagicMock()
        source.source_label = "environment (DEADLINE_HOOKS_DIR)"
        submitter_unreal.EditorDialog.show_message.return_value = submitter_unreal.AppReturnType.YES

        assert submitter._unreal_hook_confirmation([source]) is True
        # The env source_label must be forwarded so hooks aren't mislabeled as "job bundle".
        assert gen_msg.call_args.args[2] == "environment (DEADLINE_HOOKS_DIR)"

    @patch("deadline.client.job_bundle._hooks._generate_hooks_confirmation_message")
    @patch("deadline.unreal_submitter.submitter.unreal")
    def test_no_reply_cancels(self, submitter_unreal: Mock, gen_msg: Mock, _telemetry: Mock):
        """A non-YES reply from the Unreal dialog cancels."""
        gen_msg.return_value = "hooks msg"
        submitter = UnrealSubmitter(silent_mode=False)
        source = MagicMock()
        submitter_unreal.EditorDialog.show_message.return_value = submitter_unreal.AppReturnType.NO

        assert submitter._unreal_hook_confirmation([source]) is False


@patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
class TestSubmitJobsCancelation:
    @patch("deadline.unreal_submitter.submitter.UnrealSubmitter.show_message_dialog")
    @patch("subprocess.Popen")
    def test_declined_confirmation_cancels_submission(
        self, popen_mock: Mock, show_message_dialog_mock: Mock, _telemetry: Mock
    ):
        """If pre-GUI confirmation is declined, no bundle is built and submission is canceled."""
        run_mock = MagicMock(side_effect=DeadlineOperationCanceled("declined"))
        submitter = UnrealSubmitter()
        submitter._jobs.append(_make_job())

        with (
            patch.dict(sys.modules, _stub_pre_gui_hooks(run_mock)),
            patch("unreal.Paths.project_dir", return_value="/project/path"),
        ):
            submitted = submitter.submit_jobs()

        assert submitted == []
        popen_mock.assert_not_called()
        assert "canceled" in show_message_dialog_mock.mock_calls[0].args[0].lower()
