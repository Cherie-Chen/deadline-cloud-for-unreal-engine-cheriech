# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import unreal
import threading
import traceback
import subprocess
import json
import os
import sys
import time
from enum import Enum
from typing import Callable

from deadline.client.api import (
    get_deadline_cloud_library_telemetry_client,
)
from deadline.client.config import get_setting, str2bool
from deadline.client.exceptions import DeadlineOperationCanceled

from deadline.unreal_logger import get_logger
from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (
    UnrealOpenJob,
    RenderUnrealOpenJob,
)
from deadline.unreal_submitter.exceptions import UserException

from ._version import version

# Initialize telemetry client, opt-out is respected
telemetry_client = get_deadline_cloud_library_telemetry_client()
telemetry_client.update_common_details(
    {
        "deadline-cloud-for-unreal-engine-submitter-version": version,
        # Example: 5.4.3-34507850+++UE5+Release-5.4
        "unreal-engine-version": unreal.SystemLibrary.get_engine_version(),
    }
)


logger = get_logger()


def error_notify(
    notify_title: str = "Operation failed",
    notify_prefix: str = "Error occurred:\n",
    with_traceback: bool = False,
):
    def decorator(func: Callable):
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                unreal.log(str(e))
                unreal.log(traceback.format_exc())

                telemetry_client.record_error(
                    event_details={"exception_scope": "caught", "error_operation": "on_submit"},
                    exception_type=str(type(e)),
                    from_gui=not self._silent_mode,
                )

                if isinstance(e, UserException):
                    return

                message = notify_prefix + str(e)
                if with_traceback:
                    message += "\n" + traceback.format_exc()
                else:
                    message += "\nSee logs for more details."
                self.show_message_dialog(message=message, title=notify_title)

        return wrapper

    return decorator


class UnrealSubmitStatus(Enum):
    """
    Enumeration of the current UnrealSubmitter status
    """

    COMPLETED = 1
    HASHING = 2
    UPLOADING = 3


