# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for :meth:`UnrealOpenJob.apply_pre_gui_output`.

``apply_pre_gui_output`` delegates routing (name/description vs template param vs shared value)
to deadline-cloud's public ``deadline.client.ui.pre_gui_hooks.apply_pre_gui_output`` and then
writes the routed result back onto the Unreal Job — the DCC-owned piece these tests cover.

That deadline-cloud module ships in 0.60.1+; to keep these tests runnable on the sandbox's older
deadline-cloud, and since ``UnrealOpenJob`` imports it lazily inside the method, each test injects a
stub ``deadline.client.ui.pre_gui_hooks`` into ``sys.modules`` (the same ``patch.dict`` pattern
this suite already uses to stub ``P4``) whose ``apply_pre_gui_output`` is a faithful copy of the
library's documented routing contract. deadline-cloud owns and tests the real routing; here we
assert the Unreal write-back onto ``_name`` / ``_description`` / ``_extra_parameters`` / the
shared settings, plus the unmatched-parameter warning.
"""

import sys
import types
from typing import Any, Optional
from unittest.mock import MagicMock, patch

from test.deadline_submitter_for_unreal import fixtures

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (  # noqa: E402
    UnrealOpenJob,
    UnrealOpenJobParameterDefinition,
)

_TEMPLATE_PATCH = (
    "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
    "UnrealOpenJobEntity.get_template_object"
)


def _faithful_apply_pre_gui_output(
    pre_gui_output: dict,
    initial_settings: Any,
    initial_shared_parameter_values: dict,
    cli_provided_param_names: Optional[set] = None,
) -> None:
    """Faithful copy of deadline-cloud's public ``apply_pre_gui_output`` routing contract.

    Kept in sync with ``deadline.client.ui.pre_gui_hooks.apply_pre_gui_output``: any hook
    parameter whose name matches an entry in ``initial_settings.parameters`` updates that entry
    in place; every other parameter lands in ``initial_shared_parameter_values``; ``name`` /
    ``description`` overwrite the settings fields; CLI-provided names win over hook values.
    """
    if not pre_gui_output:
        return
    cli_provided_param_names = cli_provided_param_names or set()
    hook_params = pre_gui_output.get("parameters", {})
    template_parameters = getattr(initial_settings, "parameters", None) or []
    template_param_names = {p["name"] for p in template_parameters}
    for param_name, param_value in hook_params.items():
        if param_name in cli_provided_param_names:
            continue
        if param_name in template_param_names:
            for p in template_parameters:
                if p["name"] == param_name:
                    p["value"] = param_value
                    break
        else:
            initial_shared_parameter_values[param_name] = param_value
    if "name" in pre_gui_output:
        initial_settings.name = pre_gui_output["name"]
    if "description" in pre_gui_output:
        initial_settings.description = pre_gui_output["description"]


def _pre_gui_hooks_stub() -> types.ModuleType:
    stub = types.ModuleType("deadline.client.ui.pre_gui_hooks")
    stub.apply_pre_gui_output = _faithful_apply_pre_gui_output  # type: ignore[attr-defined]
    return stub


def _make_job() -> UnrealOpenJob:
    with patch(_TEMPLATE_PATCH, return_value=fixtures.f_job_template_default()):
        return UnrealOpenJob(
            file_path="",
            name="OriginalName",
            extra_parameters=[
                UnrealOpenJobParameterDefinition.from_dict(p)
                for p in fixtures.f_job_template_default()["parameterDefinitions"]
            ],
        )


@patch.dict(sys.modules, {"deadline.client.ui.pre_gui_hooks": _pre_gui_hooks_stub()}, clear=False)
class TestApplyPreGuiOutput:
    def test_empty_output_is_a_noop(self):
        """No pre-GUI hook output leaves the Job untouched (and never imports the helper)."""
        job = _make_job()

        job.apply_pre_gui_output({})

        assert job.name == "OriginalName"
        assert job.description == ""

    def test_name_and_description_applied(self):
        """``name`` / ``description`` overwrite the Job's name and description."""
        job = _make_job()

        job.apply_pre_gui_output({"name": "FROM_HOOK", "description": "set by pipeline"})

        assert job.name == "FROM_HOOK"
        assert job.description == "set by pipeline"

    def test_matching_parameter_updated_in_place(self):
        """A hook parameter matching a Job template parameter updates that parameter's value."""
        job = _make_job()

        job.apply_pre_gui_output({"parameters": {"ParamB": "overridden"}})

        param_b = job._find_extra_parameter("ParamB", "STRING")
        assert param_b is not None
        assert param_b.value == "overridden"

    def test_deadline_shared_setting_updated(self):
        """A ``deadline:`` parameter updates the serialized shared settings the bundle emits."""
        job = _make_job()

        job.apply_pre_gui_output(
            {
                "parameters": {
                    "deadline:priority": 90,
                    "deadline:targetTaskRunStatus": "SUSPENDED",
                }
            }
        )

        shared = {p["name"]: p["value"] for p in job.job_shared_settings.serialize()}
        assert shared["deadline:priority"] == 90
        assert shared["deadline:targetTaskRunStatus"] == "SUSPENDED"

    def test_unmatched_parameter_is_warned_and_skipped(self):
        """A parameter that matches neither a template param nor a shared setting is warned."""
        job = _make_job()

        with patch(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.logger"
        ) as logger_mock:
            job.apply_pre_gui_output({"parameters": {"NoSuchParam": "value"}})

        logger_mock.warning.assert_called_once()
        assert "NoSuchParam" in logger_mock.warning.call_args.args[1]

    def test_mixed_output_routes_each_target(self):
        """A single call routes name, template param, and shared setting to their homes."""
        job = _make_job()

        job.apply_pre_gui_output(
            {
                "name": "MixedJob",
                "parameters": {
                    "ParamC": 42,  # template parameter
                    "deadline:maxRetriesPerTask": 5,  # shared setting
                },
            }
        )

        assert job.name == "MixedJob"
        param_c = job._find_extra_parameter("ParamC", "INT")
        assert param_c is not None and param_c.value == 42
        shared = {p["name"]: p["value"] for p in job.job_shared_settings.serialize()}
        assert shared["deadline:maxRetriesPerTask"] == 5