class UnrealSubmitter:
    """
    Execute the OpenJob submission
    """

    open_job_class: type[UnrealOpenJob] = UnrealOpenJob

    def __init__(self, silent_mode: bool = False):
        self._silent_mode = silent_mode

        self._jobs: list[UnrealOpenJob] = []
        self.submit_status: UnrealSubmitStatus = UnrealSubmitStatus.COMPLETED
        self.submit_message: str = "Start submitting..."
        self.progress_list: list[float] = []

        self.continue_submission = True  # affect all not submitted jobs
        self.submitted_job_ids: list[str] = []  # use after submit loop is ended
        self._submission_failed_message = ""  # reset after each job in the loop

    @property
    def submission_failed_message(self) -> str:
        return self._submission_failed_message

    def add_job(self, *args, **kwargs):
        """
        Build and add to the submission queue :class:`deadline.unreal_submitter.unreal_open_job.open_job_description.OpenJobDescription`
        """
        raise NotImplementedError

    def _display_progress(self, check_submit_status, message):
        """
        Display the operation progress in the UI.

        :param check_submit_status: :class:`deadline.unreal_submitter.submitter.UnrealSubmitStatus` value
        :type check_submit_status: :class:`deadline.unreal_submitter.submitter.UnrealSubmitStatus`
        :param message: Message to display
        :type message: str
        """
        last_progress: float = 0
        with unreal.ScopedSlowTask(100, message) as submit_task:
            submit_task.make_dialog(True)
            while self.submit_status == check_submit_status:
                if self.submission_failed_message != "":
                    break

                if submit_task.should_cancel():
                    self.continue_submission = False
                    break

                if len(self.progress_list) > 0:
                    new_progress = self.progress_list.pop(0)
                else:
                    new_progress = last_progress
                submit_task.enter_progress_frame(new_progress - last_progress, self.submit_message)
                last_progress = new_progress

    def show_confirmation_dialog(self, message: str, default_prompt_response: bool):
        """
        Show message dialog in the Unreal Editor UI

        :param message: Message to display
        :type message: str
        :param default_prompt_response: Default response
        :type default_prompt_response: bool
        """

        if self._silent_mode:
            return default_prompt_response

        # TODO handle confirmation

        return True

    def _get_python_executable(self):
        """Get Python executable from Unreal's directory structure"""
        return unreal.get_interpreter_executable_path()

    def _create_subprocess_env(self):
        """Create environment for subprocess with proper PYTHONPATH"""
        return dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))

    def _handle_subprocess_message(self, data):
        """Handle JSON message from subprocess"""
        if data["type"] == "hash_progress":
            self._hash_progress_from_subprocess(data["progress"], data["message"])
        elif data["type"] == "upload_progress":
            self._upload_progress_from_subprocess(data["progress"], data["message"])
        elif data["type"] == "create_job_result":
            self._create_job_result()
        elif data["type"] == "job_created":
            logger.info(f"Job creation result: {data['job_id']}")
            self.submitted_job_ids.append(data["job_id"])
        elif data["type"] == "error":
            self._submission_failed_message = data["message"]
        elif data["type"] == "debug":
            logger.info(f"Debug: {data['message']}")
        elif data["type"] == "api_message":
            logger.info(f"API: {data['message']}")

    def _start_submit(self, job_bundle_path, project_dir):
        """
        Start the OpenJob submission using wrapper subprocess

        :param job_bundle_path: Path of the Job bundle to submit
        :type job_bundle_path: str
        :param project_dir: Project directory path
        :type project_dir: str
        """

        try:
            wrapper_path = os.path.join(os.path.dirname(__file__), "job_submit_wrapper.py")
            python_exe = self._get_python_executable()
            start_time = time.time()

            process = subprocess.Popen(
                [python_exe, wrapper_path, job_bundle_path, project_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=self._create_subprocess_env(),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

            for line in iter(process.stdout.readline, ""):  # type: ignore[union-attr]
                try:
                    data = json.loads(line.strip())
                    self._handle_subprocess_message(data)
                except json.JSONDecodeError:
                    continue

            process.wait()
            logger.info(f"Job creation result in {time.time() - start_time} seconds")

            # Capture any stderr output for debugging
            if process.returncode != 0:
                stderr_output = process.stderr.read()  # type: ignore[union-attr]
                if stderr_output:
                    logger.error(f"Subprocess stderr: {stderr_output}")
                    if not self._submission_failed_message:
                        self._submission_failed_message = f"Subprocess failed: {stderr_output}"

        except Exception as e:
            logger.error(str(e))
            logger.error(traceback.format_exc())
            self._submission_failed_message = str(e)

    def _hash_progress_from_subprocess(self, progress, message):
        self.submit_status = UnrealSubmitStatus.HASHING
        logger.info(f"Hash progress: {progress} {message}")
        self.submit_message = message
        self.progress_list.append(progress)

    def _upload_progress_from_subprocess(self, progress, message):
        self.submit_status = UnrealSubmitStatus.UPLOADING
        logger.info(f"Upload progress: {progress} {message}")
        self.submit_message = message
        self.progress_list.append(progress)

    def _hash_progress(self, hash_metadata) -> bool:
        """
        Hashing progress callback for displaying hash metadata on the progress bar

        :param hash_metadata: :class:`deadline.job_attachments.progress_tracker.ProgressReportMetadata`
        :type hash_metadata: deadline.job_attachments.progress_tracker.ProgressReportMetadata
        :return: Continue submission or not
        :rtype: bool
        """
        self.submit_status = UnrealSubmitStatus.HASHING
        logger.info(
            "Hash progress: {} {}".format(hash_metadata.progress, hash_metadata.progressMessage)
        )
        self.submit_message = hash_metadata.progressMessage
        self.progress_list.append(hash_metadata.progress)
        return self.continue_submission

    def _upload_progress(self, upload_metadata) -> bool:
        """
        Uploading progress callback for displaying upload metadata on the progress bar

        :param upload_metadata: :class:`deadline.job_attachments.progress_tracker.ProgressReportMetadata`
        :type upload_metadata: deadline.job_attachments.progress_tracker.ProgressReportMetadata
        :return: Continue submission or not
        :rtype: bool
        """

        self.submit_status = UnrealSubmitStatus.UPLOADING
        logger.info(
            "Upload progress: {} {}".format(
                upload_metadata.progress, upload_metadata.progressMessage
            )
        )
        self.submit_message = upload_metadata.progressMessage
        self.progress_list.append(upload_metadata.progress)
        return self.continue_submission

    def _create_job_result(self) -> bool:
        """
        Creates job result callback
        :return: True
        """

        self.submit_status = UnrealSubmitStatus.COMPLETED
        logger.info("Create job result...")
        return True

    def show_message_dialog(
        self, message: str, title="Job Submission", message_type=unreal.AppMsgType.OK
    ):
        """
        Show message dialog in the Unreal Editor UI

        :param message: Message to display
        :type message: str
        :param title: Message title
        :type title: str
        :param message_type: Message box type
        :type message_type: unreal.AppMsgType.OK
        """

        if self._silent_mode:
            return

        unreal.EditorDialog.show_message(title=title, message=message, message_type=message_type)

    def _pre_gui_hook_confirm_callback(self):
        """Choose the confirmation callback for pre-GUI hooks based on the auto_accept setting.

        Returns ``None`` (run hooks without prompting) when ``settings.auto_accept`` is enabled,
        otherwise the Unreal-native confirmation dialog :meth:`_unreal_hook_confirmation`. Kept as
        a small helper so the auto_accept branch can be unit-tested headlessly.

        :return: The ``confirm_callback`` to pass to ``run_pre_gui_hooks``, or ``None``.
        """
        if str2bool(get_setting("settings.auto_accept")):
            return None
        return self._unreal_hook_confirmation

    def _unreal_hook_confirmation(self, sources: list) -> bool:
        """Show the standard "these hooks will run" confirmation in the Unreal Editor UI.

        This is the Unreal-native analog of deadline-cloud's ``qt_hook_confirmation`` (Unreal
        submitters have no Qt). Returns ``True`` to proceed, ``False`` to cancel. In silent mode
        there is no UI to prompt in, so it proceeds without asking.

        :param sources: List of ``HookManager`` sources whose pre-GUI hooks will run.
        :return: Whether the user accepted running the hooks.
        :rtype: bool
        """
        from deadline.client.job_bundle._hooks import _generate_hooks_confirmation_message

        if self._silent_mode:
            return True

        # Pass source_label so an environment-configured hook source (DEADLINE_HOOKS_DIR) is not
        # shown to the user as if it came from the job bundle — this prompt is the user's
        # informed-consent point for running arbitrary code. Mirrors deadline-cloud's
        # qt_hook_confirmation.
        confirmation_msg = (
            "".join(
                _generate_hooks_confirmation_message(
                    m.hooks, m._original_bundle_dir, m.source_label
                )
                for m in sources
                if m.hooks
            )
            + "Do you want to run these hooks?"
        )
        reply = unreal.EditorDialog.show_message(
            "Job Submission Confirmation",
            confirmation_msg,
            unreal.AppMsgType.YES_NO,
            unreal.AppReturnType.NO,
        )
        return reply == unreal.AppReturnType.YES

    def _run_pre_gui_hooks(self) -> None:
        """Run pre-GUI submission hooks for every queued Job and apply their output.

        Unreal submitters have no ``SubmitJobToDeadlineDialog``; this is the submission-time
        analog of the Maya/Nuke "before the dialog opens" hook point. Unreal has no on-disk job
        bundle here, so hooks are sourced from ``DEADLINE_HOOKS_DIR`` only (``bundle_dir=None``),
        gated by ``settings.allow_environment_hooks``. The confirmation prompt is shown once (the
        env hooks are the same for every Job) and skipped when ``settings.auto_accept`` is set or
        the submitter is running silently.

        :raises deadline.client.exceptions.DeadlineOperationCanceled: If the user declines the
            hook confirmation prompt.
        """
        # Imported lazily (not at module top): the pre_gui_hooks module ships in deadline-cloud
        # 0.60.1+, and a top-level import would break importing this module — and every unit test
        # that collects it — against older deadline-cloud releases.
        from deadline.client.ui.pre_gui_hooks import (
            PreGuiHookContext,
            run_pre_gui_hooks,
        )

        confirm_callback = self._pre_gui_hook_confirm_callback()

        for i, job in enumerate(self._jobs):
            pre_gui_output = run_pre_gui_hooks(
                PreGuiHookContext(
                    bundle_dir=None,
                    job_name=job.name,
                    submitter_name="unreal",
                ),
                # Only prompt for the first Job; the env-sourced hooks are identical across the
                # queue, so re-prompting per Job would be redundant. Later Jobs run without a
                # prompt (equivalent to the user having already accepted).
                confirm_callback=confirm_callback if i == 0 else None,
            )
            job.apply_pre_gui_output(pre_gui_output)

    @error_notify("Submission failed")
    def submit_jobs(self) -> list[str]:
        """
        Submit OpenJobs to the Deadline Cloud
        """

        del self.submitted_job_ids[:]

        # Run pre-GUI submission hooks so studios can pre-populate job fields before the bundle
        # is built. Declining the confirmation prompt cancels the whole submission.
        try:
            self._run_pre_gui_hooks()
        except DeadlineOperationCanceled as e:
            logger.info(f"Submission canceled by pre-GUI hook confirmation: {e}")
            self.show_message_dialog(
                f"Jobs submission canceled.\n" f"Number of unsubmitted jobs: {len(self._jobs)}"
            )
            del self._jobs[:]
            return self.submitted_job_ids

        # Get project root directory as absolute path
        project_dir = os.path.abspath(unreal.Paths.project_dir())
        for job in self._jobs:
            logger.info("Creating job from bundle...")
            self.submit_status = UnrealSubmitStatus.HASHING
            self.progress_list = []
            self.submit_message = "Start submitting..."
            self._submission_failed_message = ""

            job_bundle_path = job.create_job_bundle()
            t = threading.Thread(
                target=self._start_submit, args=(job_bundle_path, project_dir), daemon=True
            )
            t.start()

            self._display_progress(
                check_submit_status=UnrealSubmitStatus.HASHING, message="Hashing"
            )
            if self.continue_submission:
                self._display_progress(
                    check_submit_status=UnrealSubmitStatus.UPLOADING, message="Uploading"
                )
            t.join()

            # current job failed, notify and continue
            if self.submission_failed_message != "":
                self.show_message_dialog(
                    f"Job {job.name} unsubmitted for the reason:\n {self.submission_failed_message}"
                )

            # User cancel submission, notify and quit submission queue
            if not self.continue_submission:
                self.show_message_dialog(
                    f"Jobs submission canceled.\n"
                    f"Number of unsubmitted jobs: {len(self._jobs) - len(self.submitted_job_ids)}"
                )
                break

        # Summary notification about submission process
        self.show_message_dialog(
            f"Submitted jobs ({len(self.submitted_job_ids)}):\n" + "\n".join(self.submitted_job_ids)
        )

        del self._jobs[:]

        return self.submitted_job_ids


class UnrealOpenJobDataAssetSubmitter(UnrealSubmitter):

    @error_notify("Data asset converting failed")
    def add_job(self, unreal_open_job_data_asset: unreal.DeadlineCloudJob):
        open_job = self.open_job_class.from_data_asset(unreal_open_job_data_asset)
        self._jobs.append(open_job)


class UnrealMrqJobSubmitter(UnrealSubmitter):

    open_job_class = RenderUnrealOpenJob

    @error_notify("Data asset converting failed")
    def add_job(self, mrq_job: unreal.MoviePipelineExecutorJob):
        render_open_job = self.open_job_class.from_mrq_job(mrq_job)
        self._jobs.append(render_open_job)


class UnrealOpenJobSubmitter(UnrealSubmitter):

    @error_notify("Data asset converting failed")
    def add_job(self, open_job: UnrealOpenJob):
        self._jobs.append(open_job)


class UnrealRenderOpenJobSubmitter(UnrealSubmitter):

    open_job_class = RenderUnrealOpenJob

    @error_notify("Data asset converting failed")
    def add_job(self, render_open_job: RenderUnrealOpenJob):
        self._jobs.append(render_open_job)