@patch.dict(sys.modules, {"deadline.client.ui.pre_gui_hooks": _pre_gui_hooks_stub()}, clear=False)
class TestDescriptionInTemplate:
    """The description set by a hook must reach the built OpenJD template."""

    def test_description_passed_into_built_template(self):
        """A hook description is placed into the dict handed to openjd's parse_model."""
        job = _make_job()
        job.apply_pre_gui_output({"description": "rendered by pipeline"})

        with (
            patch(_TEMPLATE_PATCH, return_value=fixtures.f_job_template_default()),
            patch(
                "deadline.unreal_submitter.unreal_open_job.unreal_open_job.parse_model"
            ) as parse_model_mock,
        ):
            job._build_template()

        template_dict = parse_model_mock.call_args.kwargs["obj"]
        assert template_dict["description"] == "rendered by pipeline"

    def test_no_description_omits_key_from_built_template(self):
        """With no hook description, no description key is emitted into the template dict."""
        job = _make_job()

        with (
            patch(_TEMPLATE_PATCH, return_value=fixtures.f_job_template_default()),
            patch(
                "deadline.unreal_submitter.unreal_open_job.unreal_open_job.parse_model"
            ) as parse_model_mock,
        ):
            job._build_template()

        template_dict = parse_model_mock.call_args.kwargs["obj"]
        assert "description" not in template_dict

    def test_description_survives_serialize_template(self):
        """serialize_template keeps the description key (it is in the ordered key list)."""
        template_json = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "JobA",
            "description": "kept",
            "parameterDefinitions": [],
            "steps": [{"name": "S"}],
        }
        template = MagicMock()
        template.json.return_value = __import__("json").dumps(template_json)

        ordered = UnrealOpenJob.serialize_template(template)

        assert ordered["description"] == "kept"
        # description is ordered right after name
        keys = list(ordered.keys())
        assert keys.index("description") == keys.index("name") + 1
